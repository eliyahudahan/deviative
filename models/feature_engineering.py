# ==========================================
# Deviative - Feature Engineering & Encounter Detection
# ==========================================
"""
This module processes AIS data to detect potentially dangerous vessel encounters.

Pipeline:
    1. Load data
    2. Remove duplicate rows (keep most dangerous per MMSI+timestamp)
    3. Compute vessel-level diffs (COG, SOG)
    4. Derive empirical thresholds from data
    5. Compute pairwise distances (Haversine)
    6. Compute DCPA/TCPA for each pair
    7. Flag anomalies based on empirical thresholds
    8. Save results

Author: Eliyahu Dahan
Date: 2026-09-14
"""

# ==========================================
# 1. Imports
# ==========================================
import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist

# ==========================================
# 2. Constants
# ==========================================
INPUT_PATH = 'data/processed/features_2025-06-01.csv'
OUTPUT_PATH = 'data/processed/encounter_results.csv'

EARTH_RADIUS_KM = 6371.0
KM_PER_DEG_LAT = 110.57
KM_PER_DEG_LON = 111.32

THRESHOLD_QUANTILE = 0.05
COG_THRESHOLD_QUANTILE = 0.95
SOG_THRESHOLD_QUANTILE = 0.95

MIN_VESSELS_PER_MINUTE = 2


# ==========================================
# 3. Helper Functions
# ==========================================
def haversine(x1, x2):
    """
    Compute Haversine distance (in km) between two (lat, lon) points.

    Args:
        x1, x2: tuples of (lat_rad, lon_rad) in radians

    Returns:
        Distance in kilometers
    """
    lat1, lon1 = x1
    lat2, lon2 = x2

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_KM * c


def select_risky_row(group):
    """
    Within a duplicate group (same MMSI + timestamp),
    select the row with the highest risk score (largest COG/SOG change).
    """
    if len(group) == 1:
        return group

    group = group.copy()

    group['cog_diff_dup'] = (group['cog'].diff() + 180) % 360 - 180
    group['sog_diff_dup'] = group['sog'].diff()

    group['risk_score'] = (
        group['cog_diff_dup'].abs().fillna(0) +
        group['sog_diff_dup'].abs().fillna(0)
    )

    return group.loc[group['risk_score'].idxmax()].to_frame().T


def calc_distances_for_minute(df_minute):
    """
    Compute pairwise Haversine distances for all vessels in a single minute.

    Returns:
        DataFrame with columns: mmsi1, mmsi2, distance_km
    """
    coords = df_minute[['lat_rad', 'lon_rad']].values
    mmsi_list = df_minute['mmsi'].values

    distances = pdist(coords, metric=haversine)

    n = len(mmsi_list)
    results = []
    for i in range(n):
        for j in range(i + 1, n):
            idx = n * i - i * (i + 1) // 2 + j - i - 1
            results.append({
                'mmsi1': mmsi_list[i],
                'mmsi2': mmsi_list[j],
                'distance_km': distances[idx]
            })
    return pd.DataFrame(results)


def merge_pair_features(distances_df, vessel_features):
    """
    Merge pairwise distances with vessel features for both vessels.
    """
    result = pd.merge(
        distances_df,
        vessel_features.rename(columns={
            'mmsi': 'mmsi1',
            'sog': 'sog1',
            'cog': 'cog1',
            'cog_diff': 'cog_diff_1',
            'sog_diff': 'sog_diff_1',
            'lat_rad': 'lat_rad_1',
            'lon_rad': 'lon_rad_1'
        }),
        on='mmsi1',
        how='left'
    )

    result = pd.merge(
        result,
        vessel_features.rename(columns={
            'mmsi': 'mmsi2',
            'sog': 'sog2',
            'cog': 'cog2',
            'cog_diff': 'cog_diff_2',
            'sog_diff': 'sog_diff_2',
            'lat_rad': 'lat_rad_2',
            'lon_rad': 'lon_rad_2'
        }),
        on='mmsi2',
        how='left'
    )

    return result


