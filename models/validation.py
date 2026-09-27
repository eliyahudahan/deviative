"""
Deviative - Validation and metrics.

All functions filter to 'moving' state and to the same
conditions used in flag_anomalies_per_state:
    - movement_state == 'moving'
    - DCPA < dcpa_th
    - TCPA >= 0
    - TCPA < tcpa_th
    - distance_km < distance_th
"""

import numpy as np
import pandas as pd


# ==========================================
# Shared helper: anomaly mask
# ==========================================
def _anomaly_mask(df, dcpa_th, tcpa_th, distance_th):
    """Single source of truth for 'anomaly' definition."""
    return (
        (df['DCPA'] < dcpa_th) &
        (df['TCPA'] >= 0) &
        (df['TCPA'] < tcpa_th) &
        (df['distance_km'] < distance_th)
    )


# ==========================================
# Out-of-Time Validation
# ==========================================
def out_of_time_validation(valid_results,
                            dcpa_th=0.1982,
                            tcpa_th=0.0293,
                            distance_th=1.0):
    """
    Validate thresholds on train/test split.
    Train: 00:00-12:00
    Test:  12:00-24:00

    Applies the same anomaly mask used in flag_anomalies_per_state.
    Filters to 'moving' only.
    """
    df = valid_results.copy()
    df['hour'] = df['base_date_time'].dt.hour

    # Filter to moving only
    moving = df[df['movement_state'] == 'moving'].copy()

    train = moving[moving['hour'] < 12]
    test = moving[moving['hour'] >= 12]

    print(f"\n=== OUT-OF-TIME VALIDATION (moving only) ===")
    print(f"Train size: {len(train):,}")
    print(f"Test size:  {len(test):,}")

    rates = {}
    for name, subset in [('Train', train), ('Test', test)]:
        anomalies = _anomaly_mask(subset, dcpa_th, tcpa_th, distance_th).sum()
        rate = anomalies / len(subset) * 100 if len(subset) > 0 else 0
        rates[name] = rate
        print(f"{name}: n={len(subset):,}, anomalies={anomalies:,}, rate={rate:.4f}%")

    if 'Train' in rates and 'Test' in rates:
        diff = abs(rates['Train'] - rates['Test'])
        print(f"\nAbsolute difference: {diff:.4f}%")

    return rates


# ==========================================
# Sanity Check
# ==========================================
def sanity_check_thresholds(valid_results,
                             dcpa_new=0.1982, tcpa_new=0.0293,
                             distance_new=1.0):
    """
    Compare old (5th percentile) vs new (2nd derivative) thresholds.
    Both applied to 'moving' subset only, with distance filter.
    """
    moving = valid_results[valid_results['movement_state'] == 'moving'].copy()

    # Compute 5th percentile on 'moving' only
    dcpa_old = moving['DCPA'].quantile(0.05)
    tcpa_old = moving['TCPA'].quantile(0.05)

    # Apply old (5th percentile)
    anomalies_old = _anomaly_mask(moving, dcpa_old, tcpa_old, distance_new).sum()

    # Apply new (2nd derivative)
    anomalies_new = _anomaly_mask(moving, dcpa_new, tcpa_new, distance_new).sum()

    ratio = anomalies_new / anomalies_old if anomalies_old > 0 else np.nan

    print(f"\n=== SANITY CHECK (moving only) ===")
    print(f"Old (5th pct):  DCPA={dcpa_old:.4f}, TCPA={tcpa_old:.4f}")
    print(f"New (2nd drv):  DCPA={dcpa_new:.4f}, TCPA={tcpa_new:.4f}")
    print(f"Distance: {distance_new:.4f} km")
    print(f"\nOld anomalies: {anomalies_old:,}")
    print(f"New anomalies: {anomalies_new:,}")
    if not np.isnan(ratio):
        print(f"Ratio (new/old): {ratio:.2f}")
    else:
        print("Ratio: N/A (old = 0)")

    if anomalies_old == 0:
        print("\n⚠️ NOTE: 5th percentile produced 0 anomalies.")
        print("   Reason: TCPA 5th percentile is negative,")
        print("   but we require TCPA >= 0 (approaching).")
        print("   → 2nd Derivative threshold is necessary.") 
    
    return {
        'anomalies_old': anomalies_old,
        'anomalies_new': anomalies_new,
        'ratio': ratio,
    }


