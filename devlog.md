# Deviative – Development Log

## Project Timeline & Lessons Learned

---

### 📝 Hebrew Version

| תאריך | טעות | תובנה / לקח |
|-------|------|--------------|
| 30.06 | התחלתי בלי Git | **תשתית תחילה** – תמיד להקים repo, README, .gitignore לפני קוד |
| 06.07 | API ללא מפתח | **API דורש מפתח** – אימות הוא חובה |
| 07.07 | ניסיתי לפתוח `.zst` עם pandas | **קבצים דחוסים → ספרייה ייעודית** – `zstandard` |
| 07.07 | pandas קרא כותרת כנתונים | **CSV עם כותרת → `skiprows=1`** – דילוג על שורה 0 |
| 08.07 | מיזוג לפני סינון | **סינון לפני מיזוג = מהיר יותר** – 199K במקום 4M |
| 08.07 | Weather – הורדה ידנית | **הורדת נתונים דרך API** – `requests.get()` + JSON |
| 08.07 | מיזוג לפי תאריך בלבד | **מיזוג לפי timestamp** – `pd.merge(on='time')` |
| 09.07 | PostgreSQL לא רץ | **PostgreSQL לא רץ → צריך Docker** |
| 09.07 | ניסיתי להריץ PostgreSQL מקומית | **הרצת DB בקופסה** – `docker run -d` |
| 12.07 | psycopg2 ניסה Unix Socket | **psycopg2 דורש TCP/IP ל-Docker** – `host=localhost` |
| 12.07 | פרטי התחברות לא תואמים | **dbname, user, password חייבים להתאים** |
| 12.07 | `commit` ללא `git` | **Git – תמיד עם `git`** |
| 12.07 | `information_schema_tables` | **PostgreSQL – schema + נקודה** – `information_schema.tables` |
| 12.07 | `""""` (4 מירכאות) | **Python – 3 מירכאות למחרוזות רב-שורתיות** |
| 12.07 | `SEARIAL` | **SQL – auto-increment = `SERIAL`** |
| 12.07 | `(conn.close())` עם סוגריים | **Python – פונקציות בלי סוגריים מיותרים** |
| 12.07 | `cur= IF NOT EXISTS { ... }` | **SQL = מחרוזת, לא בלוק קוד** |
| 12.07 | `import sqlalchemy` + `datetime` | **מייבאים רק מה שמשתמשים** |
| 13.07 | ניסיתי לחשב `sog_diff` מעמודה לא קיימת | **KeyError – להבין את מבנה הנתונים לפני חישוב** |
| 13.07 | עצרתי – לא העתקתי | **עדיף לעצור מלהעתיק בלי להבין** |
| 14.07 | שיניתי שמות עמודות ב-`save_by_coord.py` – לא עדכנתי בהמשך הקוד | **שינוי שמות = עדכון בכל מקום** – עקביות |
| 14.07 | `skiprows=1` דילג על כותרת | **עדיף לטעון עם כותרת** – `df.columns = [...]` במקום לדלג |
| 15.07 | `read_csv` עם `rows` במקום `nrows` | **פרמטר נכון = `nrows`** |
| 15.07 | `rename` במקום `columns` | **שינוי שמות = `df.columns = [...]`** |
| 15.07 | קוד קשיח מול קוד גנרי | **קוד גנרי – מזהה לפי תוכן, לא לפי מיקום** |
| 15.07 | שיניתי ארכיטקטורה – הוספתי שמות ב-`save_by_coord.py` | **החלטה ארכיטקטונית – שלי** – לא רק תיקון, תכנון |
| 16.07 | `time_diff` בלי קיבוץ לפי `mmsi` | **צריך לקבץ לפי `mmsi`** – אחרת מערבבים ספינות שונות |
| 16.07 | `diff()` בלי מיון לפי זמן | **צריך למיין לפי `base_date_time`** – אחרת ההפרשים לא כרונולוגיים |
| 16.07 | `diff()` על מחרוזות | **צריך להמיר ל-`datetime` לפני `diff()`** – `pd.to_datetime()` |
| 16.07 | בלבול בין Anchoring ל-Maneuvering | **Anchoring = SOG < 0.5, Maneuvering = SOG ≥ 0.5** |
| 16.07 | Git commit – הוספתי תובנות | **מעכשיו: commit message = מה נבנה + מה הלקח** |
| 19.07 | `time_diff_total` מחושב – אבל לא חולץ לעמודות נפרדות | **צריך לחלץ `anchoring_time` ו-`maneuvering_time` כעמודות** |
| 19.07 | עדכון `devlog.md` – קובץ מסודר | **תיעוד = שליטה. לא לזכור – לתעד.** |
| 20.07 | `dwell_time` – לא הבנתי למה Anchoring ≈ Dwell | **Anchoring = SOG<0.5 (כללי), Dwell = SOG<0.5 + ברציף (ספציפי)** |
| 20.07 | `dwell_time` – קודם `status_dwell` ואז `merge` | **צריך לחשב `time_diff` על `status_dwell` כמו על `status`** |
| 21.07 | `hour` – השתמשתי לפני שיצרתי | **סדר פעולות: צור `df['hour']` לפני `groupby`** |
| 21.07 | `occupied` – ספרתי שורות במקום מיקומים | **`nunique()` על קואורדינטות, לא `size()` על שורות** |
| 21.07 | CI/CCI – לא הבנתי את ההבדל | **CI = רגעי, CCI = מצטבר** |

