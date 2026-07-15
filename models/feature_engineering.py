import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv", nrows=5)

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

# Step 4: Check the result
print("=== After renaming and features ===")
print(df[['sog', 'sog_diff', 'cog', 'cog_diff', 'heading', 'rot']].head())
print(df.columns.tolist())

# Step 5: Save
df.to_csv('data/processed/features_2025-06-01.csv', index=False)

