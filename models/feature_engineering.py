# ==========================================
# 1. Imports
# ==========================================
import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist

# ==========================================
# 2. Haversine function
# ==========================================
def haversine(x1, x2):
    lat1, lon1 = x1
    lat2, lon2 = x2

    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# ==========================================
# 3. Load data
# ==========================================
features = pd.read_csv('data/processed/features_2025-06-01.csv')
features['base_date_time'] = pd.to_datetime(features['base_date_time'])
features = features.sort_values(['mmsi', 'base_date_time']).reset_index(drop=True)

# ==========================================
# 4. Select the most dangerous row per duplicate group
# ==========================================
def select_risky_row(group):
    if len(group) == 1:
        return group

    group = group.copy()

    # COG diff with wrap-around within duplicate group
    group['cog_diff_dup'] = (group['cog'].diff() + 180) % 360 - 180
    group['sog_diff_dup'] = group['sog'].diff()

    # Risk = absolute changes
    group['risk_score'] = group['cog_diff_dup'].abs().fillna(0) + group['sog_diff_dup'].abs().fillna(0)

    # Keep the row with highest risk
    return group.loc[group['risk_score'].idxmax()].to_frame().T

# Identify duplicate groups
dup_mask = features.duplicated(subset=['mmsi', 'base_date_time'], keep=False)
dup_rows = features[dup_mask].copy()
single_rows = features[~dup_mask].copy()

print(f"Total rows: {len(features)}")
print(f"Rows in duplicate groups: {len(dup_rows)}")
print(f"Rows without duplicates: {len(single_rows)}")

# Process only duplicate groups
if len(dup_rows) > 0:
    clean_dup = dup_rows.groupby(['mmsi', 'base_date_time'], group_keys=False).apply(select_risky_row)
    clean_dup = clean_dup.reset_index(drop=True)
    clean_features = pd.concat([single_rows, clean_dup], ignore_index=True)
else:
    clean_features = single_rows.copy()

# Sort back
clean_features = clean_features.sort_values(['mmsi', 'base_date_time']).reset_index(drop=True)

print(f"Rows after duplicate selection: {len(clean_features)}")

# ==========================================
# 5. Vessel-level diffs (time series per vessel)
# ==========================================
clean_features['cog_diff'] = clean_features.groupby('mmsi')['cog'].diff()
clean_features['cog_diff'] = (clean_features['cog_diff'] + 180) % 360 - 180

clean_features['sog_diff'] = clean_features.groupby('mmsi')['sog'].diff()

# ==========================================
# 6. Empirical thresholds from data (only from data)
# ==========================================
threshold_cog = clean_features['cog_diff'].abs().quantile(0.95)
threshold_sog = clean_features['sog_diff'].abs().quantile(0.95)

print(f"\nCOG anomaly threshold (95th percentile): {threshold_cog:.2f} degrees")
print(f"SOG anomaly threshold (95th percentile): {threshold_sog:.2f} knots")

# ==========================================
# 7. Convert lat/lon to radians
# ==========================================
clean_features['lat_rad'] = np.radians(clean_features['latitude'].astype(float))
clean_features['lon_rad'] = np.radians(clean_features['longitude'].astype(float))

# ==========================================
# 8. Prepare vessel-level features (one row per MMSI)
# ==========================================
vessel_features = clean_features[['mmsi', 'sog', 'cog', 'cog_diff', 'sog_diff', 'lat_rad', 'lon_rad']].drop_duplicates(subset=['mmsi']).copy()

# ==========================================
# 9. Function to calculate distances for one minute
# ==========================================
def calc_distances_for_minute(df_minute):
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

# ==========================================
# 10. Function to merge pair distances with vessel features
# ==========================================
def merge_pair_features(distances_df, vessel_features):
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

