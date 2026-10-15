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

    Anomaly = a 'moving' vessel pair where ALL of:
        - DCPA < dcpa_th            (close closest-point-of-approach)
        - TCPA >= 0                 (CPA in future — approaching)
        - TCPA < tcpa_th            (imminent — within threshold)
        - distance_km < distance_th (currently close — guard)

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


def flag_anomalies_per_state(valid_results,
                              dcpa_moving=DCPA_THRESHOLD_MOVING,
                              tcpa_moving=TCPA_THRESHOLD_MOVING,
                              distance_moving=DISTANCE_THRESHOLD_MOVING):
    """
    Flag anomalies using per-state thresholds.

    Delegates to get_anomaly_mask — single source of truth.
    Only 'moving' state is considered (enforced inside the mask).
    DCPA/TCPA thresholds are data-derived (2nd Derivative of KDE).
    distance_moving is a guard — see README → Known Uncertainties.
    """
    valid_results['anomaly_dcpa_tcpa'] = get_anomaly_mask(
        valid_results,
        dcpa_th=dcpa_moving,
        tcpa_th=tcpa_moving,
        distance_th=distance_moving,
    )
    return valid_results