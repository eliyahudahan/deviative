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
KNOT_TO_KMH = 1.852  # 1 knot = 1.852 km/h

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
    select the row with the highest normalized risk score.

    Risk = normalized COG change + normalized SOG change.
    Normalization uses fixed reference values (not derived from data yet):
        - COG_REF = 90° (half circle)
        - SOG_REF = 5 knots (a reasonable maneuver)

    Note: reference values will be replaced by empirical thresholds
    in a later phase once the full pipeline is validated.
    """
    if len(group) == 1:
        return group

    # Group is already sorted by time (from prior sort in load_data)
    group = group.copy()

    # COG diff with wrap-around
    group['cog_diff_dup'] = (group['cog'].diff() + 180) % 360 - 180
    group['sog_diff_dup'] = group['sog'].diff()

    # Normalize each to a comparable 0-1 scale
    COG_REF = 90.0   # degrees - half circle
    SOG_REF = 5.0    # knots - reasonable maneuver

    cog_norm = (group['cog_diff_dup'].abs().fillna(0) / COG_REF).clip(upper=1.0)
    sog_norm = (group['sog_diff_dup'].abs().fillna(0) / SOG_REF).clip(upper=1.0)

    group['risk_score'] = cog_norm + sog_norm

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
    Includes sog, cog, diffs, radians, length, and vessel_type.
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
            'lon_rad': 'lon_rad_1',
            'length': 'length_1',
            'vessel_type': 'vessel_type_1'
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
            'lon_rad': 'lon_rad_2',
            'length': 'length_2',
            'vessel_type': 'vessel_type_2'
        }),
        on='mmsi2',
        how='left'
    )

    return result


def compute_dcpa_tcpa(row):
    """
    Compute DCPA (Distance to Closest Point of Approach) and
    TCPA (Time to Closest Point of Approach) for a pair of vessels.

    Units:
        - SOG is converted from knots to km/h before velocity calculation.
        - DCPA is in kilometers.
        - TCPA is in hours.
        - Sign convention: TCPA > 0 (approaching), < 0 (receding), = 0 (at CPA).

    tcpa_type:
        - 'dynamic' : relative motion exists (speed_rel_sq > EPS)
        - 'static'  : no relative motion (speed_rel_sq <= EPS)

    Returns:
        pd.Series with TCPA (hours), DCPA (km), and tcpa_type (str)
    """
    # Guard: missing critical inputs
    if (pd.isna(row['cog1']) or pd.isna(row['cog2']) or
            pd.isna(row['sog1']) or pd.isna(row['sog2']) or
            pd.isna(row['lat_rad_1']) or pd.isna(row['lat_rad_2']) or
            pd.isna(row['lon_rad_1']) or pd.isna(row['lon_rad_2'])):
        return pd.Series({'TCPA': np.nan, 'DCPA': np.nan, 'tcpa_type': 'unknown'})

    cog1_rad = np.radians(row['cog1'])
    cog2_rad = np.radians(row['cog2'])

    # Convert SOG from knots to km/h to match distance units
    sog1_kmh = row['sog1'] * KNOT_TO_KMH
    sog2_kmh = row['sog2'] * KNOT_TO_KMH

    vx1 = sog1_kmh * np.sin(cog1_rad)
    vy1 = sog1_kmh * np.cos(cog1_rad)
    vx2 = sog2_kmh * np.sin(cog2_rad)
    vy2 = sog2_kmh * np.cos(cog2_rad)

    vx_rel = vx1 - vx2
    vy_rel = vy1 - vy2
    speed_rel_sq = vx_rel ** 2 + vy_rel ** 2

    lat1_rad = row['lat_rad_1']
    lat2_rad = row['lat_rad_2']
    lon1_rad = row['lon_rad_1']
    lon2_rad = row['lon_rad_2']

    dx_km = (lon2_rad - lon1_rad) * KM_PER_DEG_LON * np.cos((lat1_rad + lat2_rad) / 2)
    dy_km = (lat2_rad - lat1_rad) * KM_PER_DEG_LAT

    # Guard: no relative motion (both vessels moving identically)
    EPS = 1e-9
    if speed_rel_sq < EPS:
        return pd.Series({
            'TCPA': 0,
            'DCPA': np.sqrt(dx_km ** 2 + dy_km ** 2),
            'tcpa_type': 'static'
        })

    tcpa = -(dx_km * vx_rel + dy_km * vy_rel) / speed_rel_sq
    # Keep sign: positive = approaching, negative = receding, zero = at CPA

    x_cpa = dx_km + tcpa * vx_rel
    y_cpa = dy_km + tcpa * vy_rel
    dcpa = np.sqrt(x_cpa ** 2 + y_cpa ** 2)

    return pd.Series({
        'TCPA': tcpa,
        'DCPA': dcpa,
        'tcpa_type': 'dynamic'
    })

def compute_dcpa_tcpa_vectorized(df):
    """
    Vectorized version of compute_dcpa_tcpa.
    Operates on entire DataFrame columns at once.
    """
    # Guard: filter valid rows
    valid_mask = (
        df['cog1'].notna() & df['cog2'].notna() &
        df['sog1'].notna() & df['sog2'].notna() &
        df['lat_rad_1'].notna() & df['lat_rad_2'].notna() &
        df['lon_rad_1'].notna() & df['lon_rad_2'].notna()
    )

    df['TCPA'] = np.nan
    df['DCPA'] = np.nan
    df['tcpa_type'] = 'unknown'

    if valid_mask.sum() == 0:
        return df

    sub = df[valid_mask]

    cog1_rad = np.radians(sub['cog1'].astype(float).values)
    cog2_rad = np.radians(sub['cog2'].astype(float).values)

    sog1_kmh = sub['sog1'].astype(float).values * KNOT_TO_KMH
    sog2_kmh = sub['sog2'].astype(float).values * KNOT_TO_KMH

    vx1 = sog1_kmh * np.sin(cog1_rad)
    vy1 = sog1_kmh * np.cos(cog1_rad)
    vx2 = sog2_kmh * np.sin(cog2_rad)
    vy2 = sog2_kmh * np.cos(cog2_rad)

    vx_rel = vx1 - vx2
    vy_rel = vy1 - vy2
    speed_rel_sq = vx_rel ** 2 + vy_rel ** 2

    lat1_rad = sub['lat_rad_1'].values
    lat2_rad = sub['lat_rad_2'].values
    lon1_rad = sub['lon_rad_1'].values
    lon2_rad = sub['lon_rad_2'].values

    dx_km = (lon2_rad - lon1_rad) * KM_PER_DEG_LON * np.cos((lat1_rad + lat2_rad) / 2)
    dy_km = (lat2_rad - lat1_rad) * KM_PER_DEG_LAT

    EPS = 1e-9
    static_mask = speed_rel_sq < EPS
    dynamic_mask = ~static_mask

    tcpa_arr = np.zeros(len(sub))
    dcpa_arr = np.zeros(len(sub))
    type_arr = np.empty(len(sub), dtype=object)

    if static_mask.sum() > 0:
        dcpa_arr[static_mask] = np.sqrt(
            dx_km[static_mask] ** 2 + dy_km[static_mask] ** 2
        )
        type_arr[static_mask] = 'static'

    if dynamic_mask.sum() > 0:
        tcpa_dyn = -(
            dx_km[dynamic_mask] * vx_rel[dynamic_mask] +
            dy_km[dynamic_mask] * vy_rel[dynamic_mask]
        ) / speed_rel_sq[dynamic_mask]

        x_cpa = dx_km[dynamic_mask] + tcpa_dyn * vx_rel[dynamic_mask]
        y_cpa = dy_km[dynamic_mask] + tcpa_dyn * vy_rel[dynamic_mask]
        dcpa_dyn = np.sqrt(x_cpa ** 2 + y_cpa ** 2)

        tcpa_arr[dynamic_mask] = tcpa_dyn
        dcpa_arr[dynamic_mask] = dcpa_dyn
        type_arr[dynamic_mask] = 'dynamic'

    df.loc[valid_mask, 'TCPA'] = tcpa_arr
    df.loc[valid_mask, 'DCPA'] = dcpa_arr
    df.loc[valid_mask, 'tcpa_type'] = type_arr

    return df

# ==========================================
# 4. Pipeline Functions
# ==========================================
def load_data(path):
    """Load AIS features CSV and sort by vessel and time."""
    df = pd.read_csv(path)
    df['base_date_time'] = pd.to_datetime(df['base_date_time'])
    
    # Round to nearest minute (remove seconds)
    df['base_date_time'] = df['base_date_time'].dt.floor('min')
    
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

def classify_movement_state(row):
    """
    Classify a vessel pair into one of these states:
        - 'anchored' : both vessels nearly stationary (sog < 0.5)
        - 'towing'   : similar speed & course, stable distance
        - 'static'   : no relative motion (tcpa_type == 'static')
        - 'moving'   : otherwise (normal motion)
        - 'unknown'  : missing data or ambiguous
    """
    sog1, sog2 = row['sog1'], row['sog2']
    cog1, cog2 = row['cog1'], row['cog2']
    tcpa_type = row['tcpa_type']

    if pd.isna(sog1) or pd.isna(sog2) or pd.isna(cog1) or pd.isna(cog2):
        return 'unknown'

    # Anchored: both nearly stationary
    if sog1 < 0.5 and sog2 < 0.5:
        return 'anchored'

    # Static: no relative motion (from physics)
    if tcpa_type == 'static':
        return 'static'

    # Towing: similar speed & course
    if abs(sog1 - sog2) < 0.5 and abs((cog1 - cog2 + 180) % 360 - 180) < 10:
        return 'towing'

    return 'moving'

def process_all_minutes(clean_features, output_path='data/processed/pairs_temp.csv'):
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

        # Progress every 100 minutes
        if total_groups > 0 and (total_pairs % 100 == 0):
            print(f"Progress: {total_pairs} pairs written so far")

    print(f"\n✅ Total pairs written: {total_pairs}")
    print(f"✅ File: {output_path}")

    # Return path instead of DataFrame (avoid loading 14M rows into memory)
    return output_path

def analyze_pairs_in_chunks(pairs_path, chunk_size=1_000_000):
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
        # Coerce to numeric (handles any mixed types from CSV)
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


        # Step 8: Load pairs in chunks (sampled to fit memory)
    print("\n=== Loading pairs (sampled) ===")
    
    chunks = []
    max_rows = 2_000_000  # 2M rows – fits in ~1GB RAM
    loaded = 0
    
    for chunk in pd.read_csv(pairs_path, chunksize=500_000):
        # Take a portion from each chunk to stay under max_rows
        remaining = max_rows - loaded
        if remaining <= 0:
            break
        take = min(len(chunk), remaining)
        chunks.append(chunk.head(take))
        loaded += take
    
    valid = pd.concat(chunks, ignore_index=True)
    print(f"Loaded {len(valid):,} rows (sampled)")
    
    # Drop rows with missing critical values
    valid = valid.dropna(subset=['distance_km', 'TCPA', 'DCPA']).copy()
    print(f"Valid rows (with DCPA/TCPA): {len(valid):,}")
    
    # Add movement_state (compute from tcpa_type)
    valid['movement_state'] = valid.apply(classify_movement_state, axis=1)

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
        (valid_results['TCPA'] >= 0) &                # approaching only
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

def flag_anomalies_per_state(valid_results,
                              dcpa_moving=0.1982,
                              tcpa_moving=0.0293,
                              distance_moving=1.0):
    """
    Flag anomalies using per-state thresholds.

    Only 'moving' state is considered for real anomalies.
    Thresholds are derived from 2nd Derivative on the 'moving' subset:
        - DCPA: 0.1982 km (198 meters)
        - TCPA: 0.0293 hours (1.76 minutes)
        - Distance: 1.0 km (safety distance guard)

    'anchored' and 'towing' are excluded (not real encounters).

    Args:
        valid_results: DataFrame with movement_state, DCPA, TCPA, distance_km
        dcpa_moving: DCPA threshold for moving state (2nd derivative)
        tcpa_moving: TCPA threshold for moving state (2nd derivative)
        distance_moving: distance threshold for moving state

    Returns:
        DataFrame with 'anomaly_dcpa_tcpa' column
    """
    valid_results['anomaly_dcpa_tcpa'] = (
        (valid_results['movement_state'] == 'moving') &
        (valid_results['DCPA'] < dcpa_moving) &
        (valid_results['TCPA'] >= 0) &
        (valid_results['TCPA'] < tcpa_moving) &
        (valid_results['distance_km'] < distance_moving)
    )

    total = valid_results['anomaly_dcpa_tcpa'].sum()
    print(f"\n=== Anomalies (moving only, 2nd derivative thresholds) ===")
    print(f"DCPA threshold: {dcpa_moving:.4f} km ({dcpa_moving*1000:.1f} m)")
    print(f"TCPA threshold: {tcpa_moving:.4f} hours ({tcpa_moving*60:.2f} min)")
    print(f"Distance threshold: {distance_moving:.4f} km")
    print(f"\nTotal anomalies: {total:,}")

    print("\n=== Breakdown by movement_state ===")
    print(valid_results.groupby('movement_state')['anomaly_dcpa_tcpa'].sum())

    if total > 0:
        print("\n=== Sample Anomalies (moving only) ===")
        print(valid_results[valid_results['anomaly_dcpa_tcpa']][
            ['base_date_time', 'mmsi1', 'mmsi2', 'distance_km', 'TCPA', 'DCPA', 'movement_state']
        ].head(10))

    return valid_results

def save_results(df, path):
    """Save final results to CSV."""
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")

# ==========================================
# 6. Elbow Method – Three Approaches
# ==========================================
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (for saving figures)
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from scipy.signal import argrelextrema

try:
    from kneed import KneeLocator
    KNEED_AVAILABLE = True
except ImportError:
    KNEED_AVAILABLE = False
    print("Warning: kneed library not installed. Kneedle will be skipped.")


def compute_kde(data, num_points=1000, max_samples=10000):
    """
    Compute KDE for a 1D data series.
    Downsamples if data is too large (> max_samples) for speed.
    Returns (x_grid, y_grid) for plotting.
    """
    data = pd.to_numeric(data, errors='coerce').dropna().values
    if len(data) < 10:
        return None, None

    # Downsample for speed if needed
    if len(data) > max_samples:
        np.random.seed(42)  # Reproducible
        data = np.random.choice(data, size=max_samples, replace=False)

    kde = gaussian_kde(data)
    x_grid = np.linspace(data.min(), data.max(), num_points)
    y_grid = kde(x_grid)

    return x_grid, y_grid


def find_elbow_second_derivative(x_grid, y_grid):
    """
    Find the 'elbow' as the maximum of the second derivative of KDE.
    Returns the x-value at the elbow.
    """
    if x_grid is None or len(x_grid) < 10:
        return np.nan

    # First derivative
    dy = np.gradient(y_grid, x_grid)
    # Second derivative
    d2y = np.gradient(dy, x_grid)

    elbow_idx = np.argmax(d2y)
    return x_grid[elbow_idx]


def find_elbow_kneedle(x_grid, y_grid):
    """
    Find elbow using Kneedle algorithm.
    Returns the x-value at the elbow.
    """
    if not KNEED_AVAILABLE or x_grid is None:
        return np.nan

    try:
        kl = KneeLocator(
            x_grid, y_grid,
            curve='convex',
            direction='decreasing',
            S=1.0
        )
        return kl.knee if kl.knee is not None else np.nan
    except Exception:
        return np.nan


def find_elbow_gap_statistic(data, num_points=100):
    """
    Simplified Gap Statistic: compare empirical distribution to uniform.
    Find the x-value where the gap between the CDF and uniform CDF is maximal.
    """
    data = data.dropna().values
    if len(data) < 10:
        return np.nan

    # Sort data
    sorted_data = np.sort(data)
    n = len(sorted_data)

    # Empirical CDF
    ecdf = np.arange(1, n + 1) / n

    # Uniform CDF over the same range
    uniform_cdf = (sorted_data - sorted_data.min()) / (sorted_data.max() - sorted_data.min())

    # Gap
    gap = np.abs(ecdf - uniform_cdf)

    # Find max gap
    max_idx = np.argmax(gap)
    return sorted_data[max_idx]


def analyze_state_distributions(valid_results, output_dir='data/processed'):
    """
    For each movement state, analyze the distributions of DCPA, TCPA, distance_km.
    Produce:
        - Histograms + KDE plots (saved as PNG)
        - Elbow estimates from three methods
    Returns a dictionary of thresholds per state.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    states = ['anchored', 'towing', 'moving']
    metrics = ['DCPA', 'TCPA', 'distance_km']

    results = {}

    for state in states:
        subset = valid_results[valid_results['movement_state'] == state]
        n_pairs = len(subset)

        print(f"\n{'=' * 50}")
        print(f"Movement State: {state} (n={n_pairs})")
        print(f"{'=' * 50}")

        state_result = {'n_pairs': n_pairs}

        # Create figure with 3 subplots (one per metric)
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        for ax, metric in zip(axes, metrics):
            data = subset[metric].dropna()

            # For TCPA – only positive values matter (approaching)
            if metric == 'TCPA':
                data = data[data >= 0]
                if len(data) < 10:
                    ax.set_title(f'{metric} (not enough data)')
                    state_result[metric] = {
                        'elbow_2deriv': np.nan,
                        'elbow_kneedle': np.nan,
                        'elbow_gap': np.nan
                    }
                    continue

            # Histogram
            ax.hist(data, bins=50, density=True, alpha=0.5, label='Histogram')

            # KDE
            x_grid, y_grid = compute_kde(data)
            if x_grid is not None:
                ax.plot(x_grid, y_grid, 'r-', linewidth=2, label='KDE')

                # Three methods
                elbow_2deriv = find_elbow_second_derivative(x_grid, y_grid)
                elbow_kneedle = find_elbow_kneedle(x_grid, y_grid)
                elbow_gap = find_elbow_gap_statistic(data)

                # Plot vertical lines for each method
                if not np.isnan(elbow_2deriv):
                    ax.axvline(elbow_2deriv, color='green', linestyle='--',
                               linewidth=2, label=f'2nd deriv: {elbow_2deriv:.4f}')
                if not np.isnan(elbow_kneedle):
                    ax.axvline(elbow_kneedle, color='blue', linestyle='--',
                               linewidth=2, label=f'Kneedle: {elbow_kneedle:.4f}')
                if not np.isnan(elbow_gap):
                    ax.axvline(elbow_gap, color='orange', linestyle='--',
                               linewidth=2, label=f'Gap: {elbow_gap:.4f}')

                state_result[metric] = {
                    'elbow_2deriv': elbow_2deriv,
                    'elbow_kneedle': elbow_kneedle,
                    'elbow_gap': elbow_gap,
                    'mean': float(data.mean()),
                    'median': float(data.median()),
                    'q05': float(data.quantile(0.05)),
                    'q95': float(data.quantile(0.95))
                }

                print(f"\n--- {metric} ---")
                print(f"  n:              {len(data)}")
                print(f"  mean:           {data.mean():.4f}")
                print(f"  median:         {data.median():.4f}")
                print(f"  q05:            {data.quantile(0.05):.4f}")
                print(f"  q95:            {data.quantile(0.95):.4f}")
                print(f"  Elbow (2nd):    {elbow_2deriv:.4f}")
                print(f"  Elbow (Kneedle): {elbow_kneedle if not np.isnan(elbow_kneedle) else 'N/A'}")
                print(f"  Elbow (Gap):    {elbow_gap:.4f}")

            ax.set_title(f'{state} – {metric}')
            ax.set_xlabel(metric)
            ax.set_ylabel('Density')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = f'{output_dir}/{state}_distributions.png'
        plt.savefig(plot_path, dpi=100)
        plt.close()

        print(f"\n✅ Plot saved: {plot_path}")

        results[state] = state_result

    return results


