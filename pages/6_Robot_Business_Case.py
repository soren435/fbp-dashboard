"""Robot Business Case – ROI, break-even og scenarieanalyse."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px

from src.data_loader import load_all
from src.filters import render_sidebar, apply_filters
from src.business_case import (
    SCENARIOS,
    ROBOT_INVESTMENT_DKK,
    ROBOT_ANNUAL_SERVICE,
    ROBOT_REVENUE_PER_CASE,
    DISCOUNT_RATE,
    robot_capacity_summary,
    monthly_robot_cost_by_category,
    monthly_robot_volume,
    cost_per_robot_case_monthly,
    roi_table,
    cumulative_cashflow,
    robot_recommendation,
)
from src.charts import (
    capacity_heatmap,
    cumulative_cashflow_chart,
    robot_utilisation_gauge,
    CAT_COLORS,
    fmt_dkk,
)

st.set_page_config(page_title="Robot Business Case", page_icon="🤖", layout="wide")

budget_df, actuals_df, operations_df, capacity_df = load_all()
valgte_afd, periode = render_sidebar()

actuals_f = apply_filters(actuals_df, periode)
operations_f = apply_filters(operations_df, periode)
capacity_f = apply_filters(capacity_df, periode)

# ── header ─────────────────────────────────────────────────────────────────────
st.title("🤖 Robot Business Case")
st.caption(
    "Beslutningsstøtte til ledelsen: kapacitetsstatus, cost-per-case udvikling og "
    "ROI-analyse for udvidet robotkirurgikapacitet."
)

# ── capacity KPIs ──────────────────────────────────────────────────────────────
cap_summary = robot_capacity_summary(capacity_f)
avg_robot_util = cap_summary["gns_udnyttelse"].mean()

cpc_monthly = cost_per_robot_case_monthly(actuals_f, operations_f)
avg_cpc = cpc_monthly["cost_per_case"].mean() if not cpc_monthly.empty else 0

robot_vol = monthly_robot_volume(operations_f)
total_robot_cases = robot_vol["robot_cases"].sum()
robot_cost_total = actuals_f[actuals_f["afdeling"] == "Robotenhed"]["faktisk_dkk"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Gns. robotudnyttelse",
    f"{avg_robot_util:.1f}%",
    delta=f"{avg_robot_util - 80:+.1f}% ift. 80%-mål",
    delta_color="normal" if avg_robot_util >= 80 else "inverse",
)
k2.metric("Samlet robotkirurgi-cases", f"{total_robot_cases:,.0f}")
k3.metric("Gns. cost per robotcase", fmt_dkk(avg_cpc))
k4.metric("Samlet Robotenhed-omkostning", fmt_dkk(robot_cost_total))

st.divider()

# ── Gauge + capacity heatmap ───────────────────────────────────────────────────
col_gauge, col_heat = st.columns([1, 2])

with col_gauge:
    st.subheader("Kapacitetsudnyttelse")
    st.plotly_chart(robot_utilisation_gauge(avg_robot_util), use_container_width=True)
    st.markdown(robot_recommendation(capacity_f, cpc_monthly))

with col_heat:
    st.subheader("Udnyttelse pr. robotenhed og måned")
    robot_cap = capacity_f[capacity_f["type"] == "Robot"].copy()
    if not robot_cap.empty:
        st.plotly_chart(capacity_heatmap(robot_cap, height=280), use_container_width=True)

st.divider()

# ── Monthly robot cost breakdown ───────────────────────────────────────────────
col_cost, col_cpc = st.columns(2)

with col_cost:
    st.subheader("Månedlig Robotenhed-omkostning pr. kategori")
    robot_cost_cat = monthly_robot_cost_by_category(actuals_f)
    fig_cost = px.bar(
        robot_cost_cat,
        x="maaned",
        y="faktisk_dkk",
        color="kategori",
        barmode="stack",
        color_discrete_map=CAT_COLORS,
        labels={
            "maaned": "Måned",
            "faktisk_dkk": "Faktisk (DKK)",
            "kategori": "Kategori",
        },
    )
    fig_cost.update_layout(height=320, margin=dict(t=10, b=40))
    st.plotly_chart(fig_cost, use_container_width=True)

with col_cpc:
    st.subheader("Cost per robotkirurgi-case – månedlig trend")
    if not cpc_monthly.empty:
        import plotly.graph_objects as go  # noqa: E402

        fig_cpc = go.Figure()
        fig_cpc.add_scatter(
            x=cpc_monthly["maaned"],
            y=cpc_monthly["cost_per_case"],
            mode="lines+markers",
            line=dict(color="#C44E52", width=2.5),
            marker=dict(size=6),
            name="Cost per case",
        )
        avg_line = cpc_monthly["cost_per_case"].mean()
        fig_cpc.add_hline(
            y=avg_line,
            line_dash="dash",
            line_color="#888",
            annotation_text=f"Gns. {fmt_dkk(avg_line)}",
            annotation_position="right",
        )
        fig_cpc.update_layout(
            yaxis_title="DKK pr. case",
            height=320,
            margin=dict(t=10, b=40),
        )
        st.plotly_chart(fig_cpc, use_container_width=True)

st.divider()

# ── Business case assumptions ──────────────────────────────────────────────────
st.subheader("Business case – antagelser og parametre")

with st.expander("Juster antagelser (avanceret)", expanded=False):
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        inv_input = st.number_input(
            "Investering ny robot (DKK)",
            min_value=0,
            max_value=30_000_000,
            value=int(ROBOT_INVESTMENT_DKK),
            step=500_000,
        )
        service_input = st.number_input(
            "Årlig service (DKK)",
            min_value=0,
            max_value=5_000_000,
            value=int(ROBOT_ANNUAL_SERVICE),
            step=100_000,
        )
    with col_a2:
        rev_per_case = st.number_input(
            "DRG-omsætning pr. case (DKK)",
            min_value=10_000,
            max_value=100_000,
            value=int(ROBOT_REVENUE_PER_CASE),
            step=5_000,
        )
        extra_staff_cost = st.number_input(
            "Ekstra personaleomkostning/år – ny robot (DKK)",
            min_value=0,
            max_value=10_000_000,
            value=2_000_000,
            step=200_000,
        )
    with col_a3:
        discount = st.slider("Diskonteringsrente %", 2, 8, int(DISCOUNT_RATE * 100))
        horizon = st.slider("Beregningshorisont (år)", 3, 10, 5)

st.markdown(
    f"""
