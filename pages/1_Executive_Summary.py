"""Executive Summary – Ledelsesoverblik."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from src.data_loader import load_all
from src.filters import render_sidebar, apply_filters
from src.kpi import calc_total_kpis, detailed_variance
from src.commentary import (
    generate_total_commentary,
    generate_dept_commentary,
    generate_detail_commentary,
    generate_recommendation,
)
from src.charts import (
    budget_vs_actual_bar,
    variance_bar,
    fmt_dkk,
    DEPT_COLORS,
)
from src.transformations import merge_budget_actuals

import plotly.express as px

st.set_page_config(page_title="Executive Summary", page_icon="📋", layout="wide")

# ── data + filters ─────────────────────────────────────────────────────────────
budget_df, actuals_df, operations_df, capacity_df = load_all()
valgte_afd, periode = render_sidebar()

budget_f = apply_filters(budget_df, periode, valgte_afd)
actuals_f = apply_filters(actuals_df, periode, valgte_afd)
operations_f = apply_filters(operations_df, periode)
capacity_f = apply_filters(capacity_df, periode)

period_label = f"{periode[0]} – {periode[1]}"

# ── KPIs ───────────────────────────────────────────────────────────────────────
kpis = calc_total_kpis(budget_f, actuals_f, capacity_f, operations_f)

# ── header ─────────────────────────────────────────────────────────────────────
st.title("📋 Executive Summary")
st.caption(f"Periode: {period_label}  ·  Afdelinger: {', '.join(valgte_afd)}")

# ── KPI cards ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.metric("Total budget", fmt_dkk(kpis.total_budget))

with c2:
    st.metric("Faktisk forbrug", fmt_dkk(kpis.total_actuals))

with c3:
    sign = "+" if kpis.variance_dkk > 0 else ""
    st.metric(
        "Afvigelse (DKK)",
        f"{sign}{fmt_dkk(kpis.variance_dkk)}",
        delta_color="off",
    )

with c4:
    delta_color = "inverse" if kpis.variance_pct > 2 else "normal"
    st.metric(
        "Afvigelse %",
        f"{kpis.variance_pct:+.1f}%",
        delta=f"{'Over' if kpis.variance_pct > 0 else 'Under'} budget",
        delta_color=delta_color,
    )

with c5:
    util_delta = kpis.avg_capacity_util - 80
    st.metric(
        "Kapacitetsudnyttelse",
        f"{kpis.avg_capacity_util:.1f}%",
        delta=f"{util_delta:+.1f}% ift. 80%-mål",
        delta_color="normal" if util_delta >= 0 else "inverse",
    )

with c6:
    st.metric("Cost per robotkirurgi-case", fmt_dkk(kpis.cost_per_robot_case))

st.divider()

# ── Overall commentary ─────────────────────────────────────────────────────────
st.markdown(generate_total_commentary(budget_f, actuals_f, period_label))

# ── Two-column charts ──────────────────────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Budget vs. Faktisk – månedlig")
    merged_m = merge_budget_actuals(budget_f, actuals_f, ["maaned"])
    merged_m["x"] = merged_m["maaned"].dt.strftime("%b %Y")
    st.plotly_chart(
        budget_vs_actual_bar(merged_m, "x", height=320),
        use_container_width=True,
    )

with right:
    st.subheader("Afvigelse % pr. måned")
    st.plotly_chart(
        variance_bar(merged_m, "x", height=320),
        use_container_width=True,
    )

st.divider()

# ── Top 3 afvigelser ───────────────────────────────────────────────────────────
col_text, col_chart = st.columns([1, 1])

with col_text:
    st.subheader("Top-3 afvigelser")
    st.markdown(generate_detail_commentary(budget_f, actuals_f, top_n=3))

with col_chart:
    st.subheader("Forbrug pr. afdeling")
    dept_sum = (
        actuals_f.groupby("afdeling")["faktisk_dkk"]
        .sum()
        .reset_index()
        .sort_values("faktisk_dkk", ascending=False)
    )
    fig_dept = px.bar(
        dept_sum,
        x="afdeling",
        y="faktisk_dkk",
        color="afdeling",
        color_discrete_map=DEPT_COLORS,
        labels={"afdeling": "Afdeling", "faktisk_dkk": "Faktisk forbrug (DKK)"},
        text_auto=".3s",
    )
    fig_dept.update_layout(showlegend=False, height=320, margin=dict(t=10, b=40))
    st.plotly_chart(fig_dept, use_container_width=True)

st.divider()

# ── Department commentary ──────────────────────────────────────────────────────
st.subheader("Status pr. afdeling")
for line in generate_dept_commentary(budget_f, actuals_f):
    st.markdown(line)

st.divider()

# ── Recommendation ─────────────────────────────────────────────────────────────
st.subheader("Ledelsesanbefaling")
st.markdown(generate_recommendation(budget_f, actuals_f))
