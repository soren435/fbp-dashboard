"""Budget vs. Faktisk – detaljeret afvigelsesanalyse."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from src.data_loader import load_all
from src.filters import render_sidebar, apply_filters
from src.transformations import merge_budget_actuals
from src.charts import budget_vs_actual_bar, variance_bar, stacked_category_bar, CAT_COLORS

st.set_page_config(page_title="Budget vs. Faktisk", page_icon="📊", layout="wide")

budget_df, actuals_df, _, _ = load_all()
valgte_afd, periode = render_sidebar()

budget_f = apply_filters(budget_df, periode, valgte_afd)
actuals_f = apply_filters(actuals_df, periode, valgte_afd)

# ── header ─────────────────────────────────────────────────────────────────────
st.title("📊 Budget vs. Faktisk")
st.caption(f"Periode: {periode[0]} – {periode[1]}")

# ── view selector ──────────────────────────────────────────────────────────────
view = st.radio(
    "Aggreger pr.",
    ["Måned (samlet)", "Afdeling", "Kategori"],
    horizontal=True,
)

if view == "Måned (samlet)":
    merged = merge_budget_actuals(budget_f, actuals_f, ["maaned"])
    merged["x"] = merged["maaned"].dt.strftime("%b %Y")
elif view == "Afdeling":
    merged = merge_budget_actuals(budget_f, actuals_f, ["afdeling"])
    merged["x"] = merged["afdeling"]
else:
    merged = merge_budget_actuals(budget_f, actuals_f, ["kategori"])
    merged["x"] = merged["kategori"]

# ── main charts ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Budget og faktisk forbrug")
    st.plotly_chart(budget_vs_actual_bar(merged, "x"), use_container_width=True)

with col2:
    st.subheader("Afvigelse %")
    st.plotly_chart(variance_bar(merged, "x"), use_container_width=True)

# ── variance table ─────────────────────────────────────────────────────────────
st.subheader("Afvigelsestabel")

tbl = merged[["x", "budget_dkk", "faktisk_dkk", "afvigelse_dkk", "afvigelse_pct"]].copy()
tbl.columns = ["", "Budget (DKK)", "Faktisk (DKK)", "Afvigelse (DKK)", "Afvigelse %"]


def _color_row(row):  # type: ignore[no-untyped-def]
    pct = row["Afvigelse %"]
    bg = "#fde8e8" if pct > 2 else ("#e8f8e8" if pct < -2 else "")
    return [f"background-color: {bg}"] * len(row)


styled = tbl.style.apply(_color_row, axis=1).format(
    {
        "Budget (DKK)": "{:,.0f}",
        "Faktisk (DKK)": "{:,.0f}",
        "Afvigelse (DKK)": "{:+,.0f}",
        "Afvigelse %": "{:+.1f}%",
    }
)
st.dataframe(styled, use_container_width=True, hide_index=True)

# ── stacked breakdown ──────────────────────────────────────────────────────────
st.divider()
st.subheader("Faktisk forbrug pr. afdeling og kategori")
st.plotly_chart(stacked_category_bar(actuals_f), use_container_width=True)

# ── monthly trend per dept ─────────────────────────────────────────────────────
st.divider()
st.subheader("Månedlig faktisk forbrug pr. afdeling")
import plotly.express as px  # noqa: E402

monthly_dept = (
    actuals_f.groupby(["maaned", "afdeling"])["faktisk_dkk"]
    .sum()
    .reset_index()
)
fig_trend = px.line(
    monthly_dept,
    x="maaned",
    y="faktisk_dkk",
    color="afdeling",
    markers=True,
    labels={
        "maaned": "Måned",
        "faktisk_dkk": "Faktisk (DKK)",
        "afdeling": "Afdeling",
    },
    color_discrete_map={
        "Kirurgi": "#4C72B0",
        "Anæstesi": "#DD8452",
        "Sterilcentral": "#55A868",
        "Robotenhed": "#C44E52",
    },
)
fig_trend.update_layout(height=360, margin=dict(t=10, b=40))
st.plotly_chart(fig_trend, use_container_width=True)
