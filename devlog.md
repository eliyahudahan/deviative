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

---

### 📝 English Version

| Date | Mistake | Lesson Learned |
|------|---------|----------------|
| 20.07 | `dwell_time` – didn't understand why Anchoring ≈ Dwell | **Anchoring = SOG<0.5 (general), Dwell = SOG<0.5 + at berth (specific)** |
| 20.07 | `dwell_time` – first `status_dwell` then `merge` | **Need to compute `time_diff` on `status_dwell` the same way as on `status`** |

---

### 🔬 20.07 – Understanding Anchoring vs Dwell

| Metric | Definition | How it's calculated |
|--------|------------|---------------------|
| **Anchoring** | Vessel is almost stationary (SOG < 0.5 knots) | Based on SOG only |
| **Dwell** | Vessel is at berth (SOG < 0.5 AND is_berth = True) | Based on SOG + location |

**Key insight:**
- Anchoring and Dwell are **not** mutually exclusive.
- A vessel can be both Anchoring and Dwell at the same time.
- The difference: Anchoring includes **all** stationary time, Dwell only stationary time **at berth**.


### 🔬 20.07 – Anchoring vs Dwell: How to Interpret

| Condition | Meaning |
|-----------|---------|
| Anchoring ≈ Dwell | Vessel was **at berth** (Dwell) – no waiting |
| Anchoring > Dwell | Vessel was **waiting outside the berth** (true Anchoring) |
| Anchoring = 0 | Vessel did not stop at all |

**Key insight:** The difference `anchoring_time - dwell_time` indicates how much time a vessel spent waiting outside the berth. This is a direct measure of port congestion.

---

### 📊 Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Infrastructure | ✅ | 100% |
| Data Acquisition (Live + History) | ✅ | 100% |
| AIS + Weather Merge | ✅ | 100% |
| PostgreSQL Setup | ✅ | 100% |
| Feature Engineering (SOG/COG/ROT) | ✅ | 100% |
| Feature Engineering (Belcore – Anchoring Time) | ✅ | 100% |
| Feature Engineering (Belcore – Maneuvering Time) | ✅ | 100% |
| Feature Engineering (Belcore – Dwell Time) | ✅ | 100% |
| Feature Engineering (Belcore – CI, CCI) | 🔲 | 0% |
| Feature Engineering (Zhou) | 🔲 | 0% |
| Normalization + Sequences | 🔲 | 0% |
| LSTM Autoencoder | 🔲 | 0% |
| Rotterdam Evaluation | 🔲 | 0% |
| Anomaly Detection (4 types) | 🔲 | 0% |
| Production (FastAPI + Streamlit + Docker) | 🔲 | 0% |

---

### 📝 Additional Notes – Belcore Features (20.07)

**Features implemented:**
- `anchoring_time` – time with SOG < 0.5 knots ✅ (19.07)
- `maneuvering_time` – time with SOG ≥ 0.5 knots ✅ (19.07)
- `dwell_time` – time at berth (SOG < 0.5 AND is_berth) ✅ (20.07)
- `ci` – Congestion Index 🔲
- `cci` – Cumulative Congestion Index 🔲

**Reference values from Belcore (2026):**
- Anchoring (LA): 8–77 hours
- Anchoring (LB): 14–77 hours
- Maneuvering: 1–6 hours
- Dwell: 50–89% of total port time

---

*Last updated: 20.07.2026*