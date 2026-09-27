"""
Deviative - Elbow Method analysis.

Three approaches for finding the "elbow" of a distribution:
1. 2nd Derivative of KDE
2. Kneedle algorithm
3. Gap Statistic

Used to derive data-driven thresholds per movement state.
"""

import os
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

try:
    from kneed import KneeLocator
    KNEED_AVAILABLE = True
except ImportError:
    KNEED_AVAILABLE = False
    print("Warning: kneed library not installed. Kneedle will be skipped.")

from .config import PLOT_OUTPUT_DIR, PLOT_DPI


# ==========================================
# KDE
# ==========================================
def compute_kde(data, num_points=1000, max_samples=10000):
    """
    Compute KDE for a 1D data series.
    Downsamples if data is too large (> max_samples) for speed.

    Returns:
        (x_grid, y_grid) for plotting, or (None, None) if not enough data.
    """
    data = pd.to_numeric(data, errors='coerce').dropna().values
    if len(data) < 10:
        return None, None

    # Downsample for speed if needed
    if len(data) > max_samples:
        np.random.seed(42)
        data = np.random.choice(data, size=max_samples, replace=False)

    kde = gaussian_kde(data)
    x_grid = np.linspace(data.min(), data.max(), num_points)
    y_grid = kde(x_grid)

    return x_grid, y_grid


# ==========================================
# Three elbow methods
# ==========================================
def find_elbow_second_derivative(x_grid, y_grid):
    """
    Find the 'elbow' as the maximum of the second derivative of KDE.
    Returns the x-value at the elbow.
    """
    if x_grid is None or len(x_grid) < 10:
        return np.nan

    dy = np.gradient(y_grid, x_grid)
    d2y = np.gradient(dy, x_grid)

    elbow_idx = np.argmax(d2y)
    return x_grid[elbow_idx]


def find_elbow_kneedle(x_grid, y_grid):
    """
    Find elbow using Kneedle algorithm.
    Returns the x-value at the elbow.
    """
    if not KNEED_AVAILABLE or x_grid is None:
        return np.nan

    try:
        kl = KneeLocator(
            x_grid, y_grid,
            curve='convex',
            direction='decreasing',
            S=1.0
        )
        return kl.knee if kl.knee is not None else np.nan
    except Exception:
        return np.nan


def find_elbow_gap_statistic(data, num_points=100):
    """
    Simplified Gap Statistic: compare empirical distribution to uniform.
    Find the x-value where the gap between the CDF and uniform CDF is maximal.
    """
    data = data.dropna().values
    if len(data) < 10:
        return np.nan

    sorted_data = np.sort(data)
    n = len(sorted_data)

    ecdf = np.arange(1, n + 1) / n
    uniform_cdf = (sorted_data - sorted_data.min()) / (
        sorted_data.max() - sorted_data.min()
    )

    gap = np.abs(ecdf - uniform_cdf)
    max_idx = np.argmax(gap)
    return sorted_data[max_idx]


