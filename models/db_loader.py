"""
Deviative - PostgreSQL loader.

Loads encounter results from CSV into PostgreSQL.

Usage:
    python -m models.db_loader

Configuration:
    Loads from .env file (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
    Requires python-dotenv.

Security:
    - Credentials loaded from .env file (gitignored).
    - No hardcoded passwords.
    - Fails if .env is missing or incomplete.
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("ERROR: python-dotenv is not installed.")
    print("Install: pip install python-dotenv")
    sys.exit(1)

from .config import OUTPUT_PATH


# ==========================================
# Configuration (from .env – no hardcoded defaults)
# ==========================================
def get_db_config():
    """
    Load DB config from environment variables.
    Fails if any required variable is missing.
    """
    required = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    config = {}
    missing = []

    for key in required:
        value = os.getenv(key)
        if value is None or value == '':
            missing.append(key)
        config[key] = value

    if missing:
        print("ERROR: Missing environment variables:")
        for key in missing:
            print(f"  - {key}")
        print("\nCreate a .env file in the project root with:")
        print("  DB_HOST=localhost")
        print("  DB_PORT=5432")
        print("  DB_NAME=deviative")
        print("  DB_USER=<your_user>")
        print("  DB_PASSWORD=<your_password>")
        sys.exit(1)

    return config


def get_engine():
    """Create SQLAlchemy engine for PostgreSQL."""
    cfg = get_db_config()
    url = (
        f"postgresql://{cfg['DB_USER']}:{cfg['DB_PASSWORD']}"
        f"@{cfg['DB_HOST']}:{cfg['DB_PORT']}/{cfg['DB_NAME']}"
    )
    return create_engine(url)


# ==========================================
# Schema creation
# ==========================================
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS encounters (
    id SERIAL PRIMARY KEY,
    base_date_time TIMESTAMP NOT NULL,
    mmsi1 BIGINT NOT NULL,
    mmsi2 BIGINT NOT NULL,
    distance_km FLOAT,
    tcpa FLOAT,
    tcpa_type VARCHAR(10),
    dcpa FLOAT,
    movement_state VARCHAR(20),
    sog1 FLOAT,
    sog2 FLOAT,
    cog1 FLOAT,
    cog2 FLOAT,
    lat_rad_1 FLOAT,
    lon_rad_1 FLOAT,
    lat_rad_2 FLOAT,
    lon_rad_2 FLOAT,
    length_1 FLOAT,
    length_2 FLOAT,
    anomaly_dcpa_tcpa BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_movement_state ON encounters(movement_state);
CREATE INDEX IF NOT EXISTS idx_anomaly ON encounters(anomaly_dcpa_tcpa);
CREATE INDEX IF NOT EXISTS idx_datetime ON encounters(base_date_time);
CREATE INDEX IF NOT EXISTS idx_mmsi1 ON encounters(mmsi1);
CREATE INDEX IF NOT EXISTS idx_mmsi2 ON encounters(mmsi2);
"""


def create_schema(engine):
    """Create table + indexes if not exist."""
    print("\n=== Creating schema ===")
    with engine.connect() as conn:
        for statement in SCHEMA_SQL.strip().split(';'):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    print("✅ Schema ready.")


# ==========================================
# Load data
# ==========================================
def load_csv_to_db(csv_path, engine, chunk_size=100_000):
    """
    Load encounters from CSV into PostgreSQL.
    Uses chunked inserts to avoid memory issues.
    """
    print(f"\n=== Loading data from {csv_path} ===")

    # Check if table already has data
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM encounters"))
        existing = result.scalar()
    if existing > 0:
        print(f"⚠️ Table already has {existing:,} rows.")
        response = input("Delete existing rows and reload? (y/n): ")
        if response.lower() == 'y':
            with engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE encounters RESTART IDENTITY"))
                conn.commit()
            print("✅ Table cleared.")
        else:
            print("Skipping load.")
            return

        # Load in chunks
    total_loaded = 0
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size)):
        # Convert datetime
        chunk['base_date_time'] = pd.to_datetime(
            chunk['base_date_time'],
            format='ISO8601'
        )

        # CSV stores TCPA/DCPA in uppercase; DB schema uses lowercase.
        # Rename to match schema before column selection.
        chunk = chunk.rename(columns={
            'TCPA': 'tcpa',
            'DCPA': 'dcpa',
        })

        # Select only columns in schema
        columns = [
            'base_date_time', 'mmsi1', 'mmsi2',
            'distance_km', 'tcpa', 'tcpa_type', 'dcpa', 'movement_state',
            'sog1', 'sog2', 'cog1', 'cog2',
            'lat_rad_1', 'lon_rad_1', 'lat_rad_2', 'lon_rad_2',
            'length_1', 'length_2', 'anomaly_dcpa_tcpa'
        ]
        chunk = chunk[[c for c in columns if c in chunk.columns]]

        chunk.to_sql(
            'encounters',
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=10_000
        )
        total_loaded += len(chunk)
        print(f"  Chunk {i+1}: {len(chunk):,} rows (total: {total_loaded:,})")

    print(f"\n✅ Total rows loaded: {total_loaded:,}")


# ==========================================
# Quick queries
# ==========================================
def run_sample_queries(engine):
    """Run basic sanity queries."""
    print(f"\n=== Sample Queries ===")

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM encounters"))
        total = result.scalar()
        print(f"Total encounters: {total:,}")

        result = conn.execute(text(
            "SELECT COUNT(*) FROM encounters WHERE anomaly_dcpa_tcpa = TRUE"
        ))
        anomalies = result.scalar()
        print(f"Anomalies: {anomalies:,}")

        result = conn.execute(text(
            "SELECT movement_state, COUNT(*) FROM encounters GROUP BY movement_state"
        ))
        print("Movement state distribution:")
        for row in result:
            print(f"  {row[0]}: {row[1]:,}")

        result = conn.execute(text("""
            SELECT base_date_time, mmsi1, mmsi2, distance_km, tcpa, dcpa
            FROM encounters
            WHERE anomaly_dcpa_tcpa = TRUE
            LIMIT 5
        """))
        print("\nSample anomalies:")
        for row in result:
            print(f"  {row[0]} | {row[1]} - {row[2]} | d={row[3]:.3f} | tcpa={row[4]:.4f} | dcpa={row[5]:.4f}")


# ==========================================
# Main
# ==========================================
def main():
    print("=" * 50)
    print("Deviative - PostgreSQL Loader")
    print("=" * 50)

    engine = get_engine()

    create_schema(engine)
    load_csv_to_db(OUTPUT_PATH, engine)
    run_sample_queries(engine)

    print("\n" + "=" * 50)
    print("DB load complete.")
    print("=" * 50)


if __name__ == "__main__":
    main()