def compute_dcpa_tcpa(row):
    """
    Compute DCPA (Distance to Closest Point of Approach) and
    TCPA (Time to Closest Point of Approach) for a pair of vessels.

    Returns:
        pd.Series with TCPA (hours) and DCPA (km)
    """
    if (pd.isna(row['cog1']) or pd.isna(row['cog2']) or
            pd.isna(row['sog1']) or pd.isna(row['sog2'])):
        return pd.Series({'TCPA': np.nan, 'DCPA': np.nan})

    cog1_rad = np.radians(row['cog1'])
    cog2_rad = np.radians(row['cog2'])

    vx1 = row['sog1'] * np.sin(cog1_rad)
    vy1 = row['sog1'] * np.cos(cog1_rad)
    vx2 = row['sog2'] * np.sin(cog2_rad)
    vy2 = row['sog2'] * np.cos(cog2_rad)

    vx_rel = vx1 - vx2
    vy_rel = vy1 - vy2
    speed_rel_sq = vx_rel ** 2 + vy_rel ** 2

    lat1_rad = row['lat_rad_1']
    lat2_rad = row['lat_rad_2']
    lon1_rad = row['lon_rad_1']
    lon2_rad = row['lon_rad_2']

    dx_km = (lon2_rad - lon1_rad) * KM_PER_DEG_LON * np.cos((lat1_rad + lat2_rad) / 2)
    dy_km = (lat2_rad - lat1_rad) * KM_PER_DEG_LAT

    if speed_rel_sq == 0:
        return pd.Series({'TCPA': 0, 'DCPA': np.sqrt(dx_km ** 2 + dy_km ** 2)})

    tcpa = -(dx_km * vx_rel + dy_km * vy_rel) / speed_rel_sq
    tcpa = max(tcpa, 0)

    x_cpa = dx_km + tcpa * vx_rel
    y_cpa = dy_km + tcpa * vy_rel
    dcpa = np.sqrt(x_cpa ** 2 + y_cpa ** 2)

    return pd.Series({'TCPA': tcpa, 'DCPA': dcpa})


# ==========================================
# 4. Pipeline Functions
# ==========================================
def load_data(path):
    """Load AIS features CSV and sort by vessel and time."""
    df = pd.read_csv(path)
    df['base_date_time'] = pd.to_datetime(df['base_date_time'])
    df = df.sort_values(['mmsi', 'base_date_time']).reset_index(drop=True)
    return df


def remove_duplicates(features):
    """
    Remove duplicate rows for the same MMSI+timestamp.
    Keep the row with the highest risk score per group.
    """
    dup_mask = features.duplicated(subset=['mmsi', 'base_date_time'], keep=False)
    dup_rows = features[dup_mask].copy()
    single_rows = features[~dup_mask].copy()

    print(f"Total rows: {len(features)}")
    print(f"Rows in duplicate groups: {len(dup_rows)}")
    print(f"Rows without duplicates: {len(single_rows)}")

    if len(dup_rows) > 0:
        clean_dup = dup_rows.groupby(
            ['mmsi', 'base_date_time'], group_keys=False
        ).apply(select_risky_row).reset_index(drop=True)
        clean_features = pd.concat([single_rows, clean_dup], ignore_index=True)
    else:
        clean_features = single_rows.copy()

    clean_features = clean_features.sort_values(
        ['mmsi', 'base_date_time']
    ).reset_index(drop=True)

    print(f"Rows after duplicate selection: {len(clean_features)}")
    return clean_features


def add_vessel_diffs(df):
    """Add COG and SOG differences per vessel (time series)."""
    df['cog_diff'] = df.groupby('mmsi')['cog'].diff()
    df['cog_diff'] = (df['cog_diff'] + 180) % 360 - 180
    df['sog_diff'] = df.groupby('mmsi')['sog'].diff()
    return df


def add_radians(df):
    """Convert latitude and longitude to radians."""
    df['lat_rad'] = np.radians(df['latitude'].astype(float))
    df['lon_rad'] = np.radians(df['longitude'].astype(float))
    return df


def derive_vessel_thresholds(df):
    """Derive empirical thresholds for COG and SOG from the data."""
    threshold_cog = df['cog_diff'].abs().quantile(COG_THRESHOLD_QUANTILE)
    threshold_sog = df['sog_diff'].abs().quantile(SOG_THRESHOLD_QUANTILE)

    print(f"\nCOG anomaly threshold (95th percentile): {threshold_cog:.2f} degrees")
    print(f"SOG anomaly threshold (95th percentile): {threshold_sog:.2f} knots")

    return threshold_cog, threshold_sog


def prepare_vessel_features(df):
    """Extract one row per MMSI with the features needed for pair merging."""
    return df[[
        'mmsi', 'sog', 'cog', 'cog_diff', 'sog_diff', 'lat_rad', 'lon_rad'
    ]].drop_duplicates(subset=['mmsi']).copy()


