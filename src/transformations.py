"""Data transformation and aggregation helpers."""

import pandas as pd
import numpy as np


def merge_budget_actuals(
    budget: pd.DataFrame,
    actuals: pd.DataFrame,
    group_by: list[str],
) -> pd.DataFrame:
    """Merge budget and actuals on given keys; compute variance columns."""
    grp_b = budget.groupby(group_by)["budget_dkk"].sum().reset_index()
    grp_a = actuals.groupby(group_by)["faktisk_dkk"].sum().reset_index()
    merged = grp_b.merge(grp_a, on=group_by, how="inner")
    merged["afvigelse_dkk"] = merged["faktisk_dkk"] - merged["budget_dkk"]
    merged["afvigelse_pct"] = merged["afvigelse_dkk"] / merged["budget_dkk"] * 100
    return merged


def ops_cost_per_case(operations: pd.DataFrame) -> pd.DataFrame:
    """Cost-per-case by operationstype.

    Note: 'antal' is repeated across ressource rows for the same month/optype,
    so unique volume is extracted before summing.
    """
    total_cost = (
        operations.groupby("operationstype")["omkostning_dkk"].sum().reset_index()
    )
    unique_vol = (
        operations.drop_duplicates(subset=["maaned", "operationstype"])
        .groupby("operationstype")["antal"]
        .sum()
        .reset_index()
        .rename(columns={"antal": "total_antal"})
    )
    result = total_cost.merge(unique_vol, on="operationstype")
    result["cost_per_case"] = result["omkostning_dkk"] / result["total_antal"]
    return result


def ops_monthly_volume(operations: pd.DataFrame) -> pd.DataFrame:
    """Monthly unique case volume per operationstype."""
    return (
        operations.drop_duplicates(subset=["maaned", "operationstype"])
        .groupby(["maaned", "operationstype"])["antal"]
        .first()
        .reset_index()
    )


def ops_monthly_cost(operations: pd.DataFrame) -> pd.DataFrame:
    """Monthly total cost per operationstype."""
    return (
        operations.groupby(["maaned", "operationstype"])["omkostning_dkk"]
        .sum()
        .reset_index()
    )


def volume_vs_cost_trend(operations: pd.DataFrame) -> pd.DataFrame:
    """Monthly robot volume and cost index (base = first month = 100)."""
    robot = operations[operations["operationstype"] == "Robotkirurgi"].copy()
    cost_m = robot.groupby("maaned")["omkostning_dkk"].sum()
    vol_m = (
        robot.drop_duplicates(subset=["maaned", "operationstype"])
        .groupby("maaned")["antal"]
        .first()
    )
    df = pd.DataFrame({"cost": cost_m, "volume": vol_m}).dropna().sort_index()
    base_cost = df["cost"].iloc[0]
    base_vol = df["volume"].iloc[0]
    df["cost_index"] = df["cost"] / base_cost * 100
    df["volume_index"] = df["volume"] / base_vol * 100
    return df.reset_index()


def join_robot_actuals_operations(
    actuals: pd.DataFrame,
    operations: pd.DataFrame,
) -> pd.DataFrame:
    """Monthly Robotenhed cost + robot case volume → cost_per_robot_case."""
    robot_cost = (
        actuals[actuals["afdeling"] == "Robotenhed"]
        .groupby("maaned")["faktisk_dkk"]
        .sum()
        .reset_index()
        .rename(columns={"faktisk_dkk": "robot_cost"})
    )
    robot_vol = (
        operations[operations["operationstype"] == "Robotkirurgi"]
        .drop_duplicates(subset=["maaned", "operationstype"])
        .groupby("maaned")["antal"]
        .first()
        .reset_index()
        .rename(columns={"antal": "robot_cases"})
    )
    joined = robot_cost.merge(robot_vol, on="maaned", how="inner")
    joined["cost_per_robot_case"] = joined["robot_cost"] / joined["robot_cases"]
    return joined
