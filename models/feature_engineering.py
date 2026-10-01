"""
Deviative - Main pipeline.

This module orchestrates the encounter detection pipeline:

    1. Load AIS data (rounded to nearest minute)
    2. Remove duplicate rows (keep most complete per MMSI+minute)
    3. Compute vessel-level diffs (COG, SOG)
    4. Convert lat/lon to radians
    5. Process all minutes (write pairs incrementally to disk)
    6. Analyze pairs in chunks (memory-safe)
    7. Load sample into memory
    8. Compute movement_state per pair
    9. Flag anomalies (per-state thresholds)
   10. Run validation (Out-of-Time, Sanity, Manual, Anchorage)
   11. Additional diagnostics (Anchorage anomalies, hourly rate)
   12. Elbow analysis per movement state
   13. Vessel characteristics analysis
   14. Save results

Author: Eliyahu Dahan
Date: 2026-09-14 (refactored 2026-09-24, updated 2026-10-01)
"""

# ==========================================
# Imports
# ==========================================
import pandas as pd

from .config import (
    INPUT_PATH,
    OUTPUT_PATH,
    DCPA_THRESHOLD_MOVING,
    TCPA_THRESHOLD_MOVING,
    DISTANCE_THRESHOLD_MOVING,
)
from .data_io import (
    load_data,
    remove_duplicates,
    add_vessel_diffs,
    add_radians,
    save_results,
)
from .thresholds import (
    derive_vessel_thresholds,
    process_all_minutes,
    analyze_pairs_in_chunks,
)
from .physics import classify_movement_state
from .anomaly import flag_anomalies_per_state
from .elbow import (
    analyze_state_distributions,
    print_elbow_summary,
)
from .characteristics import check_vessel_characteristics
from .validation import (
    out_of_time_validation,
    sanity_check_thresholds,
    manual_inspection,
    check_anchorage_zone,
    analyze_anchorage_anomalies,
    anomaly_rate_by_hour,
)


# ==========================================
# Helper: Load sample of pairs into memory
# ==========================================
def load_pairs_sample(pairs_path, max_rows=2_000_000, chunk_size=500_000):
    """
    Load a representative sample of pairs from CSV into memory.

    Memory constraint: 8GB RAM - cannot load 14M rows at once.
    Target: 2M rows (~1.15M valid after dropping NaN).

    Sampling strategy: two-pass proportional across chunks.
        - Pass 1: count total rows (cheap - only reads mmsi1 column).
        - Pass 2: sample proportionally from each chunk.

    ASSUMPTION:
        Chunks have roughly uniform rows-per-minute.
        If hours are heavily skewed, results may be biased.
        Verification: see HOUR DISTRIBUTION in output.

    Args:
        pairs_path: path to pairs_temp.csv
        max_rows: maximum rows to load (~2M for 8GB RAM)
        chunk_size: rows per chunk (500K)

    Returns:
        DataFrame with sampled valid rows.
    """
    print(f"\n=== Loading pairs (proportional sample, max {max_rows:,} rows) ===")

    # ----------------------------------------
    # Pass 1: Count total rows
    # ----------------------------------------
    print("Pass 1: counting total rows...")
    total_rows = 0
    for chunk in pd.read_csv(pairs_path, chunksize=chunk_size, usecols=['mmsi1']):
        total_rows += len(chunk)
    print(f"Total rows in file: {total_rows:,}")

    if total_rows == 0:
        print("File is empty.")
        return pd.DataFrame()

    fraction = min(1.0, max_rows / total_rows)
    print(f"Sampling fraction: {fraction:.4f}")

    # ----------------------------------------
    # Pass 2: Sample proportionally from each chunk
    # ----------------------------------------
    print("Pass 2: sampling from each chunk...")
    chunks = []
    loaded = 0
    n_chunks = 0

    for i, chunk in enumerate(pd.read_csv(pairs_path, chunksize=chunk_size)):
        n_chunks = i + 1
        sample_size = int(len(chunk) * fraction)
        if sample_size > 0:
            sampled = chunk.sample(n=sample_size, random_state=42)
            chunks.append(sampled)
            loaded += len(sampled)

    valid = pd.concat(chunks, ignore_index=True)
    print(f"Loaded {len(valid):,} rows (from {n_chunks} chunks)")

    # ----------------------------------------
    # Convert base_date_time to datetime
    # ----------------------------------------
    valid['base_date_time'] = pd.to_datetime(
        valid['base_date_time'],
        format='ISO8601'
    )

    valid = valid.dropna(subset=['distance_km', 'TCPA', 'DCPA']).copy()
    print(f"Valid rows (with DCPA/TCPA): {len(valid):,}")

    # ----------------------------------------
    # TIME RANGE CHECK
    # ----------------------------------------
    print(f"\n=== TIME RANGE CHECK ===")
    print(f"Min:  {valid['base_date_time'].min()}")
    print(f"Max:  {valid['base_date_time'].max()}")
    print(f"Span: {valid['base_date_time'].max() - valid['base_date_time'].min()}")

    # ----------------------------------------
    # HOUR DISTRIBUTION
    # ----------------------------------------
    hours_dist = valid['base_date_time'].dt.hour.value_counts().sort_index()
    print(f"\n=== HOUR DISTRIBUTION ===")
    print(hours_dist.to_string())

    n_hours = len(hours_dist)
    print(f"\nUnique hours: {n_hours}")

    if n_hours > 0:
        min_count = hours_dist.min()
        max_count = hours_dist.max()
        ratio = max_count / min_count if min_count > 0 else float('inf')
        print(f"Min count: {min_count:,}")
        print(f"Max count: {max_count:,}")
        print(f"Max/Min ratio: {ratio:.2f}")

        if ratio < 3.0:
            print("✅ Distribution is reasonably uniform.")
        elif ratio < 10.0:
            print("⚠️ Some bias - check hour distribution manually.")
        else:
            print("❌ Strong bias - consider stratified sampling.")

    return valid


