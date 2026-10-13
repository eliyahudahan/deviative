"""
Unit tests for Deviative v1.0.
Reference: models/config.py, helpers.py, data_io.py, physics.py, anomaly.py
No AIS data, no PostgreSQL, no network required.
"""
import numpy as np
import pandas as pd
import pytest

from models.config import (
    DCPA_THRESHOLD_MOVING,
    TCPA_THRESHOLD_MOVING,
    DISTANCE_THRESHOLD_MOVING,
    KNOT_TO_KMH,
    EARTH_RADIUS_KM,
    KM_PER_DEG_LAT,
    KM_PER_DEG_LON,
    MIN_VESSELS_PER_MINUTE,
)
from models.helpers import (
    haversine,
    select_risky_row,
    calc_distances_for_minute,
    merge_pair_features,
)
from models.data_io import add_vessel_diffs, add_radians
from models.physics import (
    compute_dcpa_tcpa,
    compute_dcpa_tcpa_vectorized,
    classify_movement_state,
)
from models.anomaly import get_anomaly_mask, flag_anomalies_per_state


# ==========================================
# Config
# ==========================================
class TestConfig:
    def test_physics_constants(self):
        assert KNOT_TO_KMH == 1.852
        assert EARTH_RADIUS_KM == 6371.0
        assert KM_PER_DEG_LAT == 110.57
        assert KM_PER_DEG_LON == 111.32

    def test_thresholds_match_readme(self):
        assert DCPA_THRESHOLD_MOVING == 0.1982
        assert TCPA_THRESHOLD_MOVING == 0.0293
        assert DISTANCE_THRESHOLD_MOVING == 1.0
        assert MIN_VESSELS_PER_MINUTE == 2


# ==========================================
# helpers.haversine
# ==========================================
class TestHaversine:
    def test_same_point_is_zero(self):
        p = (np.radians(33.75), np.radians(-118.20))
        assert haversine(p, p) == 0.0

    def test_known_distance_equator(self):
        p1 = (0.0, 0.0)
        p2 = (0.0, np.radians(1.0))
        d = haversine(p1, p2)
        assert 111.0 < d < 111.5

    def test_symmetry(self):
        p1 = (np.radians(33.75), np.radians(-118.20))
        p2 = (np.radians(33.80), np.radians(-118.15))
        assert abs(haversine(p1, p2) - haversine(p2, p1)) < 1e-9


# ==========================================
# helpers.select_risky_row
# ==========================================
class TestSelectRiskyRow:
    def test_keeps_most_complete_row(self):
        df = pd.DataFrame({
            'mmsi': [1, 1, 1],
            'value_a': [10, np.nan, np.nan],
            'value_b': [20, 20, np.nan],
        })
        result = select_risky_row(df)
        assert result['value_a'].iloc[0] == 10
        assert result['value_b'].iloc[0] == 20
        assert len(result) == 1

    def test_single_row_group_returns_as_is(self):
        df = pd.DataFrame({'mmsi': [1], 'value': [10]})
        result = select_risky_row(df)
        assert len(result) == 1
        assert result['value'].iloc[0] == 10


# ==========================================
# data_io.add_vessel_diffs
# ==========================================
class TestAddVesselDiffs:
    def test_sog_diff_per_vessel(self):
        df = pd.DataFrame({
            'mmsi': [1, 1, 1, 2, 2],
            'sog': [10.0, 12.0, 11.0, 5.0, 7.0],
            'cog': [90.0, 90.0, 90.0, 0.0, 0.0],
        })
        result = add_vessel_diffs(df)
        assert pd.isna(result['sog_diff'].iloc[0])
        assert result['sog_diff'].iloc[1] == 2.0
        assert result['sog_diff'].iloc[2] == -1.0
        assert pd.isna(result['sog_diff'].iloc[3])
        assert result['sog_diff'].iloc[4] == 2.0

    def test_cog_diff_wraparound(self):
        df = pd.DataFrame({
            'mmsi': [1, 1],
            'sog': [10.0, 10.0],
            'cog': [350.0, 10.0],
        })
        result = add_vessel_diffs(df)
        assert result['cog_diff'].iloc[1] == 20.0


# ==========================================
# data_io.add_radians
# ==========================================
class TestAddRadians:
    def test_latitude_converted(self):
        df = pd.DataFrame({
            'latitude': [0.0, 90.0],
            'longitude': [0.0, 180.0],
        })
        result = add_radians(df)
        assert abs(result['lat_rad'].iloc[0] - 0.0) < 1e-9
        assert abs(result['lat_rad'].iloc[1] - np.pi / 2) < 1e-9
        assert abs(result['lon_rad'].iloc[1] - np.pi) < 1e-9


