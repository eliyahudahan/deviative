"""
Deviative - Configuration constants.

All magic numbers, paths, and thresholds live here.
"""

# ==========================================
# Paths
# ==========================================
INPUT_PATH = 'data/processed/features_2025-06-01.csv'
OUTPUT_PATH = 'data/processed/encounter_results.csv'
PAIRS_TEMP_PATH = 'data/processed/pairs_temp.csv'

# ==========================================
# Physics constants
# ==========================================
EARTH_RADIUS_KM = 6371.0
KM_PER_DEG_LAT = 110.57
KM_PER_DEG_LON = 111.32
KNOT_TO_KMH = 1.852  # 1 knot = 1.852 km/h

# ==========================================
# Thresholds
# ==========================================
THRESHOLD_QUANTILE = 0.05
COG_THRESHOLD_QUANTILE = 0.95
SOG_THRESHOLD_QUANTILE = 0.95

# 2nd Derivative thresholds for 'moving' state
DCPA_THRESHOLD_MOVING = 0.1982   # km (198 meters)
TCPA_THRESHOLD_MOVING = 0.0293   # hours (1.76 minutes)
DISTANCE_THRESHOLD_MOVING = 1.0  # km

# ==========================================
# Processing
# ==========================================
MIN_VESSELS_PER_MINUTE = 2

# ==========================================
# Plotting
# ==========================================
PLOT_OUTPUT_DIR = 'data/processed'
PLOT_DPI = 100

# ==========================================
# Chunked analysis
# ==========================================
CHUNK_SIZE = 1_000_000
MAX_ROWS_IN_MEMORY = 2_000_000