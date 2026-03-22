"""Robot Business Case / ROI calculations.

All monetary values in DKK.
Assumptions are explicitly documented and visible in the Streamlit UI.
"""

from dataclasses import dataclass, field
import numpy as np
import pandas as pd

# ── Investment assumptions (Da Vinci robot context) ───────────────────────────
ROBOT_INVESTMENT_DKK: float = 12_000_000     # Typical purchase price incl. installation
ROBOT_ANNUAL_SERVICE: float = 1_500_000      # Annual service contract
SESSIONS_PER_ROBOT_YEAR: int = 200           # Full-year capacity for one robot unit
ROBOT_REVENUE_PER_CASE: float = 45_000       # DRG-based revenue estimate per case
DISCOUNT_RATE: float = 0.04                  # 4 % public-sector discount rate


@dataclass
class Scenario:
    name: str
    label: str
    extra_sessions_year: int
    investment_dkk: float
    annual_fixed_cost_delta: float
    description: str


SCENARIOS: list[Scenario] = [
    Scenario(
        name="status_quo",
        label="Status quo",
        extra_sessions_year=0,
        investment_dkk=0,
        annual_fixed_cost_delta=0,
        description=(
            "Ingen ændring – eksisterende robotenhed opererer ved nuværende kapacitetsudnyttelse. "
            "Risiko for yderligere pres på kapacitet og udstyr."
        ),
    ),
    Scenario(
        name="extra_sessions",
        label="+2 sessioner/uge",
        extra_sessions_year=96,
        investment_dkk=200_000,
        annual_fixed_cost_delta=600_000,
        description=(
            "Udnyt eksisterende robotenhed mere intensivt ved at tilføje to ekstra sessioner "
            "om ugen. Kræver ekstra personale og forbrugsmateriel, men ingen ny-investering."
        ),
    ),
    Scenario(
        name="new_robot",
        label="Ny robotenhed",
        extra_sessions_year=SESSIONS_PER_ROBOT_YEAR,
        investment_dkk=ROBOT_INVESTMENT_DKK,
        annual_fixed_cost_delta=ROBOT_ANNUAL_SERVICE + 2_000_000,
        description=(
            "Investering i ny Da Vinci-robotenhed med fuldt bemandingsniveau. "
            "Høj initial investering, men den største kapacitetsgevinst og lavest cost-per-case over tid."
        ),
    ),
]


def robot_capacity_summary(capacity: pd.DataFrame) -> pd.DataFrame:
    """Average/max utilisation stats for robot units only."""
    robots = capacity[capacity["type"] == "Robot"].copy()
    return (
        robots.groupby("enhed")
        .agg(
            gns_udnyttelse=("udnyttelse_pct", "mean"),
            max_udnyttelse=("udnyttelse_pct", "max"),
            min_udnyttelse=("udnyttelse_pct", "min"),
            gns_anvendt_h=("anvendt_h", "mean"),
            gns_tilgaengelig_h=("tilgaengelig_h", "mean"),
        )
        .reset_index()
        .round(1)
    )


def monthly_robot_cost_by_category(actuals: pd.DataFrame) -> pd.DataFrame:
    """Monthly Robotenhed cost broken down by cost category."""
    return (
        actuals[actuals["afdeling"] == "Robotenhed"]
        .groupby(["maaned", "kategori"])["faktisk_dkk"]
        .sum()
        .reset_index()
    )


def monthly_robot_volume(operations: pd.DataFrame) -> pd.DataFrame:
    """Monthly robot surgery case volume (unique antal per month)."""
    return (
        operations[operations["operationstype"] == "Robotkirurgi"]
        .drop_duplicates(subset=["maaned", "operationstype"])
        .groupby("maaned")["antal"]
        .first()
        .reset_index()
        .rename(columns={"antal": "robot_cases"})
    )


def cost_per_robot_case_monthly(
    actuals: pd.DataFrame,
    operations: pd.DataFrame,
) -> pd.DataFrame:
    """Monthly cost-per-robot-case (Robotenhed total cost / robot case volume)."""
    costs = (
        actuals[actuals["afdeling"] == "Robotenhed"]
        .groupby("maaned")["faktisk_dkk"]
        .sum()
    )
    vols = monthly_robot_volume(operations).set_index("maaned")["robot_cases"]
    joined = pd.DataFrame({"cost": costs, "cases": vols}).dropna()
    joined["cost_per_case"] = joined["cost"] / joined["cases"]
    return joined.reset_index()


