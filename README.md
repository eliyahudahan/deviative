# ⚓ Deviative – Maritime Anomaly Detection for VTS

Real-time vessel monitoring for Vessel Traffic Services.
Detects dangerous encounters, course alterations, speed changes, and dark vessels.

## Anomaly Types
- **Encounter Detection** – ships < 2 km apart (Zhou et al. method)
- **Course Alteration** – cog_diff > 86° (empirical 95th percentile from data)
- **Speed Change** – sog_diff > 10.2 knots (empirical 95th percentile from data)
- **Dark Vessel** – missing AIS signal (gap analysis)

## Data
- **AIS**: MarineCadastre (San Pedro Bay, 2025-06-01, 200K+ records)
- **Weather**: Open-Meteo (wind_speed_10m max 13.9 km/h – no extreme conditions)

## Empirical Thresholds (derived from data)
| Metric | Threshold | Method |
|--------|-----------|--------|
| Course Alteration | 86° | 95th percentile of cog_diff |
| Speed Change | 10.2 knots | 95th percentile of sog_diff (absolute) |
| Encounter Distance | < 2 km | Zhou et al. |
| Wind Speed | N/A | No extreme wind in dataset (max 13.9 km/h) |

## Tech Stack
- **Python** – pandas, numpy, scipy
- **PyTorch** – LSTM Autoencoder for anomaly detection
- **FastAPI** – REST API for predictions
- **Streamlit** – Interactive dashboard
- **Docker** – Containerized deployment
- **PostgreSQL** – Storing AIS data and results

## Project Structure
deviative/
├── models/
│ ├── feature_engineering.py # Data loading, cleaning, feature calculation
│ ├── encounter_detection.py # CPA/TCPA calculation (Zhou method)
│ └── anomaly_detector.py # LSTM Autoencoder (future)
├── data/
│ └── processed/
│ └── features_2025-06-01.csv
├── notebooks/ # Exploratory analysis
├── tests/ # Unit tests
├── Dockerfile
├── requirements.txt
└── README.md

text

## Key Learnings (from feature_engineering.py)
- **Wrap-around correction** for circular angles (cog_diff):
cog_diff = (cog2 - cog1 + 180) % 360 - 180

text
- **Groupby per vessel** (mmsi) – each vessel processed independently
- **Empirical thresholds** – derived from 95th percentile, not arbitrary values

## Next Steps
1. LSTM Autoencoder for sequential anomaly detection
2. FastAPI + Streamlit dashboard
3. Backtesting with metrics (TP/FP/FN)
4. Deployment with Docker

## License & Acknowledgements
- Data: MarineCadastre (NOAA), Open-Meteo
- Method: Zhou et al. (2023) – "Maritime Anomaly Detection"

---

**Status:** 🟢 Phase 1 complete (Feature Engineering & Baseline Thresholds)