"""
Deviative - Physics calculations.

DCPA/TCPA computation (row-wise and vectorized)
and movement state classification.

Sign convention (fixed 2026-10-14):
    TCPA > 0  →  approaching (CPA in future)
    TCPA < 0  →  receding (CPA in past)
    TCPA = 0  →  at CPA / static
"""

import pandas as pd
import numpy as np

from .config import (
    KNOT_TO_KMH,
    KM_PER_DEG_LAT,
    KM_PER_DEG_LON,
    ANCHORED_SOG_THRESHOLD,
    TOWING_SOG_DIFF_THRESHOLD,
    TOWING_COG_DIFF_THRESHOLD,
)


# ==========================================
# DCPA / TCPA - row-wise
# ==========================================
def compute_dcpa_tcpa(row):
    """
    Compute DCPA and TCPA for a pair of vessels (row-wise).

    Units:
        - SOG is converted from knots to km/h before velocity calculation.
        - DCPA is in kilometers.
        - TCPA is in hours.
        - Sign convention: TCPA > 0 (approaching), < 0 (receding), = 0 (at CPA).

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

    sog1_kmh = row['sog1'] * KNOT_TO_KMH
    sog2_kmh = row['sog2'] * KNOT_TO_KMH

    vx1 = sog1_kmh * np.sin(cog1_rad)
    vy1 = sog1_kmh * np.cos(cog1_rad)
    vx2 = sog2_kmh * np.sin(cog2_rad)
    vy2 = sog2_kmh * np.cos(cog2_rad)

    # Relative velocity of vessel 2 relative to vessel 1:  v_rel = v2 - v1
    # (positions are r = r2 - r1, so the two are consistent)
    vx_rel = vx2 - vx1
    vy_rel = vy2 - vy1
    speed_rel_sq = vx_rel ** 2 + vy_rel ** 2

    lat1_rad = row['lat_rad_1']
    lat2_rad = row['lat_rad_2']
    lon1_rad = row['lon_rad_1']
    lon2_rad = row['lon_rad_2']

    dx_km = (lon2_rad - lon1_rad) * KM_PER_DEG_LON * np.cos((lat1_rad + lat2_rad) / 2)
    dy_km = (lat2_rad - lat1_rad) * KM_PER_DEG_LAT

    EPS = 1e-9
    if speed_rel_sq < EPS:
        return pd.Series({
            'TCPA': 0,
            'DCPA': np.sqrt(dx_km ** 2 + dy_km ** 2),
            'tcpa_type': 'static'
        })

    # TCPA = -(r · v_rel) / |v_rel|²
    # With r = r2 - r1 and v_rel = v2 - v1, TCPA > 0 ⟺ approaching.
    tcpa = -(dx_km * vx_rel + dy_km * vy_rel) / speed_rel_sq

    x_cpa = dx_km + tcpa * vx_rel
    y_cpa = dy_km + tcpa * vy_rel
    dcpa = np.sqrt(x_cpa ** 2 + y_cpa ** 2)

    return pd.Series({
        'TCPA': tcpa,
        'DCPA': dcpa,
        'tcpa_type': 'dynamic'
    })


# ==========================================
# DCPA / TCPA - vectorized
# ==========================================
def compute_dcpa_tcpa_vectorized(df):
    """
    Vectorized version of compute_dcpa_tcpa.
    Operates on entire DataFrame columns at once.
    """
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

    # v_rel = v2 - v1 (see row-wise docstring)
    vx_rel = vx2 - vx1
    vy_rel = vy2 - vy1
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
# Movement state classification - row-wise
# ==========================================
def classify_movement_state(row):
    """
    Classify a vessel pair into one of these states:
        - 'anchored' : both vessels nearly stationary (sog < ANCHORED_SOG_THRESHOLD)
        - 'towing'   : similar speed & course
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
    if sog1 < ANCHORED_SOG_THRESHOLD and sog2 < ANCHORED_SOG_THRESHOLD:
        return 'anchored'

    # Static: no relative motion
    if tcpa_type == 'static':
        return 'static'

    # Towing: similar speed & course
    cog_diff = abs((cog1 - cog2 + 180) % 360 - 180)
    if (abs(sog1 - sog2) < TOWING_SOG_DIFF_THRESHOLD and
            cog_diff < TOWING_COG_DIFF_THRESHOLD):
        return 'towing'

    return 'moving'


# ==========================================
# Movement state classification - vectorized
# ==========================================
def classify_movement_state_vectorized(df):
    """
    Vectorized version of classify_movement_state.

    Equivalent to df.apply(classify_movement_state, axis=1),
    but ~100× faster on large DataFrames.

    Priority (matches row-wise):
        1. unknown  — any of sog1/sog2/cog1/cog2 is NaN
        2. anchored — both sog < ANCHORED_SOG_THRESHOLD
        3. static   — tcpa_type == 'static'
        4. towing   — |sog1-sog2| < TOWING_SOG_DIFF_THRESHOLD
                      AND cog_diff < TOWING_COG_DIFF_THRESHOLD
        5. moving   — default

    Returns:
        numpy array of strings, same length as df.
    """
    sog1 = df['sog1'].values
    sog2 = df['sog2'].values
    cog1 = df['cog1'].values
    cog2 = df['cog2'].values
    tcpa_type = df['tcpa_type'].values

    n = len(df)
    result = np.full(n, 'moving', dtype=object)

    # Priority 1: missing data → unknown
    missing = (
        pd.isna(sog1) | pd.isna(sog2) |
        pd.isna(cog1) | pd.isna(cog2)
    )
    result[missing] = 'unknown'

    # Priority 2: anchored — both nearly stationary
    anchored = (
        (sog1 < ANCHORED_SOG_THRESHOLD) &
        (sog2 < ANCHORED_SOG_THRESHOLD) &
        ~missing
    )
    result[anchored] = 'anchored'

    # Priority 3: static — no relative motion
    static = (tcpa_type == 'static') & ~missing & ~anchored
    result[static] = 'static'

    # Priority 4: towing — similar speed & course
    cog_diff = np.abs((cog1 - cog2 + 180) % 360 - 180)
    towing = (
        (np.abs(sog1 - sog2) < TOWING_SOG_DIFF_THRESHOLD) &
        (cog_diff < TOWING_COG_DIFF_THRESHOLD) &
        ~missing & ~anchored & ~static
    )
    result[towing] = 'towing'

    # Priority 5: default = moving (already set)

    return result