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

---

### 🧠 Core Insights

| Topic | Insight |
|-------|---------|
| **Infrastructure** | Git, README, .gitignore – before anything else |
| **Data** | Use dedicated library for compressed files |
| **API** | Key + Bounding Box + WebSocket |
| **Data Processing** | Filter before merging – much faster |
| **PostgreSQL** | Docker + `host=localhost` + matching credentials |
| **Git** | Always use `git` prefix |
| **SQL** | `information_schema.tables` – with dot; `SERIAL` – not `SEARIAL` |
| **Python** | 3 quotes for multi-line; minimal imports; no extra parentheses |

---

### 📊 Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Infrastructure | ✅ | 100% |
| Data Acquisition (Live + History) | ✅ | 100% |
| AIS + Weather Merge | ✅ | 100% |
| PostgreSQL Setup | ✅ | 100% |
| Feature Engineering | 🔲 | 0% |
| LSTM Autoencoder | 🔲 | 0% |
| Anomaly Detection | 🔲 | 0% |
| Production (API + Dashboard) | 🔲 | 0% |

---

*Last updated: 13.07.2026*