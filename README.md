# ⚓ Deviative – Maritime Encounter Detection

**Portfolio project demonstrating vessel encounter detection in San Pedro Bay using AIS data and physics-based DCPA/TCPA analysis.**

---

## For Whom

**This is a portfolio project** demonstrating ability to develop maritime anomaly detection systems.

- **Intended use:** Vessel Traffic Service (VTS) operations
- **User:** VTS watchkeeper
- **Value:** Detect dangerous encounters between moving vessels in real time
- **Status:** Portfolio project – not deployed in production

---

## Problem

Detect potentially dangerous encounters between vessels in San Pedro Bay using AIS data and physics-based navigation principles.

Specifically: identify pairs of vessels that are on a collision course (small DCPA) and approaching (small positive TCPA), while filtering out routine anchorage and towing activity.

---

## Method

### Pipeline
1. Load AIS data (rounded to nearest minute)
2. Remove duplicate rows (keep most risky per MMSI+minute)
3. Compute vessel-level diffs (COG, SOG)
4. Compute pairwise distances (Haversine)
5. Compute DCPA/TCPA (physics-based)
6. Classify movement state (anchored/towing/moving)
7. Derive per-state thresholds (2nd Derivative on moving)
8. Flag anomalies (moving only)

### Physics
- **DCPA** – Distance to Closest Point of Approach (km)
- **TCPA** – Time to Closest Point of Approach (hours)
- **Sign convention:** TCPA > 0 (approaching), < 0 (receding)

### Movement State Classification
- **anchored** – both vessels nearly stationary (SOG < 0.5)
- **towing** – similar speed & course
- **static** – no relative motion
- **moving** – otherwise

### Threshold Selection

Anomaly definition (single source of truth):

