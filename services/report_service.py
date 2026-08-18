"""Static French PDF reports generated from one saved analysis snapshot.

PDF access is intentionally enabled for free accounts during development.  A
future entitlement layer may make it Premium without changing this generator.
"""

from __future__ import annotations

import json
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#10233F")
BLUE = colors.HexColor("#2563EB")
MUTED = colors.HexColor("#667085")
LIGHT = colors.HexColor("#EAF1FF")


def generate_report_pdf(analysis: dict[str, Any]) -> bytes:
    """Create a Letter-size PDF using only the saved analysis snapshot."""
    font_name = _register_font()
    styles = _styles(font_name)
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream, pagesize=LETTER, rightMargin=0.58 * inch, leftMargin=0.58 * inch,
        topMargin=0.62 * inch, bottomMargin=0.58 * inch,
    )
    inputs = _json(analysis.get("financial_inputs_json"), {})
    scenarios = _json(analysis.get("scenarios_json"), [])
    resilience = _json(analysis.get("resilience_json"), {})
    dimensions = _json(analysis.get("immodna_json"), {})
    positives = _json(analysis.get("positive_factors_json"), [])
    negatives = _json(analysis.get("negative_factors_json"), [])
    missing = _json(analysis.get("missing_data_json"), [])
    checks = _json(analysis.get("recommended_checks_json"), [])
    market_context = _json(analysis.get("market_context_json"), [])
    immovalue = _json(analysis.get("immovalue_json"), {})
    story = []

    story += [Spacer(1, 1.4 * inch), Paragraph("IMMORADAR", styles["cover_brand"]),
              Paragraph("Rapport d'analyse immobilière", styles["cover_title"]), Spacer(1, 0.25 * inch),
              Paragraph(escape(str(analysis.get("property_name", "Analyse immobilière"))), styles["cover_property"]),
              Spacer(1, 0.18 * inch), Paragraph(f"Analyse sauvegardée le {escape(str(analysis.get('created_at', '')))}", styles["center"]),
              Spacer(1, 1.45 * inch), Paragraph("Fondé exclusivement sur les hypothèses saisies et les calculs déterministes ImmoRadar.", styles["center"]),
              Paragraph("Aucune valeur marchande, donnée de comparables ou donnée de ville simulée n'est utilisée dans ce rapport.", styles["center"]), PageBreak()]

    story += _heading("1. Résumé exécutif", styles)
    summary = [
        ["Profil", analysis.get("user_profile", "Non renseigné")],
        ["Score ImmoRadar", _score(analysis.get("immo_score"))],
        ["Indice de confiance", _score(analysis.get("confidence_index"))],
        ["Verdict", analysis.get("engine_verdict") or "Données insuffisantes"],
        ["Résistance", resilience.get("status", "Non calculée")],
    ]
    story += [_table(summary, styles, [1.75 * inch, 5.0 * inch]), Spacer(1, 0.18 * inch),
              Paragraph("La confiance mesure la complétude et la qualité des hypothèses, et non la probabilité qu'une propriété soit un bon achat.", styles["note"])]
    story += _heading("2. Hypothèses", styles)
    story += [_table(_input_rows(inputs), styles, [3.3 * inch, 3.45 * inch])]
    story += _heading("3. Résultats financiers", styles)
    financial_rows = [
        ["Revenus locatifs bruts mensuels", _money(inputs.get("rental_income_monthly", analysis.get("rental_income", 0)) + inputs.get("other_income_monthly", 0))],
        ["Revenus effectifs mensuels", _effective_income(inputs)],
        ["Dépenses mensuelles totales", _money(analysis.get("monthly_expenses", 0))],
        ["RNE annuel", _money(_noi(inputs, analysis))],
        ["Flux de trésorerie mensuel", _money(analysis.get("cash_flow", 0))],
        ["Capital réellement investi", _money(inputs.get("down_payment", analysis.get("down_payment", 0)) + inputs.get("initial_repairs", 0) + inputs.get("acquisition_costs", 0))],
        ["Rendement sur capital investi", _percent(analysis.get("cash_on_cash_return"))],
        ["Taux de capitalisation", _percent(analysis.get("capitalization_rate"))],
        ["DSCR", _ratio(analysis.get("debt_service_coverage_ratio"))],
    ]
    story += [_table(financial_rows, styles, [3.3 * inch, 3.45 * inch]), PageBreak()]

    story += _heading("4. Score ImmoRadar et ImmoDNA", styles)
    story += [_table(_dimension_rows(dimensions), styles, [3.25 * inch, 0.95 * inch, 2.55 * inch])]
    story += _heading("5. Facteurs et données manquantes", styles)
    story += _list_section("Facteurs positifs", positives, styles)
    story += _list_section("Points à surveiller", negatives, styles)
    story += _list_section("Données manquantes", missing, styles)
    story += _heading("6. Scénarios « Et si? »", styles)
    story += [_table(_scenario_rows(scenarios), styles, [1.2 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.15 * inch, 1.4 * inch]), PageBreak()]

    story += _heading("7. Tests de résistance", styles)
    story += [Paragraph("Seuils : résistant si chaque test garde un flux mensuel >= 0 $ et un DSCR >= 1,10x; sensible si le test combiné garde un flux >= 0 $ et un DSCR >= 1,00x; fragile autrement.", styles["note"]),
              _table(_resilience_rows(resilience), styles, [2.2 * inch, 1.4 * inch, 1.0 * inch, 2.15 * inch])]
    story += _heading("8. Prochaines vérifications recommandées", styles)
    story += _list_section("À vérifier", checks, styles)
    story += _heading("9. Méthodologie, sources et limites", styles)
    story += [Paragraph("Les revenus effectifs appliquent le taux de vacance aux loyers; le RNE exclut le service de la dette; le paiement suit la convention hypothécaire canadienne de composition semestrielle. Les projections utilisent uniquement les taux de croissance saisis.", styles["body"]),
              Paragraph(f"Version du moteur : {escape(str(analysis.get('engine_version', 'Non renseignée')))}<br/>Provenance : {escape(str(analysis.get('data_provenance', 'Hypothèses utilisateur et calculs déterministes.')))}", styles["body"]),
              Paragraph(_market_context_text(market_context), styles["note"]),
              Spacer(1, 0.12 * inch), Paragraph("Avertissement : ce rapport est indicatif. Il ne constitue ni une évaluation officielle ni un conseil financier, juridique, fiscal ou immobilier. Faites vérifier les renseignements importants par des professionnels qualifiés avant une décision.", styles["warning"])]
    if immovalue:
        story += _heading("10. ImmoValue expérimental", styles)
        if immovalue.get("available"):
            story += [_table([["Valeur expérimentale", _money(immovalue.get("estimated_value", 0))], ["Fourchette", f"{_money(immovalue.get('low', 0))} à {_money(immovalue.get('high', 0))}"], ["Confiance", _score(immovalue.get("confidence"))]], styles, [2.2 * inch, 4.55 * inch])]
        else:
            story += [Paragraph("Aucune estimation ImmoValue disponible : au moins trois comparables admissibles sont requis.", styles["note"])]
        story += [Paragraph("ImmoValue expérimental est fondé sur les comparables déclarés par l'utilisateur; il ne constitue pas une évaluation officielle.", styles["warning"])]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return stream.getvalue()


