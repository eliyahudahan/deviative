import os 
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("dbname"),
    user=os.getenv("user_db"),      # make sure that variables adjusted to .env file
    password=os.getenv("password_db"),
    host=os.getenv("host_db")
)
print(conn)

#Creating table
cur = conn.cursor()
create_table_sql = """
CREATE TABLE if NOT EXISTS anomaly_events (
    id SERIAL PRIMARY KEY,
    vessel_id VARCHAR(50),
    timestamp TIMESTAMP,
    anomaly_type VARCHAR(50),
    score FLOAT,
    lat FLOAT,
    lon FLOAT,
    sog_before FLOAT,
    sog_after FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
    );
"""

cur.execute(create_table_sql)
conn.commit()
cur.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'anomaly_events'        
            );        
""")

exists = cur.fetchone()[0]

print(f"Table 'anomaly_events' exitsts: {exists}")
(conn.close())