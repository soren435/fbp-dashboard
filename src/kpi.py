"""KPI calculations for the FBP Dashboard."""

from typing import NamedTuple
import pandas as pd


class TotalKPIs(NamedTuple):
    total_budget: float
    total_actuals: float
    variance_dkk: float
    variance_pct: float
    avg_capacity_util: float
    cost_per_robot_case: float


def calc_total_kpis(
    budget: pd.DataFrame,
    actuals: pd.DataFrame,
    capacity: pd.DataFrame,
    operations: pd.DataFrame,
) -> TotalKPIs:
    total_budget = budget["budget_dkk"].sum()
    total_actuals = actuals["faktisk_dkk"].sum()
    variance_dkk = total_actuals - total_budget
    variance_pct = variance_dkk / total_budget * 100 if total_budget else 0
    avg_cap = capacity["udnyttelse_pct"].mean()

    # Cost per robot case (unique antal to avoid double-counting across ressource rows)
    robot_cost = actuals[actuals["afdeling"] == "Robotenhed"]["faktisk_dkk"].sum()
    robot_cases = (
        operations[operations["operationstype"] == "Robotkirurgi"]
        .drop_duplicates(subset=["maaned", "operationstype"])["antal"]
        .sum()
    )
    cost_per_rc = robot_cost / robot_cases if robot_cases else 0

    return TotalKPIs(
        total_budget, total_actuals, variance_dkk, variance_pct, avg_cap, cost_per_rc
    )


def dept_variance(budget: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Variance per department, sorted by absolute deviation."""
    grp_b = budget.groupby("afdeling")["budget_dkk"].sum().reset_index()
    grp_a = actuals.groupby("afdeling")["faktisk_dkk"].sum().reset_index()
    merged = grp_b.merge(grp_a, on="afdeling")
    merged["afvigelse_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
    merged["afvigelse_pct"] = merged["afvigelse_dkk"] / merged["budget_dkk"] * 100
    return merged.sort_values("afvigelse_dkk", ascending=False)


def category_variance(budget: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Variance per cost category."""
    grp_b = budget.groupby("kategori")["budget_dkk"].sum().reset_index()
    grp_a = actuals.groupby("kategori")["faktisk_dkk"].sum().reset_index()
    merged = grp_b.merge(grp_a, on="kategori")
    merged["afvigelse_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
    merged["afvigelse_pct"] = merged["afvigelse_dkk"] / merged["budget_dkk"] * 100
    return merged.sort_values("afvigelse_dkk", ascending=False)


def detailed_variance(budget: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Full dept × category variance table, sorted by absolute DKK deviation."""
    merged = budget.merge(
        actuals,
        on=["maaned", "afdeling", "kategori"],
        how="inner",
    )
    merged["var_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]

    agg = (
        merged.groupby(["afdeling", "kategori"])
        .agg(
            budget_dkk=("budget_dkk", "sum"),
            faktisk_dkk=("faktisk_dkk", "sum"),
            var_dkk=("var_dkk", "sum"),
        )
        .reset_index()
    )
    agg["var_pct"] = agg["var_dkk"] / agg["budget_dkk"] * 100
    agg["abs_var"] = agg["var_dkk"].abs()
    return agg.sort_values("abs_var", ascending=False).reset_index(drop=True)
