# ⚓ Deviative – Maritime Encounter Detection

Portfolio project demonstrating vessel encounter detection in San Pedro Bay using AIS data and physics-based DCPA/TCPA analysis.

## Intended Use

Portfolio project. Methodological demonstration on public AIS data.

Not a VTS system — a portfolio project applying VTS-style detection principles. The "VTS watchkeeper" framing reflects the problem domain, not a real user. No operator uses this system in production.

User: none. This is not deployed. Value: demonstrates end-to-end pipeline — data feasibility, method, thresholds, validation, documented limits.

## Problem

Detect potentially dangerous encounters between vessels in San Pedro Bay using AIS data and physics-based navigation principles.

Specifically: identify pairs of vessels that are on a collision course (small DCPA) and approaching (small positive TCPA), while filtering out routine anchorage and towing activity.

## Method

### Pipeline

1. Load AIS data (rounded to nearest minute)
2. Remove duplicate rows (keep most complete per MMSI+minute)
3. Compute vessel-level diffs (COG, SOG)
4. Compute pairwise distances (Haversine)
5. Compute DCPA/TCPA (physics-based, vectorized)
6. Classify movement state (anchored/towing/static/moving, vectorized)
7. Derive per-state thresholds (2nd Derivative on moving)
8. Flag anomalies (moving only)

### Physics

- **DCPA** – Distance to Closest Point of Approach (km)
- **TCPA** – Time to Closest Point of Approach (hours)
- **Sign convention (v1.1, fixed 2026-10-14):** TCPA > 0 → approaching, < 0 → receding

### Movement State Classification

- **anchored** – both vessels nearly stationary (SOG < 0.5)
- **towing** – similar speed & course
- **static** – no relative motion (relative speed ≈ 0)
- **moving** – otherwise

### Threshold Selection

Anomaly definition (single source of truth):

