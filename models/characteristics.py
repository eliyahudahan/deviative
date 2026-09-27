"""
Deviative - Vessel characteristics analysis.

Checks whether vessel size (length) or speed (SOG)
affects the DCPA/TCPA thresholds.

If the effect is significant - thresholds should be per-size or per-speed.
If not - a single threshold is sufficient.
"""

import pandas as pd


# ==========================================
# Vessel size effect
# ==========================================
def check_vessel_size_effect(valid_results):
    """
    Check if vessel length affects DCPA/TCPA thresholds.

    Bins vessels into small (< 50m), medium (50-150m), large (> 150m).
    Only considers approaching pairs (TCPA >= 0).

    If DCPA_q05 is similar across bins - size does not affect threshold.
    """
    if 'length_1' not in valid_results.columns:
        print("Warning: 'length_1' column not available. Skipping.")
        return

    moving = valid_results[
        valid_results['movement_state'] == 'moving'
    ].copy()

    # Filter only approaching pairs for TCPA analysis
    moving_approaching = moving[moving['TCPA'] >= 0].copy()

    moving_approaching['size_class'] = pd.cut(
        moving_approaching['length_1'],
        bins=[0, 50, 150, 10000],
        labels=['small', 'medium', 'large']
    )

    print(f"\n{'Size Class':<10} {'n':>8} {'DCPA_q05':>12} {'TCPA_q05':>12} {'DCPA_median':>14}")
    print("-" * 65)

    for size in ['small', 'medium', 'large']:
        subset = moving_approaching[moving_approaching['size_class'] == size]
        if len(subset) > 100:
            dcpa_q = subset['DCPA'].quantile(0.05)
            tcpa_q = subset['TCPA'].quantile(0.05)
            dcpa_med = subset['DCPA'].median()
            print(f"{size:<10} {len(subset):>8} {dcpa_q:>12.4f} {tcpa_q:>12.4f} {dcpa_med:>14.4f}")
        else:
            print(f"{size:<10} {len(subset):>8} (not enough data)")


# ==========================================
# Vessel speed effect
# ==========================================
def check_vessel_speed_effect(valid_results):
    """
    Check if vessel speed affects DCPA/TCPA thresholds.

    Bins vessels by average pair speed:
        - slow: < 5 knots
        - medium: 5-15 knots
        - fast: > 15 knots

    Only considers approaching pairs (TCPA >= 0).

    If DCPA_q05 is similar across bins - speed does not affect threshold.
    """
    moving = valid_results[
        valid_results['movement_state'] == 'moving'
    ].copy()

    # Average speed of the pair
    moving['avg_sog'] = (moving['sog1'] + moving['sog2']) / 2

    # Filter only approaching pairs
    moving_approaching = moving[moving['TCPA'] >= 0].copy()

    moving_approaching['speed_class'] = pd.cut(
        moving_approaching['avg_sog'],
        bins=[0, 5, 15, 100],
        labels=['slow', 'medium', 'fast']
    )

    print(f"\n{'Speed Class':<12} {'n':>8} {'DCPA_q05':>12} {'TCPA_q05':>12} {'DCPA_median':>14}")
    print("-" * 70)

    for speed in ['slow', 'medium', 'fast']:
        subset = moving_approaching[moving_approaching['speed_class'] == speed]
        if len(subset) > 100:
            dcpa_q = subset['DCPA'].quantile(0.05)
            tcpa_q = subset['TCPA'].quantile(0.05)
            dcpa_med = subset['DCPA'].median()
            print(f"{speed:<12} {len(subset):>8} {dcpa_q:>12.4f} {tcpa_q:>12.4f} {dcpa_med:>14.4f}")
        else:
            print(f"{speed:<12} {len(subset):>8} (not enough data)")


# ==========================================
# Combined check
# ==========================================
def check_vessel_characteristics(valid_results):
    """
    Run both size and speed effect checks.
    """
    print("\n" + "=" * 70)
    print("VESSEL CHARACTERISTICS ANALYSIS")
    print("=" * 70)

    print("\n=== VESSEL SIZE EFFECT ===")
    check_vessel_size_effect(valid_results)

    print("\n=== VESSEL SPEED EFFECT ===")
    check_vessel_speed_effect(valid_results)