def generate_comparison_report_pdf(comparison: dict[str, Any]) -> bytes:
    """Create a Premium report from two already-authorized saved snapshots only."""
    font_name = _register_font()
    styles = _styles(font_name)
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream, pagesize=LETTER, rightMargin=0.58 * inch, leftMargin=0.58 * inch,
        topMargin=0.62 * inch, bottomMargin=0.58 * inch,
    )
    first, second = comparison["a"], comparison["b"]
    story = [
        Spacer(1, 1.15 * inch), Paragraph("IMMORADAR", styles["cover_brand"]),
        Paragraph("Rapport comparatif de propriétés", styles["cover_title"]), Spacer(1, 0.26 * inch),
        Paragraph(escape(str(first.get("name", "Propriété A"))), styles["cover_property"]),
        Paragraph("et", styles["center"]),
        Paragraph(escape(str(second.get("name", "Propriété B"))), styles["cover_property"]),
        Spacer(1, 0.32 * inch),
        Paragraph("Fondé exclusivement sur deux instantanés sauvegardés de votre espace. Aucun calcul n'est refait.", styles["center"]),
        Paragraph("Ce rapport ne constitue ni une recommandation d'achat ni une évaluation officielle.", styles["center"]),
        PageBreak(),
    ]
    story += _heading("1. Vue d'ensemble", styles)
    story += [_table([
        ["", "Propriété A", "Propriété B"],
        ["Dossier", first.get("name", "Non disponible"), second.get("name", "Non disponible")],
        ["Date de l'analyse", first.get("date", "Non disponible"), second.get("date", "Non disponible")],
        ["Profil sauvegardé", first.get("profile", "Non disponible"), second.get("profile", "Non disponible")],
        ["Version ImmoEngine", first.get("engine_version", "Non disponible"), second.get("engine_version", "Non disponible")],
    ], styles, [1.5 * inch, 2.62 * inch, 2.62 * inch])]
    story += [Spacer(1, 0.15 * inch), Paragraph(escape(comparison["conclusion"]), styles["note"])]
    if comparison.get("engine_versions_differ"):
        story += [Paragraph("Les versions ImmoEngine diffèrent : les données sont comparées telles qu'elles ont été sauvegardées.", styles["warning"])]

    story += _heading("2. Indicateurs comparés", styles)
    indicator_rows = [["Indicateur", "Propriété A", "Propriété B", "Lecture"]]
    for item in comparison.get("indicators", []):
        indicator_rows.append([
            item.get("label", "Indicateur"), _comparison_value(item.get("key", ""), item.get("a")),
            _comparison_value(item.get("key", ""), item.get("b")), _comparison_relation(item.get("relation")),
        ])
    story += [_table(indicator_rows, styles, [2.0 * inch, 1.55 * inch, 1.55 * inch, 1.65 * inch]), PageBreak()]

    story += _heading("3. Scénarios sauvegardés", styles)
    scenario_rows = [["Scénario", "Propriété A", "Propriété B"]]
    for scenario in comparison.get("scenarios", {}).values():
        scenario_rows.append([
            scenario.get("label", "Scénario"), _comparison_value("cash_flow", scenario.get("a")),
            _comparison_value("cash_flow", scenario.get("b")),
        ])
    story += [_table(scenario_rows, styles, [2.5 * inch, 2.13 * inch, 2.13 * inch])]

    story += _heading("4. Ce qui distingue chaque propriété", styles)
    for key, title in (("a", "Propriété A"), ("b", "Propriété B")):
        story += _list_section(title + " - points d'alignement", comparison.get("strengths", {}).get(key, []), styles)
        story += _list_section(title + " - à vérifier", comparison.get("checks", {}).get(key, []), styles)

    story += _heading("5. Sources et limites", styles)
    story += [
        Paragraph("La valeur municipale, lorsqu'elle est disponible, est un repère fiscal et non une valeur marchande. ImmoValue reste une estimation expérimentale issue de comparables déclarés. ImmoScore et la confiance décrivent les hypothèses et leur complétude; ils ne garantissent pas une décision.", styles["body"]),
        Paragraph("Le rapport lit uniquement les instantanés sélectionnés dans le compte connecté. Il n'inclut aucun dossier d'un autre utilisateur et ne transmet aucune donnée à un service externe.", styles["note"]),
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return stream.getvalue()


def _register_font() -> str:
    """Use a standard PDF font with reliable Western French character support."""
    return "Helvetica"


def _styles(font: str):
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=font, fontSize=9.2, leading=13, textColor=NAVY),
        "heading": ParagraphStyle("heading", parent=base["Heading2"], fontName=font, fontSize=15, leading=18, textColor=NAVY, spaceBefore=12, spaceAfter=7),
        "note": ParagraphStyle("note", parent=base["BodyText"], fontName=font, fontSize=8.5, leading=11.5, textColor=MUTED),
        "warning": ParagraphStyle("warning", parent=base["BodyText"], fontName=font, fontSize=8.5, leading=12, textColor=NAVY, backColor=LIGHT, borderPadding=8),
        "cover_brand": ParagraphStyle("cover_brand", fontName=font, fontSize=16, leading=20, alignment=TA_CENTER, textColor=BLUE),
        "cover_title": ParagraphStyle("cover_title", fontName=font, fontSize=27, leading=32, alignment=TA_CENTER, textColor=NAVY),
        "cover_property": ParagraphStyle("cover_property", fontName=font, fontSize=16, leading=20, alignment=TA_CENTER, textColor=NAVY),
        "center": ParagraphStyle("center", fontName=font, fontSize=9, leading=13, alignment=TA_CENTER, textColor=MUTED),
        "table": ParagraphStyle("table", fontName=font, fontSize=8.2, leading=10.5, textColor=NAVY),
    }


