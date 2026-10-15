"""Unit tests for models.helpers."""
import numpy as np
import pandas as pd

from models.helpers import (
    haversine, select_risky_row,
    calc_distances_for_minute, merge_pair_features,
)


class TestHaversine:
    def test_same_point_is_zero(self):
        p = (np.radians(33.75), np.radians(-118.20))
        assert haversine(p, p) == 0.0

    def test_known_distance_equator(self):
        p1, p2 = (0.0, 0.0), (0.0, np.radians(1.0))
        assert 111.0 < haversine(p1, p2) < 111.5

    def test_symmetry(self):
        p1 = (np.radians(33.75), np.radians(-118.20))
        p2 = (np.radians(33.80), np.radians(-118.15))
        assert abs(haversine(p1, p2) - haversine(p2, p1)) < 1e-9


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
        assert len(calc_distances_for_minute(df)) == 1

    def test_distance_matches_haversine(self):
        df = pd.DataFrame({
            'mmsi': [1, 2],
            'lat_rad': np.radians([33.75, 33.80]),
            'lon_rad': np.radians([-118.20, -118.15]),
        })
        result = calc_distances_for_minute(df)
        p1 = (np.radians(33.75), np.radians(-118.20))
        p2 = (np.radians(33.80), np.radians(-118.15))
        assert abs(result['distance_km'].iloc[0] - haversine(p1, p2)) < 1e-9


class TestMergePairFeatures:
    def test_features_renamed_correctly(self):
        distances = pd.DataFrame({
            'mmsi1': [1, 1], 'mmsi2': [2, 3], 'distance_km': [0.5, 0.7],
        })
        features = pd.DataFrame({
            'mmsi': [1, 2, 3],
            'sog': [10.0, 12.0, 8.0], 'cog': [90.0, 270.0, 45.0],
            'cog_diff': [0.0] * 3, 'sog_diff': [0.0] * 3,
            'lat_rad': [0.5, 0.6, 0.7], 'lon_rad': [-2.0, -2.1, -2.2],
            'length': [100, 200, 50],
            'vessel_type': ['cargo', 'tanker', 'tug'],
        })
        result = merge_pair_features(distances, features)
        assert 'sog1' in result.columns and 'sog2' in result.columns
        assert 'cog1' in result.columns and 'cog2' in result.columns
        assert 'length_1' in result.columns
        assert 'vessel_type_2' in result.columns
        assert result['sog1'].iloc[0] == 10.0
        assert result['sog2'].iloc[0] == 12.0
        assert result['length_2'].iloc[1] == 50
