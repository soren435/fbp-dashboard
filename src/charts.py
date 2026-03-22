"""Reusable Plotly chart builders for the FBP Dashboard."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Colour palettes ────────────────────────────────────────────────────────────
DEPT_COLORS: dict[str, str] = {
    "Kirurgi": "#4C72B0",
    "Anæstesi": "#DD8452",
    "Sterilcentral": "#55A868",
    "Robotenhed": "#C44E52",
}

CAT_COLORS: dict[str, str] = {
    "Personale": "#4C72B0",
    "Udstyr": "#DD8452",
    "Forbrug": "#55A868",
    "Overhead": "#8172B2",
}

OP_COLORS: dict[str, str] = {
    "Robotkirurgi": "#C44E52",
    "Laparoskopi": "#4C72B0",
    "Åben kirurgi": "#DD8452",
    "Ambulant opfølgning": "#55A868",
}

SCENARIO_COLORS: dict[str, str] = {
    "Status quo": "#95a5a6",
    "+2 sessioner/uge": "#4C72B0",
    "Ny robotenhed": "#C44E52",
}


def fmt_dkk(val: float) -> str:
    return f"DKK {val:,.0f}".replace(",", ".")


def variance_color(pct: float) -> str:
    if pct > 2:
        return "#e74c3c"
    if pct < -2:
        return "#27ae60"
    return "#95a5a6"


# ── Budget vs. Actual ──────────────────────────────────────────────────────────

def budget_vs_actual_bar(
    merged: pd.DataFrame,
    x_col: str,
    height: int = 400,
) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=merged[x_col],
        y=merged["budget_dkk"] / 1e6,
        name="Budget",
        marker_color="#4C72B0",
        opacity=0.75,
    )
    fig.add_bar(
        x=merged[x_col],
        y=merged["faktisk_dkk"] / 1e6,
        name="Faktisk",
        marker_color="#C44E52",
        opacity=0.85,
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="Mio. DKK",
        legend=dict(orientation="h", y=1.05),
        height=height,
        margin=dict(t=10, b=40),
    )
    return fig


def variance_bar(
    data: pd.DataFrame,
    x_col: str,
    pct_col: str = "afvigelse_pct",
    height: int = 320,
) -> go.Figure:
    colors = [variance_color(v) for v in data[pct_col]]
    fig = go.Figure(
        go.Bar(
            x=data[x_col],
            y=data[pct_col],
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in data[pct_col]],
            textposition="outside",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    fig.update_layout(
        yaxis_title="Afvigelse %",
        height=height,
        margin=dict(t=20, b=40),
    )
    return fig


def stacked_category_bar(actuals: pd.DataFrame, height: int = 380) -> go.Figure:
    pivot = (
        actuals.groupby(["afdeling", "kategori"])["faktisk_dkk"]
        .sum()
        .reset_index()
    )
    fig = px.bar(
        pivot,
        x="afdeling",
        y="faktisk_dkk",
        color="kategori",
        barmode="stack",
        color_discrete_map=CAT_COLORS,
        labels={
            "afdeling": "Afdeling",
            "faktisk_dkk": "Faktisk (DKK)",
            "kategori": "Kategori",
        },
        text_auto=".3s",
    )
    fig.update_layout(height=height, margin=dict(t=10, b=40))
    return fig


# ── Capacity ───────────────────────────────────────────────────────────────────

def capacity_heatmap(capacity: pd.DataFrame, height: int = 380) -> go.Figure:
    pivot = capacity.pivot_table(
        index="enhed",
        columns=capacity["maaned"].dt.strftime("%Y-%m"),
        values="udnyttelse_pct",
        aggfunc="mean",
    )
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[
                [0.00, "#2ecc71"],
                [0.75, "#f39c12"],
                [0.90, "#e74c3c"],
                [1.00, "#8e1a0e"],
            ],
            zmin=50,
            zmax=105,
            text=pivot.values.round(1),
            texttemplate="%{text}%",
            hovertemplate="Enhed: %{y}<br>Måned: %{x}<br>Udnyttelse: %{z:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(t=10, b=60),
        xaxis_tickangle=-45,
    )
    return fig


def capacity_bar_available_vs_used(capacity: pd.DataFrame, height: int = 340) -> go.Figure:
    cap_sum = capacity.groupby("enhed")[["tilgaengelig_h", "anvendt_h"]].sum().reset_index()
    fig = go.Figure()
    fig.add_bar(
        x=cap_sum["enhed"],
        y=cap_sum["tilgaengelig_h"],
        name="Tilgængelig",
        marker_color="#4C72B0",
        opacity=0.6,
    )
    fig.add_bar(
        x=cap_sum["enhed"],
        y=cap_sum["anvendt_h"],
        name="Anvendt",
        marker_color="#C44E52",
        opacity=0.85,
    )
    fig.update_layout(
        barmode="overlay",
        yaxis_title="Timer",
        legend=dict(orientation="h", y=1.05),
        height=height,
        margin=dict(t=10, b=40),
    )
    return fig


# ── Forecast ───────────────────────────────────────────────────────────────────

def forecast_chart(
    actuals_monthly: pd.DataFrame,
    budget_monthly: pd.DataFrame,
    forecast: pd.DataFrame,
    height: int = 460,
) -> go.Figure:
    fig = go.Figure()

    fig.add_scatter(
        x=budget_monthly["maaned"],
        y=budget_monthly["budget_dkk"] / 1e6,
        name="Budget",
        mode="lines",
        line=dict(color="#4C72B0", dash="dot", width=2),
    )
    fig.add_scatter(
        x=actuals_monthly["maaned"],
        y=actuals_monthly["faktisk_dkk"] / 1e6,
        name="Faktisk",
        mode="lines+markers",
        line=dict(color="#27ae60", width=2.5),
        marker=dict(size=6),
    )
    # Confidence band (shaded)
    fig.add_scatter(
        x=pd.concat([forecast["maaned"], forecast["maaned"][::-1]]),
        y=pd.concat([forecast["upper"] / 1e6, forecast["lower"][::-1] / 1e6]),
        fill="toself",
        fillcolor="rgba(221,132,82,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Konfidensinterval",
        hoverinfo="skip",
    )
    fig.add_scatter(
        x=forecast["maaned"],
        y=forecast["forecast_dkk"] / 1e6,
        name=forecast["model"].iloc[0],
        mode="lines+markers",
        line=dict(color="#DD8452", width=2.5, dash="dash"),
        marker=dict(size=6, symbol="diamond"),
    )
    last_actual = actuals_monthly["maaned"].max()
    fig.add_vline(
        x=last_actual.timestamp() * 1000,
        line_dash="dot",
        line_color="grey",
        annotation_text="Forecast start",
        annotation_position="top right",
    )
    fig.update_layout(
        yaxis_title="Mio. DKK",
        xaxis_title="Måned",
        legend=dict(orientation="h", y=1.08),
        height=height,
        margin=dict(t=20, b=40),
    )
    return fig


# ── Business Case ──────────────────────────────────────────────────────────────

def cumulative_cashflow_chart(cashflow_df: pd.DataFrame, height: int = 380) -> go.Figure:
    fig = px.line(
        cashflow_df,
        x="År",
        y="Kumulativ nettogevinst (DKK)",
        color="Scenarie",
        color_discrete_map=SCENARIO_COLORS,
        markers=True,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    fig.update_layout(
        yaxis_title="Kumulativ nettogevinst (DKK)",
        xaxis_title="År",
        legend=dict(orientation="h", y=1.05),
        height=height,
        margin=dict(t=20, b=40),
    )
    return fig


def robot_utilisation_gauge(avg_util: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=avg_util,
            delta={"reference": 80, "suffix": "%"},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 110]},
                "bar": {"color": "#C44E52"},
                "steps": [
                    {"range": [0, 80], "color": "#d5e8d4"},
                    {"range": [80, 95], "color": "#fff2cc"},
                    {"range": [95, 110], "color": "#f8cecc"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 3},
                    "thickness": 0.75,
                    "value": 100,
                },
            },
            title={"text": "Gns. udnyttelse – Robotenheder"},
        )
    )
    fig.update_layout(height=250, margin=dict(t=30, b=0))
    return fig
