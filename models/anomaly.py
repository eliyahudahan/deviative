"""
Deviative - Anomaly flagging.

Single source of truth for the anomaly definition.
"""

import pandas as pd

from .config import (
    DCPA_THRESHOLD_MOVING,
    TCPA_THRESHOLD_MOVING,
    DISTANCE_THRESHOLD_MOVING,
)


def get_anomaly_mask(df, dcpa_th, tcpa_th, distance_th):
    """
    Single source of truth for 'anomaly' definition.

    Used by:
        - flag_anomalies_per_state
        - validation functions
    """
    return (
        (df['movement_state'] == 'moving') &
        (df['DCPA'] < dcpa_th) &
        (df['TCPA'] >= 0) &
        (df['TCPA'] < tcpa_th) &
        (df['distance_km'] < distance_th)
    )


def flag_anomalies(valid_results, distance_threshold, tcpa_threshold, dcpa_threshold):
    """Legacy: global thresholds (no movement state filter)."""
    valid_results['anomaly_dcpa_tcpa'] = (
        (valid_results['DCPA'] < dcpa_threshold) &
        (valid_results['TCPA'] >= 0) &
        (valid_results['TCPA'] < tcpa_threshold) &
        (valid_results['distance_km'] < distance_threshold)
    )

    total_anomalies = valid_results['anomaly_dcpa_tcpa'].sum()
    print(f"\n=== Total anomalies detected: {total_anomalies:,} ===")

    return valid_results


def flag_anomalies_per_state(valid_results,
                              dcpa_moving=DCPA_THRESHOLD_MOVING,
                              tcpa_moving=TCPA_THRESHOLD_MOVING,
                              distance_moving=DISTANCE_THRESHOLD_MOVING):
    """
    Flag anomalies using per-state thresholds.
    Only 'moving' state is considered.
    """
    valid_results['anomaly_dcpa_tcpa'] = get_anomaly_mask(
        valid_results, dcpa_moving, tcpa_moving, distance_moving
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