"""Unit tests for models.data_io."""
import numpy as np
import pandas as pd

from models.data_io import add_vessel_diffs, add_radians


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
            'mmsi': [1, 1], 'sog': [10.0, 10.0], 'cog': [350.0, 10.0],
        })
        assert add_vessel_diffs(df)['cog_diff'].iloc[1] == 20.0


class TestAddRadians:
    def test_latitude_converted(self):
        df = pd.DataFrame({'latitude': [0.0, 90.0], 'longitude': [0.0, 180.0]})
        result = add_radians(df)
        assert abs(result['lat_rad'].iloc[0] - 0.0) < 1e-9
        assert abs(result['lat_rad'].iloc[1] - np.pi / 2) < 1e-9
        assert abs(result['lon_rad'].iloc[1] - np.pi) < 1e-9
