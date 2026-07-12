
שלב	בעיה	פתרון	לקח
30.06	Git init, README	יצירת repo	תשתית תחילה
06.07	aisstream.io API	WebSocket + Bounding Box	API דורש מפתח
07.07	.zst file	pip install zstandard	קבצים דחוסים – ספרייה ייעודית
07.07	pandas read_csv	header=None, skiprows=1	קובץ CSV עם כותרת – דילוג על שורה 0
08.07	סינון קואורדינטות	between(-118.5, -118.0)	סינון לפני מיזוג = מהיר יותר
08.07	Weather API	requests.get() + JSON	הורדת נתונים דרך API
08.07	מיזוג AIS+Weather	pd.merge(on='time')	מיזוג לפי timestamp
09.07	PostgreSQL	psycopg2.OperationalError	PostgreSQL לא רץ → צריך Docker
09.07	Docker	docker run -d ...	הרצת DB בקופסה
12.07	PostgreSQL	host=localhost + פרטי התחברות נכונים	psycopg2 דורש TCP/IP ל-Docker; dbname, user, password חייבים להתאים
12.07	commit ללא git	git commit -m "..."	Git – תמיד עם git
12.07	information_schema_tables	information_schema.tables	PostgreSQL – Schema + נקודה
12.07	"""" (4 מירכאות)	""" (3 מירכאות)	Python – מחרוזות רב-שורתיות עם 3 מירכאות
12.07	SEARIAL	SERIAL	SQL – אוטו-אינקרמנט = SERIAL
12.07	conn.close() עם סוגריים	conn.close()	Python – פונקציות בלי סוגריים מיותרים



| Date | Task | Solution | Lesson Learned |
|------|------|----------|----------------|
| 30.06 | Git init, README | Created repository | Infrastructure first |
| 06.07 | aisstream.io API | WebSocket + Bounding Box | API requires an access key |
| 07.07 | .zst file | pip install zstandard | Compressed files need a dedicated library |
| 07.07 | pandas read_csv | header=None, skiprows=1 | CSV with header – skip row 0 for raw data |
| 08.07 | Coordinate filtering | between(-118.5, -118.0) | Filter before merging = faster processing |
| 08.07 | Weather API | requests.get() + JSON | Fetch data via API |
| 08.07 | AIS + Weather merge | pd.merge(on='time') | Merge on timestamp |
| 09.07 | PostgreSQL | psycopg2.OperationalError | PostgreSQL not running → need Docker |
| 09.07 | Docker | docker run -d ... | Run DB in a container |
| Date | Task | Solution | Lesson Learned |
|------|------|----------|----------------|
| 12.07 | PostgreSQL | `host=localhost` + correct credentials | psycopg2 requires TCP/IP for Docker; `dbname`, `user`, and `password` must match the container configuration |
| 12.07	commit without git	git commit -m "..."	Git – always use git prefix
| 12.07	information_schema_tables	information_schema.tables	PostgreSQL – schema + dot notation
| 12.07	"""" (4 quotes)	""" (3 quotes)	Python – multi-line strings use 3 quotes
| 12.07	SEARIAL	SERIAL	SQL – auto-increment is SERIAL
| 12.07	conn.close() with extra parentheses	conn.close()	Python – functions without extra parentheses