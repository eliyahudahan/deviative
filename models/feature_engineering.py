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

# Step 6: Save
df.to_csv('data/processed/features_2025-06-01.csv', index=False)

