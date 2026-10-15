"""Unit tests for models.anomaly."""
import pandas as pd

from models.config import (
    DCPA_THRESHOLD_MOVING,
    TCPA_THRESHOLD_MOVING,
    DISTANCE_THRESHOLD_MOVING,
)
from models.anomaly import get_anomaly_mask, flag_anomalies_per_state


class TestAnomalyMask:
    @staticmethod
    def _df(state, dcpa, tcpa, distance):
        return pd.DataFrame({
            'movement_state': [state],
            'DCPA': [dcpa], 'TCPA': [tcpa], 'distance_km': [distance],
        })

    def _mask(self, df):
        return get_anomaly_mask(
            df,
            dcpa_th=DCPA_THRESHOLD_MOVING,
            tcpa_th=TCPA_THRESHOLD_MOVING,
            distance_th=DISTANCE_THRESHOLD_MOVING,
        )

    def test_all_criteria_met_is_anomaly(self):
        assert self._mask(self._df('moving', 0.1, 0.01, 0.5)).iloc[0] == True

    def test_anchored_never_anomaly(self):
        assert self._mask(self._df('anchored', 0.1, 0.01, 0.5)).iloc[0] == False

    def test_towing_never_anomaly(self):
        assert self._mask(self._df('towing', 0.1, 0.01, 0.5)).iloc[0] == False

    def test_static_never_anomaly(self):
        assert self._mask(self._df('static', 0.1, 0.01, 0.5)).iloc[0] == False

    def test_negative_tcpa_excluded(self):
        assert self._mask(self._df('moving', 0.1, -0.01, 0.5)).iloc[0] == False

    def test_distance_guard_blocks_far(self):
        assert self._mask(self._df('moving', 0.1, 0.01, 2.0)).iloc[0] == False

    def test_dcpa_too_large(self):
        assert self._mask(self._df('moving', 0.5, 0.01, 0.5)).iloc[0] == False

    def test_tcpa_too_large(self):
        assert self._mask(self._df('moving', 0.1, 0.5, 0.5)).iloc[0] == False

    def test_tcpa_boundary_zero(self):
        assert self._mask(self._df('moving', 0.1, 0.0, 0.5)).iloc[0] == True

    def test_dcpa_boundary_exact(self):
        assert self._mask(
            self._df('moving', DCPA_THRESHOLD_MOVING, 0.01, 0.5)
        ).iloc[0] == False

    def test_distance_boundary_exact(self):
        assert self._mask(
            self._df('moving', 0.1, 0.01, DISTANCE_THRESHOLD_MOVING)
        ).iloc[0] == False


class TestFlagAnomaliesPerState:
    def test_wrapper_matches_mask(self):
        df = pd.DataFrame({
            'movement_state': ['moving', 'anchored', 'moving', 'moving'],
            'DCPA': [0.1, 0.1, 0.5, 0.1],
            'TCPA': [0.01, 0.01, 0.01, 0.5],
            'distance_km': [0.5, 0.5, 0.5, 0.5],
        })
        expected = get_anomaly_mask(
            df,
            dcpa_th=DCPA_THRESHOLD_MOVING,
            tcpa_th=TCPA_THRESHOLD_MOVING,
            distance_th=DISTANCE_THRESHOLD_MOVING,
        )
        result = flag_anomalies_per_state(df.copy())
        pd.testing.assert_series_equal(
            result['anomaly_dcpa_tcpa'], expected, check_names=False
        )

    def test_adds_column_to_dataframe(self):
        df = pd.DataFrame({
            'movement_state': ['moving'],
            'DCPA': [0.1], 'TCPA': [0.01], 'distance_km': [0.5],
        })
        result = flag_anomalies_per_state(df)
        assert 'anomaly_dcpa_tcpa' in result.columns
        assert result['anomaly_dcpa_tcpa'].dtype == bool
