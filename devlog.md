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
| 16.07 | `diff()` על מחרוזות | **צריך להמיר ל-`datetime` לפני `diff()`** |
| 16.07 | בלבול בין Anchoring ל-Maneuvering | **Anchoring = SOG < 0.5, Maneuvering = SOG ≥ 0.5** |
| 16.07 | Git commit – הוספתי תובנות | **מעכשיו: commit message = מה נבנה + מה הלקח** |
| 19.07 | עדכון `devlog.md` – קובץ מסודר | **תיעוד = שליטה. לא לזכור – לתעד.** |

---

### 📝 English Version

| Date | Mistake | Lesson Learned |
|------|---------|----------------|
| 30.06 | Started without Git | **Infrastructure first** – always set up repo, README, .gitignore before code |
| 06.07 | API without key | **API requires access key** – authentication is mandatory |
| 07.07 | Tried to open `.zst` with pandas | **Compressed files → dedicated library** – `zstandard` |
| 07.07 | pandas read header as data | **CSV with header → `skiprows=1`** – skip row 0 |
| 08.07 | Merged before filtering | **Filter before merging = faster** – 199K instead of 4M |
| 08.07 | Weather – manual download | **Fetch data via API** – `requests.get()` + JSON |
| 08.07 | Merged by date only | **Merge on timestamp** – `pd.merge(on='time')` |
| 09.07 | PostgreSQL not running | **PostgreSQL not running → need Docker** |
| 09.07 | Tried to run PostgreSQL locally | **Run DB in a container** – `docker run -d` |
| 12.07 | psycopg2 tried Unix Socket | **psycopg2 requires TCP/IP for Docker** – `host=localhost` |
| 12.07 | Credentials mismatch | **dbname, user, password must match** |
| 12.07 | `commit` without `git` | **Git – always with `git`** |
| 12.07 | `information_schema_tables` | **PostgreSQL – schema + dot** – `information_schema.tables` |
| 12.07 | `""""` (4 quotes) | **Python – 3 quotes for multi-line strings** |
| 12.07 | `SEARIAL` | **SQL – auto-increment is `SERIAL`** |
| 12.07 | `(conn.close())` with parentheses | **Python – functions without extra parentheses** |
| 12.07 | `cur= IF NOT EXISTS { ... }` | **SQL = string, not code block** |
| 12.07 | `import sqlalchemy` + `datetime` | **Import only what you use** |
| 13.07 | Tried to calculate `sog_diff` from non-existent column | **KeyError – understand data structure before calculating** |
| 13.07 | Stopped – didn't copy | **Better to stop than to copy without understanding** |
| 14.07 | Changed column names in `save_by_coord.py` – didn't update downstream | **Name change = update everywhere** – consistency |
| 14.07 | `skiprows=1` skipped header | **Better to load with header** – `df.columns = [...]` instead of skipping |
| 15.07 | `read_csv` with `rows` instead of `nrows` | **Correct parameter is `nrows`** |
| 15.07 | `rename` instead of `columns` | **Renaming = `df.columns = [...]`** |
| 15.07 | Hard-coded vs generic code | **Generic code – identify by content, not position** |
| 15.07 | Changed architecture – added names in `save_by_coord.py` | **Architectural decision – mine** – not just a fix, a plan |
| 16.07 | `time_diff` without grouping by `mmsi` | **Must group by `mmsi`** – otherwise mixing different vessels |
| 16.07 | `diff()` without sorting by time | **Must sort by `base_date_time`** – otherwise intervals aren't chronological |
| 16.07 | `diff()` on strings | **Convert to `datetime` before `diff()`** |
| 16.07 | Confused Anchoring vs Maneuvering | **Anchoring = SOG < 0.5, Maneuvering = SOG ≥ 0.5** |
| 16.07 | Git commit – added insights | **From now on: commit message = what was built + lesson learned** |
| 19.07 | Updated `devlog.md` – organized file | **Documentation = control. Don't remember – document.** |

### 19.07 – Understanding Anchoring Time Calculation

**How it works:**
1. `loc` – marks rows with SOG < 0.5 as 'anchoring'
2. `shift(1)` – compares each row to the previous one to detect status changes
3. `groupby('mmsi')` – calculates time differences within each vessel (not across vessels)
4. `sum()` – aggregates total time per vessel per status

**Key insight:**
- Anchoring = vessel is almost stationary (SOG < 0.5 knots)
- Maneuvering = vessel is moving (SOG ≥ 0.5 knots)
- Status change = transition point between the two states
---

### 🧠 Core Insights

| Topic | Insight |
|-------|---------|
| **Infrastructure** | Git, README, .gitignore – before anything else |
| **Data** | Use dedicated library for compressed files |
| **API** | Key + Bounding Box + WebSocket |
| **Data Processing** | Filter before merging – much faster |
| **PostgreSQL** | Docker + `host=localhost` + matching credentials |
| **Git** | Always use `git` prefix; **commit message = what was built + lesson learned** |
| **SQL** | `information_schema.tables` – with dot; `SERIAL` – not `SEARIAL` |
| **Python** | 3 quotes for multi-line; minimal imports; no extra parentheses |
| **Generic Code** | Identify columns by content, not position |
| **Consistency** | Change names = update everywhere |
| **Architecture** | Make decisions. Don't just fix. Plan. |
| **Grouping** | Group by `mmsi` before time calculations – avoid mixing vessels |
| **Sorting** | Sort by `base_date_time` before `diff()` – intervals must be chronological |
| **Type Conversion** | Convert to `datetime` before `diff()` – strings can't be subtracted |
| **Anchoring vs Maneuvering** | Anchoring = SOG < 0.5, Maneuvering = SOG ≥ 0.5 |
| **Learning Strategy** | Stop instead of copying; understand, then build |
| **Documentation** | Don't remember – document |

---

### 📊 Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Infrastructure | ✅ | 100% |
| Data Acquisition (Live + History) | ✅ | 100% |
| AIS + Weather Merge | ✅ | 100% |
| PostgreSQL Setup | ✅ | 100% |
| Feature Engineering (SOG/COG/ROT) | ✅ | 100% |
| Feature Engineering (Belcore – Anchoring) | 🔄 | 60% |
| Feature Engineering (Belcore – Dwell, CI, CCI) | 🔲 | 0% |
| Feature Engineering (Zhou) | 🔲 | 0% |
| Normalization + Sequences | 🔲 | 0% |
| LSTM Autoencoder | 🔲 | 0% |
| Rotterdam Evaluation | 🔲 | 0% |
| Anomaly Detection (4 types) | 🔲 | 0% |
| Production (FastAPI + Streamlit + Docker) | 🔲 | 0% |

---

### 📝 Additional Notes – Belcore Features (16.07)

**Features to implement:**
- `anchoring_time` – time with SOG < 0.5 knots
- `dwell_time` – time at berth (requires berth coordinates)
- `maneuvering_time` – time with SOG > 0.5 knots in port
- `ci` – Congestion Index (occupied berths / available berths)
- `cci` – Cumulative Congestion Index

**Reference values from Belcore (2026):**
- Anchoring (LA): 8–77 hours
- Anchoring (LB): 14–77 hours
- Maneuvering: 1–6 hours

---

*Last updated: 19.07.2026*