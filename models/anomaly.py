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
    DCPA/TCPA thresholds are data-derived (2nd Derivative of KDE).
    distance_moving is a guard threshold — see README Known Uncertainties.
    """
    valid_results['anomaly_dcpa_tcpa'] = (
        (valid_results['movement_state'] == 'moving') &
        (valid_results['DCPA'] < dcpa_moving) &
        (valid_results['TCPA'] >= 0) &
        (valid_results['TCPA'] < tcpa_moving) &
        (valid_results['distance_km'] < distance_moving)
    )
    return valid_results