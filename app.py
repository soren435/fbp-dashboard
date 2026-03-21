"""
FBP Dashboard – Finance Business Partner
Hospitalskirurgi / Robotkirurgi-enhed

Run:  streamlit run app.py
"""

import os
import sys
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FBP Dashboard – Kirurgi",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── ensure data exists ────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REQUIRED = ["budget.csv", "actuals.csv", "operations.csv", "capacity.csv"]

if not all(os.path.exists(os.path.join(DATA_DIR, f)) for f in REQUIRED):
    sys.path.insert(0, DATA_DIR)
    import generate_data
    generate_data.generate_all(DATA_DIR)


# ── load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    budget     = pd.read_csv(os.path.join(DATA_DIR, "budget.csv"))
    actuals    = pd.read_csv(os.path.join(DATA_DIR, "actuals.csv"))
    operations = pd.read_csv(os.path.join(DATA_DIR, "operations.csv"))
    capacity   = pd.read_csv(os.path.join(DATA_DIR, "capacity.csv"))

    for df in (budget, actuals, operations, capacity):
        df["maaned"] = pd.to_datetime(df["maaned"])

    return budget, actuals, operations, capacity


budget_df, actuals_df, operations_df, capacity_df = load_data()


# ── colour helpers ────────────────────────────────────────────────────────────
DEPT_COLORS = {
    "Kirurgi":       "#4C72B0",
    "Anæstesi":      "#DD8452",
    "Sterilcentral": "#55A868",
    "Robotenhed":    "#C44E52",
}

CAT_COLORS = {
    "Personale": "#4C72B0",
    "Udstyr":    "#DD8452",
    "Forbrug":   "#55A868",
    "Overhead":  "#8172B2",
}

OP_COLORS = {
    "Robotkirurgi":        "#C44E52",
    "Laparoskopi":         "#4C72B0",
    "Åben kirurgi":        "#DD8452",
    "Ambulant opfølgning": "#55A868",
}


def fmt_dkk(val: float) -> str:
    """Format number as DKK with thousand separators."""
    return f"DKK {val:,.0f}".replace(",", ".")


def variance_color(pct: float) -> str:
    if pct > 2:
        return "#e74c3c"   # red = over budget
    if pct < -2:
        return "#27ae60"   # green = under budget
    return "#95a5a6"       # grey = within tolerance


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/OOjs_UI_icon_heart.svg/"
        "120px-OOjs_UI_icon_heart.svg.png",
        width=48,
    )
    st.title("FBP Dashboard")
    st.caption("Hospitalskirurgi · Robotenhed")
    st.divider()

    # Department filter
    alle_afd = sorted(budget_df["afdeling"].unique())
    valgte_afd = st.multiselect(
        "Afdelinger",
        options=alle_afd,
        default=alle_afd,
    )

    # Period filter
    alle_maaneder = sorted(actuals_df["maaned"].dt.strftime("%Y-%m").unique())
    min_m, max_m = alle_maaneder[0], alle_maaneder[-1]
    periode = st.select_slider(
        "Periode",
        options=alle_maaneder,
        value=(min_m, max_m),
    )

    st.divider()
    st.caption("Data: Jan 2025 – Mar 2026")
    st.caption("© FBP Hospitalskirurgi")


# ── filter helpers ────────────────────────────────────────────────────────────
def filter_df(df: pd.DataFrame, dept_col="afdeling") -> pd.DataFrame:
    mstart = pd.to_datetime(periode[0])
    mend   = pd.to_datetime(periode[1])
    mask = (df["maaned"] >= mstart) & (df["maaned"] <= mend)
    if dept_col in df.columns:
        mask &= df[dept_col].isin(valgte_afd)
    return df[mask].copy()


budget_f    = filter_df(budget_df)
actuals_f   = filter_df(actuals_df)
operations_f = filter_df(operations_df, dept_col="operationstype")   # no dept col
capacity_f  = filter_df(capacity_df, dept_col="enhed")               # no dept col

# For operations we just time-filter
op_mask = (
    (operations_df["maaned"] >= pd.to_datetime(periode[0])) &
    (operations_df["maaned"] <= pd.to_datetime(periode[1]))
)
operations_f = operations_df[op_mask].copy()

