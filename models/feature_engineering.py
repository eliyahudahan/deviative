import pandas as pd
import numpy as np

# ======================
# 1. טעינת נתונים
# ======================
features = pd.read_csv('data/processed/features_2025-06-01.csv')
print("Columns:", features.columns.tolist())
print(features.head())

# ======================
# 2. חישוב cog_diff מתוקן (Wrap-around)
# ======================
features = features.sort_values(['mmsi', 'base_date_time'])
features['cog_diff'] = features.groupby('mmsi')['cog'].diff()
features['cog_diff'] = (features['cog_diff'] + 180) % 360 - 180

print(features[['mmsi', 'cog', 'cog_diff']].head(10))

# ======================
# 3. חישוב sog_diff (אם צריך)
# ======================
# features['sog_diff'] כבר קיים בנתונים
# אם צריך לחשב מחדש:
# features['sog_diff'] = features.groupby('mmsi')['sog'].diff()

# ======================
# 4. סטטיסטיקות תיאוריות
# ======================
print("\n=== התפלגות מהירות רוח ===")
print(features['wind_speed_10m'].describe())

print("\n=== cog_diff לפי טווחי רוח ===")
print(features.groupby(pd.cut(features['wind_speed_10m'], bins=[0, 5, 10, 15, 20]))['cog_diff'].agg(['mean', 'std', 'count']))

# ======================
# 5. ספים אמפיריים (מהנתונים עצמם)
# ======================
COG_THRESHOLD = features['cog_diff'].quantile(0.95)
SOG_THRESHOLD = features['sog_diff'].abs().quantile(0.95)

print("\n=== ספים אמפיריים ===")
print(f"cog_diff 95th percentile: {COG_THRESHOLD:.2f}°")
print(f"sog_diff 95th percentile: {SOG_THRESHOLD:.2f} knots")
print(f"wind_speed_10m max: {features['wind_speed_10m'].max():.2f} km/h (no extreme wind)")

# ======================
# 6. סינון לפי הספים החדשים (ללא רוח)
# ======================
filtered_features = features[
    (features['cog_diff'].abs() > COG_THRESHOLD) |
    (features['sog_diff'].abs() > SOG_THRESHOLD)
]

print(f"\n=== תוצאות סינון ===")
print(f"סה\"כ שורות: {len(features):,}")
print(f"שורות עם cog_diff > {COG_THRESHOLD:.2f}°: {len(features[features['cog_diff'].abs() > COG_THRESHOLD]):,}")
print(f"שורות עם sog_diff > {SOG_THRESHOLD:.2f} knots: {len(features[features['sog_diff'].abs() > SOG_THRESHOLD]):,}")
print(f"סה\"כ שורות מסוננות (OR): {len(filtered_features):,}")

# ======================
# 7. שמירת התוצאות (אופציונלי)
# ======================
# filtered_features.to_csv('data/processed/anomalies_detected.csv', index=False)
# print("\nנשמרו anomalies_detected.csv")