# ==========================================
# Manual Inspection
# ==========================================
def manual_inspection(valid_results,
                       dcpa_th=0.1982, tcpa_th=0.0293,
                       distance_th=1.0,
                       n_sample=15, random_state=42):
    """
    Sample n anomalies for manual inspection.
    Filters to 'moving' + anomaly mask (same as flag_anomalies_per_state).
    Stratified: 5 low DCPA, 5 low TCPA, 5 near-threshold.
    """
    moving = valid_results[valid_results['movement_state'] == 'moving'].copy()

    anomalies = moving[_anomaly_mask(moving, dcpa_th, tcpa_th, distance_th)].copy()

    if len(anomalies) == 0:
        print("\n=== MANUAL INSPECTION ===")
        print("No anomalies to inspect.")
        return pd.DataFrame()

    n_per_stratum = max(1, n_sample // 3)

    low_dcpa = anomalies.nsmallest(n_per_stratum, 'DCPA')
    low_tcpa = anomalies.nsmallest(n_per_stratum, 'TCPA')

    used_idx = low_dcpa.index.union(low_tcpa.index)
    remaining = anomalies.drop(used_idx)

    near_th = remaining[
        (remaining['DCPA'] > dcpa_th * 0.8) &
        (remaining['TCPA'] > tcpa_th * 0.8)
    ].head(n_sample - len(low_dcpa) - len(low_tcpa))

    sample = pd.concat([low_dcpa, low_tcpa, near_th]).drop_duplicates()

    print(f"\n=== MANUAL INSPECTION ({len(sample)} anomalies) ===")
    print(sample[[
        'base_date_time', 'mmsi1', 'mmsi2',
        'distance_km', 'TCPA', 'DCPA'
    ]].to_string())

    return sample


# ==========================================
# Anchorage Check
# ==========================================
def check_anchorage_zone(valid_results,
                          dcpa_th=0.1982, tcpa_th=0.0293,
                          distance_th=1.0,
                          lat_min=33.70, lat_max=33.76,
                          lon_min=-118.25, lon_max=-118.18):
    """
    Check how many anomalies fall within Anchorage B zone.
    Approximate coordinates of San Pedro Bay anchorage.
    """
    moving = valid_results[valid_results['movement_state'] == 'moving'].copy()
    anomalies = moving[_anomaly_mask(moving, dcpa_th, tcpa_th, distance_th)].copy()

    if len(anomalies) == 0:
        print("\n=== ANCHORAGE B CHECK ===")
        print("No anomalies to check.")
        return 0, 0

    lat_deg = np.degrees(anomalies['lat_rad_1'])
    lon_deg = np.degrees(anomalies['lon_rad_1'])

    in_anchorage = (
        lat_deg.between(lat_min, lat_max) &
        lon_deg.between(lon_min, lon_max)
    )

    n_in = in_anchorage.sum()
    n_total = len(anomalies)

    print(f"\n=== ANCHORAGE B CHECK (moving only) ===")
    print(f"Total anomalies: {n_total:,}")
    print(f"In Anchorage B:  {n_in} ({n_in/n_total*100:.1f}%)")
    print(f"Outside:         {n_total - n_in}")

    if n_in > 0:
        print(f"\n=== Sample from Anchorage B (potential FP) ===")
        print(anomalies[in_anchorage][[
            'base_date_time', 'mmsi1', 'mmsi2',
            'distance_km', 'TCPA', 'DCPA'
        ]].head(5).to_string())

    return n_in, n_total


# ==========================================
# Precision / Recall / F1
# ==========================================
def compute_metrics_proxy(tp, fp, fn):
    """Compute Precision, Recall, F1 from manual labels."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    print(f"\n=== METRICS ===")
    print(f"TP: {tp}, FP: {fp}, FN: {fn}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")

    return {'precision': precision, 'recall': recall, 'f1': f1}

# ==========================================
# Additional Diagnostics
# ==========================================
def analyze_anchorage_anomalies(valid_results,
                                  dcpa_th=0.1982, tcpa_th=0.0293,
                                  distance_th=1.0,
                                  lat_min=33.70, lat_max=33.76,
                                  lon_min=-118.25, lon_max=-118.18):
    """
    Analyze anomalies within Anchorage B.
    Check if they are slow-moving vessels (likely FP).
    """
    moving = valid_results[valid_results['movement_state'] == 'moving'].copy()
    anomalies = moving[
        (moving['DCPA'] < dcpa_th) &
        (moving['TCPA'] >= 0) &
        (moving['TCPA'] < tcpa_th) &
        (moving['distance_km'] < distance_th)
    ].copy()

    lat_deg = np.degrees(anomalies['lat_rad_1'])
    lon_deg = np.degrees(anomalies['lon_rad_1'])

    in_anchorage = (
        lat_deg.between(lat_min, lat_max) &
        lon_deg.between(lon_min, lon_max)
    )

    anchorage_anomalies = anomalies[in_anchorage]
    outside_anomalies = anomalies[~in_anchorage]

    print(f"\n=== ANCHORAGE ANOMALIES ANALYSIS ===")
    print(f"In Anchorage B: {len(anchorage_anomalies):,}")
    print(f"Outside:        {len(outside_anomalies):,}")

    if len(anchorage_anomalies) > 0:
        print(f"\n=== SOG distribution (In Anchorage B) ===")
        print(anchorage_anomalies['sog1'].describe())

    if len(outside_anomalies) > 0:
        print(f"\n=== SOG distribution (Outside) ===")
        print(outside_anomalies['sog1'].describe())

    print(f"\n=== How many are slow (< 2 knots)? ===")
    if len(anchorage_anomalies) > 0:
        slow_in = (anchorage_anomalies['sog1'] < 2.0).sum()
        print(f"In Anchorage B: {slow_in:,} ({slow_in/len(anchorage_anomalies)*100:.1f}%)")
    if len(outside_anomalies) > 0:
        slow_out = (outside_anomalies['sog1'] < 2.0).sum()
        print(f"Outside:        {slow_out:,} ({slow_out/len(outside_anomalies)*100:.1f}%)")

    return anchorage_anomalies, outside_anomalies


def anomaly_rate_by_hour(valid_results,
                          dcpa_th=0.1982, tcpa_th=0.0293,
                          distance_th=1.0):
    """
    Compute anomaly rate per hour.
    Helps detect time-dependent behavior.
    """
    moving = valid_results[valid_results['movement_state'] == 'moving'].copy()
    moving['hour'] = moving['base_date_time'].dt.hour

    moving['is_anomaly'] = (
        (moving['DCPA'] < dcpa_th) &
        (moving['TCPA'] >= 0) &
        (moving['TCPA'] < tcpa_th) &
        (moving['distance_km'] < distance_th)
    )

    print(f"\n=== ANOMALY RATE BY HOUR ===")
    print(f"{'Hour':<6} {'n':>10} {'anomalies':>12} {'rate %':>10}")
    print("-" * 42)

    for hour in range(24):
        subset = moving[moving['hour'] == hour]
        if len(subset) == 0:
            continue
        n_anom = subset['is_anomaly'].sum()
        rate = n_anom / len(subset) * 100
        print(f"{hour:<6} {len(subset):>10,} {n_anom:>12,} {rate:>10.4f}")

    return moving