# Finance Business Partner Dashboard

A decision-support tool for hospital management — built to demonstrate what strong
finance business partnering looks like in practice.

The dashboard connects **budget**, **actuals**, **surgical activity** and **capacity**
into a single analytical view, enabling data-driven leadership decisions rather than
just reporting numbers.

**Live demo:** *(add link after deployment)*

---

## Business relevance

Healthcare FBP work is complex: costs are driven by clinical activity, capacity is
constrained by physical assets, and investment decisions (like robot surgery expansion)
require rigorous quantitative grounding.

This project replicates that analytical environment using a realistic synthetic dataset
for a hospital surgical department with a robot surgery unit.

---

## Key finance capabilities demonstrated

| Capability | Where |
|---|---|
| Budget vs. actual variance analysis (dept × category) | Budget vs. Faktisk |
| Automated Danish management commentary (rule-based) | Executive Summary |
| Activity-based costing — cost per surgical case | Aktivitetsbaseret Kostpris |
| Volume vs. cost index (are costs growing faster than activity?) | Aktivitetsbaseret Kostpris |
| Capacity utilisation monitoring with threshold alerting | Kapacitetsudnyttelse |
| Multi-model forecast with confidence intervals | Forecast |
| Robot surgery ROI / NPV / break-even scenario model | Robot Business Case |

---

## Features

- **Executive Summary** — KPI cards, top-3 variance drivers and leadership recommendation
- **Budget vs. Actual** — Monthly, department and category drill-down with colour-coded table
- **Activity Costing** — Cost per case by surgery type; volume vs. cost trend index
- **Capacity** — Heatmap, OR-hours, robot utilisation gauge with traffic-light status
- **Forecast** — Holt-Winters seasonal model (≥24 months) → Holt trend → linear fallback
- **Robot Business Case** — Adjustable ROI model with three scenarios and cumulative cashflow chart

---

## Tech stack

| Layer | Technology |
|---|---|
| App framework | [Streamlit](https://streamlit.io) |
| Data manipulation | pandas, numpy |
| Forecasting | statsmodels (Holt-Winters) |
| Visualisation | Plotly |
| Data | Synthetic (reproducible via `data/generate_data.py`) |

---

## Project structure

```
fbp-dashboard/
├── app.py                    # Landing page + entry point
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── data_loader.py        # CSV loading with Streamlit caching
│   ├── transformations.py    # Merges, aggregations, cost-per-case joins
│   ├── kpi.py                # KPI calculations (variance, utilisation, cost per case)
│   ├── commentary.py         # Rule-based Danish management commentary
│   ├── forecast.py           # Holt-Winters / Holt / linear forecast logic
│   ├── business_case.py      # ROI, NPV, break-even, scenario model
│   ├── charts.py             # Reusable Plotly figure builders
│   └── filters.py            # Shared sidebar filter renderer
│
├── pages/
│   ├── 1_Executive_Summary.py
│   ├── 2_Budget_vs_Actual.py
│   ├── 3_Activity_Costing.py
│   ├── 4_Capacity.py
│   ├── 5_Forecast.py
│   └── 6_Robot_Business_Case.py
│
└── data/
    ├── budget.csv
    ├── actuals.csv
    ├── operations.csv
    ├── capacity.csv
    └── generate_data.py      # Reproducible synthetic data generator
```

---

## How to run locally

```bash
git clone https://github.com/soren435/fbp-dashboard.git
cd fbp-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Data files are auto-generated on first launch if not present.

---

## Deploy to Streamlit Community Cloud

1. Push the repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo — set **Main file path** to `app.py`
4. Deploy — no environment variables or secrets required

---

## Data note

All data is **synthetic** and generated programmatically (`data/generate_data.py`).
The dataset covers Jan 2025 – Mar 2026 and reflects realistic patterns:
seasonal cost variation, robot unit overspend in Q3/Q4, and capacity pressure
on robot surgery units.

---

*Built as a portfolio project demonstrating FBP analytics for healthcare.*
