"""
FBP Dashboard – Finance Business Partner
Hospitalskirurgi / Robotkirurgi-enhed

Entry point and landing page.
Business logic lives in src/  •  Dashboard pages live in pages/

Run:  streamlit run app.py
"""

import os
import sys

# ── path setup (must come before src imports) ──────────────────────────────────
ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FBP Dashboard – Kirurgi",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── ensure data exists ─────────────────────────────────────────────────────────
from src.data_loader import load_all  # noqa: E402  (import after sys.path setup)

load_all()  # triggers auto-generation of CSV files on first run

# ── landing page ───────────────────────────────────────────────────────────────
st.title("🏥 Finance Business Partner Dashboard")
st.subheader("Hospitalskirurgi · Robotkirurgi-enhed")

st.markdown(
    """
Velkommen til FBP Dashboard for Hospitalskirurgi og Robotkirurgi-enheden.

Dette dashboard understøtter **ledelsesmæssige beslutninger** ved at koble økonomi,
aktivitet og kapacitet i ét samlet overblik — fra budgetafvigelse til robot-ROI.

---
"""
)

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**Dataperiode**\nJan 2025 – Mar 2026\n\n*Syntetiske data til porteføljeformål.*")
with col2:
    st.info("**Enheder**\nKirurgi · Anæstesi\nSterilcentral · Robotenhed")
with col3:
    st.info("**Navigation**\nBrug sidepanelet til venstre\nfor at skifte side.")

st.divider()

st.markdown(
    """
### Sider i dashboardet

| Side | Indhold |
|------|---------|
| 📋 **Executive Summary** | KPI-overblik, top-afvigelser og ledelsesanbefaling |
| 📊 **Budget vs. Faktisk** | Afvigelsesanalyse pr. måned, afdeling og kategori |
| ⚙️ **Aktivitetsbaseret Kostpris** | Omkostning pr. operation og ressourcefordeling |
| 📅 **Kapacitetsudnyttelse** | Udnyttelsesgrad pr. enhed og OR-stue |
| 📈 **Forecast** | 12-måneders forecast med usikkerhedsbånd |
| 🤖 **Robot Business Case** | ROI-analyse og scenariemodel for robotkirurgi |
"""
)

st.divider()
st.caption("FBP Dashboard · Hospitalskirurgi · Data er syntetiske og bruges til porteføljeformål.")