def print_elbow_summary(elbow_results):
    """
    Print a clean summary table of elbow estimates across states and metrics.
    """
    print("\n" + "=" * 70)
    print("ELBOW SUMMARY – ALL STATES × ALL METRICS")
    print("=" * 70)

    metrics = ['DCPA', 'TCPA', 'distance_km']
    methods = ['elbow_2deriv', 'elbow_kneedle', 'elbow_gap']

    for state, state_data in elbow_results.items():
        print(f"\n### {state} (n={state_data.get('n_pairs', 'N/A')})")
        print(f"{'Metric':<15} {'2nd deriv':>12} {'Kneedle':>12} {'Gap':>12}")
        print("-" * 55)

        for metric in metrics:
            if metric in state_data and isinstance(state_data[metric], dict):
                m = state_data[metric]
                v1 = m.get('elbow_2deriv', np.nan)
                v2 = m.get('elbow_kneedle', np.nan)
                v3 = m.get('elbow_gap', np.nan)

                v1_str = f"{v1:.4f}" if not pd.isna(v1) else "N/A"
                v2_str = f"{v2:.4f}" if not pd.isna(v2) else "N/A"
                v3_str = f"{v3:.4f}" if not pd.isna(v3) else "N/A"

                print(f"{metric:<15} {v1_str:>12} {v2_str:>12} {v3_str:>12}")