# ==========================================
# Analysis per movement state
# ==========================================
def analyze_state_distributions(valid_results, output_dir=PLOT_OUTPUT_DIR):
    """
    For each movement state, analyze the distributions of DCPA, TCPA, distance_km.
    Produce:
        - Histograms + KDE plots (saved as PNG)
        - Elbow estimates from three methods

    Returns:
        dict of thresholds per state.
    """
    os.makedirs(output_dir, exist_ok=True)

    states = ['anchored', 'towing', 'moving']
    metrics = ['DCPA', 'TCPA', 'distance_km']

    results = {}

    for state in states:
        subset = valid_results[valid_results['movement_state'] == state]
        n_pairs = len(subset)

        print(f"\n{'=' * 50}")
        print(f"Movement State: {state} (n={n_pairs})")
        print(f"{'=' * 50}")

        state_result = {'n_pairs': n_pairs}

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        for ax, metric in zip(axes, metrics):
            data = subset[metric].dropna()

            if metric == 'TCPA':
                data = data[data >= 0]
                if len(data) < 10:
                    ax.set_title(f'{metric} (not enough data)')
                    state_result[metric] = {
                        'elbow_2deriv': np.nan,
                        'elbow_kneedle': np.nan,
                        'elbow_gap': np.nan
                    }
                    continue

            ax.hist(data, bins=50, density=True, alpha=0.5, label='Histogram')

            x_grid, y_grid = compute_kde(data)
            if x_grid is not None:
                ax.plot(x_grid, y_grid, 'r-', linewidth=2, label='KDE')

                elbow_2deriv = find_elbow_second_derivative(x_grid, y_grid)
                elbow_kneedle = find_elbow_kneedle(x_grid, y_grid)
                elbow_gap = find_elbow_gap_statistic(data)

                if not np.isnan(elbow_2deriv):
                    ax.axvline(elbow_2deriv, color='green', linestyle='--',
                               linewidth=2, label=f'2nd deriv: {elbow_2deriv:.4f}')
                if not np.isnan(elbow_kneedle):
                    ax.axvline(elbow_kneedle, color='blue', linestyle='--',
                               linewidth=2, label=f'Kneedle: {elbow_kneedle:.4f}')
                if not np.isnan(elbow_gap):
                    ax.axvline(elbow_gap, color='orange', linestyle='--',
                               linewidth=2, label=f'Gap: {elbow_gap:.4f}')

                state_result[metric] = {
                    'elbow_2deriv': elbow_2deriv,
                    'elbow_kneedle': elbow_kneedle,
                    'elbow_gap': elbow_gap,
                    'mean': float(data.mean()),
                    'median': float(data.median()),
                    'q05': float(data.quantile(0.05)),
                    'q95': float(data.quantile(0.95))
                }

                print(f"\n--- {metric} ---")
                print(f"  n:              {len(data)}")
                print(f"  mean:           {data.mean():.4f}")
                print(f"  median:         {data.median():.4f}")
                print(f"  q05:            {data.quantile(0.05):.4f}")
                print(f"  q95:            {data.quantile(0.95):.4f}")
                print(f"  Elbow (2nd):    {elbow_2deriv:.4f}")
                print(f"  Elbow (Kneedle): {elbow_kneedle if not np.isnan(elbow_kneedle) else 'N/A'}")
                print(f"  Elbow (Gap):    {elbow_gap:.4f}")

            ax.set_title(f'{state} – {metric}')
            ax.set_xlabel(metric)
            ax.set_ylabel('Density')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = f'{output_dir}/{state}_distributions.png'
        plt.savefig(plot_path, dpi=PLOT_DPI)
        plt.close()

        print(f"\n✅ Plot saved: {plot_path}")
        results[state] = state_result

    return results


# ==========================================
# Summary printout
# ==========================================
def print_elbow_summary(elbow_results):
    """Print a clean summary table of elbow estimates across states and metrics."""
    print("\n" + "=" * 70)
    print("ELBOW SUMMARY – ALL STATES × ALL METRICS")
    print("=" * 70)

    metrics = ['DCPA', 'TCPA', 'distance_km']

    for state, state_data in elbow_results.items():
        print(f"\n### {state} (n={state_data.get('n_pairs', 'N/A')})")
        print(f"{'Metric':<15} {'2nd deriv':>12} {'Kneedle':>12} {'Gap':>12}")
        print("-" * 55)

        for metric in metrics:
            if metric in state_data and isinstance(state_data[metric], dict):
                m = state_data[metric]
                v1 = m.get('elbow_2deriv', np.nan)
                v2 = m.get('elbow_kneedle', np.nan)
                v3 = m.get('elbow_gap', np.nan)

                v1_str = f"{v1:.4f}" if not pd.isna(v1) else "N/A"
                v2_str = f"{v2:.4f}" if not pd.isna(v2) else "N/A"
                v3_str = f"{v3:.4f}" if not pd.isna(v3) else "N/A"

                print(f"{metric:<15} {v1_str:>12} {v2_str:>12} {v3_str:>12}")