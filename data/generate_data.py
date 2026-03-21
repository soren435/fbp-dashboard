"""
Generate realistic sample data for the FBP Dashboard.
Covers Jan 2025 – Mar 2026 (15 months), with budget for the full year 2025
and actuals through March 2026.

Run directly:  python data/generate_data.py
Also auto-imported by app.py on first launch.
"""

import os
import numpy as np
import pandas as pd

# ── reproducibility ─────────────────────────────────────────────────────────
rng = np.random.default_rng(42)

# ── constants ────────────────────────────────────────────────────────────────
DEPARTMENTS   = ["Kirurgi", "Anæstesi", "Sterilcentral", "Robotenhed"]
CATEGORIES    = ["Personale", "Udstyr", "Forbrug", "Overhead"]
OP_TYPES      = ["Robotkirurgi", "Laparoskopi", "Åben kirurgi", "Ambulant opfølgning"]
OR_ROOMS      = ["OR-1", "OR-2", "OR-3", "OR-4"]
ROBOT_UNITS   = ["Robot-A", "Robot-B"]

# Monthly budget base (DKK) per department × category (annual, split evenly)
# Robotenhed is expensive; Sterilcentral is cheaper
BUDGET_BASE = {
    ("Kirurgi",       "Personale"):   8_200_000,
    ("Kirurgi",       "Udstyr"):        950_000,
    ("Kirurgi",       "Forbrug"):       620_000,
    ("Kirurgi",       "Overhead"):      480_000,
    ("Anæstesi",      "Personale"):   6_100_000,
    ("Anæstesi",      "Udstyr"):        540_000,
    ("Anæstesi",      "Forbrug"):       390_000,
    ("Anæstesi",      "Overhead"):      310_000,
    ("Sterilcentral", "Personale"):   2_400_000,
    ("Sterilcentral", "Udstyr"):        280_000,
    ("Sterilcentral", "Forbrug"):       190_000,
    ("Sterilcentral", "Overhead"):      130_000,
    ("Robotenhed",    "Personale"):   4_800_000,
    ("Robotenhed",    "Udstyr"):      3_200_000,   # high – robot maintenance
    ("Robotenhed",    "Forbrug"):       850_000,
    ("Robotenhed",    "Overhead"):      420_000,
}

# Seasonal index (Jan–Dec); peaks in autumn
SEASONAL = np.array([0.85, 0.80, 0.88, 0.92, 0.95, 0.90,
                     0.78, 0.75, 1.10, 1.18, 1.15, 1.05])

OUTPUT_DIR = os.path.join(os.path.dirname(__file__))


# ── 1. budget.csv ────────────────────────────────────────────────────────────
def make_budget() -> pd.DataFrame:
    rows = []
    months = pd.date_range("2025-01-01", periods=12, freq="MS")
    for month in months:
        m_idx = month.month - 1
        for dept in DEPARTMENTS:
            for cat in CATEGORIES:
                annual = BUDGET_BASE[(dept, cat)]
                monthly = annual / 12 * SEASONAL[m_idx]
                rows.append({
                    "maaned":     month.strftime("%Y-%m"),
                    "afdeling":   dept,
                    "kategori":   cat,
                    "budget_dkk": round(monthly, 0),
                })
    return pd.DataFrame(rows)


# ── 2. actuals.csv ───────────────────────────────────────────────────────────
def make_actuals() -> pd.DataFrame:
    """
    Actuals for Jan 2025 – Mar 2026 (15 months).
    Robotenhed runs ~12-14 % over budget in Q3/Q4 due to extra robot sessions.
    Sterilcentral runs slightly under.
    """
    rows = []
    months_2025 = pd.date_range("2025-01-01", periods=12, freq="MS")
    months_2026 = pd.date_range("2026-01-01", periods=3,  freq="MS")
    all_months = months_2025.tolist() + months_2026.tolist()

    for month in all_months:
        m_idx = min(month.month - 1, 11)   # reuse 2025 seasonal for 2026
        for dept in DEPARTMENTS:
            for cat in CATEGORIES:
                annual = BUDGET_BASE[(dept, cat)]
                budget_m = annual / 12 * SEASONAL[m_idx]

                # Base noise ±4 %
                noise = rng.normal(1.0, 0.04)

                # Department-specific over/under-spend patterns
                if dept == "Robotenhed":
                    # Extra sessions in Q3 (Jul–Sep) and Nov; also mild overrun in 2026
                    if month.month in (7, 8, 9, 11) or month.year == 2026:
                        noise *= rng.uniform(1.10, 1.16)
                    else:
                        noise *= rng.uniform(0.98, 1.04)
                elif dept == "Sterilcentral":
                    noise *= rng.uniform(0.93, 0.99)  # consistently under
                elif dept == "Kirurgi" and month.month in (10, 11):
                    noise *= rng.uniform(1.05, 1.09)  # autumn peak
                elif dept == "Anæstesi" and month.month in (8,):
                    noise *= rng.uniform(0.88, 0.94)  # summer low

                # Udstyr in Robotenhed: big spike in Q3 (unplanned maintenance)
                if dept == "Robotenhed" and cat == "Udstyr" and month.month in (8, 9):
                    noise *= rng.uniform(1.20, 1.30)

                actual = budget_m * noise
                rows.append({
                    "maaned":      month.strftime("%Y-%m"),
                    "afdeling":    dept,
                    "kategori":    cat,
                    "faktisk_dkk": round(actual, 0),
                })
    return pd.DataFrame(rows)