def check_vessel_size_effect(valid_results):
    """
    Check if vessel length affects DCPA/TCPA thresholds.
    Only considers approaching pairs (TCPA >= 0).
    """
    if 'length_1' not in valid_results.columns:
        print("Warning: 'length_1' column not available. Skipping.")
        return

    moving = valid_results[
        valid_results['movement_state'] == 'moving'
    ].copy()

    # Filter only approaching pairs for TCPA analysis
    moving_approaching = moving[moving['TCPA'] >= 0].copy()

    moving_approaching['size_class'] = pd.cut(
        moving_approaching['length_1'],
        bins=[0, 50, 150, 10000],
        labels=['small', 'medium', 'large']
    )

    print(f"\n{'Size Class':<10} {'n':>8} {'DCPA_q05':>12} {'TCPA_q05':>12} {'DCPA_median':>14}")
    print("-" * 65)

    for size in ['small', 'medium', 'large']:
        subset = moving_approaching[moving_approaching['size_class'] == size]
        if len(subset) > 100:
            dcpa_q = subset['DCPA'].quantile(0.05)
            tcpa_q = subset['TCPA'].quantile(0.05)
            dcpa_med = subset['DCPA'].median()
            print(f"{size:<10} {len(subset):>8} {dcpa_q:>12.4f} {tcpa_q:>12.4f} {dcpa_med:>14.4f}")
        else:
            print(f"{size:<10} {len(subset):>8} (not enough data)")

