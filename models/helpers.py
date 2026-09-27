"""
Deviative - Helper functions.

Low-level utilities for distance calculation, duplicate handling,
and pairwise merging.
"""

import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist

from .config import (
    EARTH_RADIUS_KM,
    KM_PER_DEG_LAT,
    KM_PER_DEG_LON,
)


# ==========================================
# Haversine distance
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


# ==========================================
# Duplicate handling
# ==========================================
def select_risky_row(group):
    """
    Within a duplicate group (same MMSI + timestamp),
    select the row with the highest normalized risk score.

    Risk = normalized COG change + normalized SOG change.
    Normalization uses fixed reference values:
        - COG_REF = 90 degrees (half circle)
        - SOG_REF = 5 knots (reasonable maneuver)

    Note: reference values will be replaced by empirical thresholds
    in a later phase once the full pipeline is validated.
    """
    if len(group) == 1:
        return group

    group = group.copy()

    # COG diff with wrap-around
    group['cog_diff_dup'] = (group['cog'].diff() + 180) % 360 - 180
    group['sog_diff_dup'] = group['sog'].diff()

    # Normalize each to a comparable 0-1 scale
    COG_REF = 90.0
    SOG_REF = 5.0

    cog_norm = (group['cog_diff_dup'].abs().fillna(0) / COG_REF).clip(upper=1.0)
    sog_norm = (group['sog_diff_dup'].abs().fillna(0) / SOG_REF).clip(upper=1.0)

    group['risk_score'] = cog_norm + sog_norm

    return group.loc[group['risk_score'].idxmax()].to_frame().T


# ==========================================
# Pairwise distances
# ==========================================
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


# ==========================================
# Merging
# ==========================================
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