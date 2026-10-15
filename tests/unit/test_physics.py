"""Unit tests for models.physics."""
import numpy as np
import pandas as pd

from models.physics import (
    compute_dcpa_tcpa,
    compute_dcpa_tcpa_vectorized,
    classify_movement_state,
    classify_movement_state_vectorized,
)


class TestComputeDcpaTcpa:
    def _row(self, cog1, sog1, cog2, sog2, lat1, lon1, lat2, lon2):
        return pd.Series({
            'cog1': cog1, 'sog1': sog1,
            'cog2': cog2, 'sog2': sog2,
            'lat_rad_1': np.radians(lat1), 'lon_rad_1': np.radians(lon1),
            'lat_rad_2': np.radians(lat2), 'lon_rad_2': np.radians(lon2),
        })

    def test_same_position_same_velocity_is_static(self):
        row = self._row(90, 10, 90, 10, 33.75, -118.20, 33.75, -118.20)
        result = compute_dcpa_tcpa(row)
        assert result['tcpa_type'] == 'static'
        assert result['DCPA'] == 0.0
        assert result['TCPA'] == 0

    def test_head_on_returns_positive_tcpa(self):
        """
        Head-on = approaching = TCPA > 0.
        Fixed 2026-10-14 (v1.1): prior version used v_rel = v1 - v2
        while positions were r = r2 - r1, producing negative TCPA.
        Physical sign convention: TCPA > 0 = approaching.
        """
        row = self._row(90, 10, 270, 10, 33.75, -118.20, 33.75, -118.19)
        result = compute_dcpa_tcpa(row)
        assert result['tcpa_type'] == 'dynamic'
        assert result['TCPA'] > 0
        assert result['DCPA'] < 0.01

    def test_diverging_returns_negative_tcpa(self):
        """Diverging = receding = TCPA < 0."""
        row = self._row(90, 5, 90, 15, 33.75, -118.20, 33.75, -118.19)
        result = compute_dcpa_tcpa(row)
        assert result['tcpa_type'] == 'dynamic'
        assert result['TCPA'] < 0

    def test_missing_input_returns_nan(self):
        row = pd.Series({
            'cog1': np.nan, 'sog1': 10,
            'cog2': 90, 'sog2': 10,
            'lat_rad_1': np.radians(33.75), 'lon_rad_1': np.radians(-118.20),
            'lat_rad_2': np.radians(33.75), 'lon_rad_2': np.radians(-118.19),
        })
        result = compute_dcpa_tcpa(row)
        assert pd.isna(result['TCPA'])
        assert pd.isna(result['DCPA'])
        assert result['tcpa_type'] == 'unknown'


class TestVectorizedConsistency:
    def test_vectorized_matches_rowwise(self):
        rows = []
        for lat2_off in [0.0, 0.005, -0.005]:
            for cog2 in [0, 90, 180, 270]:
                rows.append({
                    'cog1': 90, 'sog1': 10,
                    'cog2': cog2, 'sog2': 12,
                    'lat_rad_1': np.radians(33.75),
                    'lon_rad_1': np.radians(-118.20),
                    'lat_rad_2': np.radians(33.75 + lat2_off),
                    'lon_rad_2': np.radians(-118.19),
                })
        df = pd.DataFrame(rows)
        row_results = df.apply(compute_dcpa_tcpa, axis=1)
        vec_df = compute_dcpa_tcpa_vectorized(df.copy())
        for i in range(len(df)):
            rt = row_results.iloc[i]['tcpa_type']
            vt = vec_df.iloc[i]['tcpa_type']
            assert rt == vt, f"Row {i}: type mismatch"
            if rt == 'dynamic':
                assert abs(row_results.iloc[i]['TCPA'] - vec_df.iloc[i]['TCPA']) < 1e-6
                assert abs(row_results.iloc[i]['DCPA'] - vec_df.iloc[i]['DCPA']) < 1e-6


class TestClassifyMovementState:
    def _row(self, sog1, cog1, sog2, cog2, tcpa_type='dynamic'):
        return pd.Series({
            'sog1': sog1, 'cog1': cog1,
            'sog2': sog2, 'cog2': cog2, 'tcpa_type': tcpa_type,
        })

    def test_both_slow_is_anchored(self):
        assert classify_movement_state(self._row(0.3, 90, 0.4, 270)) == 'anchored'

    def test_static_when_not_anchored(self):
        row = self._row(5.0, 90, 5.0, 90, tcpa_type='static')
        assert classify_movement_state(row) == 'static'

    def test_towing_similar_speed_and_course(self):
        assert classify_movement_state(self._row(8.0, 90, 8.2, 95)) == 'towing'

    def test_moving_by_default(self):
        assert classify_movement_state(self._row(10.0, 90, 15.0, 270)) == 'moving'

    def test_missing_data_is_unknown(self):
        row = pd.Series({
            'sog1': np.nan, 'cog1': 90,
            'sog2': 10, 'cog2': 90, 'tcpa_type': 'dynamic',
        })
        assert classify_movement_state(row) == 'unknown'


class TestClassifyMovementStateVectorized:
    def test_vectorized_matches_rowwise(self):
        df = pd.DataFrame({
            'sog1': [0.3, 5.0, 8.0, 10.0, np.nan, 0.0, 15.0, 10.0, np.nan],
            'sog2': [0.4, 5.0, 8.2, 15.0, 10.0, 0.0, 15.0, 10.0, 10.0],
            'cog1': [90, 90, 90, 90, 90, 0, 45, np.nan, 90],
            'cog2': [270, 90, 95, 270, 90, 0, 47, 90, 90],
            'tcpa_type': ['dynamic'] * 8 + ['static'],
        })
        row_result = df.apply(classify_movement_state, axis=1)
        vec_result = classify_movement_state_vectorized(df)
        assert list(row_result) == list(vec_result)

    def test_empty_dataframe(self):
        df = pd.DataFrame({
            'sog1': pd.Series([], dtype=float),
            'sog2': pd.Series([], dtype=float),
            'cog1': pd.Series([], dtype=float),
            'cog2': pd.Series([], dtype=float),
            'tcpa_type': pd.Series([], dtype=object),
        })
        assert len(classify_movement_state_vectorized(df)) == 0

    def test_anchored_beats_towing(self):
        df = pd.DataFrame({
            'sog1': [0.3], 'sog2': [0.3],
            'cog1': [90.0], 'cog2': [90.0], 'tcpa_type': ['dynamic'],
        })
        assert classify_movement_state_vectorized(df)[0] == 'anchored'

    def test_missing_beats_anchored(self):
        df = pd.DataFrame({
            'sog1': [0.3], 'sog2': [0.3],
            'cog1': [np.nan], 'cog2': [90.0], 'tcpa_type': ['dynamic'],
        })
        assert classify_movement_state_vectorized(df)[0] == 'unknown'
