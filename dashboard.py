"""
Deviative - Streamlit Dashboard.

Interactive dashboard for maritime encounter detection.

Structure (Nir Etzion standard):
    Tab 1 - The Problem:      What are we trying to solve?
    Tab 2 - The Principles:   What is the solution based on?
    Tab 3 - The Results:      What was actually achieved?

All data is loaded from PostgreSQL (via SQLAlchemy + .env credentials).

Run:
    streamlit run dashboard.py
"""

import os
import streamlit as st
import pandas as pd
import pydeck as pdk
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

RAD_TO_DEG = 180.0 / 3.141592653589793


# ==========================================
# Page config
# ==========================================
st.set_page_config(
    page_title="Deviative – Maritime Encounter Detection",
    page_icon="⚓",
    layout="wide",
)

st.title("⚓ Deviative – Maritime Encounter Detection")
st.markdown("*Portfolio project – San Pedro Bay, 2025-06-01*")
st.markdown("---")


# ==========================================
# DB connection (all values from .env – no defaults)
# ==========================================
@st.cache_resource
def get_engine():
    """Create SQLAlchemy engine from .env (cached across reruns)."""
    required = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    config = {key: os.getenv(key) for key in required}

    missing = [k for k, v in config.items() if not v]
    if missing:
        st.error(f"Missing environment variables in .env: {', '.join(missing)}")
        st.stop()

    url = (
        f"postgresql://{config['DB_USER']}:{config['DB_PASSWORD']}"
        f"@{config['DB_HOST']}:{config['DB_PORT']}/{config['DB_NAME']}"
    )
    return create_engine(url)


engine = get_engine()


# ==========================================
# Sidebar: Map controls
# ==========================================
st.sidebar.header("🎛️ Map Controls")

map_rows = st.sidebar.slider(
    "Max points on map",
    min_value=1000,
    max_value=50000,
    value=10000,
    step=1000,
)

point_radius = st.sidebar.slider(
    "Point radius (m)",
    min_value=5,
    max_value=100,
    value=20,
    step=5,
)

show_lines = st.sidebar.checkbox("Show pair lines", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Deviative v1.0**  \n"
    "Portfolio project – not deployed."
)


# ==========================================
# Cached data loaders
# ==========================================
@st.cache_data(ttl=600)
def fetch_stats():
    """Aggregate stats (used across tabs)."""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM encounters")).scalar()
        moving = conn.execute(text(
            "SELECT COUNT(*) FROM encounters WHERE movement_state = 'moving'"
        )).scalar()
        anchored = conn.execute(text(
            "SELECT COUNT(*) FROM encounters WHERE movement_state = 'anchored'"
        )).scalar()
        towing = conn.execute(text(
            "SELECT COUNT(*) FROM encounters WHERE movement_state = 'towing'"
        )).scalar()
        anomalies = conn.execute(text(
            "SELECT COUNT(*) FROM encounters WHERE anomaly_dcpa_tcpa = TRUE"
        )).scalar()
    return {
        'total': total,
        'moving': moving,
        'anchored': anchored,
        'towing': towing,
        'anomalies': anomalies,
    }


@st.cache_data(ttl=600)
def fetch_map_all(limit):
    """Fetch sample for Tab 1 map (all encounters)."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                base_date_time, mmsi1, mmsi2,
                distance_km, tcpa, dcpa,
                movement_state, anomaly_dcpa_tcpa,
                lat_rad_1, lon_rad_1,
                lat_rad_2, lon_rad_2
            FROM encounters
            ORDER BY base_date_time
            LIMIT {limit}
        """))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    if len(df) > 0:
        df['lat_1'] = df['lat_rad_1'] * RAD_TO_DEG
        df['lon_1'] = df['lon_rad_1'] * RAD_TO_DEG
        df['lat_2'] = df['lat_rad_2'] * RAD_TO_DEG
        df['lon_2'] = df['lon_rad_2'] * RAD_TO_DEG
    return df


@st.cache_data(ttl=600)
def fetch_map_moving(limit):
    """Fetch sample for Tab 2 map (moving only)."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                base_date_time, mmsi1, mmsi2,
                distance_km, tcpa, dcpa,
                movement_state, anomaly_dcpa_tcpa,
                lat_rad_1, lon_rad_1,
                lat_rad_2, lon_rad_2
            FROM encounters
            WHERE movement_state = 'moving'
            ORDER BY base_date_time
            LIMIT {limit}
        """))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    if len(df) > 0:
        df['lat_1'] = df['lat_rad_1'] * RAD_TO_DEG
        df['lon_1'] = df['lon_rad_1'] * RAD_TO_DEG
        df['lat_2'] = df['lat_rad_2'] * RAD_TO_DEG
        df['lon_2'] = df['lon_rad_2'] * RAD_TO_DEG
    return df


