# ============================================================
# FEATURE ENGINEERING + ENCOUNTER DETECTION (Zhou et al., 2023)
# For VTS – Vessel Traffic Services
# Deviative Project – AIS + Weather + Anomaly Detection
# ============================================================

# pandas = DataFrame library – turns CSV into tables with rows & columns
import pandas as pd

# pdist = Pairwise Distance – calculates all distances between all ships at once
# Much faster than double loop (C code, not Python)
from scipy.spatial.distance import pdist

# NumPy = array math – necessary for pdist and vectorized operations
import numpy as np

# Show all columns and full width when printing
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# ============================================================
# 1. LOAD DATA
# ============================================================
# Read the merged AIS + Weather CSV file
df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv")

# Print column names to see what features we have
print("Columns:", df.columns.tolist())

# Print first row as a dictionary – easier to read than a table
print("\nFirst row:")
print(df.iloc[0].to_dict())

# ============================================================
# 2. BASIC FEATURE ENGINEERING – WITH groupby
# ============================================================
# Without groupby: diff() would compare rows across DIFFERENT ships → wrong!
# With groupby('mmsi'): each ship is treated separately

# sog_diff = Speed Over Ground difference between consecutive readings per ship
df['sog_diff'] = df.groupby('mmsi')['sog'].diff()

# cog_diff = Course Over Ground difference (direction change) per ship
df['cog_diff'] = df.groupby('mmsi')['cog'].diff()

# rot = Rate of Turn – heading change per ship
# Heading = where the bow points; diff = how fast the ship is turning
df['rot'] = df.groupby('mmsi')['heading'].diff()

# ============================================================
# 3. TIME HANDLING
# ============================================================
# Convert timestamp string to datetime object
df['base_date_time'] = pd.to_datetime(df['base_date_time'])

# Sort chronologically – needed before any time-based calculations
df.sort_values('base_date_time', inplace=True)

# Extract hour (0–23) and minute (rounded down)
df['hour'] = df['base_date_time'].dt.hour
df['minute'] = df['base_date_time'].dt.floor('min')

# ============================================================
# 4. ENCOUNTER DETECTION – Minute-level (Zhou et al., 2023)
# ============================================================
# Why minutes, not hours?
# One hour = many duplicate readings per ship (10,212 rows, only 481 unique MMSI)
# One minute = each ship appears once → no duplicates → correct distance calculation

# Loop over each minute group
results = []

for minute, group in df.groupby('minute'):
    # Need at least 2 ships to have an encounter
    if len(group) < 2:
        continue
    
    # Extract coordinates as a NumPy array
    # Shape: (n_ships, 2) – each row = [latitude, longitude]
    coords = group[['latitude', 'longitude']].values
    
    # pdist calculates all pairwise Euclidean distances in one go
    # Returns distances in degrees
    distances_deg = pdist(coords, metric='euclidean')
    
    # Convert degrees to kilometers (1 degree ≈ 111 km)
    distances_km = distances_deg * 111
    
    # Count how many pairs are less than 2 km apart
    # distances_km < 2 returns a boolean array (True/False)
    # np.sum() counts the True values (True = 1, False = 0)
    encounters = np.sum(distances_km < 2)
    
    # Save results for this minute
    results.append({
        'minute': minute,
        'ships': len(group),
        'encounters': encounters,
        'pairs': len(distances_km)
    })

# Convert list of dictionaries to a clean DataFrame
results_df = pd.DataFrame(results)

# Sort by minute to see chronological order (00:00 → 23:59)
results_df = results_df.sort_values('minute')

# ============================================================
# 5. OUTPUT – DIAGNOSTICS & STATISTICS
# ============================================================
print("\n" + "="*60)
print("ENCOUNTER DETECTION RESULTS")
print("="*60)

print("\n📊 First 5 minutes:")
print(results_df.head())

print(f"\n📊 Total minutes analyzed: {len(results_df)}")
print(f"📊 First minute: {results_df['minute'].iloc[0]}")
print(f"📊 Last minute: {results_df['minute'].iloc[-1]}")

print("\n📊 First 10 minutes:")
print(results_df.head(10))

print("\n📊 Last 10 minutes:")
print(results_df.tail(10))

print("\n📊 Summary Statistics (describe):")
print(results_df.describe())

# ============================================================
# 6. SAVE PROCESSED DATA
# ============================================================
# Save the enriched DataFrame with all new features
# index=False = don't save row numbers
df.to_csv('data/processed/features_2025-06-01.csv', index=False)

print("\n✅ Features saved to data/processed/features_2025-06-01.csv")
print("="*60)