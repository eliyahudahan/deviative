"""
Deviative - Streamlit Dashboard (DEMO).

Same as dashboard.py, but reads from a local CSV file
instead of PostgreSQL. Designed for Streamlit Cloud deployment.

Run locally:
    streamlit run dashboard_demo.py
"""

import os
import streamlit as st
import pandas as pd
import pydeck as pdk

RAD_TO_DEG = 180.0 / 3.141592653589793
DEMO_CSV = 'data/processed/encounter_results_demo.csv'


# ==========================================
# Page config
# ==========================================
st.set_page_config(
    page_title="Deviative – Maritime Encounter Detection (Demo)",
    page_icon="⚓",
    layout="wide",
)

st.title("⚓ Deviative – Maritime Encounter Detection")
st.markdown("*Portfolio demo – San Pedro Bay, 2025-06-01*")
st.info(
    "**Demo mode** – using a sampled dataset (~10K rows). "
    "Full project: 1.16M rows in PostgreSQL."
)
st.markdown("---")


# ==========================================
# Load CSV once
# ==========================================
@st.cache_data
def load_demo_data():
    """Load demo CSV and prepare coordinates."""
    if not os.path.exists(DEMO_CSV):
        st.error(f"Demo CSV not found: {DEMO_CSV}")
        st.stop()

    df = pd.read_csv(DEMO_CSV)
    df['base_date_time'] = pd.to_datetime(df['base_date_time'], format='ISO8601')

    # Radians → degrees
    df['lat_1'] = df['lat_rad_1'] * RAD_TO_DEG
    df['lon_1'] = df['lon_rad_1'] * RAD_TO_DEG
    df['lat_2'] = df['lat_rad_2'] * RAD_TO_DEG
    df['lon_2'] = df['lon_rad_2'] * RAD_TO_DEG

    return df


df_full = load_demo_data()


# ==========================================
# Sidebar: Map controls
# ==========================================
st.sidebar.header("🎛️ Map Controls")

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
    "**Deviative v1.0 – Demo**  \n"
    "Portfolio project – not deployed."
)


# ==========================================
# Shared: render map
# ==========================================
def render_map(df, color_mode='state', radius=20, show_lines=True):
    """Render PyDeck map. color_mode: 'state' or 'anomaly'."""
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
# Stats (computed from demo CSV)
# ==========================================
stats = {
    'total': len(df_full),
    'anchored': int((df_full['movement_state'] == 'anchored').sum()),
    'moving': int((df_full['movement_state'] == 'moving').sum()),
    'towing': int((df_full['movement_state'] == 'towing').sum()),
    'anomalies': int(df_full['anomaly_dcpa_tcpa'].sum()),
}


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
    **San Pedro Bay – 1,163,761 encounters between vessels in a single day**
    *(demo shows {stats['total']:,} sampled rows)*.

    - **63.4%** anchored
    - **36.5%** moving
    - **0.05%** towing

    **The challenge:** identify which of the **moving** encounters represent
    real risk, not routine traffic.
    """)

    st.markdown("---")
    st.markdown("##### All Encounters (colored by movement state)")
    st.markdown("🔵 Anchored  |  🟢 Towing  |  ⚪ Moving  |  🔴 Anomaly")

    render_map(df_full, color_mode='state', radius=point_radius, show_lines=False)

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

    with st.expander("Show sample table (first 500 rows)"):
        st.dataframe(df_full.head(500), width="stretch", height=400)


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
    st.markdown("##### Moving Encounters Only")
    st.markdown("⚪ Moving  |  🔴 Anomaly")

    df_moving = df_full[df_full['movement_state'] == 'moving']
    st.caption(f"Showing {len(df_moving):,} moving encounters (sample of 425,230)")
    render_map(df_moving, color_mode='state', radius=point_radius, show_lines=show_lines)

    with st.expander("Show sample table (first 500 moving rows)"):
        st.dataframe(df_moving.head(500), width="stretch", height=400)


# ==========================================
# Tab 3: The Results
# ==========================================
with tab3:
    st.subheader("The Results")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total (demo)", f"{stats['total']:,}")
    col2.metric("Moving", f"{stats['moving']:,}")
    col3.metric("Anomalies", f"{stats['anomalies']:,}")
    col4.metric(
        "Anomaly Rate",
        f"{stats['anomalies']/stats['moving']*100:.2f}%" if stats['moving'] > 0 else "N/A"
    )

    st.markdown("""
    **Full project results** (from 1.16M rows in PostgreSQL):

    - **No official Ground Truth exists** – therefore, no Precision/Recall is reported.
    - **Stability:** Train 1.45% / Test 0.91% anomaly rate (difference: 0.54%)
    - **Manual inspection:** 10/10 sampled anomalies are physically plausible
    - **Anchorage B:** 15.9% of anomalies fall within a known anchorage zone
      (mean SOG 4.15 knots – not dominated by false positives)
    """)

    st.markdown("---")
    st.markdown("##### Anomalies Only")
    st.markdown("🔴 Anomaly")

    df_anom = df_full[df_full['anomaly_dcpa_tcpa'] == True]
    st.caption(f"Showing {len(df_anom):,} anomalies (sample of 4,372)")
    render_map(df_anom, color_mode='anomaly', radius=point_radius, show_lines=show_lines)

    st.markdown("---")
    st.markdown("##### Top-10 Anomalies (ranked by severity)")
    st.caption("Severity = 1 / (DCPA × TCPA). Higher = more urgent.")

    top10 = df_anom[df_anom['dcpa'] > 0].copy()
    top10 = top10[top10['tcpa'] > 0].copy()
    top10['severity'] = 1.0 / (top10['dcpa'] * top10['tcpa'])
    top10 = top10.nlargest(10, 'severity')[[
        'base_date_time', 'mmsi1', 'mmsi2',
        'distance_km', 'tcpa', 'dcpa', 'severity'
    ]].round(4)

    if len(top10) > 0:
        st.dataframe(top10, width="stretch", height=400)
    else:
        st.info("No anomalies with valid DCPA/TCPA in demo sample.")

    with st.expander("Show sample anomalies table (first 500 rows)"):
        st.dataframe(df_anom.head(500), width="stretch", height=400)


# ==========================================
# Footer
# ==========================================
st.markdown("---")
st.caption(
    "**Deviative v1.0 – Demo** – Physics-based encounter detection.  \n"
    "Data: MarineCadastre.gov (2025-06-01, San Pedro Bay).  \n"
    "Portfolio project – not for production use.  \n"
    "Full project (1.16M rows) runs locally on PostgreSQL."
)