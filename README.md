# ⚓ Deviative – Maritime Anomaly Detection

**Real‑time vessel monitoring using AIS + LSTM Autoencoder + Weather Fusion**

Deviative detects operational anomalies in San Pedro Bay (Los Angeles) and generalizes to Rotterdam. It combines AIS data with weather context to reduce false alarms and provide actionable alerts for port operators and maritime insurers.

---

## 🎯 Purpose

- Identify **engine failures**, **weather‑induced slowdowns**, **dark vessels**, and **route deviations**
- Detect **congestion build‑up** in LA (Belcore & Polimeni, 2026)
- Detect **abnormal vessel encounters** in Rotterdam (Zhou et al., 2023)
- Provide a **production‑ready API** (FastAPI) and **interactive dashboard** (Streamlit)
- Package the full pipeline in **Docker** for easy deployment

---

## 🧠 How It Works
AIS Data (LA) + NOAA Weather
↓
Feature Engineering (SOG, COG, ROT, Draught, Wind, Waves)
↓
LSTM Autoencoder (PyTorch) – trained on LA
↓
Reconstruction Error → Anomaly Score (95th percentile / A‑Contrario)
↓
Classification: Engine / Weather / Dark / Route
↓
FastAPI + Streamlit Dashboard

text

**Key architectural choices:**
- **Train on LA** (San Pedro Bay) – 30 days of AIS + weather
- **Test on Rotterdam** – 10 days, to measure generalisation
- **Adaptive threshold** – Moving error window (6h) adjusts sensitivity during storms or unusual traffic

---

## 🏗️ Project Structure
deviative/
├── app/
│ ├── main.py # FastAPI endpoints
│ ├── model.py # LSTM Autoencoder (PyTorch)
│ ├── features.py # Feature engineering
│ ├── anomaly.py # 4 anomaly types
│ └── adaptive.py # Moving error window (bonus)
├── data/
│ ├── ais/ # AccessAIS – San Pedro Bay / Rotterdam
│ ├── weather/ # Open‑Meteo
│ └── processed/ # Merged & cleaned
├── notebooks/ # EDA, features, model, evaluation
├── scripts/ # fetch_ais.py, fetch_weather.py, train_model.py
├── models/
│ └── lstm_autoencoder.pth
├── research/
│ └── papers.md # Annotated references
├── dashboard.py # Streamlit app
├── Dockerfile
├── docker‑compose.yml
├── requirements.txt
└── README.md

text

---

## 📡 Data Sources

| Source | Use |
|--------|-----|
| **AccessAIS** (Norwegian Coastal Administration) | AIS positional data (SOG, COG, Heading, Draught) |
| **Open‑Meteo** | Historical weather (wind speed, wave height) – free, global, no API key |
| **San Pedro Bay, LA** | Training set – 30 days |
| **Rotterdam** | Generalisation test set – 10 days |

---

## 📊 AIS Data Columns (17 original + 8 derived)

| # | Column Name | Description |
|---|-------------|-------------|
| 0 | `mmsi` | Unique vessel identifier |
| 1 | `base_date_time` | Timestamp (UTC) |
| 2 | `longitude` | Longitude |
| 3 | `latitude` | Latitude |
| 4 | `sog` | Speed Over Ground (knots) |
| 5 | `cog` | Course Over Ground (degrees) |
| 6 | `heading` | Compass heading (degrees) |
| 7 | `vessel_name` | Vessel name |
| 8 | `imo` | IMO number |
| 9 | `call_sign` | Call sign |
| 10 | `vessel_type` | Vessel type code |
| 11 | `status` | Navigation status |
| 12 | `length` | Length (meters) |
| 13 | `width` | Width (meters) |
| 14 | `draft` | Draft (meters) |
| 15 | `cargo` | Cargo type code |
| 16 | `transceiver` | AIS transceiver type |

**Derived Features (added after merge):**

| # | Column Name | Description |
|---|-------------|-------------|
| 17 | `time` | Timestamp (weather merge key) |
| 18 | `temperature_2m` | Temperature (°C) |
| 19 | `wind_speed_10m` | Wind speed (km/h) |
| 20 | `wind_direction_10m` | Wind direction (degrees) |
| 21 | `wind_gusts_10m` | Wind gusts (km/h) |
| 22 | `sog_diff` | Speed change between readings |
| 23 | `cog_diff` | Course change between readings |
| 24 | `rot` | Rate of Turn (heading change) |


## 📚 Research Basis

| Paper | Contribution |
|-------|--------------|
| **Belcore & Polimeni (2026)** | Congestion metrics: `anchoring_time`, `dwell_time`, CI, CCI – adapted for LA |
| **Zhou et al. (2023)** | Encounter detection: `course_alteration`, `speed_change`, `lateral_distance` – directly validated on Rotterdam |
| **Olesen (2023)** | LSTM Autoencoder + A‑Contrario threshold – core anomaly detection architecture |

> **Note:** Belcore thresholds (CI > 0.60, dwell 3–5 days) were originally derived from a Mediterranean port. They are applied here as a baseline and validated against San Pedro Bay data.

---

## 🚀 Quick Start

### With Docker (recommended)

```bash
docker pull eliyahudahan/deviative:latest
docker run -p 8000:8000 -p 8501:8501 deviative:latest
API: http://localhost:8000/docs

Dashboard: http://localhost:8501

Manual Setup
bash
git clone https://github.com/eliyahudahan/deviative.git
cd deviative
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Fetch data
python scripts/fetch_ais.py --port LA --days 30
python scripts/fetch_weather.py --lat 33.7 --lon -118.2 --days 30

# Train model
python scripts/train_model.py

# Run API + Dashboard
uvicorn app.main:app --reload
streamlit run dashboard.py
🔍 Anomaly Types
Type	Detection Logic	Source
Engine Failure	SOG drop + ROT change (weather‑adjusted)	Olesen + weather fusion
Weather‑Induced	All ships affected; high wind/waves → filtered out	Fusion layer
Dark Vessel	AIS signal lost	Rule‑based
Route Deviation	Heading ≠ COG + positional outlier	Rule‑based
Congestion	CI, CCI, dwell time exceeding adaptive thresholds	Belcore (adapted)
Abnormal Encounter	Course alteration > 0.4×beam; speed change > 10%; distance < 5×beam	Zhou
📊 Performance (Targets)
Metric	Target
Anomaly detection latency	< 2 seconds
False alarm reduction (weather fusion)	70%
Rotterdam generalisation	Reported in evaluation notebook
Model size	< 50 MB
🧪 Adaptive Threshold (Bonus)
A moving error window (6 hours) adjusts the anomaly threshold in real time:

If average reconstruction error rises across all vessels (e.g., during a storm), the threshold increases – reducing false alarms.

If error drops, threshold decreases – restoring sensitivity.

This mimics real‑world calibration without requiring human feedback.

🛠️ Tech Stack
Component	Technology
Deep Learning	PyTorch (LSTM Autoencoder)
Data	Pandas, NumPy, Geopandas
API	FastAPI
Dashboard	Streamlit, Plotly
Container	Docker, Docker Compose
Monitoring	(Optional) Evidently AI
Geospatial	Shapely, PyDeck
📄 License
MIT

📬 Connect
GitHub: eliyahudahan

LinkedIn: Eliyahu Dahan

Email: framgangsrik747@gmail.com

Last updated: 06.07.2026