# ==========================================
# Main pipeline
# ==========================================
def main():
    print("=" * 50)
    print("Deviative - Encounter Detection Pipeline")
    print("=" * 50)

    # ----------------------------------------
    # Step 1: Load data
    # ----------------------------------------
    features = load_data(INPUT_PATH)

    # ----------------------------------------
    # Step 2: Remove duplicates (keep most complete)
    # ----------------------------------------
    clean_features = remove_duplicates(features)

    # ----------------------------------------
    # Step 3: Vessel-level diffs
    # ----------------------------------------
    clean_features = add_vessel_diffs(clean_features)

    print(f"\nlength in clean_features: {'length' in clean_features.columns}")
    print(f"vessel_type in clean_features: {'vessel_type' in clean_features.columns}")

    # ----------------------------------------
    # Step 4: Vessel-level empirical thresholds
    # ----------------------------------------
    derive_vessel_thresholds(clean_features)

    # ----------------------------------------
    # Step 5: Convert lat/lon to radians
    # ----------------------------------------
    clean_features = add_radians(clean_features)

    # ----------------------------------------
    # Step 6: Process all minutes (write to disk)
    # ----------------------------------------
    pairs_path = process_all_minutes(clean_features)

    if pairs_path is None:
        print("No valid pairs to analyze.")
        return

    # ----------------------------------------
    # Step 7: Analyze pairs in chunks
    # ----------------------------------------
    print("\n" + "=" * 70)
    print("PAIRS ANALYSIS (CHUNKED)")
    print("=" * 70)

    analysis = analyze_pairs_in_chunks(pairs_path)
    print(f"\n✅ Analysis complete. Total valid pairs: {analysis['total_valid']:,}")

    # ----------------------------------------
    # Step 8: Load sample into memory
    # ----------------------------------------
    valid = load_pairs_sample(pairs_path)

    # ----------------------------------------
    # Step 9: Compute movement_state
    # ----------------------------------------
    print("\n=== Computing movement_state ===")
    valid['movement_state'] = valid.apply(classify_movement_state, axis=1)
    print("Movement state distribution:")
    print(valid['movement_state'].value_counts())

    # ----------------------------------------
    # Step 10: Flag anomalies (per-state)
    # ----------------------------------------
    valid = flag_anomalies_per_state(valid)

    # ----------------------------------------
    # Step 11: Out-of-Time Validation
    # ----------------------------------------
    out_of_time_validation(
        valid,
        dcpa_th=DCPA_THRESHOLD_MOVING,
        tcpa_th=TCPA_THRESHOLD_MOVING,
        distance_th=DISTANCE_THRESHOLD_MOVING,
    )

    # ----------------------------------------
    # Step 12: Sanity Check
    # ----------------------------------------
    sanity_check_thresholds(
        valid,
        dcpa_new=DCPA_THRESHOLD_MOVING,
        tcpa_new=TCPA_THRESHOLD_MOVING,
        distance_new=DISTANCE_THRESHOLD_MOVING,
    )

    # ----------------------------------------
    # Step 13: Manual inspection
    # ----------------------------------------
    manual_inspection(
        valid,
        dcpa_th=DCPA_THRESHOLD_MOVING,
        tcpa_th=TCPA_THRESHOLD_MOVING,
        distance_th=DISTANCE_THRESHOLD_MOVING,
        n_sample=15,
    )

    # ----------------------------------------
    # Step 14: Anchorage B check
    # ----------------------------------------
    check_anchorage_zone(
        valid,
        dcpa_th=DCPA_THRESHOLD_MOVING,
        tcpa_th=TCPA_THRESHOLD_MOVING,
        distance_th=DISTANCE_THRESHOLD_MOVING,
    )

    # ----------------------------------------
    # Step 15: Additional diagnostics
    # ----------------------------------------
    analyze_anchorage_anomalies(
        valid,
        dcpa_th=DCPA_THRESHOLD_MOVING,
        tcpa_th=TCPA_THRESHOLD_MOVING,
        distance_th=DISTANCE_THRESHOLD_MOVING,
    )

    anomaly_rate_by_hour(
        valid,
        dcpa_th=DCPA_THRESHOLD_MOVING,
        tcpa_th=TCPA_THRESHOLD_MOVING,
        distance_th=DISTANCE_THRESHOLD_MOVING,
    )

    # ----------------------------------------
    # Step 16: Elbow analysis per movement state
    # ----------------------------------------
    print("\n" + "=" * 70)
    print("ELBOW ANALYSIS PER MOVEMENT STATE")
    print("=" * 70)

    elbow_results = analyze_state_distributions(valid)
    print_elbow_summary(elbow_results)

    # ----------------------------------------
    # Step 17: Vessel characteristics
    # ----------------------------------------
    check_vessel_characteristics(valid)

    # ----------------------------------------
    # Step 18: Save results
    # ----------------------------------------
    save_results(valid, OUTPUT_PATH)

    print("\n" + "=" * 50)
    print("Pipeline complete.")
    print("=" * 50)


if __name__ == "__main__":
    main()