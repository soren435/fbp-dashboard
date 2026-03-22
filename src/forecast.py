"""Forecast logic for the FBP Dashboard.

Strategy (in priority order):
  ≥ 24 months of data → Holt-Winters additive seasonality (period = 12)
  ≥ 12 months         → Holt double-exponential (trend only)
  < 12 months         → linear trend fallback

Requires statsmodels for the first two; falls back gracefully if not installed.
"""

import warnings
import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    _HAS_STATSMODELS = True
except ImportError:
    _HAS_STATSMODELS = False


def build_total_forecast(
    actuals: pd.DataFrame,
    periods: int = 12,
    confidence_pct: float = 0.10,
) -> pd.DataFrame:
    """Build a monthly forecast from historical actuals (all departments combined).

    Returns DataFrame with columns:
        maaned, forecast_dkk, lower, upper, model
    """
    monthly = (
        actuals.groupby("maaned")["faktisk_dkk"]
        .sum()
        .sort_index()
        .reset_index()
    )
    y = monthly["faktisk_dkk"].values
    n = len(y)
    last_date = monthly["maaned"].max()
    fc_dates = pd.date_range(
        last_date + pd.DateOffset(months=1), periods=periods, freq="MS"
    )

    if _HAS_STATSMODELS and n >= 24:
        model = ExponentialSmoothing(
            y, trend="add", seasonal="add", seasonal_periods=12
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fitted = model.fit(optimized=True)
        fcast = fitted.forecast(periods)
        model_label = "Holt-Winters (sæsonkorrigeret)"

    elif _HAS_STATSMODELS and n >= 12:
        model = ExponentialSmoothing(y, trend="add", seasonal=None)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fitted = model.fit(optimized=True)
        fcast = fitted.forecast(periods)
        model_label = "Holt (trend + eksponentiel udjævning)"

    else:
        t = np.arange(n)
        coeffs = np.polyfit(t, y, 1)
        fcast = np.polyval(coeffs, np.arange(n, n + periods))
        model_label = "Lineær trend"

    fcast = np.maximum(fcast, 0)

    return pd.DataFrame(
        {
            "maaned": fc_dates,
            "forecast_dkk": fcast,
            "lower": fcast * (1 - confidence_pct),
            "upper": fcast * (1 + confidence_pct),
            "model": model_label,
        }
    )


def build_dept_forecast(
    actuals: pd.DataFrame,
    periods: int = 6,
) -> pd.DataFrame:
    """Linear trend forecast per department."""
    rows = []
    for dept, grp in actuals.groupby("afdeling"):
        monthly = grp.groupby("maaned")["faktisk_dkk"].sum().sort_index()
        y = monthly.values
        n = len(y)
        last_date = monthly.index.max()

        t = np.arange(n)
        coeffs = np.polyfit(t, y, 1)
        fcast = np.maximum(np.polyval(coeffs, np.arange(n, n + periods)), 0)

        fc_dates = pd.date_range(
            last_date + pd.DateOffset(months=1), periods=periods, freq="MS"
        )
        for d, v in zip(fc_dates, fcast):
            rows.append({"maaned": d, "afdeling": dept, "forecast_dkk": v})

    return pd.DataFrame(rows)