def _heading(text, styles): return [Paragraph(text, styles["heading"])]


def _table(rows, styles, widths):
    formatted = [[Paragraph(escape(str(cell)), styles["table"]) for cell in row] for row in rows]
    table = Table(formatted, colWidths=widths, repeatRows=1 if rows and len(rows[0]) > 2 else 0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT if len(rows[0]) > 2 else colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DCE4EF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _list_section(title, items, styles):
    rows = [Paragraph(f"<b>{escape(title)}</b>", styles["body"])]
    if items:
        rows.extend(Paragraph("- " + escape(str(item)), styles["body"]) for item in items)
    else:
        rows.append(Paragraph("- Aucun élément disponible.", styles["note"]))
    rows.append(Spacer(1, 0.07 * inch))
    return rows


def _input_rows(inputs):
    return [[label, value] for label, value in [
        ("Prix / mise de fonds", f"{_money(inputs.get('price', 0))} / {_money(inputs.get('down_payment', 0))}"),
        ("Taux / amortissement", f"{inputs.get('annual_interest_rate', 0):.2f} % / {inputs.get('amortization_years', 0)} ans"),
        ("Vacance / horizon", f"{inputs.get('vacancy_rate_pct', 0):.1f} % / {inputs.get('holding_period_years', 0)} ans"),
        ("Croissance loyers / dépenses", f"{inputs.get('rent_growth_annual_pct', 0):.2f} % / {inputs.get('expense_growth_annual_pct', 0):.2f} %"),
        ("Travaux / frais d'acquisition", f"{_money(inputs.get('initial_repairs', 0))} / {_money(inputs.get('acquisition_costs', 0))}"),
    ]]


def _dimension_rows(dimensions):
    rows = [["Dimension", "Note", "État"]]
    for item in dimensions.values():
        rows.append([item.get("label", "Dimension"), _score(item.get("score")), "Disponible" if item.get("available") else "Données insuffisantes"])
    return rows


def _scenario_rows(scenarios):
    rows = [["Scénario", "Paiement", "RNE", "Flux", "Score", "Verdict"]]
    for item in scenarios:
        financial, engine = item.get("financial", {}), item.get("engine", {})
        rows.append([item.get("name", ""), _money(financial.get("monthly_payment", 0)), _money(financial.get("net_operating_income_annual", 0)), _money(financial.get("cash_flow_monthly", 0)), _score(engine.get("score")), engine.get("verdict", "")])
    return rows


def _resilience_rows(resilience):
    rows = [["Test", "Flux mensuel", "DSCR", "Verdict"]]
    for item in resilience.get("tests", []):
        financial, engine = item.get("financial", {}), item.get("engine", {})
        rows.append([item.get("name", ""), _money(financial.get("cash_flow_monthly", 0)), _ratio(financial.get("debt_service_coverage_ratio")), engine.get("verdict", "")])
    return rows


def _effective_income(inputs):
    return _money(inputs.get("rental_income_monthly", 0) * (1 - inputs.get("vacancy_rate_pct", 0) / 100) + inputs.get("other_income_monthly", 0))


def _noi(inputs, analysis):
    return float(analysis.get("capitalization_rate", 0) or 0) / 100 * float(analysis.get("price", inputs.get("price", 0)) or 0)


def _json(value, default):
    try: return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError): return default


