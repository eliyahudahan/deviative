"""
Deviative - Threshold derivation and chunked processing.

Handles:
- Vessel-level thresholds (COG, SOG)
- Pairwise processing with disk-based incremental writes
- Chunked pair analysis (memory-safe)
- Empirical threshold derivation
"""

import pandas as pd
import numpy as np

from .config import (
    COG_THRESHOLD_QUANTILE,
    SOG_THRESHOLD_QUANTILE,
    THRESHOLD_QUANTILE,
    MIN_VESSELS_PER_MINUTE,
    PAIRS_TEMP_PATH,
    CHUNK_SIZE,
)
from .helpers import calc_distances_for_minute, merge_pair_features
from .physics import compute_dcpa_tcpa_vectorized


# ==========================================
# Vessel-level thresholds
# ==========================================
def derive_vessel_thresholds(df):
    """Derive empirical thresholds for COG and SOG from the data."""
    threshold_cog = df['cog_diff'].abs().quantile(COG_THRESHOLD_QUANTILE)
    threshold_sog = df['sog_diff'].abs().quantile(SOG_THRESHOLD_QUANTILE)

    print(f"\nCOG anomaly threshold (95th percentile): {threshold_cog:.2f} degrees")
    print(f"SOG anomaly threshold (95th percentile): {threshold_sog:.2f} knots")

    return threshold_cog, threshold_sog


# ==========================================
# Pairwise processing (disk-based)
# ==========================================
def process_all_minutes(clean_features, output_path=PAIRS_TEMP_PATH):
    """
    Process all minutes, writing results incrementally to disk.
    Avoids holding all pairs in memory.
    """
    grouped = clean_features.groupby('base_date_time')
    total_groups = len(grouped)

    print(f"\nTotal minutes to process: {total_groups}")

    first_write = True
    total_pairs = 0

    for minute, df_minute in grouped:
        if len(df_minute) < MIN_VESSELS_PER_MINUTE:
            continue
        if (df_minute['sog'] < 0.5).all():
            continue

        vessel_features_minute = df_minute[[
            'mmsi', 'sog', 'cog', 'cog_diff', 'sog_diff',
            'lat_rad', 'lon_rad', 'length', 'vessel_type'
        ]].copy()

        # Ensure numeric types
        for col in ['sog', 'cog', 'cog_diff', 'sog_diff', 'lat_rad', 'lon_rad', 'length']:
            vessel_features_minute[col] = pd.to_numeric(
                vessel_features_minute[col], errors='coerce'
            )

        distances_df = calc_distances_for_minute(df_minute)
        result = merge_pair_features(distances_df, vessel_features_minute)
        result = compute_dcpa_tcpa_vectorized(result)
        result['base_date_time'] = minute

        # Write incrementally
        result.to_csv(
            output_path,
            mode='w' if first_write else 'a',
            header=first_write,
            index=False
        )
        first_write = False
        total_pairs += len(result)

        # Progress every 100K pairs
        if total_pairs % 100_000 < len(result):
            print(f"Progress: {total_pairs:,} pairs written so far")

    print(f"\n✅ Total pairs written: {total_pairs:,}")
    print(f"✅ File: {output_path}")

    return output_path