```python
(movement_state == 'moving') &
(DCPA < 0.1982 km) &
(TCPA >= 0) &
(TCPA < 0.0293 hours) &
(distance_km < 1.0 km)
Why 2nd Derivative?

The 5th percentile threshold (DCPA=8.3m, TCPA=-0.0663h) produced 0 anomalies after the TCPA ≥ 0 filter (5th percentile TCPA is negative).

The 2nd Derivative of the KDE curve identifies the "elbow" of the DCPA distribution (191m) and TCPA distribution (1.77 min).

These thresholds are stable across multiple runs (DCPA: 191-198m, TCPA: 1.76-1.77 min).

Data
AIS: MarineCadastre.gov – San Pedro Bay, 2025-06-01

Records: 199,910 rows, 636 unique vessels

Time span: 24 hours (00:00 – 23:59)

Weather: Not used as a filter (max wind 13.9 km/h – no extreme conditions)

Ground Truth
No independent ground truth is available.

There is no official record of "dangerous encounters" or "near-misses" for this dataset. Anomaly labels are detection rules, not verified accident/near-miss labels.

Therefore:

No Precision/Recall/F1 is reported.

Instead: stability, sensitivity, and manual plausibility are documented.

## Results

### Data Processing
- **Total pairs:** 14,049,693
- **Valid pairs (with DCPA/TCPA):** 8,180,440
- **Sample loaded (memory-limited, 8GB RAM):** 1,999,973 rows
- **Valid sample (after NaN drop):** 1,163,761

**Note on numbers:**
- Full analysis: 8,180,440 valid pairs → **5,170 anomalies** (23.09.2026 run, not in DB)
- DB loaded: 1,163,761 rows (representative 14% sample) → **4,372 anomalies**
- The DB reflects a sampled subset, not the full 8.18M-pair analysis.
- Difference (5,170 → 4,372) is ~15% – expected for a 14% sample.
- Both are documented; neither is a contradiction.

Movement States (sample)
State	Count	%
anchored	737,971	63.4%
moving	425,230	36.5%
towing	560	0.05%
Anomalies
Total anomalies (moving only): 4,372

Anomaly rate (moving): 1.03%

Anchored/Towing anomalies: 0

Thresholds
Metric	Value	Source
DCPA	0.1982 km (198.2 m)	2nd Derivative
TCPA	0.0293 h (1.76 min)	2nd Derivative
Distance	1.0 km	Guard
Validation
Out-of-Time Validation (moving only)
Split by time of day:

Train (00:00–12:00): n=95,687, anomalies=1,384, rate=1.4464%

Test (12:00–24:00): n=329,543, anomalies=2,988, rate=0.9067%

Absolute difference: 0.5397%

Interpretation: Train rate is higher than Test rate (diff: 0.54%). This reflects real diurnal traffic patterns, not overfitting.

Sanity Check (moving only)
Threshold	DCPA	TCPA	Anomalies
Old (5th percentile)	0.0083	-0.0663	0
New (2nd Derivative)	0.1982	0.0293	4,372
The 5th percentile produced 0 anomalies because TCPA 5th percentile is negative, and we require TCPA ≥ 0. This confirms the 2nd Derivative threshold is necessary.

Temporal Diagnostic (Anomaly Rate by Hour)
Hour	n	Anomalies	Rate %
00:00	13,734	206	1.50%
06:00	3,461	73	2.11% (max)
16:00	16,774	115	0.69% (min)
22:00	48,928	437	0.89%
Range: 0.69% – 2.11% (ratio ~3×). Reflects real traffic patterns – morning has fewer but more dangerous encounters.

Manual Inspection (10 cases, stratified)
Sample of 10 anomalies showed:

distance_km: 0.035 – 0.568 km

DCPA: 2.88e-07 – 9.88e-03 km (near-zero)

TCPA: 1.10e-07 – 3.31e-03 h (< 12 seconds)

All 10 cases are physically plausible encounters under the DCPA/TCPA criteria.

Anchorage B Check
Total anomalies: 4,372

In Anchorage B zone: 694 (15.9%)

Mean SOG (in Anchorage B): 4.15 knots

Mean SOG (outside): 2.20 knots

47.4% of in-zone cases are slow (< 2 knots)

Interpretation: Anchorage B zone is NOT dominated by false positives – mean SOG is 4.15 knots (higher than outside), indicating actual vessel movement. 47.4% are slow, which may be FP (slow drift) – documented as uncertainty.

Known Uncertainties
Data
Single day (2025-06-01): Threshold derived from one day only. Not validated on other days or ports.

Single location (San Pedro Bay): Results may not generalize to other ports without retraining.

Ground Truth
No independent ground truth: No official record of "dangerous encounters" exists.

Anomaly labels are detection rules, not verified accident/near-miss labels.

Sampling
Memory-limited sampling: 2M rows from 14M total (14.24%).

Assumption: Chunks have roughly uniform rows-per-minute.

Verification: Hour distribution checked (Max/Min ratio: 2.60 – reasonably uniform).

Temporal Patterns
Anomaly rate varies by hour: 0.69% (16:00) to 2.11% (06:00).

Morning periods may be overrepresented if uniform rate is assumed.

Anchorage Zone
No official anchorage boundaries were used.

Anchorage B bounds are approximate (lat 33.70-33.76, lon -118.25 to -118.18).

15.9% of anomalies fall within this zone – may include FP.

### Model

**LSTM not included in v1.0.**

Reason:
- LSTM Autoencoder requires sequences per pair over time.
- Continuity check on 2M sampled pairs:
  - Total unique pairs: 74,972
  - Pairs with continuous run >= 30 min: **0**
  - Max continuous run: **5 minutes**
  - Mean run length: 1.02 minutes
- The dataset is **event-based**, not trajectory-based.
- Pairs appear at a single minute and dissolve.

**This is a documented data-driven decision, not a failure.**

The physics-based approach (DCPA/TCPA) does not require sequences
and provides stable, explainable results.

**Alternatives considered:**
- Per-vessel LSTM: would require reconstructing single-vessel trajectories.
  Not applicable to pairwise detection.
- Graph Neural Network: nodes = vessels, edges = pairs. More complex,
  not justified for the current dataset.
- Reference: Olesen (2023) used LSTM for per-vessel trajectories,
  not for pair encounters.

- **Vessel size/speed** do not alter the base threshold.
- **No future maneuver prediction.**

What the Model Did NOT See
Multi-day data – only single day (2025-06-01).

Multi-port data – only San Pedro Bay.

Official accident records – no GT available.

Weather as filter – not used (max wind 13.9 km/h).

Vessel type effect – not modeled.

Vessel size effect – not modeled (DCPA_q05 similar across sizes).

Vessel speed effect – not modeled (DCPA_q05 similar across speeds).

Future maneuver prediction – not predicted.

Historical vessel behavior – not used.

Cargo/draft effects – not modeled.

Communication between vessels – not available.

Sources
Data
AIS: MarineCadastre.gov (NOAA/USCG federal repository)

Methodology
DCPA/TCPA: IMO COLREGs (International Regulations for Preventing Collisions at Sea)

Ship behavior in encounters: Zhou, Y., Daamen, W., Vellinga, T., & Hoogendoorn, S. P. (2023). Ship behavior during encounters in ports and waterways based on AIS data: From theoretical definitions to empirical findings. Ocean Engineering, 272, Article 113879. TU Delft. DOI: 10.1016/j.oceaneng.2023.113879

Abnormal Maritime Behaviour (LSTM reference): Olesen, K. V. (2023). Enhancing Situation Awareness of Maritime Surveillance Operators using Deep Learning based Abnormal Maritime Behaviour Detection. DTU.

Elbow Method: Satopaa, V., Albrecht, J., Irwin, D., & Raghavan, B. (2011). Finding a Knee in a Haystack: Detecting Knee Points in System Behavior.

Gap Statistic: Tibshirani, R., Walther, G., & Hastie, T. (2001). Estimating the number of clusters in a data set via the gap statistic.

Libraries
pandas, numpy, scipy, matplotlib, scikit-learn

kneed (Kneedle algorithm)

Project Structure
text
deviative/
├── models/
│   ├── __init__.py
│   ├── config.py               # Constants and thresholds
│   ├── helpers.py              # Haversine, distances, merges
│   ├── physics.py              # DCPA/TCPA, movement_state
│   ├── data_io.py              # Load, clean, save
│   ├── thresholds.py           # Thresholds, chunked analysis
│   ├── anomaly.py              # Anomaly flagging
│   ├── elbow.py                # KDE, elbow methods, plots
│   ├── validation.py           # Out-of-time, sanity, manual, anchorage
│   ├── characteristics.py      # Vessel size/speed effect
│   └── feature_engineering.py  # Main pipeline
├── data/
│   └── processed/
│       ├── features_2025-06-01.csv
│       ├── pairs_temp.csv               # Excluded from repo (3.1GB)
│       ├── encounter_results.csv        # Excluded (288MB)
│       ├── encounter_results_sample.csv # 10K rows
│       └── *_distributions.png
├── tests/
├── Dockerfile
├── requirements.txt
├── .gitignore
└── README.md
How to Run
bash
# Clone
git clone https://github.com/eliyahudahan/deviative.git
cd deviative

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run pipeline
python -m models.feature_engineering
Note: pairs_temp.csv is generated by the pipeline (~3.1GB). It is excluded from the repository.

Status
Phase 1 complete: Physics-based encounter detection + validation + documentation.

Next phases: (documented but not implemented)

LSTM Autoencoder (evaluated if signal is found)

PostgreSQL storage

Streamlit dashboard