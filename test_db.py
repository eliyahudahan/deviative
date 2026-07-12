import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("dbname"),
    user=os.getenv("user_db"),       # make sure that variables adjusted to .env file
    password=os.getenv("password_db"),
    host=os.getenv("host_db")
)
print(conn)