# ==========================================
# Chunked analysis (memory-safe)
# ==========================================
def analyze_pairs_in_chunks(pairs_path, chunk_size=CHUNK_SIZE):
    """
    Analyze pairs in chunks to avoid memory issues.
    Uses histograms to compute quantiles precisely without loading all data.

    Returns dict with:
        - total_valid
        - distance_threshold
        - tcpa_threshold
        - dcpa_threshold
        - histograms (for potential plotting)
    """
    # Histogram bins (fine resolution for accurate quantiles)
    dcpa_bins = np.linspace(0, 2.0, 1001)
    tcpa_bins = np.linspace(-1.0, 1.0, 1001)
    distance_bins = np.linspace(0, 50.0, 1001)

    dcpa_hist = np.zeros(len(dcpa_bins) - 1)
    tcpa_hist = np.zeros(len(tcpa_bins) - 1)
    distance_hist = np.zeros(len(distance_bins) - 1)

    total_valid = 0

    print(f"\n=== Analyzing pairs in chunks of {chunk_size:,} ===")

    for i, chunk in enumerate(pd.read_csv(pairs_path, chunksize=chunk_size)):
        # Coerce to numeric
        for col in ['DCPA', 'TCPA', 'distance_km']:
            chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

        chunk_valid = chunk.dropna(subset=['distance_km', 'TCPA', 'DCPA'])
        total_valid += len(chunk_valid)

        if len(chunk_valid) > 0:
            dcpa_hist += np.histogram(chunk_valid['DCPA'], bins=dcpa_bins)[0]
            tcpa_hist += np.histogram(chunk_valid['TCPA'], bins=tcpa_bins)[0]
            distance_hist += np.histogram(
                chunk_valid['distance_km'], bins=distance_bins
            )[0]

        print(f"  Chunk {i+1}: {len(chunk):,} rows, {len(chunk_valid):,} valid")

    # Compute quantiles from histograms
    def hist_quantile(hist, bins, q):
        cumsum = np.cumsum(hist)
        if cumsum[-1] == 0:
            return 0.0
        target = cumsum[-1] * q
        idx = np.searchsorted(cumsum, target)
        if idx >= len(bins) - 1:
            idx = len(bins) - 2
        return bins[idx]

    distance_threshold = max(hist_quantile(distance_hist, distance_bins, 0.05), 0.001)
    tcpa_threshold = max(hist_quantile(tcpa_hist, tcpa_bins, 0.05), 0.001)
    dcpa_threshold = max(hist_quantile(dcpa_hist, dcpa_bins, 0.05), 0.001)

    print(f"\n=== Results (from chunks) ===")
    print(f"Total valid pairs: {total_valid:,}")
    print(f"\nDistance threshold (5th percentile): {distance_threshold:.4f} km")
    print(f"TCPA threshold (5th percentile): {tcpa_threshold:.4f} hours")
    print(f"DCPA threshold (5th percentile): {dcpa_threshold:.4f} km")

    return {
        'total_valid': total_valid,
        'distance_threshold': distance_threshold,
        'tcpa_threshold': tcpa_threshold,
        'dcpa_threshold': dcpa_threshold,
        'dcpa_hist': dcpa_hist,
        'tcpa_hist': tcpa_hist,
        'distance_hist': distance_hist,
        'dcpa_bins': dcpa_bins,
        'tcpa_bins': tcpa_bins,
        'distance_bins': distance_bins,
    }


# ==========================================
# Pair-level thresholds (legacy, in-memory)
# ==========================================
def derive_pair_thresholds(all_results):
    """
    Derive empirical thresholds for distance, TCPA, DCPA from the data.
    Legacy in-memory version. Prefer analyze_pairs_in_chunks for large data.
    """
    valid = all_results.dropna(subset=['distance_km', 'TCPA', 'DCPA']).copy()

    print(f"\nValid pairs (with DCPA/TCPA): {len(valid):,}")

    distance_threshold = max(valid['distance_km'].quantile(THRESHOLD_QUANTILE), 0.001)
    tcpa_threshold = max(valid['TCPA'].quantile(THRESHOLD_QUANTILE), 0.001)
    dcpa_threshold = max(valid['DCPA'].quantile(THRESHOLD_QUANTILE), 0.001)

    print(f"\n=== Empirical Thresholds (from entire dataset) ===")
    print(f"Distance threshold (5th percentile): {distance_threshold:.4f} km")
    print(f"TCPA threshold (5th percentile): {tcpa_threshold:.4f} hours")
    print(f"DCPA threshold (5th percentile): {dcpa_threshold:.4f} km")

    return valid, distance_threshold, tcpa_threshold, dcpa_threshold