@st.cache_data(ttl=600)
def fetch_map_anomalies():
    """Fetch ALL anomalies for Tab 3 map (no limit)."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                base_date_time, mmsi1, mmsi2,
                distance_km, tcpa, dcpa,
                movement_state, anomaly_dcpa_tcpa,
                lat_rad_1, lon_rad_1,
                lat_rad_2, lon_rad_2
            FROM encounters
            WHERE anomaly_dcpa_tcpa = TRUE
            ORDER BY base_date_time
        """))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    if len(df) > 0:
        df['lat_1'] = df['lat_rad_1'] * RAD_TO_DEG
        df['lon_1'] = df['lon_rad_1'] * RAD_TO_DEG
        df['lat_2'] = df['lat_rad_2'] * RAD_TO_DEG
        df['lon_2'] = df['lon_rad_2'] * RAD_TO_DEG
    return df


@st.cache_data(ttl=600)
def fetch_table_all(limit=1000):
    """Fetch table for Tab 1."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                base_date_time, mmsi1, mmsi2,
                ROUND(distance_km::numeric, 3) AS distance_km,
                ROUND(tcpa::numeric, 4) AS tcpa,
                ROUND(dcpa::numeric, 4) AS dcpa,
                movement_state, anomaly_dcpa_tcpa
            FROM encounters
            ORDER BY base_date_time
            LIMIT {limit}
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=600)
def fetch_table_moving(limit=1000):
    """Fetch table for Tab 2."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                base_date_time, mmsi1, mmsi2,
                ROUND(distance_km::numeric, 3) AS distance_km,
                ROUND(tcpa::numeric, 4) AS tcpa,
                ROUND(dcpa::numeric, 4) AS dcpa,
                movement_state, anomaly_dcpa_tcpa
            FROM encounters
            WHERE movement_state = 'moving'
            ORDER BY base_date_time
            LIMIT {limit}
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=600)
def fetch_table_anomalies(limit=1000):
    """Fetch table for Tab 3."""
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                base_date_time, mmsi1, mmsi2,
                ROUND(distance_km::numeric, 3) AS distance_km,
                ROUND(tcpa::numeric, 4) AS tcpa,
                ROUND(dcpa::numeric, 4) AS dcpa,
                movement_state
            FROM encounters
            WHERE anomaly_dcpa_tcpa = TRUE
            ORDER BY base_date_time
            LIMIT {limit}
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@st.cache_data(ttl=600)
def fetch_top10_anomalies():
    """Top-10 by severity = 1 / (DCPA * TCPA)."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                base_date_time, mmsi1, mmsi2,
                ROUND(distance_km::numeric, 3) AS distance_km,
                ROUND(tcpa::numeric, 4) AS tcpa,
                ROUND(dcpa::numeric, 4) AS dcpa,
                ROUND((1.0 / NULLIF(dcpa * tcpa, 0))::numeric, 2) AS severity
            FROM encounters
            WHERE anomaly_dcpa_tcpa = TRUE
              AND dcpa > 0
              AND tcpa > 0
            ORDER BY 1.0 / (dcpa * tcpa) DESC
            LIMIT 10
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


# ==========================================
# Shared: render map
# ==========================================
def render_map(df, color_mode='state', radius=20, show_lines=True):
    """
    Render a PyDeck map.

    Args:
        df: DataFrame with lat_1, lon_1, lat_2, lon_2, distance_km
        color_mode: 'state' (movement state) or 'anomaly' (all red)
        radius: point radius in meters
        show_lines: draw lines between pairs (close pairs < 1 km)
    """
    if len(df) == 0:
        st.info("No data to display.")
        return

    df = df.copy()

    if color_mode == 'anomaly':
        df['color'] = [[255, 50, 50, 200]] * len(df)
    else:
        def get_color(row):
            if row['anomaly_dcpa_tcpa']:
                return [255, 50, 50, 200]
            if row['movement_state'] == 'anchored':
                return [0, 100, 200, 150]
            if row['movement_state'] == 'towing':
                return [0, 200, 0, 150]
            return [180, 180, 180, 100]
        df['color'] = df.apply(get_color, axis=1)

    layers = []

    # Lines (only close pairs < 1 km)
    if show_lines:
        close = df[df['distance_km'] < 1.0]
        if len(close) > 0:
            layers.append(pdk.Layer(
                "LineLayer",
                close,
                get_source_position=["lon_1", "lat_1"],
                get_target_position=["lon_2", "lat_2"],
                get_color=[200, 200, 200, 80],
                get_width=1,
                pickable=False,
            ))

    # Points (vessel 1 + vessel 2)
    p1 = df[['lat_1', 'lon_1', 'color', 'mmsi1', 'mmsi2',
             'distance_km', 'tcpa', 'dcpa',
             'movement_state', 'anomaly_dcpa_tcpa']].copy()
    p1.columns = ['lat', 'lon', 'color', 'mmsi_a', 'mmsi_b',
                  'distance_km', 'tcpa', 'dcpa',
                  'movement_state', 'anomaly_dcpa_tcpa']

    p2 = df[['lat_2', 'lon_2', 'color', 'mmsi1', 'mmsi2',
             'distance_km', 'tcpa', 'dcpa',
             'movement_state', 'anomaly_dcpa_tcpa']].copy()
    p2.columns = ['lat', 'lon', 'color', 'mmsi_a', 'mmsi_b',
                  'distance_km', 'tcpa', 'dcpa',
                  'movement_state', 'anomaly_dcpa_tcpa']

    points_all = pd.concat([p1, p2], ignore_index=True)

    layers.append(pdk.Layer(
        "ScatterplotLayer",
        points_all,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=radius,
        pickable=True,
        auto_highlight=True,
        radius_min_pixels=2,
        radius_max_pixels=20,
    ))

    center_lat = float(df[['lat_1', 'lat_2']].stack().mean())
    center_lon = float(df[['lon_1', 'lon_2']].stack().mean())

    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=11,
            pitch=0,
        ),
        tooltip={
            "html": (
                "<b>Pair:</b> {mmsi_a} / {mmsi_b}<br/>"
                "<b>Distance:</b> {distance_km} km<br/>"
                "<b>TCPA:</b> {tcpa} h<br/>"
                "<b>DCPA:</b> {dcpa} km<br/>"
                "<b>State:</b> {movement_state}<br/>"
                "<b>Anomaly:</b> {anomaly_dcpa_tcpa}"
            )
        },
    ))


# ==========================================
# Load stats ONCE (used by Tab 1 and Tab 3)
# ==========================================
stats = fetch_stats()


# ==========================================
# Tabs (Nir Etzion standard)
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📊 The Problem",
    "⚛️ The Principles",
    "✅ The Results",
])


# ==========================================
# Tab 1: The Problem
# ==========================================
with tab1:
    st.subheader("The Problem")
    st.markdown(f"""
    **San Pedro Bay – {stats['total']:,} encounters between vessels in a single day.**

    - **{stats['anchored']/stats['total']*100:.1f}%** anchored
    - **{stats['moving']/stats['total']*100:.1f}%** moving
    - **{stats['towing']/stats['total']*100:.2f}%** towing

    **The challenge:** identify which of the **moving** encounters represent
    real risk, not routine traffic.

    *This is a portfolio project. No independent ground truth exists for
    "dangerous encounters" in this dataset – see README for limitations.*
    """)

    st.markdown("---")
    st.markdown("##### All Encounters (sample, colored by movement state)")
    st.markdown("🔵 Anchored  |  🟢 Towing  |  ⚪ Moving  |  🔴 Anomaly")

    df_all = fetch_map_all(limit=map_rows)
    st.caption(f"Showing {len(df_all):,} encounters (sample of {stats['total']:,})")
    render_map(df_all, color_mode='state', radius=point_radius, show_lines=False)

    st.markdown("---")
    st.markdown("##### Movement State Distribution")
    states_df = pd.DataFrame([
        {'State': 'anchored', 'Count': stats['anchored']},
        {'State': 'moving',   'Count': stats['moving']},
        {'State': 'towing',   'Count': stats['towing']},
    ])
    states_df['Percentage'] = (states_df['Count'] / stats['total'] * 100).round(2)
    st.bar_chart(states_df.set_index('State')['Count'])
    st.dataframe(states_df, width="stretch")

    st.markdown("---")
    st.markdown("##### Sample of All Encounters")
    with st.expander("Show table (first 1000 rows)"):
        table_df = fetch_table_all(limit=1000)
        st.dataframe(table_df, width="stretch", height=400)


# ==========================================
# Tab 2: The Principles
# ==========================================
with tab2:
    st.subheader("The Principles")
    st.markdown("""
    **Method: DCPA/TCPA – standard parameters for collision risk assessment
    in maritime navigation, within the framework of COLREGs principles.**

    - **DCPA** – Distance to Closest Point of Approach (km)
    - **TCPA** – Time to Closest Point of Approach (hours)

    **Movement state filtering:** only `moving` pairs are considered.
    Anchored and towing pairs are excluded.

    **Thresholds** (derived from data via 2nd Derivative of KDE):
    - **DCPA** < 198 m
    - **TCPA** < 1.77 min
    - **Distance** < 1 km (guard)
    """)

    st.markdown("---")
    st.markdown("##### Moving Encounters Only (sample)")
    st.markdown("⚪ Moving  |  🔴 Anomaly (defined by DCPA/TCPA thresholds)")

    df_moving = fetch_map_moving(limit=map_rows)
    st.caption(f"Showing {len(df_moving):,} moving encounters (sample of {stats['moving']:,})")
    render_map(df_moving, color_mode='state', radius=point_radius, show_lines=show_lines)

    st.markdown("---")
    st.markdown("##### Sample of Moving Encounters")
    with st.expander("Show table (first 1000 moving rows)"):
        table_df = fetch_table_moving(limit=1000)
        st.dataframe(table_df, width="stretch", height=400)
    st.info(
    "🔴 Red points = anomalies detected by threshold "
    "(DCPA < 198m, TCPA < 1.77min). "
    "These are candidates for review, not confirmed incidents. "
    "No independent ground truth exists for this dataset."
    )

# ==========================================
# Tab 3: The Results
# ==========================================
with tab3:
    st.subheader("The Results")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Encounters", f"{stats['total']:,}")
    col2.metric("Moving", f"{stats['moving']:,}")
    col3.metric("Anomalies", f"{stats['anomalies']:,}")
    col4.metric(
        "Anomaly Rate",
        f"{stats['anomalies']/stats['moving']*100:.2f}%" if stats['moving'] > 0 else "N/A"
    )

    st.markdown("""
    **No official Ground Truth exists** – therefore, no Precision/Recall is reported.

    **What we do report:**
    - **Stability:** Train 1.45% / Test 0.91% anomaly rate (difference: 0.54%)
    - **Manual inspection:** 10/10 sampled anomalies are physically plausible
    - **Anchorage B:** 15.9% of anomalies fall within a known anchorage zone
      (mean SOG 4.15 knots – not dominated by false positives)
    """)

    st.markdown("---")
    st.markdown(f"##### Anomalies Only (all {stats['anomalies']:,})")
    st.markdown("🔴 Anomaly")

    df_anom = fetch_map_anomalies()
    st.caption(f"Showing {len(df_anom):,} anomalies")
    render_map(df_anom, color_mode='anomaly', radius=point_radius, show_lines=show_lines)

    st.markdown("---")
    st.markdown("##### Top-10 Anomalies (ranked by severity)")
    st.caption("Severity = 1 / (DCPA × TCPA). Higher = more urgent.")

    top10 = fetch_top10_anomalies()
    if len(top10) > 0:
        st.dataframe(top10, width="stretch", height=400)
    else:
        st.info("No anomalies with valid DCPA/TCPA.")

    st.markdown("---")
    st.markdown("##### All Anomalies (first 1000 rows)")
    with st.expander("Show table (first 1000 anomalies)"):
        table_df = fetch_table_anomalies(limit=1000)
        st.dataframe(table_df, width="stretch", height=400)
    st.warning(
    "⚠️ **No Ground Truth available.** "
    "Anomalies are detection-rule outputs, not verified near-misses. "
    "No Precision/Recall can be computed. "
    "Manual inspection of 10 cases showed 10/10 physically plausible, "
    "but this is not accuracy."
    )

# ==========================================
# Footer
# ==========================================
st.markdown("---")
st.caption(
    "**Deviative v1.0** – Physics-based encounter detection.  \n"
    "Data: MarineCadastre.gov (2025-06-01, San Pedro Bay).  \n"
    "Portfolio project – not for production use.  \n"
    "No Ground Truth available – see README for limitations."
)