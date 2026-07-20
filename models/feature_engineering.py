import pandas as pd

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

print(df[['mmsi', 'status', 'time_diff_total']].head())
print(df[['mmsi', 'status', 'anchoring_time', 'maneuvering_time']].head())
print(df[['mmsi','status_dwell','dwell_time', 'anchoring_time']].head())
# Step 6: Save
df.to_csv('data/processed/features_2025-06-01.csv', index=False)