---

### 🔬 02.08 – Optimization with scipy.spatial.distance.pdist

| תאריך | טעות | תובנה / לקח |
|-------|------|--------------|
| 02.08 | לולאה כפולה על 481 ספינות (115,440 זוגות) | **חישוב וקטורי** – `pdist` מחשב הכל ב-C, מהיר פי 100 |
| 02.08 | ניסיתי לחשב מרחקים בזמן אמת | **לחשב מרחקים בבת אחת** – `coords = df[['lat','lon']].values` |

**Key insight:** 
- 481 ships = 115,440 pairs
- Loop: ~10-30 seconds
- `pdist`: < 0.1 seconds
- **Always prefer vectorized operations!**

---

### 🔬 05.08 – Encounter Detection – From Hours to Minutes

| תאריך | טעות | תובנה / לקח |
|-------|------|--------------|
| 05.08 | חישבתי Encounter על שעה שלמה (10,212 שורות) | **שעה = יותר מדי דגימות** – 481 ספינות מופיעות 21 פעמים כל אחת |
| 05.08 | קיבלתי 4.4M מפגשים על 52M זוגות | **צריך לקבץ לפי דקות** – כל דקה = 100-200 ספינות, ללא כפילויות |
| 05.08 | `results.append()` היה מחוץ ללולאה | **הזחה קובעת** – append בתוך הלולאה = 1440 דקות, מחוץ = דקה אחת |
| 05.08 | חשבתי ש-pdist על 10,212 שורות זה בסדר | **pdist מחשב n*(n-1)/2** – 10,212 → 52M זוגות (יותר מדי) |
| 05.08 | לא הבנתי את הקשר בין `df['minute']` ל-`groupby('minute')` | **groupby משתמש בעמודה** – `df['minute']` היא העמודה, `groupby` מקבץ לפיה |

**Key insights:**
- **שעה שלמה:** 10,212 שורות, 52M זוגות, 4.4M מפגשים (לא הגיוני)
- **דקה אחת:** 100-200 שורות, 10-20K זוגות, 1-2K מפגשים (הגיוני)
- **הפתרון:** קיבוץ לפי `minute` במקום `hour`
- **תוצאה:** 1440 דקות, ממוצע 138.8 ספינות לדקה, 940.7 מפגשים לדקה

---

### 🔬 21.07 – Understanding CI and CCI

