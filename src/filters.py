"""Shared sidebar filter renderer for all dashboard pages."""

import pandas as pd
import streamlit as st

from src.data_loader import load_all


def render_sidebar() -> tuple[list[str], tuple[str, str]]:
    """Render sidebar filters and return (valgte_afdelinger, (start, slut))."""
    budget_df, actuals_df, _, _ = load_all()

    with st.sidebar:
        st.title("FBP Dashboard")
        st.caption("Hospitalskirurgi · Robotenhed")
        st.divider()

        alle_afd = sorted(budget_df["afdeling"].unique())
        valgte_afd: list[str] = st.multiselect(
            "Afdelinger",
            options=alle_afd,
            default=alle_afd,
        )
        if not valgte_afd:
            valgte_afd = alle_afd

        alle_maaneder = sorted(actuals_df["maaned"].dt.strftime("%Y-%m").unique())
        min_m, max_m = alle_maaneder[0], alle_maaneder[-1]
        periode: tuple[str, str] = st.select_slider(
            "Periode",
            options=alle_maaneder,
            value=(min_m, max_m),
        )

        st.divider()
        st.caption("Data: Jan 2025 – Mar 2026")
        st.caption("© FBP Hospitalskirurgi")

    return valgte_afd, periode


def apply_filters(
    df: pd.DataFrame,
    periode: tuple[str, str],
    valgte_afd: list[str] | None = None,
    dept_col: str = "afdeling",
) -> pd.DataFrame:
    """Filter DataFrame by period and optionally by department."""
    mstart = pd.to_datetime(periode[0])
    mend = pd.to_datetime(periode[1])
    mask = (df["maaned"] >= mstart) & (df["maaned"] <= mend)
    if valgte_afd and dept_col in df.columns:
        mask &= df[dept_col].isin(valgte_afd)
    return df[mask].copy()
