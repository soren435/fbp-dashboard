"""Data loading with Streamlit caching for the FBP Dashboard."""

import os
import sys
import pandas as pd
import streamlit as st

# Locate data/ relative to project root (one level up from src/)
_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(_ROOT, "data")

REQUIRED_FILES = ["budget.csv", "actuals.csv", "operations.csv", "capacity.csv"]


def _ensure_data() -> None:
    """Auto-generate synthetic data if CSV files are missing."""
    if not all(os.path.exists(os.path.join(DATA_DIR, f)) for f in REQUIRED_FILES):
        sys.path.insert(0, DATA_DIR)
        import generate_data  # type: ignore
        generate_data.generate_all(DATA_DIR)


@st.cache_data
def load_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (budget, actuals, operations, capacity) with parsed dates."""
    _ensure_data()

    budget = pd.read_csv(os.path.join(DATA_DIR, "budget.csv"))
    actuals = pd.read_csv(os.path.join(DATA_DIR, "actuals.csv"))
    operations = pd.read_csv(os.path.join(DATA_DIR, "operations.csv"))
    capacity = pd.read_csv(os.path.join(DATA_DIR, "capacity.csv"))

    for df in (budget, actuals, operations, capacity):
        df["maaned"] = pd.to_datetime(df["maaned"])

    return budget, actuals, operations, capacity
