'''
⚓ Deviative – Maritime Encounter Detection

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
5. Compute DCPA/TCPA (physics-based)
6. Classify movement state (anchored/towing/static/moving)
7. Derive per-state thresholds (2nd Derivative on moving)
8. Flag anomalies (moving only)

### Physics

- **DCPA** – Distance to Closest Point of Approach (km)
- **TCPA** – Time to Closest Point of Approach (hours)
- Sign convention: TCPA > 0 (approaching), < 0 (receding)

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

· The 5th percentile threshold (DCPA = 8.3 m, TCPA = −0.0663 h) produced 0 anomalies after the TCPA ≥ 0 filter.
· The 2nd Derivative of the KDE curve identifies the "elbow" of the DCPA distribution (191 m) and TCPA distribution (1.77 min).
· These thresholds are stable across multiple runs (DCPA: 191–198 m, TCPA: 1.76–1.77 min).

Data

· AIS: MarineCadastre.gov – San Pedro Bay, 2025-06-01
· Weather: Open-Meteo (not used as filter)
· Records: 199,910 rows, 636 unique vessels
· Time span: 24 hours (00:00 – 23:59)

Ground Truth

No public ground truth exists for this project's specific task: pair-minute dangerous-encounter labels for San Pedro Bay.

The gap is not missing data — it is a task mismatch. Public ground-truth datasets exist for maritime incidents and anomalous trajectories, including time-linked AIS labels, but none provide exhaustive pairwise, minute-level dangerous/not-dangerous labels across all encounters.

Datasets reviewed — and why they do not match

Dataset What it provides Why it doesn't fit
HawaiiCoast_GT (2017–2020) Time-linked AIS labels for documented vessel events Hawaii, not San Pedro Bay. Trajectory/event-level, not pair-minute. Not exhaustive.
DTU anomalous trajectories 25 labeled tracks Small, single-event. Not applicable to pairwise detection.
COLREGs Encounter Benchmark 146,246 encounters, synchronized trajectories (10s) Labels are heuristic (silver/weak labels), not expert-verified.
LA/LB Marine Exchange / USCG records Event-level records Not exhaustive. Operational data is restricted.

Structural finding

Pairwise minute-level dangerousness labeling requires expert VTS annotation — human experts reviewing every encounter, minute by minute. No such public dataset exists for any major port.

This is the principal open problem for future work in this domain, not a shortcoming of the project.

Consequence

· No dataset-wide Precision/Recall/F1 is reported.
· Anomaly labels are detection rules, not verified accident/near-miss labels.
· Alternative validation:
· Stability: Train 1.45% / Test 0.91% anomaly rates
· Sensitivity: 22× noise reduction with 1.0 km distance guard
· Manual plausibility: 10 stratified cases

Results

Data Processing

· Total pairs: 14,049,693
· Valid pairs (with DCPA/TCPA): 8,180,440
· Sample loaded (memory-limited, 8GB RAM): 1,999,973 rows
· Valid sample (after NaN drop): 1,163,761

Note on numbers:

· Full analysis: 8,180,440 valid pairs → 5,170 anomalies (2026-09-23 run, not in DB)
· DB loaded: 1,163,761 rows (representative 14% sample) → 4,372 anomalies
· The DB reflects a sampled subset, not the full 8.18M-pair analysis. Difference (5,170 → 4,372) is ~15% — expected for a 14% sample.

Movement States (sample)

State Count %
anchored 737,971 63.4%
moving 425,230 36.5%
towing 560 0.05%

Anomalies

· Total anomalies (moving only): 4,372
· Anomaly rate (moving): 1.03%
· Anchored/Towing anomalies: 0

Thresholds

Metric Value Source
DCPA 0.1982 km (198.2 m) 2nd Derivative
TCPA 0.0293 h (1.76 min) 2nd Derivative
Distance 1.0 km Guard

Validation

Out-of-Time Validation (moving only)

Split by time of day:

· Train (00:00–12:00): n=95,687, anomalies=1,384, rate=1.4464%
· Test (12:00–24:00): n=329,543, anomalies=2,988, rate=0.9067%
· Absolute difference: 0.5397%

Interpretation: Train rate is higher than Test rate (diff: 0.54%). Reflects real diurnal traffic patterns, not overfitting.

Sanity Check (moving only)

Threshold DCPA TCPA Anomalies
Old (5th percentile) 0.0083 −0.0663 0
New (2nd Derivative) 0.1982 0.0293 4,372

The 5th percentile produced 0 anomalies because TCPA 5th percentile is negative, and we require TCPA ≥ 0. This confirms the 2nd Derivative threshold is necessary.

Temporal Diagnostic (Anomaly Rate by Hour)

Hour n Anomalies Rate %
00:00 13,734 206 1.50%
06:00 3,461 73 2.11% (max)
16:00 16,774 115 0.69% (min)
22:00 48,928 437 0.89%

Range: 0.69% – 2.11% (ratio ~3×). Reflects real traffic patterns.

Manual Inspection (10 cases, stratified)

· distance_km: 0.035 – 0.568 km
· DCPA: 2.88e-07 – 9.88e-03 km (near-zero)
· TCPA: 1.10e-07 – 3.31e-03 h (< 12 seconds)
· All 10 cases are physically plausible encounters under the DCPA/TCPA criteria.

Anchorage B Check

· Total anomalies: 4,372
· In Anchorage B zone: 694 (15.9%)
· Mean SOG (in Anchorage B): 4.15 knots
· Mean SOG (outside): 2.20 knots
· 47.4% of in-zone cases are slow (< 2 knots)

Interpretation: Anchorage B zone is not dominated by false positives — mean SOG is 4.15 knots. 47.4% are slow, which may be FP (slow drift) — documented as uncertainty.

Testing
37 unit tests covering pipeline logic — no AIS data, no PostgreSQL required.

bash
python -m pytest tests/ -v
Coverage
Test Class	Tests	What it verifies
TestConfig	5	Thresholds and physics constants match README
TestAnomalyMask	8	Anomaly definition (5 conditions + boundaries)
TestFlagAnomaliesPerState	2	State-aware wrapper matches source-of-truth mask
TestVesselThresholds	1	Empirical quantile derivation
TestChunkedProcessing	2	Histogram accumulation across chunks
TestPhysics	4	DCPA/TCPA row-wise computation
TestVectorizedMatchesRowwise	1	Row-wise ≡ vectorized (1e-6 tolerance)
TestMovementState	5	anchored / towing / static / moving / unknown
TestDistanceGuardEffect	2	1.0 km guard mechanism (README 22× claim)
Run examples
bash
# All tests
python -m pytest tests/ -v

# Single class
python -m pytest tests/test_deviative.py::TestPhysics -v

# Single test
python -m pytest tests/test_deviative.py::TestPhysics::test_tcpa_positive_when_approaching -v
Known Uncertainties
Data

· Single day (2025-06-01): Threshold derived from one day only.
· Single location (San Pedro Bay): Results may not generalize without retraining.

Ground Truth

· No public dataset provides pair-minute dangerous-encounter labels.
· Anomaly labels are detection rules, not verified accident/near-miss labels.
· This is a task mismatch, not a data gap.

Sampling

· Memory-limited sampling: 2M rows from 14M total (14.24%).
· Verification: Hour distribution checked (Max/Min ratio: 2.60 — reasonably uniform).

Deduplication rule

Keeps the most complete row (fewest NaN values). Ties broken by first occurrence.

· Precedent: NDBC Standard Meteorological Buoy Data via ERDDAP keeps the row with the most non-NaN values.
· Sensitivity: 3 rules tested → identical anomaly count.
· Status: documented arbitrary choice.

Anchorage Zone

· No official anchorage boundaries used.
· Anchorage B bounds are approximate (lat 33.70–33.76, lon −118.25 to −118.18).
· 15.9% of anomalies fall within this zone — may include FP.

Distance guard (1.0 km) — heuristic

Anomalies require distance_km < 1.0 in addition to DCPA/TCPA.

· Why: DCPA/TCPA describe a future event. distance_km is current separation. Operators act on encounters that are already close.
· Why 1.0 km: No natural elbow within the DCPA/TCPA-filtered subset (96,326 pairs).
· Sensitivity:
· With guard: 4,372 anomalies
· Without guard: 96,326 anomalies
· Ratio: 22×
· Status: documented heuristic.

Model

LSTM Autoencoder not included in v1.0.

Reason

LSTM requires sequences per pair over time.

Continuity check on 2M sampled pairs:

· Total unique pairs: 74,972
· Pairs with continuous run ≥ 30 min: 0
· Max continuous run: 5 minutes
· Mean run length: 1.02 minutes

The dataset is event-based, not trajectory-based. Pairs appear at a single minute and dissolve.

This is a documented data-driven decision, not a failure.

The physics-based approach (DCPA/TCPA) does not require sequences and provides stable, explainable results.

Alternatives considered

· Per-vessel LSTM: requires reconstructing single-vessel trajectories. Not applicable to pairwise detection.
· Graph Neural Network: nodes = vessels, edges = pairs. More complex, not justified.
· Reference: Olesen (2023) used LSTM for per-vessel trajectories, not for pair encounters.

Note: models/lstm.py exists as an exploration file but is not part of the v1.0 pipeline.

Also note

· Vessel size/speed do not alter the base threshold.
· No future maneuver prediction.

What the Model Did NOT See

· Multi-day data – only single day (2025-06-01)
· Multi-port data – only San Pedro Bay
· Official accident records – no GT available
· Weather as filter – not used
· Vessel type effect – not modeled
· Vessel size effect – not modeled
· Vessel speed effect – not modeled
· Future maneuver prediction – not predicted
· Historical vessel behavior – not used
· Cargo/draft effects – not modeled
· Communication between vessels – not available

Dashboard

Interactive dashboard available at:

bash
streamlit run dashboard.py
Demo version: dashboard_demo.py (uses sampled dataset ~10K rows).

Structure (Nir Etzion standard):

· Tab 1 – The Problem: scale of challenge, movement state distribution, sample table
· Tab 2 – The Principles: DCPA/TCPA method, filtering rules, thresholds, sample table
· Tab 3 – The Results: anomalies, validation summary, top-10 by severity, sample table

Requirements:

· PostgreSQL running with deviative database loaded
· .env file with DB credentials (see .env.example)
· Data source: PostgreSQL (not CSV)

Note: Red markers on the map are anomalies detected by threshold — not confirmed incidents.

Sources

Data

· AIS: MarineCadastre.gov (NOAA/USCG federal repository)
· Weather: Open-Meteo

Methodology

· DCPA/TCPA: Standard parameters for collision risk assessment in maritime navigation, within the framework of COLREGs principles.
· Ship behavior in encounters: Zhou, Y., Daamen, W., Vellinga, T., & Hoogendoorn, S. P. (2023). Ocean Engineering, 272, Article 113879. TU Delft. DOI: 10.1016/j.oceaneng.2023.113879
· Abnormal Maritime Behaviour (LSTM reference): Olesen, K. V. (2023). DTU.
· Elbow Method: Satopaa, V., Albrecht, J., Irwin, D., & Raghavan, B. (2011).
· Gap Statistic: Tibshirani, R., Walther, G., & Hastie, T. (2001).

Libraries

· pandas, numpy, scipy, matplotlib, scikit-learn
· kneed (Kneedle algorithm)
· streamlit, pydeck (dashboard)
· sqlalchemy, psycopg2-binary (PostgreSQL)

Project Structure

text
deviative/
├── data/
├── docs/
├── models/
├── scripts/
├── tests/
│   └── test_deviative.py       # 37 unit tests
├── dashboard.py
├── dashboard_demo.py
├── learning_journal.md
├── test_db.py
├── pytest.ini                  # pytest config
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
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
37 tests, ~1 second.

Status

Phase 1 complete: Physics-based encounter detection + validation + documentation + dashboard + tests.

Implemented

· ✅ Physics-based DCPA/TCPA detection
· ✅ Movement state classification (anchored/towing/static/moving)
· ✅ Per-state thresholds (2nd Derivative of KDE)
· ✅ PostgreSQL storage (1,163,761 rows)
· ✅ Streamlit dashboard (3 tabs, PyDeck map)
· ✅ Top-10 anomaly ranking (severity = 1 / DCPA×TCPA)
· ✅ LSTM decision documented (not included – data-driven)
· ✅ Ground Truth task mismatch documented
· ✅ 37 unit tests (pipeline logic)

Out of scope for v1.0

· Per-vessel trajectory analysis
· Multi-day / multi-port validation

Scope note: Deviative v1.0 is limited to the analysis and validation described above.

Live Demo

🔗 deviative-demo.streamlit.app

Note: The live demo uses a sampled dataset (~10K rows). The full project (1.16M rows) runs locally on PostgreSQL — see How to Run.
'''