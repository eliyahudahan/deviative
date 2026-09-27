"""
Deviative - LSTM feasibility check.

Purpose:
- Determine whether the current dataset can support an LSTM Autoencoder.
- LSTM Autoencoder requires sequences per pair over time.
- Check if pairs persist continuously for at least `min_duration` minutes.

If yes: LSTM is feasible (scaffold provided).
If no:  LSTM not included in v1.0 (reason documented).

Reference:
- Olesen, K. V. (2023). Enhancing Situation Awareness of Maritime
  Surveillance Operators using Deep Learning based Abnormal 
  Maritime Behaviour Detection. DTU.

Note: Olesen used LSTM for per-vessel trajectories, not for pairs.
"""

import pandas as pd
import numpy as np

from .config import PAIRS_TEMP_PATH
from .physics import classify_movement_state


# ==========================================
# Pair continuity check
# ==========================================
def check_pair_continuity(valid_results, min_duration=30):
    """
    Check how many pairs (mmsi1, mmsi2) appear **continuously**
    for at least `min_duration` minutes.

    A pair is considered continuous if it appears in
    `min_duration` consecutive minutes without gaps.
    """
    print(f"\n=== PAIR CONTINUITY CHECK ===")
    print(f"Minimum duration: {min_duration} minutes")

    df = valid_results[['mmsi1', 'mmsi2', 'base_date_time']].copy()

    # Canonical pair key
    df['mmsi_a'] = df[['mmsi1', 'mmsi2']].min(axis=1)
    df['mmsi_b'] = df[['mmsi1', 'mmsi2']].max(axis=1)
    df['pair'] = list(zip(df['mmsi_a'], df['mmsi_b']))

    # Deduplicate: same pair at same minute = 1
    df = df[['pair', 'base_date_time']].drop_duplicates()

    total_unique = df['pair'].nunique()
    print(f"\nTotal unique pairs: {total_unique:,}")

    pair_counts = df.groupby('pair').size()
    raw_enough = (pair_counts >= min_duration).sum()
    print(f"Pairs appearing >= {min_duration} times (any minutes): {raw_enough:,}")

    # True continuity
    df = df.sort_values(['pair', 'base_date_time']).reset_index(drop=True)

    df['dt'] = df.groupby('pair')['base_date_time'].diff().dt.total_seconds() / 60

    df['new_run'] = (df['dt'].isna()) | (df['dt'] != 1)

    df['run_id'] = df.groupby('pair')['new_run'].cumsum()

    run_lengths = df.groupby(['pair', 'run_id']).size().reset_index(name='run_len')

    max_run_per_pair = run_lengths.groupby('pair')['run_len'].max()

    continuous_enough = (max_run_per_pair >= min_duration).sum()
    print(f"Pairs with continuous run >= {min_duration} minutes: {continuous_enough:,}")

    max_run = max_run_per_pair.max() if len(max_run_per_pair) > 0 else 0
    print(f"Max continuous run (any pair): {max_run} minutes")

    print(f"\n=== RUN LENGTH DISTRIBUTION ===")
    print(run_lengths['run_len'].describe())

    if len(max_run_per_pair) > 0:
        top_pairs = max_run_per_pair.sort_values(ascending=False).head(5)
        print(f"\n=== Top 5 pairs by continuous run ===")
        print(top_pairs.to_string())

    print(f"\n=== DECISION ===")
    if continuous_enough >= 100:
        print(f"✅ LSTM FEASIBLE: {continuous_enough:,} pairs persist for >= {min_duration} min.")
    elif continuous_enough > 0:
        print(f"⚠️ LIMITED: Only {continuous_enough:,} pairs persist for >= {min_duration} min.")
        print(f"   LSTM possible but on a small subset.")
    else:
        print(f"❌ NOT FEASIBLE: No pairs persist for >= {min_duration} min.")
        print(f"   LSTM not applicable to pair data.")
        print(f"   Reason documented for README.")

    return {
        'total_unique_pairs': total_unique,
        'pairs_with_enough_minutes': raw_enough,
        'pairs_with_continuous_run': continuous_enough,
        'max_run_minutes': max_run,
        'top_pairs': max_run_per_pair.head(5).to_dict() if len(max_run_per_pair) > 0 else {},
    }


# ==========================================
# Load sample (compute movement_state after load)
# ==========================================
def _load_sample(pairs_path, max_rows=2_000_000, chunk_size=500_000):
    """
    Load a sample of pairs from CSV.
    Computes movement_state after loading (not stored in CSV).
    """
    print(f"\n=== Loading sample for continuity check ===")

    # Pass 1: count total rows
    total_rows = 0
    for chunk in pd.read_csv(pairs_path, chunksize=chunk_size, usecols=['mmsi1']):
        total_rows += len(chunk)
    print(f"Total rows: {total_rows:,}")

    if total_rows == 0:
        return pd.DataFrame()

    fraction = min(1.0, max_rows / total_rows)
    print(f"Sampling fraction: {fraction:.4f}")

    # Pass 2: sample without movement_state
    chunks = []
    for chunk in pd.read_csv(
        pairs_path,
        chunksize=chunk_size,
        usecols=['mmsi1', 'mmsi2', 'base_date_time',
                 'sog1', 'sog2', 'cog1', 'cog2', 'tcpa_type']
    ):
        sample_size = int(len(chunk) * fraction)
        if sample_size > 0:
            chunks.append(chunk.sample(n=sample_size, random_state=42))

    valid = pd.concat(chunks, ignore_index=True)
    print(f"Loaded {len(valid):,} rows")

    # Convert datetime
    valid['base_date_time'] = pd.to_datetime(
        valid['base_date_time'],
        format='ISO8601'
    )

    # Compute movement_state
    print("Computing movement_state...")
    valid['movement_state'] = valid.apply(classify_movement_state, axis=1)

    # Filter to moving
    valid = valid[valid['movement_state'] == 'moving'].copy()
    print(f"Moving pairs: {len(valid):,}")

    return valid


# ==========================================
# Main
# ==========================================
def main():
    print("=" * 50)
    print("Deviative - LSTM Feasibility Check")
    print("=" * 50)

    valid = _load_sample(PAIRS_TEMP_PATH)

    if len(valid) == 0:
        print("No data to analyze.")
        return

    results = check_pair_continuity(valid, min_duration=30)

    print("\n" + "=" * 50)
    print("Continuity check complete.")
    print("=" * 50)


if __name__ == "__main__":
    main()