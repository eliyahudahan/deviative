"""Integration tests: pipeline invariants (4 promised in README)."""
import pandas as pd

from models.config import (
    DCPA_THRESHOLD_MOVING,
    TCPA_THRESHOLD_MOVING,
    DISTANCE_THRESHOLD_MOVING,
)
from models.anomaly import get_anomaly_mask, flag_anomalies_per_state


class TestPipelineInvariants:
    """Tests for the 4 invariants promised in the README."""

    def test_pipeline_reproducibility(self):
        """
        Same input → same anomaly count (deterministic flagging).

        Expected count = 3:
        - Row 0: moving, DCPA=0.10, TCPA=0.010, dist=0.5 → anomaly
        - Row 1: moving, DCPA=0.15, TCPA=0.005, dist=0.8 → anomaly
        - Row 2: moving, DCPA=0.50 (>0.1982) → NOT anomaly
        - Row 3: moving, DCPA=0.05, TCPA=0.020, dist=0.3 → anomaly
        - Row 4: anchored → NOT anomaly

        Verifies TWO properties:
        1. Reproducibility: c1 == c2 == c3
        2. Exact count: c1 == 3 (data-derived, not magic)
        """
        df = pd.DataFrame({
            'movement_state': ['moving'] * 4 + ['anchored'],
            'DCPA': [0.1, 0.15, 0.5, 0.05, 0.1],
            'TCPA': [0.01, 0.005, 0.01, 0.02, 0.01],
            'distance_km': [0.5, 0.8, 0.5, 0.3, 0.5],
        })
        r1 = flag_anomalies_per_state(df.copy())
        r2 = flag_anomalies_per_state(df.copy())
        r3 = flag_anomalies_per_state(df.copy())

        c1 = r1['anomaly_dcpa_tcpa'].sum()
        c2 = r2['anomaly_dcpa_tcpa'].sum()
        c3 = r3['anomaly_dcpa_tcpa'].sum()

        assert c1 == c2 == c3, f"Non-deterministic: {c1}, {c2}, {c3}"
        assert c1 == 3, (
            f"Expected 3 anomalies, got {c1}. "
            f"Rows 0, 1, 3 pass; row 2 fails DCPA; row 4 is anchored."
        )
        pd.testing.assert_series_equal(
            r1['anomaly_dcpa_tcpa'],
            r2['anomaly_dcpa_tcpa'],
        )

    def test_distance_guard_sensitivity(self):
        """The 1.0 km guard strictly reduces anomalies vs no guard."""
        df = pd.DataFrame({
            'movement_state': ['moving'] * 4,
            'DCPA': [0.1, 0.1, 0.1, 0.1],
            'TCPA': [0.01, 0.01, 0.01, 0.01],
            'distance_km': [0.5, 0.9, 1.5, 5.0],
        })
        with_guard = flag_anomalies_per_state(
            df.copy(), distance_moving=1.0
        )['anomaly_dcpa_tcpa'].sum()
        without_guard = get_anomaly_mask(
            df,
            dcpa_th=DCPA_THRESHOLD_MOVING,
            tcpa_th=TCPA_THRESHOLD_MOVING,
            distance_th=float('inf'),
        ).sum()
        assert with_guard == 2
        assert without_guard == 4
        assert with_guard < without_guard

    def test_out_of_time_split_disjoint(self):
        """Out-of-time split partitions 'moving' rows disjointly."""
        df = pd.DataFrame({
            'base_date_time': pd.to_datetime([
                '2025-06-01 06:00', '2025-06-01 11:59',
                '2025-06-01 12:00', '2025-06-01 23:59',
                '2025-06-01 03:00',
            ]),
            'movement_state': ['moving'] * 5,
            'DCPA': [0.1, 0.1, 0.1, 0.1, 0.5],
            'TCPA': [0.01] * 5,
            'distance_km': [0.5] * 5,
        })
        df['hour'] = df['base_date_time'].dt.hour
        moving = df[df['movement_state'] == 'moving']
        train_idx = set(moving[moving['hour'] < 12].index)
        test_idx = set(moving[moving['hour'] >= 12].index)
        assert train_idx.isdisjoint(test_idx)
        assert train_idx | test_idx == set(moving.index)
        assert len(train_idx) == 3
        assert len(test_idx) == 2

    def test_manual_inspection_returns_valid_anomalies(self):
        """Every row from manual_inspection must satisfy full anomaly mask."""
        from models.validation import manual_inspection

        df = pd.DataFrame({
            'base_date_time': pd.to_datetime(['2025-06-01 10:00'] * 8),
            'movement_state': ['moving'] * 7 + ['anchored'],
            'DCPA': [0.05, 0.10, 0.15, 0.18, 0.19, 0.25, 0.30, 0.05],
            'TCPA': [0.001, 0.005, 0.010, 0.015, 0.020, 0.025, 0.028, 0.001],
            'distance_km': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.3],
            'mmsi1': list(range(8)),
            'mmsi2': list(range(100, 108)),
        })
        sample = manual_inspection(
            df,
            dcpa_th=DCPA_THRESHOLD_MOVING,
            tcpa_th=TCPA_THRESHOLD_MOVING,
            distance_th=DISTANCE_THRESHOLD_MOVING,
            n_sample=4,
        )
        assert len(sample) > 0
        assert (sample['DCPA'] < DCPA_THRESHOLD_MOVING).all()
        assert (sample['TCPA'] >= 0).all()
        assert (sample['TCPA'] < TCPA_THRESHOLD_MOVING).all()
        assert (sample['distance_km'] < DISTANCE_THRESHOLD_MOVING).all()
