"""
Deviative - Physics calculations.

DCPA/TCPA computation (row-wise and vectorized)
and movement state classification.
"""

import pandas as pd
import numpy as np

from .config import (
    KNOT_TO_KMH,
    KM_PER_DEG_LAT,
    KM_PER_DEG_LON,
)


# ==========================================
# DCPA / TCPA - row-wise (legacy)
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

    vx_rel = vx1 - vx2
    vy_rel = vy1 - vy2
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
# Movement state classification
# ==========================================
def classify_movement_state(row):
    """
    Classify a vessel pair into one of these states:
        - 'anchored' : both vessels nearly stationary (sog < 0.5)
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
    if sog1 < 0.5 and sog2 < 0.5:
        return 'anchored'

    # Static: no relative motion
    if tcpa_type == 'static':
        return 'static'

    # Towing: similar speed & course
    if abs(sog1 - sog2) < 0.5 and abs((cog1 - cog2 + 180) % 360 - 180) < 10:
        return 'towing'

    return 'moving'