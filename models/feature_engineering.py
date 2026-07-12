import pandas as pd

df = pd.read_csv("data/processed/la_ais_weather_2025-06-01.csv")
print(df.columns)
print(df.head())