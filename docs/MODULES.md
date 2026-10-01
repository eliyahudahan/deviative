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
  **NOT data-derived.** See README → Known Uncertainties → Distance guard.

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

---

## `models/helpers.py`

**Purpose:**
Low-level utilities: Haversine distance, duplicate handling,
pairwise distance calculation, and feature merging.

**Key functions:**

### `haversine(x1, x2)`
Compute Haversine distance (in km) between two `(lat_rad, lon_rad)` tuples.

### `select_risky_row(group)`
Select one row per `(MMSI, timestamp)` group.
Rule: keep the **most complete row** (fewest NaN). Ties: first occurrence.

**Note:** documented arbitrary choice — no AIS industry standard.
See README → Known Uncertainties → Deduplication rule.

### `calc_distances_for_minute(df_minute)`
Compute pairwise Haversine distances for all vessels in a single minute.
Uses `scipy.spatial.distance.pdist` (vectorized).
Returns: `mmsi1`, `mmsi2`, `distance_km`.

### `merge_pair_features(distances_df, vessel_features)`
Merge pairwise distances with vessel features for both vessels.
Adds: sog, cog, diffs, radians, length, vessel_type.

**Dependencies:** `config.py`, `scipy`, `pandas`, `numpy`.

**Used by:** `thresholds.py`, `feature_engineering.py`.

---

## `models/physics.py`

**Purpose:**
DCPA/TCPA calculation (row-wise and vectorized) and movement state
classification.

**Key functions:**

### `compute_dcpa_tcpa(row)`
Row-wise DCPA/TCPA calculation. Slow but readable.
Returns: `TCPA` (hours), `DCPA` (km), `tcpa_type` (static/dynamic).

### `compute_dcpa_tcpa_vectorized(df)`
Vectorized version. ~50× faster.
Same output columns as `compute_dcpa_tcpa`.

### `classify_movement_state(row)`
Classify a vessel pair into: `anchored`, `towing`, `static`, `moving`, `unknown`.

Rules:
- `anchored`: SOG < 0.5 for both.
- `towing`: |ΔSOG| < 0.5 AND |ΔCOG| < 10°. Means **convoy-like motion**, not legal towing.
- `static`: tcpa_type == 'static'.
- `moving`: otherwise.

**Dependencies:** `config.py`.

**Used by:** `thresholds.py`, `feature_engineering.py`.

---

## `models/data_io.py`

**Purpose:**
Load, clean, and save AIS data.

**Key functions:**

### `load_data(path)`
Load CSV, parse timestamps, round to nearest minute.

### `remove_duplicates(features)`
Remove duplicate `(MMSI, timestamp)` rows using `select_risky_row`.

### `add_vessel_diffs(df)`
Add COG and SOG differences per vessel (time-series).

### `add_radians(df)`
Convert lat/lon to radians.

### `save_results(df, path)`
Save final results to CSV.

**Dependencies:** `helpers.py`.

**Used by:** `feature_engineering.py`.

---

## `models/thresholds.py`

**Purpose:**
Derive vessel-level thresholds and process all minutes (memory-safe,
write-to-disk).

**Key functions:**

### `derive_vessel_thresholds(df)`
Derive COG/SOG thresholds from 95th percentile.

### `process_all_minutes(clean_features, output_path)`
For each minute: build pairs, compute DCPA/TCPA, write incrementally
to `pairs_temp.csv` (~3.1 GB).

### `analyze_pairs_in_chunks(pairs_path)`
Read CSV in chunks (1M rows). Compute histograms for quantiles.
Returns: distance/TCPA/DCPA thresholds from 5th percentile.

**Dependencies:** `config.py`, `helpers.py`, `physics.py`.

**Used by:** `feature_engineering.py`.

---

## `models/anomaly.py`

**Purpose:**
Flag anomalies (per-state thresholds).

**Key functions:**

### `_anomaly_mask(df, dcpa_th, tcpa_th, distance_th)`
**Single source of truth** for "anomaly" definition.

### `flag_anomalies_per_state(valid_results, ...)`
Apply the mask to a DataFrame. Only `moving` pairs are flagged.

**Dependencies:** `config.py`.

**Used by:** `feature_engineering.py`, `validation.py`.

---

## `models/elbow.py`

**Purpose:**
KDE computation + 3 elbow methods (2nd Derivative, Kneedle, Gap).

**Key functions:**

### `compute_kde(data, num_points, max_samples)`
Compute KDE for 1D data. Downsamples if > 10K points.

### `find_elbow_second_derivative(x_grid, y_grid)`
Find elbow as max of 2nd derivative. Used for final thresholds.

### `find_elbow_kneedle`, `find_elbow_gap_statistic`
Alternative methods. Not used for final thresholds.

### `analyze_state_distributions`, `print_elbow_summary`
Plot and summarize per state.

**Dependencies:** `config.py`, `scipy`, `matplotlib`, `kneed`.

**Used by:** `feature_engineering.py`.

---

## `models/validation.py`

**Purpose:**
Validation and diagnostics.

**Key functions:**

### `out_of_time_validation(valid, ...)`
Train (00-12) / Test (12-24) split. Reports anomaly rate for each.

### `sanity_check_thresholds(valid, ...)`
Compare 5th percentile (old) vs 2nd Derivative (new).

### `manual_inspection(valid, ..., n_sample=15)`
Stratified sample: low DCPA, low TCPA, near-threshold.

### `check_anchorage_zone(valid, ...)`
Anomalies within approximate Anchorage B bounds.

### `analyze_anchorage_anomalies(valid, ...)`
SOG distribution in/out of Anchorage B.

### `anomaly_rate_by_hour(valid, ...)`
Anomaly rate per hour of day.

**Dependencies:** `config.py`, `numpy`, `pandas`.

**Used by:** `feature_engineering.py`.

---

## `models/characteristics.py`

**Purpose:**
Vessel size/speed effect on thresholds.

**Key functions:**

### `check_vessel_size_effect(valid)`
DCPA/TCPA thresholds per size class (small/medium/large).

### `check_vessel_speed_effect(valid)`
DCPA/TCPA thresholds per speed class (slow/medium/fast).

**Dependencies:** `pandas`.

**Used by:** `feature_engineering.py`.

---

## `models/db_loader.py`

**Purpose:**
Load encounter results into PostgreSQL.

**Key functions:**

### `get_engine()`
Create SQLAlchemy engine from `.env`.

### `create_schema(engine)`
Create `encounters` table + 5 indexes.

### `load_csv_to_db(csv_path, engine, chunk_size)`
Load CSV in chunks. Renames `TCPA`→`tcpa`, `DCPA`→`dcpa`.

**Dependencies:** `config.py`, `sqlalchemy`, `psycopg2`, `python-dotenv`.

**Used by:** CLI only.

---

## `models/feature_engineering.py`

**Purpose:**
Main pipeline. Orchestrates all modules.

**Sections:**
1. Load → 2. Clean → 3. Diffs → 4. Thresholds → 5. Radians
6. Process minutes → 7. Analyze chunks → 8. Load sample
9. Movement state → 10. Flag anomalies
11-15. Validation & diagnostics
16. Elbow analysis → 17. Vessel characteristics → 18. Save

**Key function:** `main()`.

**Dependencies:** All other modules.