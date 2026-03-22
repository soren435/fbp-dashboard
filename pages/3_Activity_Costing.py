"""Aktivitetsbaseret Kostpris – cost per case og ressourcefordeling."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px

from src.data_loader import load_all
from src.filters import render_sidebar, apply_filters
from src.transformations import (
    ops_cost_per_case,
    ops_monthly_cost,
    ops_monthly_volume,
    join_robot_actuals_operations,
    volume_vs_cost_trend,
)
from src.charts import OP_COLORS, CAT_COLORS, fmt_dkk

st.set_page_config(page_title="Aktivitetsbaseret Kostpris", page_icon="⚙️", layout="wide")

budget_df, actuals_df, operations_df, capacity_df = load_all()
valgte_afd, periode = render_sidebar()

actuals_f = apply_filters(actuals_df, periode, valgte_afd)
operations_f = apply_filters(operations_df, periode)

# ── header ─────────────────────────────────────────────────────────────────────
st.title("⚙️ Aktivitetsbaseret Kostpris (ABC)")
st.caption(
    "Omkostningsfordeling baseret på operationstype og ressource. "
    "Kobler aktivitetsdata med økonomidata for at beregne cost-per-case."
)

# ── KPI row ────────────────────────────────────────────────────────────────────
cpc = ops_cost_per_case(operations_f)
robot_row = cpc[cpc["operationstype"] == "Robotkirurgi"]
lap_row = cpc[cpc["operationstype"] == "Laparoskopi"]
robot_cpc = robot_row["cost_per_case"].values[0] if len(robot_row) else 0
lap_cpc = lap_row["cost_per_case"].values[0] if len(lap_row) else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total operationsomkostning", fmt_dkk(operations_f["omkostning_dkk"].sum()))
k2.metric(
    "Cost per robotkirurgi-case",
    fmt_dkk(robot_cpc),
    delta=f"{(robot_cpc / lap_cpc - 1) * 100:+.0f}% ift. laparoskopi" if lap_cpc else None,
    delta_color="off",
)
k3.metric("Cost per laparoskopi-case", fmt_dkk(lap_cpc))
total_cases = (
    operations_f.drop_duplicates(subset=["maaned", "operationstype"])["antal"].sum()
)
k4.metric("Samlet antal operationer", f"{total_cases:,.0f}")

st.divider()

# ── Cost per case + resource breakdown ─────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cost per case pr. operationstype")
    fig_cpc = px.bar(
        cpc.sort_values("cost_per_case", ascending=False),
        x="operationstype",
        y="cost_per_case",
        color="operationstype",
        color_discrete_map=OP_COLORS,
        text_auto=".0f",
        labels={
            "operationstype": "Operationstype",
            "cost_per_case": "DKK pr. case",
        },
    )
    fig_cpc.update_layout(showlegend=False, height=360, margin=dict(t=10, b=40))
    st.plotly_chart(fig_cpc, use_container_width=True)

with col2:
    st.subheader("Ressourcefordeling pr. operationstype")
    res_breakdown = (
        operations_f.groupby(["operationstype", "ressource"])["omkostning_dkk"]
        .sum()
        .reset_index()
    )
    fig_res = px.bar(
        res_breakdown,
        x="operationstype",
        y="omkostning_dkk",
        color="ressource",
        barmode="stack",
        color_discrete_map=CAT_COLORS,
        text_auto=".3s",
        labels={
            "operationstype": "Operationstype",
            "omkostning_dkk": "Omkostning (DKK)",
            "ressource": "Ressource",
        },
    )
    fig_res.update_layout(height=360, margin=dict(t=10, b=40))
    st.plotly_chart(fig_res, use_container_width=True)

# ── Monthly cost trend ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Månedlig omkostningsudvikling pr. operationstype")

op_trend = ops_monthly_cost(operations_f)
fig_trend = px.line(
    op_trend,
    x="maaned",
    y="omkostning_dkk",
    color="operationstype",
    color_discrete_map=OP_COLORS,
    markers=True,
    labels={
        "maaned": "Måned",
        "omkostning_dkk": "Omkostning (DKK)",
        "operationstype": "Operationstype",
    },
)
fig_trend.update_layout(height=360, margin=dict(t=10, b=40))
st.plotly_chart(fig_trend, use_container_width=True)

# ── Volume vs. cost index ──────────────────────────────────────────────────────
st.divider()
st.subheader("Robotkirurgi: Volumen- vs. Omkostningsindeks (base = jan 2025)")
st.caption(
    "Viser om omkostningerne stiger proportionalt med aktiviteten, eller om der er et "
    "yderligere strukturelt cost-pres ud over aktivitetsvæksten."
)

trend_idx = volume_vs_cost_trend(operations_f)
if not trend_idx.empty:
    import plotly.graph_objects as go  # noqa: E402

    fig_idx = go.Figure()
    fig_idx.add_scatter(
        x=trend_idx["maaned"],
        y=trend_idx["volume_index"],
        name="Volumenindeks",
        mode="lines+markers",
        line=dict(color="#4C72B0", width=2.5),
    )
    fig_idx.add_scatter(
        x=trend_idx["maaned"],
        y=trend_idx["cost_index"],
        name="Omkostningsindeks",
        mode="lines+markers",
        line=dict(color="#C44E52", width=2.5, dash="dash"),
    )
    fig_idx.add_hline(y=100, line_dash="dot", line_color="grey")
    fig_idx.update_layout(
        yaxis_title="Indeks (jan 2025 = 100)",
        legend=dict(orientation="h", y=1.05),
        height=340,
        margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig_idx, use_container_width=True)

# ── Productivity KPIs: cost vs. robot actuals ──────────────────────────────────
st.divider()
st.subheader("Robotenhed: Faktisk omkostning vs. robot-aktivitet pr. måned")

robot_linked = join_robot_actuals_operations(actuals_f, operations_f)

if not robot_linked.empty:
    col_a, col_b = st.columns(2)

    with col_a:
        import plotly.graph_objects as go  # noqa: F811, E402

        fig_rc = go.Figure()
        fig_rc.add_bar(
            x=robot_linked["maaned"].dt.strftime("%b %Y"),
            y=robot_linked["robot_cases"],
            name="Robotkirurgi-cases",
            marker_color="#4C72B0",
            opacity=0.8,
        )
        fig_rc.update_layout(
            yaxis_title="Antal cases",
            height=300,
            margin=dict(t=10, b=40),
        )
        st.plotly_chart(fig_rc, use_container_width=True)

    with col_b:
        fig_cpc2 = px.line(
            robot_linked,
            x="maaned",
            y="cost_per_robot_case",
            markers=True,
            labels={
                "maaned": "Måned",
                "cost_per_robot_case": "DKK pr. robotcase",
            },
        )
        fig_cpc2.update_traces(line_color="#C44E52", line_width=2.5)
        fig_cpc2.update_layout(height=300, margin=dict(t=10, b=40))
        st.plotly_chart(fig_cpc2, use_container_width=True)

# ── Summary table ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Nøgletal pr. operationstype")
st.dataframe(
    cpc.rename(
        columns={
            "operationstype": "Operationstype",
            "omkostning_dkk": "Samlet omkostning (DKK)",
            "total_antal": "Samlet antal cases",
            "cost_per_case": "Cost per case (DKK)",
        }
    )
    .style.format(
        {
            "Samlet omkostning (DKK)": "{:,.0f}",
            "Samlet antal cases": "{:,.0f}",
            "Cost per case (DKK)": "{:,.0f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
