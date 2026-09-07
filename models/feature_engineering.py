# ==========================================
# 1. Imports
# ==========================================
import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist

# ==========================================
# 2. Haversine function (The Calculator)
# ==========================================
def haversine(x1, x2):
    # x1 and x2 are arrays of [lat_rad, lon_rad]
    lat1, lon1 = x1
    lat2, lon2 = x2
    
    R = 6371.0  # Earth radius in km
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

# ==========================================
# 3. Function to return distances with vessel IDs
# ==========================================
def calc_distances_for_minute(df_minute):
    coords = df_minute[['lat_rad', 'lon_rad']].values
    mmsi_list = df_minute['mmsi'].values
    
    distances = pdist(coords, metric=haversine)
    
    n = len(mmsi_list)
    results = []
    for i in range(n):
        for j in range(i + 1, n):
            # Formula to find the index of pair (i, j)
            idx = n * i - i * (i + 1) // 2 + j - i - 1
            
            results.append({
                'mmsi1': mmsi_list[i],
                'mmsi2': mmsi_list[j],
                'distance_km': distances[idx]
            })
    
    return pd.DataFrame(results)

# ==========================================
# 4. Load data
# ==========================================
features = pd.read_csv('data/processed/features_2025-06-01.csv')

# ==========================================
# 4.1 Data Quality Check – Duplicate Rows
# ==========================================
duplicates = features.groupby(['mmsi', 'base_date_time']).size()
print(duplicates[duplicates > 1])
print(f"{duplicates.sum()}")
# ==========================================
# 5. Sort, compute features, and convert to radians
# ==========================================
features = features.sort_values(['mmsi', 'base_date_time'])
features['cog_diff'] = features.groupby('mmsi')['cog'].diff()
features['cog_diff'] = (features['cog_diff'] + 180) % 360 - 180

features['sog_diff_percent'] = features['sog_diff'] / features['sog'].where(features['sog'] != 0)
features['sog_diff_percent'] = features['sog_diff_percent'].replace([float('inf'), float('-inf')], None)
features['sog_diff_percent'] = features['sog_diff_percent'].clip(lower=-10, upper=10)

features['lat_rad'] = np.radians(features['latitude'])
features['lon_rad'] = np.radians(features['longitude'])

# ==========================================
# 6. Run the distance calculation on the selected sample
# ==========================================
sample_time = features['base_date_time'].value_counts().index[5]
sample = features[features['base_date_time'] == sample_time]
distances_df = calc_distances_for_minute(sample)

# ==========================================
# 7. Print the results
# ==========================================
print(distances_df.head(10))
print(f"Total number of pairs in this minute: {len(distances_df)}")