# ==========================================
# 11. Function to compute DCPA/TCPA
# ==========================================
def compute_dcpa_tcpa(row):
    """
    Compute DCPA and TCPA for a pair of vessels.
    Expects: sog1, cog1, sog2, cog2, lat_rad_1, lon_rad_1, lat_rad_2, lon_rad_2
    """
    # If missing COG or SOG, cannot compute
    if pd.isna(row['cog1']) or pd.isna(row['cog2']) or pd.isna(row['sog1']) or pd.isna(row['sog2']):
        return pd.Series({'TCPA': np.nan, 'DCPA': np.nan})

    # Convert COG to radians
    cog1_rad = np.radians(row['cog1'])
    cog2_rad = np.radians(row['cog2'])

    # Velocity components for vessel 1
    vx1 = row['sog1'] * np.sin(cog1_rad)
    vy1 = row['sog1'] * np.cos(cog1_rad)

    # Velocity components for vessel 2
    vx2 = row['sog2'] * np.sin(cog2_rad)
    vy2 = row['sog2'] * np.cos(cog2_rad)

    # Relative velocity
    vx_rel = vx1 - vx2
    vy_rel = vy1 - vy2
    speed_rel_sq = vx_rel**2 + vy_rel**2

    # Relative position (in km)
    lat1_rad = row['lat_rad_1']
    lat2_rad = row['lat_rad_2']
    lon1_rad = row['lon_rad_1']
    lon2_rad = row['lon_rad_2']

    dx_km = (lon2_rad - lon1_rad) * 111.32 * np.cos((lat1_rad + lat2_rad) / 2)
    dy_km = (lat2_rad - lat1_rad) * 110.57

    if speed_rel_sq == 0:
        tcpa = 0
        dcpa = np.sqrt(dx_km**2 + dy_km**2)
    else:
        tcpa = -(dx_km * vx_rel + dy_km * vy_rel) / speed_rel_sq
        tcpa = max(tcpa, 0)

        x_cpa = dx_km + tcpa * vx_rel
        y_cpa = dy_km + tcpa * vy_rel
        dcpa = np.sqrt(x_cpa**2 + y_cpa**2)

    return pd.Series({'TCPA': tcpa, 'DCPA': dcpa})

# ==========================================
# 12. Process all minutes
# ==========================================
all_minutes = clean_features['base_date_time'].unique()
print(f"\nTotal minutes to process: {len(all_minutes)}")

all_pairs = []

for minute in all_minutes:
    df_minute = clean_features[clean_features['base_date_time'] == minute].copy()

    # Skip minutes with fewer than 2 vessels
    if len(df_minute) < 2:
        continue

    # Calculate pairwise distances
    distances_df = calc_distances_for_minute(df_minute)

    # Merge with vessel features
    result = merge_pair_features(distances_df, vessel_features)

    # Compute DCPA/TCPA
    result[['TCPA', 'DCPA']] = result.apply(compute_dcpa_tcpa, axis=1)

    # Add timestamp for reference
    result['base_date_time'] = minute

    all_pairs.append(result)

# Combine all minutes
if all_pairs:
    all_results = pd.concat(all_pairs, ignore_index=True)
else:
    all_results = pd.DataFrame()

print(f"\nTotal pairs across all minutes: {len(all_results)}")

# ==========================================
# 13. Derive empirical thresholds from data
# ==========================================
if len(all_results) > 0:
    # Remove rows with NaN in critical columns
    valid_results = all_results.dropna(subset=['distance_km', 'TCPA', 'DCPA']).copy()

    print(f"\nValid pairs (with DCPA/TCPA): {len(valid_results)}")

    distance_threshold = valid_results['distance_km'].quantile(0.05)
    tcpa_threshold = valid_results['TCPA'].quantile(0.05)
    dcpa_threshold = valid_results['DCPA'].quantile(0.05)

    # Ensure thresholds are not zero
    distance_threshold = max(distance_threshold, 0.001)
    tcpa_threshold = max(tcpa_threshold, 0.001)
    dcpa_threshold = max(dcpa_threshold, 0.001)

    print(f"\n=== Empirical Thresholds (from entire dataset) ===")
    print(f"Distance threshold (5th percentile): {distance_threshold:.4f} km")
    print(f"TCPA threshold (5th percentile): {tcpa_threshold:.4f} hours")
    print(f"DCPA threshold (5th percentile): {dcpa_threshold:.4f} km")

    # ==========================================
    # 14. Flag true anomalies
    # ==========================================
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

    # ==========================================
    # 15. Save results to CSV
    # ==========================================
    output_path = 'data/processed/encounter_results.csv'
    valid_results.to_csv(output_path, index=False)
    print(f"\n✅ Results saved to {output_path}")
else:
    print("No valid pairs to analyze.")