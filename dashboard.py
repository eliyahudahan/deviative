"""
Deviative - Streamlit Dashboard.

Interactive dashboard for maritime encounter detection.

Run:
    streamlit run dashboard.py
"""

import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Deviative – Maritime Encounter Detection",
    page_icon="⚓",
    layout="wide",
)

st.title("⚓ Deviative – Maritime Encounter Detection")
st.markdown("*Interactive dashboard for VTS operators*")

# Placeholder
st.write("Dashboard scaffold ready. Filters coming next.")