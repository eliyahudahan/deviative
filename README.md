# ⚓ Deviative – Maritime Anomaly Detection for VTS

Real-time vessel monitoring for Vessel Traffic Services.
Detects dangerous encounters, course alterations, speed changes, and dark vessels.
Weather context reduces false alarms.

## Anomaly Types
- Encounter Detection – ships < 2 km apart
- Course Alteration – cog_diff > 40°
- Speed Change – sog_diff > 10%
- Dark Vessel – missing AIS signal

## Data
- AIS: MarineCadastre (San Pedro Bay)
- Weather: Open-Meteo

## Tech
Python, PyTorch, FastAPI, Docker, Streamlit, PostgreSQL