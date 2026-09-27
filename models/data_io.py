"""
Deviative - Data I/O.

Load, clean, transform, and save AIS data.
"""

import pandas as pd
import numpy as np

from .helpers import select_risky_row


# ==========================================
# Load
# ==========================================
def load_data(path):
    """
    Load AIS features CSV and sort by vessel and time.

    Timestamps are rounded to the nearest minute (seconds removed)
    to ensure proper grouping of vessels reporting within the same minute.
    """
    df = pd.read_csv(path)
    df['base_date_time'] = pd.to_datetime(df['base_date_time'])

    # Round to nearest minute (remove seconds)
    df['base_date_time'] = df['base_date_time'].dt.floor('min')

    df = df.sort_values(['mmsi', 'base_date_time']).reset_index(drop=True)
    return df


# ==========================================
# Clean
# ==========================================
def remove_duplicates(features):
    """
    Remove duplicate rows for the same MMSI + timestamp.
    Keep the row with the highest risk score per group.
    """
    dup_mask = features.duplicated(subset=['mmsi', 'base_date_time'], keep=False)
    dup_rows = features[dup_mask].copy()
    single_rows = features[~dup_mask].copy()

    print(f"Total rows: {len(features)}")
    print(f"Rows in duplicate groups: {len(dup_rows)}")
    print(f"Rows without duplicates: {len(single_rows)}")

    if len(dup_rows) > 0:
        clean_dup = dup_rows.groupby(
            ['mmsi', 'base_date_time'], group_keys=False
        ).apply(select_risky_row).reset_index(drop=True)
        clean_features = pd.concat([single_rows, clean_dup], ignore_index=True)
    else:
        clean_features = single_rows.copy()

    clean_features = clean_features.sort_values(
        ['mmsi', 'base_date_time']
    ).reset_index(drop=True)

    print(f"Rows after duplicate selection: {len(clean_features)}")
    return clean_features


# ==========================================
# Transform
# ==========================================
def add_vessel_diffs(df):
    """
    Add COG and SOG differences per vessel (time series).
    COG diff uses wrap-around for proper angle handling.
    """
    df['cog_diff'] = df.groupby('mmsi')['cog'].diff()
    df['cog_diff'] = (df['cog_diff'] + 180) % 360 - 180
    df['sog_diff'] = df.groupby('mmsi')['sog'].diff()
    return df


def add_radians(df):
    """Convert latitude and longitude to radians."""
    df['lat_rad'] = np.radians(df['latitude'].astype(float))
    df['lon_rad'] = np.radians(df['longitude'].astype(float))
    return df


# ==========================================
# Save
# ==========================================
def save_results(df, path):
    """Save final results to CSV."""
    df.to_csv(path, index=False)
    print(f"\n✅ Results saved to {path}")