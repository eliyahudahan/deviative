import pandas as pd
from itertools import combinations
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv")

print("Columns:", df.columns.tolist())
print("\nFirst row:")
print(df.iloc[0].to_dict())

import pandas as pd

def detect_columns(df):
    """מזהה עמודות לפי תוכן – לא לפי מיקום"""
    col_map = {}
    
    

# Step 3: Calculate features
df['sog_diff'] = df['sog'] - df['sog'].shift(1)
df['cog_diff'] = df['cog'] - df['cog'].shift(1)
df['rot'] = df['heading'] - df['heading'].shift(1)

#Convert base date time for computing
df['base_date_time'] = pd.to_datetime(df['base_date_time'])

# Step 1: Status
df.sort_values('base_date_time')
df['status'] = 'maneuvering'
df.loc[df['sog']<0.5, 'status'] = 'anchoring'

# Step 2: Changes detected
df['status_change'] = df['status'] != df['status'].shift(1)

# Step 3: Computing time

df['time_diff'] = df.groupby('mmsi')['base_date_time'].diff().dt.total_seconds() / 3600


# Step 4: Total time any condition
time_per_status = df[df['status_change']].groupby(['mmsi', 'status'])['time_diff'].sum()




# Step 5: Check the result
print("=== After renaming and features ===")
print(df[['sog', 'sog_diff', 'cog', 'cog_diff', 'heading', 'rot', 'status_change', 'time_diff']].head())
print(df.columns.tolist())
# After computing time_per_status
df = df.merge(time_per_status.reset_index(), on=['mmsi', 'status'], how='left', suffixes=('', '_total'))
df['anchoring_time'] = df['time_diff_total'].where(df['status'] == 'anchoring', 0)
df['maneuvering_time'] = df['time_diff_total'].where(df['status'] == 'maneuvering', 0)

# לעגל קואורדינטות לדיוק של ~100 מטר
df['lat_rounded'] = df['latitude'].round(3)
df['lon_rounded'] = df['longitude'].round(3)

# זיהוי מיקומים חוזרים (רציף משוער)
df['is_berth'] = df.groupby(['lat_rounded', 'lon_rounded'])['mmsi'].transform('count') > 5

# Dwell = SOG < 0.5 AND is_berth = True
df['status_dwell'] = 'maneuvering'
df.loc[(df['sog'] < 0.5) & (df['is_berth']), 'status_dwell'] = 'dwell'

# זיהוי שינויים ב-status_dwell
df['dwell_change'] = df['status_dwell'] != df['status_dwell'].shift(1)

# סיכום זמן לפי mmsi ו-status_dwell
time_per_dwell = df[df['dwell_change']].groupby(['mmsi', 'status_dwell'])['time_diff'].sum()

# מיזוג
df = df.merge(time_per_dwell.reset_index(), on=['mmsi', 'status_dwell'], how='left', suffixes=('', '_dwell_total'))

# חילוץ dwell_time
df['dwell_time'] = df['time_diff_dwell_total'].where(df['status_dwell'] == 'dwell', 0)

# 1. Creating hour column
df['hour'] = df['base_date_time'].dt.hour
# 2. occupied berths per hour (unique rounded coordinates)
occupied = df[df['status_dwell'] == 'dwell'].groupby('hour')[['lat_rounded', 'lon_rounded']].nunique().sum(axis=1)
# 3. total berths identified in the dataset (or set a realistic number)
total_berths = df['is_berth'].sum()  # count of unique berth locations
# OR: total_berths = 30  # if you prefer a constant

# 4. CI
ci = occupied / total_berths

# 5. CCI
cci = ci.cumsum()

print("Occupied berths per hour:", occupied)
print("CI per hour:", ci)
print("CCI (cumulative):", cci)


#course_alteration = lateral_distance[df['cog']>0.4]
#course_alteration = lateral_distance[df['sog']>0.1]

# Make sure that there is hour column
#df['hour'] = df['base_date_time'].dt.hour

# Sort by hour and ship
df= df.sort_values(['hour', 'mmsi'])

one_hour = df[df['hour']==23]
mmsi_list = one_hour['mmsi'].unique()
print(f"Total MMSI in hour 23: {len(mmsi_list)} ")

encounter_count = 0

for mmsi1, mmsi2 in combinations(mmsi_list, 2):
    ship1 = one_hour[one_hour['mmsi']==mmsi1].iloc[0]
    ship2 = one_hour[one_hour['mmsi']==mmsi2].iloc[0]

    lat1, lon1 = ship1['latitude'], ship1['longitude']
    lat2, lon2 = ship2['latitude'], ship2['longitude']

    dist_deg = ((lat1-lat2)**2 + (lon1-lon2)**2)**0.5
    dist_km = dist_deg*111

    if dist_km < 2:
        encounter_count+=1

print(f"Number of encounters in hour 23: {encounter_count}")        




print(df[['mmsi', 'status', 'time_diff_total']].head())
print(df[['mmsi', 'status', 'anchoring_time', 'maneuvering_time']].head())
print(df[['mmsi','status_dwell','dwell_time', 'anchoring_time']].head())
# Step 6: Save
df.to_csv('data/processed/features_2025-06-01.csv', index=False)