| Metric | Definition | How to calculate |
|--------|------------|------------------|
| **CI (Congestion Index)** | Instant congestion – ratio of occupied berths to total berths at a given hour | `occupied / total_berths` |
| **CCI (Cumulative Congestion Index)** | Accumulated congestion over time – shows trend | `ci.cumsum()` |

**Key insights:**
- `occupied` = number of **unique locations** (lat_rounded, lon_rounded) where `status_dwell == 'dwell'`
- `total_berths` = `df['is_berth'].sum()` – total unique berth locations identified
- CI is **momentary**, CCI is **cumulative** – they serve different purposes
- CI tells you "how congested right now?" – CCI tells you "is congestion getting worse?"

**Formulas:**
occupied = df[df['status_dwell'] == 'dwell'].groupby('hour')[['lat_rounded', 'lon_rounded']].nunique().sum(axis=1)
total_berths = df['is_berth'].sum()
CI = occupied / total_berths
CCI = ci.cumsum()

text

---

### 🔬 20.07 – Understanding Anchoring vs Dwell

| Metric | Definition | How it's calculated |
|--------|------------|---------------------|
| **Anchoring** | Vessel is almost stationary (SOG < 0.5 knots) | Based on SOG only |
| **Dwell** | Vessel is at berth (SOG < 0.5 AND is_berth = True) | Based on SOG + location |

**How to interpret:**

| Condition | Meaning |
|-----------|---------|
| Anchoring ≈ Dwell | Vessel was **at berth** (Dwell) – no waiting |
| Anchoring > Dwell | Vessel was **waiting outside the berth** (true Anchoring) |
| Anchoring = 0 | Vessel did not stop at all |

**Key insight:** The difference `anchoring_time - dwell_time` indicates how much time a vessel spent waiting outside the berth. This is a direct measure of port congestion.

---

### 📊 Progress Summary (מעודכן – 05.08.2026)

| Phase | Status | Completion |
|-------|--------|------------|
| Infrastructure | ✅ | 100% |
| Data Acquisition (Live + History) | ✅ | 100% |
| AIS + Weather Merge | ✅ | 100% |
| PostgreSQL Setup | ✅ | 100% |
| Feature Engineering (SOG/COG/ROT) | ✅ | 100% |
| Feature Engineering (Zhou – Encounter Detection) | ✅ | 100% |
| Feature Engineering (Zhou – Course Alteration) | 🔲 | 0% |
| Feature Engineering (Zhou – Speed Change) | 🔲 | 0% |
| Weather Context (Filter) | 🔲 | 0% |
| Dark Vessel Detection | 🔲 | 0% |
| Normalization + Sequences | 🔲 | 0% |
| LSTM Autoencoder | 🔲 | 0% |
| Production (FastAPI + Streamlit + Docker) | 🔲 | 0% |

---

### 📝 Belcore Features – Removed (30.07)

| Feature | Status | Note |
|---------|--------|------|
| `anchoring_time` | ❌ | Removed – not relevant for VTS |
| `maneuvering_time` | ❌ | Removed – not relevant for VTS |
| `dwell_time` | ❌ | Removed – not relevant for VTS |
| `ci` (Congestion Index) | ❌ | Removed – not relevant for VTS |
| `cci` (Cumulative C.I.) | ❌ | Removed – not relevant for VTS |
| **Belcore** | ❌ | **Removed from product** – kept in backup |

**Decision:** Belcore is port/berth analysis, not VTS safety.
**Backup location:** `models/feature_engineering_backup.py`
**Commit:** `f0cf038`

---

### 📊 Encounter Detection – תוצאות סופיות (05.08)
Total minutes: 1440
Average ships per minute: 138.8
Average encounters per minute: 940.7
Max ships in a minute: 219 (23:00)
Max encounters in a minute: 2,018 (23:00)
Average pairs per minute: 9,785.6

text

---

*Last updated: 05.08.2026*