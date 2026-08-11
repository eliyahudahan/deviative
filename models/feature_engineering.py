import pandas as pd
#from itertools import combinations
from scipy.spatial.distance import pdist
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# 1. Reading data
df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv")

print("Columns:", df.columns.tolist())
print("\nFirst row:")
print(df.iloc[0].to_dict())

    

# 2. Basic Feature Engineering – תיקון עם groupby
df['sog_diff'] = df.groupby('mmsi')['sog'].diff()
df['cog_diff'] = df.groupby('mmsi')['cog'].diff()
df['rot'] = df.groupby('mmsi')['heading'].diff()

# 3. Convert base date time for computing
df['base_date_time'] = pd.to_datetime(df['base_date_time'])

# Step 1: Status
df.sort_values('base_date_time', inplace=True)

df['hour'] = df['base_date_time'].dt.hour
#  Creating one minute

df['minute'] = df['base_date_time'].dt.floor('min')
one_minute_sample = df[df['minute']=='2025-06-01 23:00:00'] 

print("/n=== Feature Engineering completed ===")
print(f"/n Total records: {len(df)}")
print(f"Features: {df.columns.tolist()}")

# 4. Encounter Detection (Zhou) - Just for example
sample_minute = df[df['minute']=='2025-06-01 23:00:00']
print(f"\nSample minute shape: {sample_minute.shape}")
print(f"Unique MMSI in sample {sample_minute['mmsi'].unique()}")


# Running loop about all minutes
results = []
for minute, group in df.groupby('minute'):
    if len(group)<2:
        continue
# 5. Fast calculating using by pdist
    coords = group[['latitude', 'longitude']].values
    distances = pdist(coords, metric='euclidean') * 111
    encounters = np.sum(distances<2)

    results.append({
        'minute':minute,
        'ships': len(group),
        'encoutnres': encounters,
        'pair': len(distances)
    })

results_df = pd.DataFrame(results)
print(results_df.head())

# אחרי שיצרת את results_df:
results_df = results_df.sort_values('minute')
print(results_df.head())  # עכשיו יראה מ-00:00
df = df.sort_values('base_date_time')
# אחרי שיצרת את results_df:
print(f"Total minutes in results: {len(results_df)}")
print(f"First minute: {results_df['minute'].iloc[0]}")
print(f"Last minute: {results_df['minute'].iloc[-1]}")
print(f"All minutes:\n{results_df['minute'].head(10)}")
# כל הדקות
print(results_df)

# 10 הראשונות
print(results_df.head(10))

# 10 האחרונות
print(results_df.tail(10))

# סטטיסטיקה
print(results_df.describe())

# Step 3: Save
df.to_csv('data/processed/features_2025-06-01.csv', index=False)
print("\n✅ Features saved to data/processed/features_2025-06-01.csv")

