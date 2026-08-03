import pandas as pd
#from itertools import combinations
from scipy.spatial.distance import pdist
import numpy as np
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

#Reading data
df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv")

print("Columns:", df.columns.tolist())
print("\nFirst row:")
print(df.iloc[0].to_dict())

    

# Basic Feature Engineering
df['sog_diff'] = df['sog'] - df['sog'].shift(1)
df['cog_diff'] = df['cog'] - df['cog'].shift(1)
df['rot'] = df['heading'] - df['heading'].shift(1)

#Convert base date time for computing
df['base_date_time'] = pd.to_datetime(df['base_date_time'])

# Step 1: Status
df.sort_values('base_date_time', inplace=True)

#  Creating hour column
df['hour'] = df['base_date_time'].dt.hour

print("/n=== Feature Engineering completed ===")
print(f"/n Total records: {len(df)}")
print(f"Features: {df.columns.tolist()}")

#2. Encounter Detection (Zhou) - Just for example
one_hour = df[df['hour']==23]
#mmsi_list = one_hour['mmsi'].unique()
#print(f"Total MMSI in hour 23: {len(mmsi_list)} ")
print(f"/nTotal MMSI in hour 23: {len(one_hour['mmsi'].unique())}")
#encounter_count = 0

"""for mmsi1, mmsi2 in combinations(mmsi_list, 2):
    ship1 = one_hour[one_hour['mmsi']==mmsi1].iloc[0]
    ship2 = one_hour[one_hour['mmsi']==mmsi2].iloc[0]

    lat1, lon1 = ship1['latitude'], ship1['longitude']
    lat2, lon2 = ship2['latitude'], ship2['longitude']
    #Haversine formula
    dist_deg = ((lat1-lat2)**2 + (lon1-lon2)**2)**0.5
    dist_km = dist_deg*111

    if dist_km < 2:
        encounter_count+=1

print(f"Number of encounters in hour 23: {encounter_count}")        
"""
#Fast calculating using by scipy
coords = one_hour[['latitude', 'longitude']].values
distance_deg = pdist(coords, metric='euclidean')
distance_km = distance_deg * 111

encounter_count = np.sum(distance_km<2)
print(f"Noumbers of encounters in 23: {encounter_count}")


# Step 3: Save
df.to_csv('data/processed/features_2025-06-01.csv', index=False)
print("\n✅ Features saved to data/processed/features_2025-06-01.csv")