# ── 3. operations.csv ────────────────────────────────────────────────────────
def make_operations() -> pd.DataFrame:
    """Cost per operation type, broken down by resource."""
    rows = []
    months = pd.date_range("2025-01-01", periods=15, freq="MS")

    # Base volumes per month; Robotkirurgi peaks Q3 due to waiting-list reduction
    base_volumes = {
        "Robotkirurgi":         18,
        "Laparoskopi":          55,
        "Åben kirurgi":         30,
        "Ambulant opfølgning": 120,
    }
    # Unit cost (DKK) split by resource type
    unit_costs = {
        "Robotkirurgi":         {"Personale": 28_000, "Udstyr": 18_000, "Forbrug":  6_000, "Overhead": 4_500},
        "Laparoskopi":          {"Personale": 12_000, "Udstyr":  4_500, "Forbrug":  2_200, "Overhead": 1_800},
        "Åben kirurgi":         {"Personale": 14_500, "Udstyr":  3_200, "Forbrug":  3_500, "Overhead": 2_000},
        "Ambulant opfølgning":  {"Personale":  2_800, "Udstyr":    300, "Forbrug":    250, "Overhead":   400},
    }

    for month in months:
        for op in OP_TYPES:
            vol = base_volumes[op]
            # Robotkirurgi: +35 % in Jul–Sep 2025 (waiting list)
            if op == "Robotkirurgi" and month.month in (7, 8, 9) and month.year == 2025:
                vol = int(vol * rng.uniform(1.30, 1.40))
            else:
                vol = int(vol * rng.uniform(0.90, 1.10))

            for res, unit in unit_costs[op].items():
                total = vol * unit * rng.uniform(0.96, 1.04)
                rows.append({
                    "maaned":          month.strftime("%Y-%m"),
                    "operationstype":  op,
                    "ressource":       res,
                    "antal":           vol,
                    "omkostning_dkk":  round(total, 0),
                })
    return pd.DataFrame(rows)


# ── 4. capacity.csv ──────────────────────────────────────────────────────────
def make_capacity() -> pd.DataFrame:
    """
    Available vs. used hours per OR room / robot unit per month.
    Working days ≈ 21/month; OR room = 8 h/day; robot = 6 h/day (shared scrub time).
    """
    rows = []
    months = pd.date_range("2025-01-01", periods=15, freq="MS")

    units = {room: "OR" for room in OR_ROOMS}
    units.update({ru: "Robot" for ru in ROBOT_UNITS})

    for month in months:
        work_days = 21 if month.month not in (7, 12) else 17  # holiday months
        for unit, utype in units.items():
            if utype == "OR":
                available = work_days * 8
                # utilization: high in Sept-Nov, lower in summer/Dec
                base_util = {7: 0.62, 8: 0.65, 9: 0.91, 10: 0.93, 11: 0.90,
                             12: 0.72}.get(month.month, 0.80)
                used = available * base_util * rng.uniform(0.95, 1.05)
            else:
                available = work_days * 6
                base_util = {7: 0.70, 8: 0.75, 9: 0.95, 10: 0.96, 11: 0.93,
                             12: 0.68}.get(month.month, 0.82)
                # Robot-A is busier than Robot-B
                if unit == "Robot-A":
                    base_util = min(base_util * 1.08, 1.02)  # can go >100 % (overtime)
                used = available * base_util * rng.uniform(0.95, 1.05)

            rows.append({
                "maaned":        month.strftime("%Y-%m"),
                "enhed":         unit,
                "type":          utype,
                "tilgaengelig_h": round(available, 1),
                "anvendt_h":      round(min(used, available * 1.05), 1),  # cap at 105 %
                "udnyttelse_pct": round(min(used / available, 1.05) * 100, 1),
            })
    return pd.DataFrame(rows)


# ── main ─────────────────────────────────────────────────────────────────────
def generate_all(output_dir: str = OUTPUT_DIR) -> dict[str, pd.DataFrame]:
    os.makedirs(output_dir, exist_ok=True)
    datasets = {
        "budget.csv":     make_budget(),
        "actuals.csv":    make_actuals(),
        "operations.csv": make_operations(),
        "capacity.csv":   make_capacity(),
    }
    for fname, df in datasets.items():
        path = os.path.join(output_dir, fname)
        df.to_csv(path, index=False)
        print(f"  Wrote {len(df):>5} rows → {path}")
    return datasets


if __name__ == "__main__":
    print("Genererer data …")
    generate_all()
    print("Færdig.")
