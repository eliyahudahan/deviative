import pandas as pd
from scipy.spatial.distance import pdist
import numpy as np

# טען נתונים
df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv")
df['base_date_time'] = pd.to_datetime(df['base_date_time'])
df['hour'] = df['base_date_time'].dt.hour

# סנן שעה 23
one_hour = df[df['hour'] == 23]
print(f"Rows in hour 23: {len(one_hour)}")
print(f"Unique MMSI: {one_hour['mmsi'].nunique()}")

# חלץ קואורדינטות
coords = one_hour[['latitude', 'longitude']].values
print(f"coords shape: {coords.shape}")

# חישוב מרחקים
dist_deg = pdist(coords, metric='euclidean')
dist_km = dist_deg * 111
encounters = np.sum(dist_km < 2)

print(f"Pairs: {len(dist_deg)}")
print(f"Encounters (<2km): {encounters}")
print(f"Valid? {encounters <= len(dist_deg)}")