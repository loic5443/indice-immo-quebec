"""Premium buy-box: transparent thresholds and missing data, no made-up deals."""
import streamlit as st

from components.premium_teaser import show_premium_teaser
from domain.investment_criteria import CRITERIA, screen_snapshot
from services.entitlements_service import can_use
from services.investment_criteria_service import CriteriaAccessError, get_criteria, save_criteria, price_ceiling_for_snapshot
from services.snapshot_history_service import snapshot_positions


LABELS = {"matches": "Correspond à vos critères", "outside": "Hors de vos critères",
          "incomplete": "Données à compléter", "not_configured": "Critères non définis"}


def show_investment_criteria(user, analyses, database_path):
    st.markdown("### Vos critères d’achat")
    st.caption("Repérez les dossiers qui respectent vos seuils. Les chiffres restent ceux de vos instantanés sauvegardés.")
    if not can_use(user, "investment_criteria"):
        show_premium_teaser(feature="Critères d’achat personnalisés", title="Triez selon vos objectifs.",
                           detail="Prix, flux mensuel, couverture de dette et scénario prudent : Premium compare chaque dossier à vos propres seuils.",
                           key="criteria_premium")
        return {}
    try:
        criteria = get_criteria(user["id"], database_path)
    except CriteriaAccessError:
        st.info("Actualisez votre compte pour retrouver vos droits Premium.")
        return {}
    with st.expander("Définir mes seuils", expanded=not bool(criteria)):
        st.caption("Activez uniquement les critères utiles à votre projet. Les seuils proposés dans les champs sont des exemples modifiables.")
        with st.form(f"investment_criteria_{user['id']}"):
            chosen = {}
            for key, (label, metric, operator, unit, lower, upper) in CRITERIA.items():
                toggle, field = st.columns([1, 3])
                enabled = toggle.checkbox("Activer", value=key in criteria, key=f"criterion_enabled_{user['id']}_{key}")
                example = 1.1 if key == "min_dscr" else 500_000.0 if key == "max_price" else 0.0
                value = field.number_input(f"{label} ({unit})", min_value=float(lower), max_value=float(upper),
                                           value=float(criteria.get(key, example)), step=0.1 if unit == "x" else 1.0,
                                           key=f"criterion_value_{user['id']}_{key}")
                if enabled:
                    chosen[key] = value
            if st.form_submit_button("Enregistrer mes critères", type="primary", width="stretch"):
                save_criteria(user["id"], chosen, database_path)
                criteria = chosen
                st.success("Critères enregistrés. Vos analyses sauvegardées restent inchangées.")
    if not criteria:
        st.info("Choisissez vos seuils pour voir quels dossiers correspondent à votre projet.")
        return {}
    positions = snapshot_positions(analyses)
    latest = [analysis for analysis in analyses if not positions.get(int(analysis["id"])) or positions[int(analysis["id"])].is_latest]
    results = {int(analysis["id"]): {**screen_snapshot(analysis, criteria), "price_ceiling": price_ceiling_for_snapshot(analysis, criteria)} for analysis in analyses}
    rows = [{"Dossier": analysis["property_name"], "Résultat": LABELS[results[int(analysis["id"])] ["status"]],
             "Critères atteints": f"{results[int(analysis['id'])]['matched']} / {len(criteria)}",
             "Données manquantes": results[int(analysis["id"])]["missing"]} for analysis in latest]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Le tableau présente le dernier instantané de chaque dossier, sans compter deux fois ses anciennes versions. Un critère manquant ne devient jamais une réussite.")
    return results


def show_screening_details(result):
    st.markdown("**Vos critères d’achat : " + LABELS[result["status"]] + "**")
    rows = []
    for row in result["rows"]:
        value = "Non disponible" if row["value"] is None else f"{row['value']:,.2f} {row['unit']}".replace(",", " ")
        rows.append({"Critère": row["label"], "Instantané": value,
                     "Votre seuil": ("≤ " if row["operator"] == "max" else "≥ ") + f"{row['threshold']:,.2f} {row['unit']}".replace(",", " "),
                     "Résultat": "À compléter" if row["meets"] is None else "Atteint" if row["meets"] else "Non atteint"})
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption(result["note"])

    ceiling = result.get("price_ceiling") or {}
    if ceiling.get("status") == "available":
        st.metric("Plafond de prix selon vos hypothèses fixes", f"{ceiling['price']:,.0f} $".replace(",", " "))
        st.caption("Seuil déterminant : " + ceiling["binding_criterion"])
        st.caption(ceiling["note"])
    elif ceiling.get("reason"):
        st.caption(ceiling["reason"])
