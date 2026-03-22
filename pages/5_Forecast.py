"""Forecast – 12-måneders fremskrivning med usikkerhedsbånd."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px

from src.data_loader import load_all
from src.filters import render_sidebar, apply_filters
from src.forecast import build_total_forecast, build_dept_forecast
from src.charts import forecast_chart, fmt_dkk

st.set_page_config(page_title="Forecast", page_icon="📈", layout="wide")

budget_df, actuals_df, _, _ = load_all()
valgte_afd, periode = render_sidebar()

# Forecast uses all historical actuals (not filtered by period) for better fit
actuals_all = actuals_df[actuals_df["afdeling"].isin(valgte_afd)].copy()
budget_all = budget_df[budget_df["afdeling"].isin(valgte_afd)].copy()

# ── header ─────────────────────────────────────────────────────────────────────
st.title("📈 Forecast – 12-måneders fremskrivning")
st.caption(
    "Forecast beregnes på det fulde historiske datasæt for de valgte afdelinger. "
    "Periodsfiltret påvirker ikke modellen – kun de viste afvigelser."
)

# ── model selector ─────────────────────────────────────────────────────────────
col_opts = st.columns([1, 1, 2])
with col_opts[0]:
    n_periods = st.slider("Antal forecast-måneder", min_value=3, max_value=18, value=12)
with col_opts[1]:
    conf_pct = st.slider("Konfidensinterval ±%", min_value=5, max_value=25, value=10)

# ── build forecast ─────────────────────────────────────────────────────────────
fc = build_total_forecast(actuals_all, periods=n_periods, confidence_pct=conf_pct / 100)

act_monthly = actuals_all.groupby("maaned")["faktisk_dkk"].sum().reset_index()
bud_monthly = budget_all.groupby("maaned")["budget_dkk"].sum().reset_index()

# ── model info ─────────────────────────────────────────────────────────────────
model_label = fc["model"].iloc[0]
st.info(
    f"**Model:** {model_label}  ·  "
    f"**Datapunkter brugt:** {len(act_monthly)} måneder  ·  "
    f"**Konfidensinterval:** ±{conf_pct}%"
)

# ── KPI row ────────────────────────────────────────────────────────────────────
last_actual_date = act_monthly["maaned"].max()
fc_total = fc["forecast_dkk"].sum()
bud_remaining = bud_monthly[bud_monthly["maaned"] > last_actual_date]["budget_dkk"].sum()
avg_monthly_fc = fc["forecast_dkk"].mean()

k1, k2, k3 = st.columns(3)
k1.metric(f"Forecast samlet ({n_periods} mdr.)", fmt_dkk(fc_total))
k2.metric("Resterende budgetramme", fmt_dkk(bud_remaining))
k3.metric("Gns. månedligt forecast", fmt_dkk(avg_monthly_fc))

# ── main chart ─────────────────────────────────────────────────────────────────
st.subheader("Samlet forecast – alle afdelinger")
st.plotly_chart(
    forecast_chart(act_monthly, bud_monthly, fc),
    use_container_width=True,
)

# ── Department forecast ────────────────────────────────────────────────────────
st.divider()
st.subheader("Forecast pr. afdeling (næste 6 måneder)")
st.caption("Lineær trendekstrapolation pr. afdeling baseret på historiske actuals.")

dept_fc = build_dept_forecast(actuals_all, periods=6)

# Combine actuals + forecast for each dept into one chart
dept_actuals = actuals_all.groupby(["maaned", "afdeling"])["faktisk_dkk"].sum().reset_index()

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

DEPT_COLORS = {
    "Kirurgi": "#4C72B0",
    "Anæstesi": "#DD8452",
    "Sterilcentral": "#55A868",
    "Robotenhed": "#C44E52",
}

fig_dept = go.Figure()
for dept in dept_actuals["afdeling"].unique():
    color = DEPT_COLORS.get(dept, "#888")
    act = dept_actuals[dept_actuals["afdeling"] == dept]
    fc_d = dept_fc[dept_fc["afdeling"] == dept]

    fig_dept.add_scatter(
        x=act["maaned"],
        y=act["faktisk_dkk"] / 1e6,
        name=dept,
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5),
        legendgroup=dept,
    )
    fig_dept.add_scatter(
        x=fc_d["maaned"],
        y=fc_d["forecast_dkk"] / 1e6,
        name=f"{dept} (forecast)",
        mode="lines+markers",
        line=dict(color=color, width=2, dash="dash"),
        marker=dict(size=5, symbol="diamond"),
        legendgroup=dept,
        showlegend=False,
    )

fig_dept.add_vline(
    x=last_actual_date.timestamp() * 1000,
    line_dash="dot",
    line_color="grey",
    annotation_text="Forecast start",
    annotation_position="top right",
)
fig_dept.update_layout(
    yaxis_title="Mio. DKK",
    legend=dict(orientation="h", y=1.08),
    height=400,
    margin=dict(t=20, b=40),
)
st.plotly_chart(fig_dept, use_container_width=True)

# ── forecast table ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Forecast-detaljer (samlet)")
fc_disp = fc[["maaned", "forecast_dkk", "lower", "upper"]].copy()
fc_disp["maaned"] = fc_disp["maaned"].dt.strftime("%b %Y")
fc_disp.columns = ["Måned", "Forecast (DKK)", "Nedre grænse", "Øvre grænse"]
st.dataframe(
    fc_disp.style.format(
        {
            "Forecast (DKK)": "{:,.0f}",
            "Nedre grænse": "{:,.0f}",
            "Øvre grænse": "{:,.0f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# ── model explanation ──────────────────────────────────────────────────────────
st.divider()
with st.expander("Om forecast-modellen og begrænsninger"):
    st.markdown(
        """
**Modelvalg:**

| Tilgængelige datapunkter | Model |
|--------------------------|-------|
| ≥ 24 måneder | Holt-Winters med additiv sæsonkomponent (periode 12) |
| 12–23 måneder | Holt double-eksponentiel (trend + udjævning) |
| < 12 måneder | Lineær trend (OLS-regression) |

**Begrænsninger:**
- Modellen tager ikke højde for budgetjusteringer eller planlagte strukturelle ændringer.
- Sæsoneffekter er kun robuste med ≥ 2 fulde årsforløb i data.
- Konfidensintervallet er symmetrisk og beregnet som ±% af punktestimatet — ikke et statistisk bånd.
- Forecastet bør suppleres med faglig vurdering fra afdeling og økonomiansvarlig.
"""
    )
