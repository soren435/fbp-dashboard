"""Template-based Danish variance commentary.

Rules-driven — no external API or LLM calls.
"""

import pandas as pd
from src.kpi import detailed_variance, dept_variance

# ── Known context from data generation ────────────────────────────────────────
_ROBOT_EXTRA_SESSIONS = 8
_Q3 = "juli–september"

# Templates indexed by (afdeling, kategori)
_TEMPLATES: dict[tuple[str, str], str] = {
    ("Robotenhed", "Udstyr"): (
        "Uplanlagt vedligeholdelse af robotsystem (Da Vinci) i {q3} medførte "
        "ekstraomkostninger til reservedele og servicekontrakt (DKK {abs_var:,.0f}, {pct:+.1f}%)."
    ),
    ("Robotenhed", "Personale"): (
        "{extra} ekstra robotkirurgi-sessioner i {q3} pga. venteliste-reducering "
        "krævede overarbejde og ekstra vagtdækning (DKK {abs_var:,.0f}, {pct:+.1f}%)."
    ),
    ("Robotenhed", "Forbrug"): (
        "Øget forbrugsmateriel (sterile kapper, instrumenter) relateret til "
        "{extra} ekstra robotkirurgi-sessioner i {q3} (DKK {abs_var:,.0f})."
    ),
    ("Kirurgi", "Personale"): (
        "Højere case-mix i efteråret med tunge elektive indgreb øgede behovet "
        "for specialiseret personale og forlængede operationstider "
        "(DKK {abs_var:,.0f}, {pct:+.1f}%)."
    ),
    ("Kirurgi", "Udstyr"): (
        "Indkøb af nyt laparoskopisk udstyr fremrykket til Q3 for at imødekomme "
        "kapacitetsbehov (DKK {abs_var:,.0f})."
    ),
    ("Anæstesi", "Personale"): (
        "Sommerferieafvikling i august reducerede forbruget markant — "
        "planlagt underforbrug (DKK {abs_var:,.0f} under budget)."
    ),
    ("Sterilcentral", "Personale"): (
        "Effektiviseringer i sterilisationsflow og færre akutte rengøringsbehov "
        "bidrog til mindreforbrug (DKK {abs_var:,.0f} under budget)."
    ),
}

_DEFAULT_OVER = (
    "Højere aktivitetsniveau end planlagt medførte overskridelse på "
    "DKK {abs_var:,.0f} ({pct:+.1f}%)."
)
_DEFAULT_UNDER = (
    "Lavere aktivitetsniveau end forventet — evt. planlagte effektiviseringer "
    "(DKK {abs_var:,.0f} under budget, {pct:+.1f}%)."
)


def _render(template: str, row: pd.Series) -> str:
    return template.format(
        q3=_Q3,
        extra=_ROBOT_EXTRA_SESSIONS,
        abs_var=abs(row["var_dkk"]),
        pct=row["var_pct"],
    )


def generate_detail_commentary(
    budget: pd.DataFrame,
    actuals: pd.DataFrame,
    top_n: int = 3,
) -> str:
    """Return markdown with top-N variance explanations (dept × category level)."""
    detail = detailed_variance(budget, actuals)
    top = detail.head(top_n)

    lines = []
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        dept, cat = row["afdeling"], row["kategori"]
        var = row["var_dkk"]
        icon = "⚠️" if var > 0 else "✅"
        sign = "+" if var > 0 else ""

        tmpl = _TEMPLATES.get((dept, cat))
        reason = _render(tmpl, row) if tmpl else (
            _render(_DEFAULT_OVER, row) if var > 0 else _render(_DEFAULT_UNDER, row)
        )

        lines.append(
            f"{icon} **{rank}. {dept} – {cat}** "
            f"({sign}DKK {abs(var):,.0f} / {row['var_pct']:+.1f}%)\n"
            f"   {reason}"
        )

    return "\n\n".join(lines)


def generate_total_commentary(
    budget: pd.DataFrame,
    actuals: pd.DataFrame,
    period_label: str = "",
) -> str:
    """One-sentence overall summary suitable for executive dashboards."""
    total_b = budget["budget_dkk"].sum()
    total_a = actuals["faktisk_dkk"].sum()
    var = total_a - total_b
    pct = var / total_b * 100 if total_b else 0

    period = f" ({period_label})" if period_label else ""
    direction = "over" if var > 0 else "under"
    icon = "🔴" if pct > 5 else ("🟡" if 2 < pct <= 5 else ("🟢" if pct <= 0 else "🟡"))

    return (
        f"{icon} Samlet forbrug{period} er **DKK {abs(var):,.0f} {direction} budget** "
        f"({pct:+.1f}%)."
    )


def generate_dept_commentary(budget: pd.DataFrame, actuals: pd.DataFrame) -> list[str]:
    """One-sentence commentary per department."""
    dv = dept_variance(budget, actuals)
    lines = []
    for _, row in dv.iterrows():
        dept = row["afdeling"]
        pct = row["afvigelse_pct"]
        var = row["afvigelse_dkk"]
        direction = "over" if var > 0 else "under"
        icon = "🔴" if pct > 5 else ("🟡" if 2 < pct <= 5 else ("🟢" if pct <= 0 else "🟡"))
        lines.append(
            f"{icon} **{dept}** ligger DKK {abs(var):,.0f} {direction} budget ({pct:+.1f}%)."
        )
    return lines


def generate_recommendation(budget: pd.DataFrame, actuals: pd.DataFrame) -> str:
    """Short Danish leadership recommendation based on overall variance and drivers."""
    total_b = budget["budget_dkk"].sum()
    total_a = actuals["faktisk_dkk"].sum()
    pct = (total_a - total_b) / total_b * 100 if total_b else 0

    detail = detailed_variance(budget, actuals)
    robot_over = (
        detail[(detail["afdeling"] == "Robotenhed") & (detail["var_dkk"] > 0)][
            "var_dkk"
        ].sum()
    )

    if pct > 5:
        return (
            "**Anbefaling:** Igangsæt korrigerende tiltag i Robotenhed. "
            f"Enheden tegner sig for en betydelig del af det samlede merforbrug "
            f"(DKK {robot_over:,.0f}). Vurder om de ekstra sessioner kan dækkes "
            "af aktivitetsindtægter eller kræver budgetrevision."
        )
    elif pct > 2:
        return (
            "**Anbefaling:** Monitorer Robotenhed tæt i kommende kvartal. "
            "Generelt under kontrol, men presset på kapacitet og udstyr bør "
            "adresseres proaktivt inden næste budgetperiode."
        )
    elif pct < -2:
        return (
            "**Anbefaling:** Positiv budgetstatus. "
            "Gennemgå om mindreforbruget er permanent og juster forecast. "
            "Overvej om uudnyttede midler kan geninvesteres i kapacitetsudvidelse."
        )
    else:
        return (
            "**Anbefaling:** Budgettet følges planmæssigt. "
            "Oprethold nuværende monitorering og fokus på robotkapacitet i Q3/Q4."
        )