def process_all_minutes(clean_features, vessel_features):
    """
    Process all minutes using groupby (fast, no O(N*M) filtering).
    Returns a DataFrame with all pairs and their DCPA/TCPA.
    """
    # Group by timestamp - much faster than filtering inside a loop
    grouped = clean_features.groupby('base_date_time')

    all_pairs = []
    total_groups = len(grouped)

    print(f"\nTotal minutes to process: {total_groups}")

    for minute, df_minute in grouped:
        if len(df_minute) < MIN_VESSELS_PER_MINUTE:
            continue

        distances_df = calc_distances_for_minute(df_minute)
        result = merge_pair_features(distances_df, vessel_features)
        result[['TCPA', 'DCPA']] = result.apply(compute_dcpa_tcpa, axis=1)
        result['base_date_time'] = minute

        all_pairs.append(result)

    if not all_pairs:
        return pd.DataFrame()

    return pd.concat(all_pairs, ignore_index=True)


def derive_pair_thresholds(all_results):
    """Derive empirical thresholds for distance, TCPA, DCPA from the data."""
    valid = all_results.dropna(subset=['distance_km', 'TCPA', 'DCPA']).copy()

    print(f"\nValid pairs (with DCPA/TCPA): {len(valid)}")

    distance_threshold = max(valid['distance_km'].quantile(THRESHOLD_QUANTILE), 0.001)
    tcpa_threshold = max(valid['TCPA'].quantile(THRESHOLD_QUANTILE), 0.001)
    dcpa_threshold = max(valid['DCPA'].quantile(THRESHOLD_QUANTILE), 0.001)

    print(f"\n=== Empirical Thresholds (from entire dataset) ===")
    print(f"Distance threshold (5th percentile): {distance_threshold:.4f} km")
    print(f"TCPA threshold (5th percentile): {tcpa_threshold:.4f} hours")
    print(f"DCPA threshold (5th percentile): {dcpa_threshold:.4f} km")

    return valid, distance_threshold, tcpa_threshold, dcpa_threshold


def flag_anomalies(valid_results, distance_threshold, tcpa_threshold, dcpa_threshold):
    """Flag true anomalies based on empirical thresholds."""
    valid_results['anomaly_dcpa_tcpa'] = (
        (valid_results['DCPA'] < dcpa_threshold) &
        (valid_results['TCPA'] < tcpa_threshold) &
        (valid_results['distance_km'] < distance_threshold)
    )

    total_anomalies = valid_results['anomaly_dcpa_tcpa'].sum()
    print(f"\n=== Total anomalies detected: {total_anomalies} ===")

    if total_anomalies > 0:
        print("\n=== Sample Anomalies ===")
        print(valid_results[valid_results['anomaly_dcpa_tcpa']][
            ['base_date_time', 'mmsi1', 'mmsi2', 'distance_km', 'TCPA', 'DCPA']
        ].head(10))

    return valid_results


def save_results(df, path):
    """Save final results to CSV."""
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")


# ==========================================
# 5. Main
# ==========================================
def main():
    print("=" * 50)
    print("Deviative - Encounter Detection Pipeline")
    print("=" * 50)

    # Step 1: Load
    features = load_data(INPUT_PATH)

    # Step 2: Remove duplicates
    clean_features = remove_duplicates(features)

    # Step 3: Vessel-level diffs
    clean_features = add_vessel_diffs(clean_features)

    # Step 4: Empirical thresholds (vessel-level)
    derive_vessel_thresholds(clean_features)

    # Step 5: Convert to radians
    clean_features = add_radians(clean_features)

    # Step 6: Prepare vessel features
    vessel_features = prepare_vessel_features(clean_features)

    # Step 7: Process all minutes
    all_results = process_all_minutes(clean_features, vessel_features)
    print(f"\nTotal pairs across all minutes: {len(all_results)}")

    if len(all_results) == 0:
        print("No valid pairs to analyze.")
        return

    # Step 8: Derive pair-level thresholds
    valid, dist_th, tcpa_th, dcpa_th = derive_pair_thresholds(all_results)

    # Step 9: Flag anomalies
    valid = flag_anomalies(valid, dist_th, tcpa_th, dcpa_th)

    # Step 10: Save
    save_results(valid, OUTPUT_PATH)

    print("\n" + "=" * 50)
    print("Pipeline complete.")
    print("=" * 50)


if __name__ == "__main__":
    main()