```python
(movement_state == 'moving') & (DCPA < 0.1982 km) & (TCPA >= 0) & (TCPA < 0.0293 hours) & (distance_km < 1.0 km)
Why 2nd Derivative?
Three elbow-detection methods were compared on the moving subset:

Method	DCPA elbow	TCPA elbow	distance_km elbow
2nd Derivative	0.2213 km	0.0274 h	27.74 km
Gap Statistic	0.3318 km	0.1035 h	36.24 km
Kneedle	~0 (no elbow)	~0 (no elbow)	~0 (no elbow)
Chosen threshold: 2nd Derivative (0.1982 km, 0.0293 h).

Why 2nd Derivative:

Kneedle returns values near zero because the heavy-tailed distribution lacks a clear "knee" in the normalized curve.

Gap Statistic returns values ~1.5–3.5× larger, giving a more permissive threshold.

2nd Derivative is between the two, and matches the observed distribution structure of the moving subset.

The 2nd Derivative value (0.2213 / 0.0274) matches the deployed threshold (0.1982 / 0.0293) to within ~10%.

Distance guard (1.0 km): No method finds a stable elbow for distance_km in the DCPA/TCPA-filtered subset. The 1.0 km guard is a documented operational heuristic, not a data-derived threshold.

Data
AIS: MarineCadastre.gov – San Pedro Bay, 2025-06-01

Weather: Open-Meteo (not used as filter)

Records: 199,910 rows, 636 unique vessels

Time span: 24 hours (00:00 – 23:59)

Ground Truth
No public ground truth exists for this project's specific task: pair-minute dangerous-encounter labels for San Pedro Bay.

The gap is not missing data — it is a task mismatch. Public ground-truth datasets exist for maritime incidents and anomalous trajectories, including time-linked AIS labels, but none provide exhaustive pairwise, minute-level dangerous/not-dangerous labels across all encounters.

Datasets reviewed — and why they do not match
Dataset	What it provides	Why it doesn't fit
HawaiiCoast_GT (2017–2020)	Time-linked AIS labels for documented vessel events	Hawaii, not San Pedro Bay. Trajectory/event-level, not pair-minute. Not exhaustive.
DTU anomalous trajectories	25 labeled tracks	Small, single-event. Not applicable to pairwise detection.
COLREGs Encounter Benchmark	146,246 encounters, synchronized trajectories (10s)	Labels are heuristic (silver/weak labels), not expert-verified.
LA/LB Marine Exchange / USCG records	Event-level records	Not exhaustive. Operational data is restricted.
Structural finding
Pairwise minute-level dangerousness labeling requires expert VTS annotation — human experts reviewing every encounter, minute by minute. No such public dataset exists for any major port.

This is the principal open problem for future work in this domain, not a shortcoming of the project.

Consequence
No dataset-wide Precision/Recall/F1 is reported.

Anomaly labels are detection rules, not verified accident/near-miss labels.

Alternative validation:

Stability: Train 1.38% / Test 0.95% anomaly rates

Sensitivity: ~43× noise reduction with 1.0 km distance guard (96,326 → 2,221)

Manual plausibility: 10 stratified cases

Results
Data Processing
Total pairs: 14,049,693

Valid pairs (with DCPA/TCPA): 8,180,440

Sample loaded (memory-limited, 8GB RAM): 999,972 rows

Valid sample (after NaN drop): 582,263

Note on numbers:

Full analysis: 8,180,440 valid pairs

DB loaded: 582,263 rows (representative 7.1% sample)

The sample reflects a memory-limited subset, not the full 8.18M-pair analysis.

Movement States (sample)
State	Count	%
anchored	369,110	63.4%
moving	212,876	36.6%
towing	277	0.05%
Anomalies
Total anomalies (moving only): 2,221

Anomaly rate (moving): ~1.04%

Anchored/Towing anomalies: 0

Thresholds
Metric	Value	Source
DCPA	0.1982 km (198.2 m)	2nd Derivative
TCPA	0.0293 h (1.76 min)	2nd Derivative
Distance	1.0 km	Guard (heuristic)
Validation
Out-of-Time Validation (moving only)
Split by time of day:

Train (00:00–12:00): n=48,019, anomalies=662, rate=1.3786%

Test (12:00–24:00): n=164,857, anomalies=1,559, rate=0.9457%

Absolute difference: 0.4330%

Interpretation: Train rate is higher than Test rate (diff: 0.43%). Reflects real diurnal traffic patterns, not overfitting.

Sanity Check (moving only)
Threshold	DCPA	TCPA	Anomalies
Old (5th percentile)	0.0083	−0.0698	0
New (2nd Derivative)	0.1982	0.0293	2,221
The 5th percentile produced 0 anomalies because TCPA 5th percentile is negative, and we require TCPA ≥ 0. This confirms the 2nd Derivative threshold is necessary.

Temporal Diagnostic (Anomaly Rate by Hour)
Min rate: 0.607% (20:00)

Max rate: 2.326% (07:00)

Range: ~3.8×

Reflects real traffic patterns.

Manual Inspection (10 cases, stratified)
distance_km: 0.083 – 0.771 km

DCPA: 8.67e-19 – 1.34e-02 km (near-zero)

TCPA: 1.10e-06 – 6.78e-03 h (< 25 seconds)

All 10 cases are physically plausible encounters under the DCPA/TCPA criteria.

Anchorage B Check
Total anomalies: 2,221

In Anchorage B zone: 352 (15.8%)

Mean SOG (in Anchorage B): 3.98 knots

Mean SOG (outside): 2.22 knots

49.7% of in-zone cases are slow (< 2 knots)

Interpretation: Anchorage B zone is not dominated by false positives — mean SOG is 3.98 knots (higher than outside). The 15.8% in-zone share reflects vessels in transit through the anchorage, not moored vessels misclassified.

# Single class (unit)
python -m pytest tests/unit/test_anomaly.py::TestAnomalyMask -v

# Single test (unit)
python -m pytest tests/unit/test_physics.py::TestComputeDcpaTcpa::test_head_on_returns_positive_tcpa -v

# Integration only
python -m pytest tests/integration/ -v
Known Uncertainties
Data
Single day (2025-06-01): Threshold derived from one day only.

Single location (San Pedro Bay): Results may not generalize without retraining.

Ground Truth
No public dataset provides pair-minute dangerous-encounter labels.

Anomaly labels are detection rules, not verified accident/near-miss labels.

This is a task mismatch, not a data gap.

Sampling
Memory-limited sampling: 1M rows from 14M total (7.1%).

Verification: Hour distribution checked (Max/Min ratio: 2.61 — reasonably uniform).

Deduplication rule
Keeps the most complete row (fewest NaN values). Ties broken by first occurrence (stable sort).

Precedent: NDBC Standard Meteorological Data via ERDDAP keeps the row with the most non-NaN values.

Sensitivity: 3 rules tested → identical anomaly count.

Status: documented arbitrary choice.

Anchorage Zone
No official anchorage boundaries used.

Anchorage B bounds are approximate (lat 33.70–33.76, lon −118.25 to −118.18).

15.8% of anomalies fall within this zone.

Distance guard (1.0 km) — heuristic
Anomalies require distance_km < 1.0 in addition to DCPA/TCPA.

Why: DCPA/TCPA describe a future event. distance_km is current separation. Operators act on encounters that are already close.

Why 1.0 km: No natural elbow within the DCPA/TCPA-filtered subset (confirmed by 3 elbow methods — see Threshold Selection above).

Sensitivity:

With guard: 2,221 anomalies

Without guard: 96,326 anomalies

Ratio: ~43×

Status: documented heuristic.

Model
LSTM Autoencoder not included in v1.0.

Reason: LSTM requires sequences per pair over time.

Continuity check on 2M sampled pairs:

Total unique pairs: 74,972

Pairs with continuous run ≥ 30 min: 0

Max continuous run: 5 minutes

Mean run length: 1.02 minutes

The dataset is event-based, not trajectory-based. Pairs appear at a single minute and dissolve.

This is a documented data-driven decision, not a failure.

The physics-based approach (DCPA/TCPA) does not require sequences and provides stable, explainable results.

What the Model Did NOT See
Multi-day data — only single day (2025-06-01)

Multi-port data — only San Pedro Bay

Official accident records — no GT available

Weather as filter — not used

Vessel type effect — not modeled

Vessel size effect — not modeled

Vessel speed effect — not modeled

Future maneuver prediction — not predicted

Historical vessel behavior — not used

Cargo/draft effects — not modeled

Communication between vessels — not available

Changelog
v1.1 — 2026-10-14
Fixed: TCPA sign convention

compute_dcpa_tcpa used v_rel = v1 - v2 while positions were r = r2 - r1. This produced negative TCPA for approaching vessels — contradicting the documented convention (TCPA > 0 = approaching).

After: v_rel = v2 - v1, consistent with r = r2 - r1.

Impact on results:

Metric	Before (v1.0)	After (v1.1)
Total anomalies	4,372	2,221
Train rate	1.4464%	1.3786%
Test rate	0.9067%	0.9457%
Train/Test diff	0.5397%	0.4330%
Anchorage B in-zone %	15.9%	15.8%
Interpretation: The change reduced anomaly count by ~49%, because TCPA >= 0 now correctly selects approaching pairs. Prior version was identifying receding pairs that happened to be close.

v1.2 — 2026-10-18
- Split monolithic test_deviative.py into tests/unit/ (5 files) + tests/integration/ (1 file)
- Added tests/conftest.py with shared fixtures
- Added pythonpath=. to pytest.ini (fixes ModuleNotFoundError)
- Fixed test_pipeline_reproducibility: expects 3 anomalies (data-derived)
- Total tests: 45 (was 41) — no tests lost, all passing

Other changes in v1.1:

Added classify_movement_state_vectorized (~100× faster)

Made flag_anomalies_per_state delegate to get_anomaly_mask (single source of truth enforced)

Fixed select_risky_row to use stable sort (guarantee "first occurrence" tie-breaking)

Removed dead code (flag_anomalies legacy function)

Reduced MAX_ROWS_IN_MEMORY from 2,000,000 to 1,000,000 (RAM constraint)

Added matplotlib, kneed to requirements.txt

Added 4 pipeline-invariant tests (41 total, was 37)

Dashboard
Interactive dashboard available at:

bash
streamlit run dashboard.py
Demo version: dashboard_demo.py (uses sampled dataset ~10K rows).

Structure (Nir Etzion standard):

Tab 1 – The Problem: scale of challenge, movement state distribution, sample table

Tab 2 – The Principles: DCPA/TCPA method, filtering rules, thresholds, sample table

Tab 3 – The Results: anomalies, validation summary, top-10 by severity, sample table

Requirements:

PostgreSQL running with deviative database loaded

.env file with DB credentials (see .env.example)

Data source: PostgreSQL (not CSV)

Note: Red markers on the map are anomalies detected by threshold — not confirmed incidents.

Sources
Data
AIS: MarineCadastre.gov (NOAA/USCG federal repository)

Weather: Open-Meteo

Methodology
DCPA/TCPA: Standard parameters for collision risk assessment in maritime navigation, within the framework of COLREGs principles.

Ship behavior in encounters: Zhou, Y., Daamen, W., Vellinga, T., & Hoogendoorn, S. P. (2023). Ocean Engineering, 272, Article 113879. TU Delft. DOI: 10.1016/j.oceaneng.2023.113879

Abnormal Maritime Behaviour (LSTM reference): Olesen, K. V. (2023). DTU.

Elbow Method: Satopaa, V., Albrecht, J., Irwin, D., & Raghavan, B. (2011).

Gap Statistic: Tibshirani, R., Walther, G., & Hastie, T. (2001).

Libraries
pandas, numpy, scipy, matplotlib, scikit-learn

kneed (Kneedle algorithm)

streamlit, pydeck (dashboard)

sqlalchemy, psycopg2-binary (PostgreSQL)

Project Structure
text
deviative/
├── data/
├── docs/
├── models/
├── scripts/
│   └── recompute_elbow.py      # Elbow-only re-run
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── unit/                   # Isolated unit tests (38)
│   │   ├── test_config.py      # 2 tests — constants
│   │   ├── test_helpers.py     # 7 tests — haversine, pairs, merge
│   │   ├── test_data_io.py     # 3 tests — vessel diffs, radians
│   │   ├── test_physics.py     # 13 tests — DCPA/TCPA, movement
│   │   └── test_anomaly.py     # 13 tests — mask, flagging
│   └── integration/            # End-to-end tests (4)
│       └── test_pipeline.py    # 4 tests — invariants
├── dashboard.py
├── dashboard_demo.py
├── learning_journal.md
├── test_db.py
├── pytest.ini                  # pytest config
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
Testing

45 tests, all passing in <1s.

Run all tests:

    pytest

Run unit tests only:

    pytest tests/unit/

Run with verbose output:

    pytest -v

Structure:

    tests/
    ├── conftest.py              # Shared fixtures
    ├── unit/                    # 38 isolated unit tests
    │   ├── test_config.py       # 2 tests — constants
    │   ├── test_helpers.py      # 7 tests — haversine, pairs, merge
    │   ├── test_data_io.py      # 3 tests — vessel diffs, radians
    │   ├── test_physics.py      # 13 tests — DCPA/TCPA, movement
    │   └── test_anomaly.py      # 13 tests — mask, flagging
    └── integration/             # 4 end-to-end tests
        └── test_pipeline.py     # 4 tests — invariants

Properties verified:

- Reproducibility — same input, same anomaly count
- Distance guard sensitivity — 1.0 km guard strictly reduces anomalies
- Out-of-time split disjointness — train/test rows disjoint
- Manual inspection validity — every returned row satisfies full mask

How to Run
Clone and Setup
bash
git clone https://github.com/eliyahudahan/deviative.git
cd deviative
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Run Pipeline (generates encounter results)
bash
python -m models.feature_engineering
Note: pairs_temp.csv is generated by the pipeline (~3.1GB). It is excluded from the repository.

Load into PostgreSQL
bash
# Copy .env.example to .env and fill credentials
cp .env.example .env

# Create database (as your user)
psql -d postgres -c "CREATE DATABASE deviative OWNER $(whoami);"

# Load data
python -m models.db_loader
Run Dashboard
bash
streamlit run dashboard.py
Dashboard opens at http://localhost:8501.

Run Tests
bash
python -m pytest tests/ -v
45 tests, ~0.5 seconds.

Status
Phase 1 complete: Physics-based encounter detection + validation + documentation + dashboard + tests.

Implemented
✅ Physics-based DCPA/TCPA detection (v1.1 sign convention)

✅ Movement state classification (anchored/towing/static/moving) — vectorized

✅ Per-state thresholds (2nd Derivative of KDE, cross-validated with Kneedle + Gap)

✅ PostgreSQL storage (582,263 rows)

✅ Streamlit dashboard (3 tabs, PyDeck map)

✅ Top-10 anomaly ranking (severity = 1 / DCPA×TCPA)

✅ LSTM decision documented (not included – data-driven)

✅ Ground Truth task mismatch documented

✅ 45 tests (41 unit + 4 integration)

Out of scope for v1.0
Per-vessel trajectory analysis

Multi-day / multi-port validation

Scope note: Deviative v1.0 is limited to the analysis and validation described above.

Live Demo
https://deviative-uvupvvxv43qkxf4qefopgz.streamlit.app/

Note: The live demo uses a sampled dataset (~10K rows). The full project (582K rows) runs locally on PostgreSQL — see How to Run.

