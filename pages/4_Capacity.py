"""Kapacitetsudnyttelse – heatmap, OR-timer og trendanalyse."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px

from src.data_loader import load_all
from src.filters import render_sidebar, apply_filters
from src.charts import capacity_heatmap, capacity_bar_available_vs_used

st.set_page_config(page_title="Kapacitetsudnyttelse", page_icon="📅", layout="wide")

_, _, _, capacity_df = load_all()
valgte_afd, periode = render_sidebar()

capacity_f = apply_filters(capacity_df, periode)

# ── header ─────────────────────────────────────────────────────────────────────
st.title("📅 Kapacitetsudnyttelse")
st.caption(f"Periode: {periode[0]} – {periode[1]}")

# ── KPI row ────────────────────────────────────────────────────────────────────
avg_util = capacity_f["udnyttelse_pct"].mean()
robot_util = capacity_f[capacity_f["type"] == "Robot"]["udnyttelse_pct"].mean()
or_util = capacity_f[capacity_f["type"] == "OR"]["udnyttelse_pct"].mean()
max_util = capacity_f["udnyttelse_pct"].max()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Gns. udnyttelse (alle enheder)", f"{avg_util:.1f}%")
k2.metric(
    "Gns. udnyttelse – Robotenheder",
    f"{robot_util:.1f}%",
    delta=f"{robot_util - 80:+.1f}% ift. 80%-mål",
    delta_color="normal" if robot_util >= 80 else "inverse",
)
k3.metric(
    "Gns. udnyttelse – OR-stuer",
    f"{or_util:.1f}%",
    delta=f"{or_util - 80:+.1f}% ift. 80%-mål",
    delta_color="normal" if or_util >= 80 else "inverse",
)
k4.metric(
    "Højeste enkelt-måned",
    f"{max_util:.1f}%",
    delta="Kritisk" if max_util > 100 else ("Høj" if max_util > 95 else "OK"),
    delta_color="inverse" if max_util > 95 else "normal",
)

st.divider()

# ── Heatmap + status ───────────────────────────────────────────────────────────
col_heat, col_status = st.columns([3, 1])

with col_heat:
    st.subheader("Udnyttelse % pr. enhed og måned")
    st.plotly_chart(capacity_heatmap(capacity_f), use_container_width=True)

with col_status:
    st.subheader("Status pr. enhed")
    avg_per_unit = capacity_f.groupby("enhed")["udnyttelse_pct"].mean().reset_index()
    for _, row in avg_per_unit.iterrows():
        u = row["udnyttelse_pct"]
        color = "#e74c3c" if u > 95 else ("#f39c12" if u > 85 else "#27ae60")
        tag = "Overbooket" if u > 100 else ("Høj" if u > 90 else ("God" if u > 75 else "Lav"))
        st.markdown(
            f"**{row['enhed']}**  "
            f"<span style='color:{color}; font-weight:bold'>{u:.1f}% – {tag}</span>",
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.caption("🟢 Mål: 80%")
    st.caption("🟡 Advarsel: > 90%")
    st.caption("🔴 Kritisk: > 100% (overtid)")

# ── Available vs used hours ────────────────────────────────────────────────────
st.divider()
st.subheader("Tilgængelige vs. anvendte timer pr. enhed (perioden samlet)")
st.plotly_chart(capacity_bar_available_vs_used(capacity_f), use_container_width=True)

# ── Monthly trend per type ─────────────────────────────────────────────────────
st.divider()
st.subheader("Udnyttelsesgrad over tid – Robot vs. OR")

import plotly.graph_objects as go  # noqa: E402

cap_type = capacity_f.groupby(["maaned", "type"])["udnyttelse_pct"].mean().reset_index()
fig_trend = px.line(
    cap_type,
    x="maaned",
    y="udnyttelse_pct",
    color="type",
    markers=True,
    labels={"maaned": "Måned", "udnyttelse_pct": "Udnyttelse %", "type": "Type"},
    color_discrete_sequence=["#C44E52", "#4C72B0"],
)
fig_trend.add_hline(
    y=80,
    line_dash="dash",
    line_color="#27ae60",
    annotation_text="Mål 80%",
    annotation_position="right",
)
fig_trend.add_hline(
    y=100,
    line_dash="dash",
    line_color="#e74c3c",
    annotation_text="Kapacitetsgrænse",
    annotation_position="right",
)
fig_trend.update_layout(height=360, margin=dict(t=10, b=40))
st.plotly_chart(fig_trend, use_container_width=True)

# ── Table ──────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Detaljedata")
tbl = (
    capacity_f.groupby("enhed")
    .agg(
        gns_udnyttelse=("udnyttelse_pct", "mean"),
        max_udnyttelse=("udnyttelse_pct", "max"),
        sum_tilgaengelig_h=("tilgaengelig_h", "sum"),
        sum_anvendt_h=("anvendt_h", "sum"),
    )
    .reset_index()
    .rename(
        columns={
            "enhed": "Enhed",
            "gns_udnyttelse": "Gns. udnyttelse %",
            "max_udnyttelse": "Maks. udnyttelse %",
            "sum_tilgaengelig_h": "Tilgængelig timer",
            "sum_anvendt_h": "Anvendt timer",
        }
    )
)
st.dataframe(
    tbl.style.format(
        {
            "Gns. udnyttelse %": "{:.1f}%",
            "Maks. udnyttelse %": "{:.1f}%",
            "Tilgængelig timer": "{:,.0f}",
            "Anvendt timer": "{:,.0f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