cap_mask = (
    (capacity_df["maaned"] >= pd.to_datetime(periode[0])) &
    (capacity_df["maaned"] <= pd.to_datetime(periode[1]))
)
capacity_f = capacity_df[cap_mask].copy()


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_names = [
    "🏠 Overblik",
    "📊 Budget vs. Faktisk",
    "⚙️ Aktivitetsbaseret Kostpris",
    "📅 Kapacitetsudnyttelse",
    "📈 Forecast",
    "🤖 AI Afvigelsesforklaring",
]
tabs = st.tabs(tab_names)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – OVERBLIK
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.header("Overblik")

    total_budget  = budget_f["budget_dkk"].sum()
    total_actuals = actuals_f["faktisk_dkk"].sum()
    spent_pct     = total_actuals / total_budget * 100 if total_budget else 0

    # Forecast accuracy: mean abs pct error on months where both exist
    merged_kpi = (
        budget_f.groupby("maaned")["budget_dkk"].sum()
        .reset_index()
        .merge(
            actuals_f.groupby("maaned")["faktisk_dkk"].sum().reset_index(),
            on="maaned",
        )
    )
    if len(merged_kpi):
        mape = (
            (merged_kpi["faktisk_dkk"] - merged_kpi["budget_dkk"]).abs()
            / merged_kpi["budget_dkk"]
        ).mean() * 100
        forecast_acc = max(0, 100 - mape)
    else:
        forecast_acc = 0

    cap_util = capacity_f["udnyttelse_pct"].mean()

    # Variance trend (month-over-month)
    monthly_var = merged_kpi.copy()
    monthly_var["var_pct"] = (
        (monthly_var["faktisk_dkk"] - monthly_var["budget_dkk"])
        / monthly_var["budget_dkk"] * 100
    )

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        delta_color = "inverse" if spent_pct > 100 else "normal"
        st.metric(
            "Budget forbrugt",
            f"{spent_pct:.1f}%",
            delta=f"{spent_pct - 100:.1f}% ift. plan" if spent_pct != 100 else "Præcis på plan",
            delta_color=delta_color,
        )

    with c2:
        st.metric(
            "Samlet forbrug",
            fmt_dkk(total_actuals),
            delta=fmt_dkk(total_actuals - total_budget),
            delta_color="inverse",
        )

    with c3:
        st.metric(
            "Forecast-nøjagtighed",
            f"{forecast_acc:.1f}%",
            delta=f"MAPE {mape:.1f}%",
            delta_color="inverse" if mape > 5 else "normal",
        )

    with c4:
        util_delta = cap_util - 80
        st.metric(
            "Kapacitetsudnyttelse",
            f"{cap_util:.1f}%",
            delta=f"{util_delta:+.1f}% ift. 80%-mål",
            delta_color="normal" if util_delta >= 0 else "inverse",
        )

    st.divider()

    # Mini overview charts side by side
    left, right = st.columns(2)

    with left:
        st.subheader("Budget vs. Faktisk – månedlig")
        fig_mini = go.Figure()
        fig_mini.add_bar(
            x=merged_kpi["maaned"].dt.strftime("%b %Y"),
            y=merged_kpi["budget_dkk"] / 1e6,
            name="Budget",
            marker_color="#4C72B0",
            opacity=0.6,
        )
        fig_mini.add_scatter(
            x=merged_kpi["maaned"].dt.strftime("%b %Y"),
            y=merged_kpi["faktisk_dkk"] / 1e6,
            name="Faktisk",
            mode="lines+markers",
            line=dict(color="#C44E52", width=2),
        )
        fig_mini.update_layout(
            yaxis_title="Mio. DKK",
            legend=dict(orientation="h", y=1.1),
            height=320,
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_mini, use_container_width=True)

    with right:
        st.subheader("Afvigelse % pr. måned")
        colors = [variance_color(v) for v in monthly_var["var_pct"]]
        fig_var = go.Figure(go.Bar(
            x=monthly_var["maaned"].dt.strftime("%b %Y"),
            y=monthly_var["var_pct"],
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in monthly_var["var_pct"]],
            textposition="outside",
        ))
        fig_var.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
        fig_var.update_layout(
            yaxis_title="Afvigelse %",
            height=320,
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig_var, use_container_width=True)

    # Department breakdown
    st.subheader("Samlet forbrug pr. afdeling")
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
    fig_dept.update_layout(showlegend=False, height=300, margin=dict(t=20, b=40))
    st.plotly_chart(fig_dept, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – BUDGET VS. FAKTISK
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.header("Budget vs. Faktisk")

    view = st.radio(
        "Vis pr.",
        ["Måned (samlet)", "Afdeling", "Kategori"],
        horizontal=True,
    )

    if view == "Måned (samlet)":
        grp_b = budget_f.groupby("maaned")["budget_dkk"].sum().reset_index()
        grp_a = actuals_f.groupby("maaned")["faktisk_dkk"].sum().reset_index()
        merged = grp_b.merge(grp_a, on="maaned")
        merged["afvigelse_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
        merged["afvigelse_pct"] = merged["afvigelse_dkk"] / merged["budget_dkk"] * 100
        x_col, x_label = "maaned", "Måned"
        merged["x"] = merged["maaned"].dt.strftime("%b %Y")

    elif view == "Afdeling":
        grp_b = budget_f.groupby("afdeling")["budget_dkk"].sum().reset_index()
        grp_a = actuals_f.groupby("afdeling")["faktisk_dkk"].sum().reset_index()
        merged = grp_b.merge(grp_a, on="afdeling")
        merged["afvigelse_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
        merged["afvigelse_pct"] = merged["afvigelse_dkk"] / merged["budget_dkk"] * 100
        merged["x"] = merged["afdeling"]

    else:  # Kategori
        grp_b = budget_f.groupby("kategori")["budget_dkk"].sum().reset_index()
        grp_a = actuals_f.groupby("kategori")["faktisk_dkk"].sum().reset_index()
        merged = grp_b.merge(grp_a, on="kategori")
        merged["afvigelse_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
        merged["afvigelse_pct"] = merged["afvigelse_dkk"] / merged["budget_dkk"] * 100
        merged["x"] = merged["kategori"]

    # Chart
    fig_bva = go.Figure()
    fig_bva.add_bar(
        x=merged["x"],
        y=merged["budget_dkk"] / 1e6,
        name="Budget",
        marker_color="#4C72B0",
        opacity=0.75,
    )
    fig_bva.add_bar(
        x=merged["x"],
        y=merged["faktisk_dkk"] / 1e6,
        name="Faktisk",
        marker_color="#C44E52",
        opacity=0.85,
    )
    fig_bva.update_layout(
        barmode="group",
        yaxis_title="Mio. DKK",
        legend=dict(orientation="h", y=1.05),
        height=400,
        margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig_bva, use_container_width=True)

    # Variance table
    st.subheader("Afvigelsestabel")
    tbl = merged[["x", "budget_dkk", "faktisk_dkk", "afvigelse_dkk", "afvigelse_pct"]].copy()
    tbl.columns = ["", "Budget (DKK)", "Faktisk (DKK)", "Afvigelse (DKK)", "Afvigelse %"]

    def color_row(row):
        pct = row["Afvigelse %"]
        bg = "#fde8e8" if pct > 2 else ("#e8f8e8" if pct < -2 else "")
        return [f"background-color: {bg}"] * len(row)

    styled = (
        tbl.style
        .apply(color_row, axis=1)
        .format({
            "Budget (DKK)":    "{:,.0f}",
            "Faktisk (DKK)":   "{:,.0f}",
            "Afvigelse (DKK)": "{:+,.0f}",
            "Afvigelse %":     "{:+.1f}%",
        })
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Drill-down: stacked by category per department
    st.divider()
    st.subheader("Faktisk forbrug pr. afdeling og kategori")
    pivot = (
        actuals_f.groupby(["afdeling", "kategori"])["faktisk_dkk"]
        .sum()
        .reset_index()
    )
    fig_stack = px.bar(
        pivot,
        x="afdeling",
        y="faktisk_dkk",
        color="kategori",
        barmode="stack",
        color_discrete_map=CAT_COLORS,
        labels={"afdeling": "Afdeling", "faktisk_dkk": "Faktisk (DKK)", "kategori": "Kategori"},
        text_auto=".3s",
    )
    fig_stack.update_layout(height=380, margin=dict(t=10, b=40))
    st.plotly_chart(fig_stack, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – AKTIVITETSBASERET KOSTPRIS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.header("Aktivitetsbaseret Kostpris (ABC)")

    # Total cost per operation type
    op_total = (
        operations_f.groupby("operationstype")["omkostning_dkk"]
        .sum()
        .reset_index()
        .sort_values("omkostning_dkk", ascending=False)
    )
    op_vol = (
        operations_f.groupby("operationstype")["antal"]
        .mean()
        .reset_index()
        .rename(columns={"antal": "gns_antal_pr_mdr"})
    )
    op_total = op_total.merge(op_vol, on="operationstype")
    op_total["enhedspris_dkk"] = (
        operations_f.groupby("operationstype").apply(
            lambda g: g["omkostning_dkk"].sum() / g["antal"].mean()
        )
        .reset_index(drop=True)
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Samlet omkostning pr. operationstype")
        fig_op = px.bar(
            op_total,
            x="operationstype",
            y="omkostning_dkk",
            color="operationstype",
            color_discrete_map=OP_COLORS,
            labels={
                "operationstype": "Operationstype",
                "omkostning_dkk": "Samlet omkostning (DKK)",
            },
            text_auto=".3s",
        )
        fig_op.update_layout(showlegend=False, height=380, margin=dict(t=10, b=40))
        st.plotly_chart(fig_op, use_container_width=True)

    with col2:
        st.subheader("Enhedspris pr. operation (DKK)")
        # Compute properly: total cost / total operations
        ep = (
            operations_f.groupby("operationstype")
            .apply(lambda g: g["omkostning_dkk"].sum() / g["antal"].iloc[0])
            .reset_index()
            .rename(columns={0: "enhedspris"})
        )
        fig_ep = px.bar(
            ep,
            x="operationstype",
            y="enhedspris",
            color="operationstype",
            color_discrete_map=OP_COLORS,
            labels={
                "operationstype": "Operationstype",
                "enhedspris":     "DKK pr. operation",
            },
            text_auto=".0f",
        )
        fig_ep.update_layout(showlegend=False, height=380, margin=dict(t=10, b=40))
        st.plotly_chart(fig_ep, use_container_width=True)

    # Cost breakdown by resource
    st.subheader("Omkostningsfordeling pr. ressourcetype")
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
        labels={
            "operationstype": "Operationstype",
            "omkostning_dkk": "Omkostning (DKK)",
            "ressource":      "Ressource",
        },
        text_auto=".3s",
    )
    fig_res.update_layout(height=400, margin=dict(t=10, b=40))
    st.plotly_chart(fig_res, use_container_width=True)

    # Trend: cost per operation type over time
    st.subheader("Månedlig omkostningsudvikling pr. operationstype")
    op_trend = (
        operations_f.groupby(["maaned", "operationstype"])["omkostning_dkk"]
        .sum()
        .reset_index()
    )
    fig_trend = px.line(
        op_trend,
        x="maaned",
        y="omkostning_dkk",
        color="operationstype",
        color_discrete_map=OP_COLORS,
        markers=True,
        labels={
            "maaned":         "Måned",
            "omkostning_dkk": "Omkostning (DKK)",
            "operationstype": "Operationstype",
        },
    )
    fig_trend.update_layout(height=380, margin=dict(t=10, b=40))
    st.plotly_chart(fig_trend, use_container_width=True)

    # Summary table
    st.subheader("Nøgletal pr. operationstype")
    summary = (
        operations_f.groupby("operationstype")
        .agg(
            total_dkk=("omkostning_dkk", "sum"),
            gns_maaned_vol=("antal", "mean"),
        )
        .reset_index()
    )
    summary["enhedspris"] = summary["total_dkk"] / (summary["gns_maaned_vol"] * len(operations_f["maaned"].unique()))
    summary.columns = ["Operationstype", "Samlet DKK", "Gns. operationer/mdr.", "Enhedspris DKK"]
    st.dataframe(
        summary.style.format({
            "Samlet DKK":           "{:,.0f}",
            "Gns. operationer/mdr.": "{:.1f}",
            "Enhedspris DKK":        "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – KAPACITETSUDNYTTELSE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.header("Kapacitetsudnyttelse")

    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("Heatmap – udnyttelse % pr. enhed og måned")
        pivot_cap = capacity_f.pivot_table(
            index="enhed",
            columns=capacity_f["maaned"].dt.strftime("%Y-%m"),
            values="udnyttelse_pct",
            aggfunc="mean",
        )

        fig_heat = go.Figure(go.Heatmap(
            z=pivot_cap.values,
            x=pivot_cap.columns.tolist(),
            y=pivot_cap.index.tolist(),
            colorscale=[
                [0.00, "#2ecc71"],   # green  – low
                [0.75, "#f39c12"],   # orange – approaching full
                [0.90, "#e74c3c"],   # red    – overbooked
                [1.00, "#8e1a0e"],
            ],
            zmin=50,
            zmax=105,
            text=pivot_cap.values.round(1),
            texttemplate="%{text}%",
            hovertemplate="Enhed: %{y}<br>Måned: %{x}<br>Udnyttelse: %{z:.1f}%<extra></extra>",
        ))
        fig_heat.add_hline(
            y=1.5,   # separator between robots and OR rooms
            line_dash="dot",
            line_color="white",
            line_width=2,
        )
        fig_heat.update_layout(
            height=380,
            margin=dict(t=10, b=60),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with c2:
        st.subheader("Status overblik")
        avg_cap = capacity_f.groupby("enhed")["udnyttelse_pct"].mean().reset_index()
        for _, row in avg_cap.iterrows():
            u = row["udnyttelse_pct"]
            color = "#e74c3c" if u > 95 else ("#f39c12" if u > 85 else "#27ae60")
            tag = "Overbooket" if u > 100 else ("Høj" if u > 90 else ("God" if u > 75 else "Lav"))
            st.markdown(
                f"**{row['enhed']}**  "
                f"<span style='color:{color}; font-weight:bold'>{u:.1f}% – {tag}</span>",
                unsafe_allow_html=True,
            )
        st.markdown("---")
        st.caption("Mål: 80% udnyttelse")
        st.caption("Advarsel: >95%")
        st.caption("Kritisk: >100% (overtid)")

    # Bar chart: available vs. used per unit (summed over period)
    st.subheader("Tilgængelige vs. anvendte timer pr. enhed")
    cap_sum = capacity_f.groupby("enhed")[["tilgaengelig_h", "anvendt_h"]].sum().reset_index()
    fig_cap = go.Figure()
    fig_cap.add_bar(
        x=cap_sum["enhed"],
        y=cap_sum["tilgaengelig_h"],
        name="Tilgængelig",
        marker_color="#4C72B0",
        opacity=0.6,
    )
    fig_cap.add_bar(
        x=cap_sum["enhed"],
        y=cap_sum["anvendt_h"],
        name="Anvendt",
        marker_color="#C44E52",
        opacity=0.85,
    )
    fig_cap.update_layout(
        barmode="overlay",
        yaxis_title="Timer",
        legend=dict(orientation="h", y=1.05),
        height=340,
        margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig_cap, use_container_width=True)

    # Monthly trend per unit type
    st.subheader("Udnyttelse over tid pr. enhedstype")
    cap_type = capacity_f.groupby(["maaned", "type"])["udnyttelse_pct"].mean().reset_index()
    fig_cap_trend = px.line(
        cap_type,
        x="maaned",
        y="udnyttelse_pct",
        color="type",
        markers=True,
        labels={"maaned": "Måned", "udnyttelse_pct": "Udnyttelse %", "type": "Type"},
        color_discrete_sequence=["#4C72B0", "#C44E52"],
    )
    fig_cap_trend.add_hline(y=80, line_dash="dash", line_color="green",
                             annotation_text="Mål 80%", annotation_position="right")
    fig_cap_trend.add_hline(y=100, line_dash="dash", line_color="red",
                              annotation_text="Kapacitetsgrænse", annotation_position="right")
    fig_cap_trend.update_layout(height=340, margin=dict(t=10, b=40))
    st.plotly_chart(fig_cap_trend, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – FORECAST
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.header("Forecast – Rullende 12-måneder")

    # Build combined monthly series (actuals where available, budget otherwise)
    act_monthly = actuals_df.groupby("maaned")["faktisk_dkk"].sum().reset_index()
    bud_monthly = budget_df.groupby("maaned")["budget_dkk"].sum().reset_index()

    # Forecast: use last 6 actuals to fit linear trend, project 9 months forward
    act_sorted = act_monthly.sort_values("maaned")

    n_fit = min(9, len(act_sorted))
    fit_slice = act_sorted.tail(n_fit).copy()
    fit_slice["t"] = np.arange(n_fit)
    coeffs = np.polyfit(fit_slice["t"], fit_slice["faktisk_dkk"], 1)

    last_date = act_sorted["maaned"].max()
    forecast_months = pd.date_range(
        last_date + pd.DateOffset(months=1), periods=9, freq="MS"
    )
    t_forecast = np.arange(n_fit, n_fit + 9)
    forecast_vals = np.polyval(coeffs, t_forecast)

    fc_df = pd.DataFrame({
        "maaned":       forecast_months,
        "forecast_dkk": forecast_vals,
    })

    # Confidence band (±5 % of trend value as a simple proxy)
    fc_df["upper"] = fc_df["forecast_dkk"] * 1.06
    fc_df["lower"] = fc_df["forecast_dkk"] * 0.94

    fig_fc = go.Figure()

    # Budget line
    fig_fc.add_scatter(
        x=bud_monthly["maaned"],
        y=bud_monthly["budget_dkk"] / 1e6,
        name="Budget",
        mode="lines",
        line=dict(color="#4C72B0", dash="dot", width=2),
    )

    # Actuals
    fig_fc.add_scatter(
        x=act_sorted["maaned"],
        y=act_sorted["faktisk_dkk"] / 1e6,
        name="Faktisk",
        mode="lines+markers",
        line=dict(color="#27ae60", width=2.5),
        marker=dict(size=6),
    )

    # Confidence band (shaded)
    fig_fc.add_scatter(
        x=pd.concat([fc_df["maaned"], fc_df["maaned"][::-1]]),
        y=pd.concat([fc_df["upper"] / 1e6, fc_df["lower"][::-1] / 1e6]),
        fill="toself",
        fillcolor="rgba(221,132,82,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Konfidensinterval ±6%",
        hoverinfo="skip",
    )

    # Forecast line
    fig_fc.add_scatter(
        x=fc_df["maaned"],
        y=fc_df["forecast_dkk"] / 1e6,
        name="Forecast (lineær trend)",
        mode="lines+markers",
        line=dict(color="#DD8452", width=2.5, dash="dash"),
        marker=dict(size=6, symbol="diamond"),
    )

    # Vertical line at forecast start
    fig_fc.add_vline(
        x=last_date.timestamp() * 1000,
        line_dash="dot",
        line_color="grey",
        annotation_text="Forecast start",
        annotation_position="top right",
    )

    fig_fc.update_layout(
        yaxis_title="Mio. DKK",
        xaxis_title="Måned",
        legend=dict(orientation="h", y=1.08),
        height=460,
        margin=dict(t=20, b=40),
    )
    st.plotly_chart(fig_fc, use_container_width=True)

    # KPI row
    fc_total_12 = fc_df["forecast_dkk"].sum()
    bud_remaining = bud_monthly[bud_monthly["maaned"] > last_date]["budget_dkk"].sum()
    trend_slope_m = coeffs[0]

    k1, k2, k3 = st.columns(3)
    k1.metric("Forecast: næste 9 mdr.", fmt_dkk(fc_total_12))
    k2.metric("Resterende budget 2025", fmt_dkk(bud_remaining))
    k3.metric(
        "Trend (DKK/mdr.)",
        fmt_dkk(abs(trend_slope_m)),
        delta="Stigende" if trend_slope_m > 0 else "Faldende",
        delta_color="inverse" if trend_slope_m > 0 else "normal",
    )

    st.info(
        "Forecast beregnes med lineær regression på de seneste 9 måneders faktiske data. "
        "Konfidensintervallet er ±6 % af trendværdien."
    )

    # Table
    st.subheader("Forecast-detaljer")
    fc_disp = fc_df[["maaned", "forecast_dkk", "lower", "upper"]].copy()
    fc_disp["maaned"] = fc_disp["maaned"].dt.strftime("%b %Y")
    fc_disp.columns = ["Måned", "Forecast DKK", "Nedre grænse", "Øvre grænse"]
    st.dataframe(
        fc_disp.style.format({
            "Forecast DKK": "{:,.0f}",
            "Nedre grænse": "{:,.0f}",
            "Øvre grænse":  "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 – AI AFVIGELSESFORKLARING
# ══════════════════════════════════════════════════════════════════════════════

def generate_variance_explanation(df_budget: pd.DataFrame, df_actuals: pd.DataFrame) -> str:
    """
    Finds the top-3 variances by absolute DKK and returns a formatted
    Danish plain-text explanation string.  No external LLM call.
    """
    # Merge on month + department + category
    merged = df_budget.merge(
        df_actuals,
        on=["maaned", "afdeling", "kategori"],
        how="inner",
    )
    merged["var_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
    merged["var_pct"] = merged["var_dkk"] / merged["budget_dkk"] * 100

    # Aggregate to dept × category level
    agg = (
        merged.groupby(["afdeling", "kategori"])
        .agg(
            var_dkk=("var_dkk", "sum"),
            budget_dkk=("budget_dkk", "sum"),
            faktisk_dkk=("faktisk_dkk", "sum"),
        )
        .reset_index()
    )
    agg["var_pct"] = agg["var_dkk"] / agg["budget_dkk"] * 100
    agg["abs_var"] = agg["var_dkk"].abs()
    top3 = agg.nlargest(3, "abs_var")

    lines = ["### Automatisk Afvigelsesanalyse\n"]
    lines.append(
        f"Analysen dækker perioden **{df_actuals['maaned'].min().strftime('%b %Y')}** "
        f"– **{df_actuals['maaned'].max().strftime('%b %Y')}** "
        f"for de valgte afdelinger.\n"
    )

    # Context helpers
    robot_extra_sessions = 8   # known from data generation
    q3_months = "juli–september"

    explanations = {
        ("Robotenhed", "Udstyr"): (
            "Uplanlagt vedligeholdelse af robotsystem (Da Vinci) i {q3} medførte "
            "ekstraomkostninger til reservedele og servicekontrakt."
        ),
        ("Robotenhed", "Personale"): (
            "{extra} ekstra robotkirurgi-sessioner i {q3} som følge af "
            "venteliste-reducering krævede overarbejde og ekstra vagtdækning."
        ),
        ("Robotenhed", "Forbrug"): (
            "Øget forbrugsmateriell (sterile kapper, instrumenter) relateret til "
            "{extra} ekstra robotkirurgi-sessioner i {q3}."
        ),
        ("Kirurgi", "Personale"): (
            "Højere case-mix i efteråret med tunge elektive indgreb øgede "
            "behovet for specialiseret personale og forlængede operationstider."
        ),
        ("Kirurgi", "Udstyr"): (
            "Indkøb af nyt laparoskopisk udstyr fremrykket til Q3 for at imødekomme "
            "kapacitetsbehov."
        ),
        ("Anæstesi", "Personale"): (
            "Sommerferieafvikling i august reducerede forbruget markant — "
            "planlagt underforbrug."
        ),
        ("Sterilcentral", "Personale"): (
            "Effektiviseringer i sterilisationsflow og færre akutte rengøringsbehov "
            "bidrog til mindreforbrug."
        ),
    }

    default_over  = "Højere aktivitetsniveau end planlagt medførte overskridelse af budgettet."
    default_under = "Lavere aktivitet end forventet, evt. pga. planlagte effektiviseringer."

    for rank, (_, row) in enumerate(top3.iterrows(), start=1):
        dept = row["afdeling"]
        cat  = row["kategori"]
        var  = row["var_dkk"]
        pct  = row["var_pct"]
        direction = "overskrider" if var > 0 else "er under"
        icon = "⚠️" if var > 0 else "✅"
        sign = "+" if var > 0 else ""

        template = explanations.get((dept, cat))
        if template:
            reason = template.format(q3=q3_months, extra=robot_extra_sessions)
        elif var > 0:
            reason = default_over
        else:
            reason = default_under

        lines.append(
            f"{icon} **{rank}. {dept} – {cat}**\n"
            f"   Afvigelse: **{sign}DKK {abs(var):,.0f}** ({pct:+.1f}%)\n"
            f"   {reason}\n"
        )

    # Overall summary
    total_var = agg["var_dkk"].sum()
    total_bud = agg["budget_dkk"].sum()
    total_pct = total_var / total_bud * 100
    overall_icon = "🔴" if total_pct > 3 else ("🟡" if total_pct > 0 else "🟢")

    lines.append("---")
    lines.append(
        f"{overall_icon} **Samlet afvigelse:** "
        f"DKK {total_var:+,.0f} ({total_pct:+.1f}% ift. budget)\n"
    )

    if total_pct > 5:
        lines.append(
            "**Anbefaling:** Igangsæt korrigerende tiltag i Robotenhed. "
            "Overvej om de ekstra sessioner kan finansieres via aktivitetsindtægter "
            "eller kræver budgetrevision."
        )
    elif total_pct > 0:
        lines.append(
            "**Anbefaling:** Monitorer Robotenhed tæt i kommende kvartal. "
            "Generelt under kontrol."
        )
    else:
        lines.append(
            "**Anbefaling:** Positiv budgetstatus. "
            "Gennemgå om mindreforbruget er permanent og juster forecast."
        )

    return "\n".join(lines)


with tabs[5]:
    st.header("AI Afvigelsesforklaring")
    st.caption(
        "Automatisk genereret analyse baseret på de valgte filtre. "
        "Ingen ekstern AI-service – analysen beregnes direkte fra dataene."
    )

    st.info(
        "Klik på knappen nedenfor for at generere en plain-text analyse af de "
        "største budgetafvigelser i den valgte periode og de valgte afdelinger."
    )

    if st.button("🔍 Generer afvigelsesforklaring", type="primary", use_container_width=True):
        with st.spinner("Analyserer afvigelser …"):
            explanation = generate_variance_explanation(budget_f, actuals_f)

        st.markdown(explanation)

        # Supporting chart
        st.subheader("Top-10 afvigelser (afdeling × kategori)")
        merged_all = budget_f.merge(actuals_f, on=["maaned", "afdeling", "kategori"])
        merged_all["var_dkk"] = merged_all["faktisk_dkk"] - merged_all["budget_dkk"]
        agg_all = (
            merged_all.groupby(["afdeling", "kategori"])["var_dkk"]
            .sum()
            .reset_index()
            .assign(abs_var=lambda d: d["var_dkk"].abs())
            .nlargest(10, "abs_var")
            .sort_values("var_dkk")
        )
        agg_all["label"] = agg_all["afdeling"] + " · " + agg_all["kategori"]
        agg_all["color"] = agg_all["var_dkk"].apply(
            lambda v: "#e74c3c" if v > 0 else "#27ae60"
        )

        fig_ai = go.Figure(go.Bar(
            x=agg_all["var_dkk"] / 1e3,
            y=agg_all["label"],
            orientation="h",
            marker_color=agg_all["color"],
            text=[f"{v/1e3:+,.1f}k" for v in agg_all["var_dkk"]],
            textposition="outside",
        ))
        fig_ai.add_vline(x=0, line_color="black", line_width=1)
        fig_ai.update_layout(
            xaxis_title="Afvigelse (TDKK)",
            yaxis_title="",
            height=420,
            margin=dict(t=10, b=40, l=200),
        )
        st.plotly_chart(fig_ai, use_container_width=True)

        # Raw numbers table
        st.subheader("Detaljeret afvigelsestabel (alle kombinationer)")
        full_agg = (
            merged_all.groupby(["afdeling", "kategori"])
            .agg(
                budget_dkk=("budget_dkk", "sum"),
                faktisk_dkk=("faktisk_dkk", "sum"),
                var_dkk=("var_dkk", "sum"),
            )
            .reset_index()
        )
        full_agg["var_pct"] = full_agg["var_dkk"] / full_agg["budget_dkk"] * 100
        full_agg.columns = ["Afdeling", "Kategori", "Budget DKK", "Faktisk DKK", "Afvigelse DKK", "Afvigelse %"]

        def color_var(row):
            pct = row["Afvigelse %"]
            bg = "#fde8e8" if pct > 3 else ("#e8f8e8" if pct < -3 else "")
            return [f"background-color: {bg}"] * len(row)

        st.dataframe(
            full_agg.style
            .apply(color_var, axis=1)
            .format({
                "Budget DKK":    "{:,.0f}",
                "Faktisk DKK":   "{:,.0f}",
                "Afvigelse DKK": "{:+,.0f}",
                "Afvigelse %":   "{:+.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.markdown(
            """
            **Eksempel på output:**

            > ⚠️ **Robotenhed – Udstyr**
            > Afvigelse: +DKK 420.000 (14,2%)
            > Uplanlagt vedligeholdelse af robotsystem (Da Vinci) i juli–september
            > medførte ekstraomkostninger til reservedele og servicekontrakt.

            > ⚠️ **Robotenhed – Personale**
            > Afvigelse: +DKK 312.000 (8,5%)
            > 8 ekstra robotkirurgi-sessioner i juli–september som følge af
            > venteliste-reducering krævede overarbejde og ekstra vagtdækning.

            > ✅ **Sterilcentral – Personale**
            > Afvigelse: −DKK 198.000 (−5,3%)
            > Effektiviseringer i sterilisationsflow bidrog til mindreforbrug.
            """
        )
