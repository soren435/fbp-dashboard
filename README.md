# Finance Business Partner Dashboard

An interactive dashboard built for hospital finance departments, demonstrating core FBP competencies: budget control, activity-based costing, capacity management, and forecasting.

**Live demo:** *(add link after deployment)*

---

## Features

| Module | Description |
|--------|-------------|
| **Budget vs. Faktisk** | Monthly/department/category variance analysis with color-coded deviation table |
| **Aktivitetsbaseret Kostpris** | Cost per operation type (Robot surgery, Laparoscopy, Open surgery, Outpatient) broken down by resource |
| **Kapacitetsudnyttelse** | OR room and robot unit utilization heatmap with overbooked/underutilized highlighting |
| **Forecast** | Rolling 12-month linear trend with confidence interval |
| **AI Afvigelsesforklaring** | Automated Danish-language variance commentary identifying top cost drivers |

## Tech Stack

- **Python** + **pandas** — data processing
- **Streamlit** — dashboard framework
- **Plotly** — interactive charts
- Simulated dataset: 15 months of hospital surgical department data (Jan 2025 – Mar 2026)

## Run locally

```bash
git clone https://github.com/<your-username>/fbp-dashboard.git
cd fbp-dashboard
pip install -r requirements.txt
streamlit run app.py
```

App opens at `http://localhost:8501`

## Project context

Built to demonstrate Finance Business Partner skills in a healthcare setting:
- Variance analysis and budget accountability
- Activity-based costing for surgical procedures
- Capacity planning for OR rooms and robot surgery units
- Forward-looking forecasting for budget cycles

## Screenshots

*(add screenshots here)*

---

*Data is synthetic and does not represent any real hospital or patient information.*