**Faste antagelser:**
- Investering ny Da Vinci-robot: DKK {inv_input:,.0f} (inkl. installation)
- Årslig servicekontrakt: DKK {service_input:,.0f}
- DRG-baseret omsætning pr. case: DKK {rev_per_case:,.0f}
- Diskonteringsrente (offentlig sektor): {discount}%
- *Variabel cost per case beregnes fra faktiske data: {fmt_dkk(avg_cpc)}*
"""
)

# Update scenarios with user input
from src.business_case import Scenario  # noqa: E402
import copy  # noqa: E402

custom_scenarios = copy.deepcopy(SCENARIOS)
for sc in custom_scenarios:
    if sc.name == "new_robot":
        sc.investment_dkk = inv_input
        sc.annual_fixed_cost_delta = service_input + extra_staff_cost

# ── ROI table ──────────────────────────────────────────────────────────────────
st.subheader("ROI-analyse pr. scenarie")

roi_df = roi_table(avg_cpc, scenarios=custom_scenarios, horizon_years=horizon)


def _color_npv(val: object) -> str:
    if isinstance(val, (int, float)):
        return "color: #27ae60; font-weight: bold" if val > 0 else "color: #e74c3c"
    return ""


styled_roi = roi_df.style.applymap(
    _color_npv, subset=[f"NPV {horizon} år (DKK)"]
).format(
    {
        "Investering (DKK)": "{:,.0f}",
        "Ekstra sessioner/år": "{:,.0f}",
        "Ekstra omsætning/år (DKK)": "{:,.0f}",
        "Nettoresultat/år (DKK)": "{:,.0f}",
        f"NPV {horizon} år (DKK)": "{:,.0f}",
    }
)
st.dataframe(styled_roi, use_container_width=True, hide_index=True)

# ── Cashflow chart ─────────────────────────────────────────────────────────────
st.subheader(f"Kumulativ nettogevinst over {horizon} år")
cf_df = cumulative_cashflow(avg_cpc, scenarios=custom_scenarios, horizon_years=horizon)
st.plotly_chart(cumulative_cashflow_chart(cf_df, height=380), use_container_width=True)

# ── Scenario descriptions ──────────────────────────────────────────────────────
st.divider()
st.subheader("Scenariebeskrivelser")
for sc in custom_scenarios:
    icon = "⚪" if sc.name == "status_quo" else ("🔵" if sc.name == "extra_sessions" else "🔴")
    st.markdown(f"{icon} **{sc.label}:** {sc.description}")

# ── Final recommendation ───────────────────────────────────────────────────────
st.divider()
st.subheader("Samlet ledelsesanbefaling")
st.markdown(robot_recommendation(capacity_f, cpc_monthly))

best_npv_row = roi_df.loc[roi_df[f"NPV {horizon} år (DKK)"].idxmax()]
if best_npv_row["Scenarie"] != "Status quo":
    st.success(
        f"Scenariet **'{best_npv_row['Scenarie']}'** giver den bedste NPV over {horizon} år: "
        f"DKK {best_npv_row[f'NPV {horizon} år (DKK)']:,.0f}"
    )

st.caption(
    "Alle beløb er baseret på syntetiske data. DRG-omsætning og investeringsomkostninger "
    "er estimater og bør verificeres med aktuelle takster og leverandørtilbud."
)