def roi_table(
    cost_per_case: float,
    scenarios: list[Scenario] | None = None,
    horizon_years: int = 5,
) -> pd.DataFrame:
    """Compute ROI/NPV for each scenario over the given horizon."""
    if scenarios is None:
        scenarios = SCENARIOS

    rows = []
    for sc in scenarios:
        annual_revenue = sc.extra_sessions_year * ROBOT_REVENUE_PER_CASE
        annual_variable_cost = sc.extra_sessions_year * cost_per_case
        annual_fixed_delta = sc.annual_fixed_cost_delta
        annual_net = annual_revenue - annual_variable_cost - annual_fixed_delta

        if annual_net > 0 and sc.investment_dkk > 0:
            break_even_years: float | str = round(sc.investment_dkk / annual_net, 1)
        elif sc.investment_dkk == 0:
            break_even_years = 0.0
        else:
            break_even_years = "N/A"

        npv = -sc.investment_dkk + sum(
            annual_net / (1 + DISCOUNT_RATE) ** yr for yr in range(1, horizon_years + 1)
        )

        rows.append(
            {
                "Scenarie": sc.label,
                "Investering (DKK)": int(sc.investment_dkk),
                "Ekstra sessioner/år": sc.extra_sessions_year,
                "Ekstra omsætning/år (DKK)": int(annual_revenue),
                "Nettoresultat/år (DKK)": int(annual_net),
                "Break-even (år)": break_even_years,
                f"NPV {horizon_years} år (DKK)": int(npv),
            }
        )

    return pd.DataFrame(rows)


def cumulative_cashflow(
    cost_per_case: float,
    scenarios: list[Scenario] | None = None,
    horizon_years: int = 5,
) -> pd.DataFrame:
    """Year-by-year cumulative net cashflow for each scenario (for charting)."""
    if scenarios is None:
        scenarios = SCENARIOS

    rows = []
    for sc in scenarios:
        annual_revenue = sc.extra_sessions_year * ROBOT_REVENUE_PER_CASE
        annual_cost = sc.extra_sessions_year * cost_per_case + sc.annual_fixed_cost_delta
        annual_net = annual_revenue - annual_cost
        cumulative = -sc.investment_dkk
        for yr in range(1, horizon_years + 1):
            cumulative += annual_net
            rows.append({"År": yr, "Scenarie": sc.label, "Kumulativ nettogevinst (DKK)": cumulative})

    return pd.DataFrame(rows)


def robot_recommendation(capacity: pd.DataFrame, cost_df: pd.DataFrame) -> str:
    """Auto-generate a short Danish leadership recommendation."""
    robots = capacity[capacity["type"] == "Robot"]
    avg_util = robots["udnyttelse_pct"].mean()
    max_util = robots["udnyttelse_pct"].max()
    avg_cpc = cost_df["cost_per_case"].mean() if "cost_per_case" in cost_df.columns else 0

    if max_util > 97:
        return (
            f"🔴 **Kritisk kapacitetspres:** Robotenhederne opererer konsekvent over 97 % udnyttelse "
            f"(maks. {max_util:.1f}%). Risikoen for nedbrud og planlagte operationer der ikke kan "
            "gennemføres er markant forhøjet. En ny robotenhed bør vurderes som strategisk prioritet."
        )
    elif avg_util > 88:
        return (
            f"🟡 **Høj kapacitetsudnyttelse:** Gennemsnitsudnyttelse på {avg_util:.1f}% efterlader "
            "minimal buffer til uplanlagte hændelser. Ekstra sessioner på eksisterende enhed anbefales "
            "som kortfristet løsning, mens business case for ny enhed udarbejdes."
        )
    else:
        return (
            f"🟢 **Kapacitet under kontrol:** Gennemsnitsudnyttelse på {avg_util:.1f}%. "
            "Nuværende kapacitet er tilstrækkelig på kort sigt. Fokus bør være på at optimere "
            "cost-per-case og øge sessionbelægningen yderligere."
        )