def _market_context_text(context):
    if not context:
        return "Aucun indicateur externe officiel n'était disponible dans le contexte sauvegardé."
    return "Contexte externe observé (informatif, sans effet sur le score) : " + "; ".join(
        f"{item.get('metric')} {item.get('value')} {item.get('unit')} — observé le {item.get('observed_at')} — {item.get('source_url')}"
        for item in context
    )


def _comparison_value(key: str, value: Any) -> str:
    if value is None:
        return "Non disponible"
    if key in {"cash_on_cash_return", "capitalization_rate"}:
        return f"{float(value):.2f} %"
    if key == "dscr":
        return f"{float(value):.2f}x"
    if key in {"score", "confidence", "immovalue_confidence"}:
        return f"{float(value):.0f} / 100"
    return _money(value)


def _comparison_relation(relation: str | None) -> str:
    return {
        "avantage_a": "Avantage A",
        "avantage_b": "Avantage B",
        "égalité": "Équivalent",
        "non_comparable": "Non comparable",
    }.get(relation, "Non comparable")


def _money(value): return f"{float(value):,.0f} $".replace(",", " ")
def _percent(value): return f"{float(value or 0):.2f} %"
def _ratio(value): return f"{float(value or 0):.2f}x"
def _score(value): return f"{float(value):.0f} / 100" if value is not None else "Indisponible"


def _footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DCE4EF"))
    canvas.line(document.leftMargin, 0.45 * inch, LETTER[0] - document.rightMargin, 0.45 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 0.29 * inch, "ImmoRadar - Analyse indicative")
    canvas.drawRightString(LETTER[0] - document.rightMargin, 0.29 * inch, f"Page {document.page}")
    canvas.restoreState()
