# Deviative – Module Documentation

A quick reference for each module: purpose, key constants/functions, and dependencies.

---

## `models/config.py`

**Purpose:**
Central place for all constants, paths, and thresholds used throughout the project.
No functions — only static configuration.

**Sections:**

### Paths
- `INPUT_PATH` — input AIS features CSV (~32 MB, 199,910 rows).
- `OUTPUT_PATH` — output encounter results CSV (~288 MB).
- `PAIRS_TEMP_PATH` — intermediate pairwise file (~3.1 GB, excluded from repo).

### Physics constants
- `EARTH_RADIUS_KM = 6371.0` — Earth radius, used by the Haversine formula.
- `KM_PER_DEG_LAT = 110.57` — km per degree of latitude (equirectangular approximation).
- `KM_PER_DEG_LON = 111.32` — km per degree of longitude (at the equator).
- `KNOT_TO_KMH = 1.852` — conversion factor from knots to km/h (critical for DCPA/TCPA units).

### Thresholds
- `THRESHOLD_QUANTILE = 0.05` — 5th percentile, used as a baseline for distance metrics.
- `COG_THRESHOLD_QUANTILE = 0.95` — 95th percentile for COG anomaly.
- `SOG_THRESHOLD_QUANTILE = 0.95` — 95th percentile for SOG anomaly.

### Final thresholds (per-state, `moving` only)
- `DCPA_THRESHOLD_MOVING = 0.1982` km (198 m) — derived from 2nd Derivative of KDE.
- `TCPA_THRESHOLD_MOVING = 0.0293` h (1.76 min) — derived from 2nd Derivative of KDE.
- `DISTANCE_THRESHOLD_MOVING = 1.0` km — guard threshold.

### Processing
- `MIN_VESSELS_PER_MINUTE = 2` — minimum vessels needed to form a pair.

### Plotting
- `PLOT_OUTPUT_DIR = 'data/processed'` — where KDE plots are saved.
- `PLOT_DPI = 100` — plot resolution.

### Chunked analysis (memory-safe)
- `CHUNK_SIZE = 1_000_000` — rows per chunk when reading large CSV.
- `MAX_ROWS_IN_MEMORY = 2_000_000` — memory limit for sample loading.

**Dependencies:** None.

**Used by:** All other modules.