# ==========================================
# helpers.calc_distances_for_minute
# ==========================================
class TestCalcDistancesForMinute:
    def test_three_vessels_produce_three_pairs(self):
        df = pd.DataFrame({
            'mmsi': [1, 2, 3],
            'lat_rad': np.radians([33.75, 33.76, 33.77]),
            'lon_rad': np.radians([-118.20, -118.19, -118.18]),
        })
        result = calc_distances_for_minute(df)
        assert len(result) == 3
        assert set(result.columns) == {'mmsi1', 'mmsi2', 'distance_km'}
        assert (result['distance_km'] > 0).all()

    def test_two_vessels_produce_one_pair(self):
        df = pd.DataFrame({
            'mmsi': [1, 2],
            'lat_rad': np.radians([33.75, 33.76]),
            'lon_rad': np.radians([-118.20, -118.19]),
        })
        result = calc_distances_for_minute(df)
        assert len(result) == 1

    def test_distance_matches_haversine(self):
        df = pd.DataFrame({
            'mmsi': [1, 2],
            'lat_rad': np.radians([33.75, 33.80]),
            'lon_rad': np.radians([-118.20, -118.15]),
        })
        result = calc_distances_for_minute(df)
        p1 = (np.radians(33.75), np.radians(-118.20))
        p2 = (np.radians(33.80), np.radians(-118.15))
        expected = haversine(p1, p2)
        assert abs(result['distance_km'].iloc[0] - expected) < 1e-9


# ==========================================
# helpers.merge_pair_features
# ==========================================
class TestMergePairFeatures:
    def test_features_renamed_correctly(self):
        distances = pd.DataFrame({
            'mmsi1': [1, 1],
            'mmsi2': [2, 3],
            'distance_km': [0.5, 0.7],
        })
        features = pd.DataFrame({
            'mmsi': [1, 2, 3],
            'sog': [10.0, 12.0, 8.0],
            'cog': [90.0, 270.0, 45.0],
            'cog_diff': [0.0, 0.0, 0.0],
            'sog_diff': [0.0, 0.0, 0.0],
            'lat_rad': [0.5, 0.6, 0.7],
            'lon_rad': [-2.0, -2.1, -2.2],
            'length': [100, 200, 50],
            'vessel_type': ['cargo', 'tanker', 'tug'],
        })
        result = merge_pair_features(distances, features)
        assert 'sog1' in result.columns
        assert 'sog2' in result.columns
        assert 'cog1' in result.columns
        assert 'cog2' in result.columns
        assert 'length_1' in result.columns
        assert 'vessel_type_2' in result.columns
        assert result['sog1'].iloc[0] == 10.0
        assert result['sog2'].iloc[0] == 12.0
        assert result['length_2'].iloc[1] == 50


# ==========================================
# physics.compute_dcpa_tcpa
# ==========================================
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

    def test_head_on_returns_negative_tcpa(self):
        row = self._row(90, 10, 270, 10, 33.75, -118.20, 33.75, -118.19)
        result = compute_dcpa_tcpa(row)
        assert result['tcpa_type'] == 'dynamic'
        assert result['TCPA'] < 0
        assert result['DCPA'] < 0.01

    def test_diverging_returns_positive_tcpa(self):
        row = self._row(90, 5, 90, 15, 33.75, -118.20, 33.75, -118.19)
        result = compute_dcpa_tcpa(row)
        assert result['tcpa_type'] == 'dynamic'
        assert result['TCPA'] > 0

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


# ==========================================
# Vectorized consistency
# ==========================================
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


# ==========================================
# classify_movement_state
# ==========================================
class TestClassifyMovementState:
    def _row(self, sog1, cog1, sog2, cog2, tcpa_type='dynamic'):
        return pd.Series({
            'sog1': sog1, 'cog1': cog1,
            'sog2': sog2, 'cog2': cog2,
            'tcpa_type': tcpa_type,
        })

    def test_both_slow_is_anchored(self):
        row = self._row(0.3, 90, 0.4, 270)
        assert classify_movement_state(row) == 'anchored'

    def test_static_when_not_anchored(self):
        row = self._row(5.0, 90, 5.0, 90, tcpa_type='static')
        assert classify_movement_state(row) == 'static'

    def test_towing_similar_speed_and_course(self):
        row = self._row(8.0, 90, 8.2, 95)
        assert classify_movement_state(row) == 'towing'

    def test_moving_by_default(self):
        row = self._row(10.0, 90, 15.0, 270)
        assert classify_movement_state(row) == 'moving'

    def test_missing_data_is_unknown(self):
        row = pd.Series({
            'sog1': np.nan, 'cog1': 90,
            'sog2': 10, 'cog2': 90,
            'tcpa_type': 'dynamic',
        })
        assert classify_movement_state(row) == 'unknown'


# ==========================================
# get_anomaly_mask
# ==========================================
class TestAnomalyMask:
    @staticmethod
    def _df(state, dcpa, tcpa, distance):
        return pd.DataFrame({
            'movement_state': [state],
            'DCPA': [dcpa],
            'TCPA': [tcpa],
            'distance_km': [distance],
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
        assert self._mask(self._df('moving', DCPA_THRESHOLD_MOVING, 0.01, 0.5)).iloc[0] == False

    def test_distance_boundary_exact(self):
        assert self._mask(self._df('moving', 0.1, 0.01, DISTANCE_THRESHOLD_MOVING)).iloc[0] == False


# ==========================================
# flag_anomalies_per_state wrapper
# ==========================================
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
            'DCPA': [0.1],
            'TCPA': [0.01],
            'distance_km': [0.5],
        })
        result = flag_anomalies_per_state(df)
        assert 'anomaly_dcpa_tcpa' in result.columns
        assert result['anomaly_dcpa_tcpa'].dtype == bool
