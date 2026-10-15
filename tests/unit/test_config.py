"""Config constants — match README."""
from models.config import (
    DCPA_THRESHOLD_MOVING, TCPA_THRESHOLD_MOVING,
    DISTANCE_THRESHOLD_MOVING, KNOT_TO_KMH,
    EARTH_RADIUS_KM, KM_PER_DEG_LAT,
    KM_PER_DEG_LON, MIN_VESSELS_PER_MINUTE,
)


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