def check_vessel_speed_effect(valid_results):
    """
    Check if vessel speed affects DCPA/TCPA thresholds.
    Only considers approaching pairs (TCPA >= 0).
    """
    moving = valid_results[
        valid_results['movement_state'] == 'moving'
    ].copy()

    moving['avg_sog'] = (moving['sog1'] + moving['sog2']) / 2

    # Filter only approaching pairs
    moving_approaching = moving[moving['TCPA'] >= 0].copy()

    moving_approaching['speed_class'] = pd.cut(
        moving_approaching['avg_sog'],
        bins=[0, 5, 15, 100],
        labels=['slow', 'medium', 'fast']
    )

    print(f"\n{'Speed Class':<12} {'n':>8} {'DCPA_q05':>12} {'TCPA_q05':>12} {'DCPA_median':>14}")
    print("-" * 70)

    for speed in ['slow', 'medium', 'fast']:
        subset = moving_approaching[moving_approaching['speed_class'] == speed]
        if len(subset) > 100:
            dcpa_q = subset['DCPA'].quantile(0.05)
            tcpa_q = subset['TCPA'].quantile(0.05)
            dcpa_med = subset['DCPA'].median()
            print(f"{speed:<12} {len(subset):>8} {dcpa_q:>12.4f} {tcpa_q:>12.4f} {dcpa_med:>14.4f}")
        else:
            print(f"{speed:<12} {len(subset):>8} (not enough data)")

