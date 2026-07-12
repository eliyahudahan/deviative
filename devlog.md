
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