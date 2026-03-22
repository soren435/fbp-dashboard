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
st.caption("Hospitalskirurgi · Robotkirurgi-enhed  ·  Dataperiode: Jan 2025 – Mar 2026  ·  Simulerede data til porteføljeformål")

st.divider()

st.markdown(
    """
Dette dashboard identificerer centrale økonomiske og driftsmæssige drivere i
hospitalskirurgien, med særligt fokus på **robotkirurgi som kapacitets- og
omkostningsdriver**.

Analysen peger på:
- betydelig aktivitetstilvækst i robotkirurgi
- høj kapacitetsudnyttelse i robotenheden
- afvigelser primært drevet af udstyr og øget produktion

Dashboardet kan anvendes til at understøtte beslutninger om **kapacitetsudvidelse**,
prioritering af operationsprogram og økonomisk styring.
"""
)

# ── Key insights ───────────────────────────────────────────────────────────────
st.subheader("Nøgleindsigter")

i1, i2, i3, i4 = st.columns(4)
with i1:
    st.warning("**Kapacitetspres**\nRobotenheden nærmer sig kapacitetsloft i højaktivitetsperioder")
with i2:
    st.error("**Omkostningsdrivere**\nAfvigelser drives primært af udstyr og øget aktivitet i Robotenhed")
with i3:
    st.info("**Efterspørgselsvækst**\nEfterspørgslen efter robotkirurgi overstiger nuværende kapacitet")
with i4:
    st.success("**Potentiale**\nBusiness case for kapacitetsudvidelse understøttes af aktivitets- og økonomidata")

st.divider()

# ── Særligt fokus: robot ───────────────────────────────────────────────────────
st.subheader("Særligt fokus: Robotkirurgi")
st.markdown(
    """
Robotenheden er analyseret som en selvstændig driftsenhed, hvor kombinationen af
**stigende aktivitet**, **høj kapacitetsudnyttelse** og **øgede udstyrsomkostninger**
potentielt peger mod et kapacitetsloft.

Dette muliggør en konkret business case for udvidelse af robotkapaciteten —
baseret på både drifts- og økonomidata, ikke kun investeringsomkostninger.

➡️ Se **Robot Business Case** i sidepanelet for ROI-analyse og scenariemodel.
"""
)

st.divider()

# ── Navigation table ───────────────────────────────────────────────────────────
st.subheader("Analyseområder")

st.markdown(
    """
| Side | Forretningsværdi |
|------|-----------------|
| 📋 **Executive Summary** | Samlet ledelsesoverblik med KPI'er, afvigelser og anbefalinger |
| 📊 **Budget vs. Faktisk** | Identifikation af afvigelser og underliggende cost drivers |
| ⚙️ **Aktivitetsbaseret Kostpris** | Indblik i omkostningsstruktur pr. operationstype |
| 📅 **Kapacitetsudnyttelse** | Identifikation af flaskehalse og uudnyttet kapacitet |
| 📈 **Forecast** | Fremadskuende vurdering af økonomisk udvikling |
| 🤖 **Robot Business Case** | Beslutningsgrundlag for investering i robotkapacitet |
"""
)

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.caption("Afdelinger: Kirurgi · Anæstesi · Sterilcentral · Robotenhed")
with col2:
    st.caption("FBP Dashboard · Simulerede data · Bruges til porteføljeformål")