def sanity_check_thresholds(valid_results):
    """
    Compare old (5th percentile) and new (2nd derivative) thresholds.
    """
    # OLD thresholds
    dcpa_old = valid_results['DCPA'].quantile(0.05)
    tcpa_old = valid_results['TCPA'].quantile(0.05)

    # NEW thresholds (from 2nd derivative)
    dcpa_new = 0.1956
    tcpa_new = 0.0276

    # Count with OLD (moving only)
    moving = valid_results[valid_results['movement_state'] == 'moving']
    anomalies_old = (
        (moving['DCPA'] < dcpa_old) &
        (moving['TCPA'] >= 0) &
        (moving['TCPA'] < tcpa_old)
    ).sum()

    # Count with NEW (moving only)
    anomalies_new = (
        (moving['DCPA'] < dcpa_new) &
        (moving['TCPA'] >= 0) &
        (moving['TCPA'] < tcpa_new)
    ).sum()

    print(f"\n=== SANITY CHECK ===")
    print(f"Old threshold anomalies:  {anomalies_old}")
    print(f"New threshold anomalies:  {anomalies_new}")
    print(f"Ratio (new/old):          {anomalies_new/anomalies_old if anomalies_old > 0 else 'N/A'}")

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

    # Step 3.5: Verify columns exist
    print(f"length in clean_features: {'length' in clean_features.columns}")
    print(f"vessel_type in clean_features: {'vessel_type' in clean_features.columns}")
    
    # Step 4: Empirical thresholds (vessel-level)
    derive_vessel_thresholds(clean_features)

    # Step 5: Convert to radians
    clean_features = add_radians(clean_features)

        # Step 6: Process all minutes (writes to disk)
    pairs_path = process_all_minutes(clean_features)

    if pairs_path is None:
        print("No valid pairs to analyze.")
        return

    # Step 7: Analyze pairs in chunks
    print("\n" + "=" * 70)
    print("PAIRS ANALYSIS (CHUNKED)")
    print("=" * 70)

    analysis = analyze_pairs_in_chunks(pairs_path)

    dist_th = analysis['distance_threshold']
    tcpa_th = analysis['tcpa_threshold']
    dcpa_th = analysis['dcpa_threshold']

    print(f"\n✅ Analysis complete. Total valid pairs: {analysis['total_valid']:,}")

    # ==========================================
    # Step 8: Load pairs (sampled) into memory
    # ==========================================
    print("\n=== Loading pairs (sampled) ===")

    chunks = []
    max_rows = 2_000_000  # ~1.5GB RAM
    loaded = 0

    for chunk in pd.read_csv(pairs_path, chunksize=500_000):
        remaining = max_rows - loaded
        if remaining <= 0:
            break
        take = min(len(chunk), remaining)
        chunks.append(chunk.head(take))
        loaded += take

    valid = pd.concat(chunks, ignore_index=True)
    print(f"Loaded {len(valid):,} rows (sampled)")

    # Drop rows with missing critical values
    valid = valid.dropna(subset=['distance_km', 'TCPA', 'DCPA']).copy()
    print(f"Valid rows (with DCPA/TCPA): {len(valid):,}")

    # ==========================================
    # Step 8.5: Compute movement_state
    # ==========================================
    print("\n=== Computing movement_state ===")
    valid['movement_state'] = valid.apply(classify_movement_state, axis=1)
    print("Movement state distribution:")
    print(valid['movement_state'].value_counts())

    # ==========================================
    # Step 9: Flag anomalies
    # ==========================================
    # Use per-state thresholds (2nd Derivative on moving only)
    valid = flag_anomalies_per_state(valid)

    # ==========================================
    # SUMMARY
    # ==========================================
    print("\n" + "=" * 70)
    print("SUMMARY – ANOMALIES AFTER PER-STATE FILTERING")
    print("=" * 70)

    print(f"\nTotal pairs loaded: {len(valid):,}")
    print(f"Total anomalies (moving only): {valid['anomaly_dcpa_tcpa'].sum():,}")
    print(f"Anomaly rate: {valid['anomaly_dcpa_tcpa'].sum() / len(valid) * 100:.4f}%")

    print(f"\nBreakdown by movement_state:")
    print(valid['movement_state'].value_counts())

    print(f"\nAnomalies by movement_state:")
    print(valid.groupby('movement_state')['anomaly_dcpa_tcpa'].sum())
    
    # Step 9.5: Movement state distribution
    print("\n=== Movement State Distribution ===")
    print(valid['movement_state'].value_counts())
    print("\n=== Movement State × Anomaly Crosstab ===")
    print(pd.crosstab(valid['movement_state'], valid['anomaly_dcpa_tcpa']))

    # Step 9.6: Elbow analysis per movement state
    print("\n" + "=" * 70)
    print("ELBOW ANALYSIS PER MOVEMENT STATE")
    print("=" * 70)

    elbow_results = analyze_state_distributions(valid)
    print_elbow_summary(elbow_results)

    # Step 9.7: Check vessel characteristics
    print("\n" + "=" * 70)
    print("VESSEL CHARACTERISTICS ANALYSIS")
    print("=" * 70)

    print("\n=== VESSEL SIZE EFFECT ===")
    check_vessel_size_effect(valid)

    print("\n=== VESSEL SPEED EFFECT ===")
    check_vessel_speed_effect(valid)
 
    # Step 10: Save
    save_results(valid, OUTPUT_PATH)

    print("\n" + "=" * 50)
    print("Pipeline complete.")
    print("=" * 50)
    

if __name__ == "__main__":
    main()