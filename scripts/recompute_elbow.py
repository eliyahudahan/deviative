"""
Recompute elbow analysis only (from existing encounter_results.csv).
No re-run of the pipeline required.
"""
import pandas as pd

from models.elbow import analyze_state_distributions, print_elbow_summary
from models.config import OUTPUT_PATH


def main():
    print("Loading existing results from:", OUTPUT_PATH)
    df = pd.read_csv(OUTPUT_PATH)

    if 'base_date_time' in df.columns and df['base_date_time'].dtype == object:
        df['base_date_time'] = pd.to_datetime(df['base_date_time'])

    print(f"Loaded {len(df):,} rows")
    print("Movement states:", df['movement_state'].value_counts().to_dict())

    elbow_results = analyze_state_distributions(df)
    print_elbow_summary(elbow_results)


if __name__ == "__main__":
    main()
