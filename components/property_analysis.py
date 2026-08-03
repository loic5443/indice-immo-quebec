"""Complete property analysis UI with enriched assumptions and deterministic scenarios."""

from dataclasses import asdict

import streamlit as st

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis, validate_inputs
from components.account import current_user, is_authenticated
from components.immoengine import show_immoengine_result
from components.scenarios import show_scenarios
from components.sidebar import go_to
from data.database import save_analysis
from data.database import DATABASE_PATH
from domain.immoengine import PROFILE_WEIGHTS, evaluate_immoengine
from services.market_data_service import market_context_snapshot
from domain.immovalue import SubjectProperty, estimate_immovalue
from services.comparable_csv import csv_template, validate_csv_rows
from services.analysis_workflow import STEPS
from services.entitlements_service import quota_status, consume_estimation
from domain.address import normalize_address,AddressValidationError
from services.address_lookup_service import lookup
from services.quebec_role_importer import search_role_units
from services.quebec_role_admin_service import territory_for_municipality


DEFAULTS = {
    "property_price": 450_000.0, "down_payment": 90_000.0, "mortgage_rate": 4.75,
    "amortization_years": 25, "municipal_taxes": 3_600.0, "school_taxes": 400.0,
    "insurance": 125.0, "condo_fees": 0.0, "rental_income": 2_600.0,
    "other_expenses": 250.0, "household_income": 0.0, "other_debts": 0.0,
    "vacancy_rate": 3.0, "maintenance": 100.0, "management": 0.0,
    "utilities": 0.0, "capital_reserve": 100.0, "initial_repairs": 0.0,
    "acquisition_costs": 0.0, "other_income": 0.0, "rent_growth": 2.0,
    "expense_growth": 2.0, "holding_period": 5,
}


def reset_analysis() -> None:
    st.session_state.update(DEFAULTS)


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def _inputs_from_state() -> PropertyInputs:
    household_income = st.session_state["household_income"] or None
    return PropertyInputs(
        price=st.session_state["property_price"], down_payment=st.session_state["down_payment"],
        annual_interest_rate=st.session_state["mortgage_rate"], amortization_years=st.session_state["amortization_years"],
        municipal_taxes_annual=st.session_state["municipal_taxes"], school_taxes_annual=st.session_state["school_taxes"],
        insurance_monthly=st.session_state["insurance"], condo_fees_monthly=st.session_state["condo_fees"],
        rental_income_monthly=st.session_state["rental_income"], other_expenses_monthly=st.session_state["other_expenses"],
        household_income_annual=household_income, other_debt_payments_monthly=st.session_state["other_debts"],
        vacancy_rate_pct=st.session_state["vacancy_rate"], maintenance_monthly=st.session_state["maintenance"],
        management_monthly=st.session_state["management"], owner_paid_utilities_monthly=st.session_state["utilities"],
        capital_reserve_monthly=st.session_state["capital_reserve"], initial_repairs=st.session_state["initial_repairs"],
        acquisition_costs=st.session_state["acquisition_costs"], other_income_monthly=st.session_state["other_income"],
        rent_growth_annual_pct=st.session_state["rent_growth"], expense_growth_annual_pct=st.session_state["expense_growth"],
        holding_period_years=st.session_state["holding_period"],
    )


def show_property_analysis() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.title("Analyse immobilière")
    with st.expander("Commencer par une adresse", expanded=True):
        street,city,postal,unit=st.columns(4)
        address_error=st.session_state.get("address_error",{})
        with street:
            address_street=st.text_input("Adresse",key="address_street")
            if address_error.get("field")=="street": st.error(address_error["message"])
        with city:
            address_city=st.text_input("Ville",key="address_city")
            if address_error.get("field")=="city": st.error(address_error["message"])
        with postal:
            address_postal=st.text_input("Code postal",key="address_postal")
            if address_error.get("field")=="postal": st.error(address_error["message"])
        with unit:
            address_unit=st.text_input("Appartement / local (facultatif)",key="address_unit")
            if address_error.get("field")=="unit": st.error(address_error["message"])
        consent=st.checkbox("J'accepte qu'ImmoRadar recherche des renseignements publics autorisés pour cette adresse.",key="address_consent")
        if st.button("Rechercher les renseignements disponibles",key="address_lookup"):
            try:
                st.session_state.pop("address_error",None)
                result=lookup(normalize_address(address_street,address_city,address_postal,address_unit),consent);st.session_state["address_lookup_result"]=result;st.info(result["message"])
                if consent:
                    territory=territory_for_municipality(DATABASE_PATH,address_city)
                    st.session_state["role_01023_matches"]=search_role_units(DATABASE_PATH,territory,address_street) if territory else []
                    st.session_state["role_coverage"] = bool(territory)
            except AddressValidationError as error:
                st.session_state["address_error"]={"field":error.field,"message":str(error)};st.rerun()
            except ValueError as error: st.error("Vérifiez les renseignements saisis.")
        st.caption("Adresse saisie et renseignements publics éventuels restent séparés des calculs ImmoValue et ImmoScore.")
    if st.session_state.get("role_coverage") is False:
        st.info("Les données officielles de cette municipalité ne sont pas encore synchronisées. Vous pouvez continuer manuellement.")
    for match in st.session_state.get("role_01023_matches",[]):
        st.info(f"Rôle officiel 01023 — {match['address_text'] or 'adresse partielle'} · valeur totale au rôle : {_money(match['total_value'] or 0)} · rôle {match['role_year']} · référence {match['market_reference_date'] or 'non publiée'}.")
    if st.session_state.get("role_01023_matches"):
        st.caption("Source : MAMH / Données Québec. Valeur au rôle, distincte d’ImmoValue; aucune donnée n’est appliquée automatiquement à vos hypothèses.")
    step = st.session_state.setdefault("analysis_step", 1)
    completed = st.session_state.setdefault("analysis_completed_steps", {1})
    st.progress(step / len(STEPS), text=f"Étape {step}/9 — {STEPS[step-1]}")
    selected = st.selectbox("Étape du parcours", list(range(1, len(STEPS)+1)), index=step-1, format_func=lambda value: f"{value}. {STEPS[value-1]}")
    if selected <= max(completed): st.session_state["analysis_step"] = selected
    st.caption("Les valeurs restent dans le brouillon de cette session; une analyse n'est sauvegardée dans l'historique qu'après votre confirmation.")
    st.write("Saisissez vos hypothèses pour obtenir une analyse financière claire et personnalisée. Les calculs sont reproductibles et présentés avant impôt.")
    with st.expander("Portée de l'analyse"):
        st.write("ImmoRadar fonde ses résultats sur les renseignements et hypothèses fournis. La qualité de l'analyse dépend donc de leur exactitude et de leur exhaustivité.")
    st.button("Réinitialiser l'analyse", on_click=reset_analysis, type="secondary")

    with st.expander("Acquisition et financement", expanded=True):
        acquisition, financing = st.columns(2)
        with acquisition:
            st.number_input("Prix de la propriété ($)", min_value=0.0, step=5_000.0, key="property_price")
            st.number_input("Mise de fonds ($)", min_value=0.0, step=5_000.0, key="down_payment")
            st.number_input("Travaux initiaux ($)", min_value=0.0, step=1_000.0, key="initial_repairs")
            st.number_input("Frais d'acquisition ($)", min_value=0.0, step=1_000.0, key="acquisition_costs")
        with financing:
            st.number_input("Taux hypothécaire annuel (%)", min_value=0.0, max_value=25.0, step=0.05, format="%.2f", key="mortgage_rate")
            st.number_input("Amortissement (années)", min_value=5, max_value=30, step=1, key="amortization_years")
            st.number_input("Revenu brut annuel du ménage ($, facultatif)", min_value=0.0, step=5_000.0, key="household_income")
            st.number_input("Autres dettes mensuelles ($, facultatif)", min_value=0.0, step=100.0, key="other_debts")

    with st.expander("Revenus et dépenses d'exploitation", expanded=True):
        revenue, monthly, annual = st.columns(3)
        with revenue:
            st.number_input("Revenus locatifs mensuels ($)", min_value=0.0, step=100.0, key="rental_income")
            st.number_input("Autres revenus mensuels ($)", min_value=0.0, step=50.0, key="other_income")
            st.number_input("Taux de vacance (%)", min_value=0.0, max_value=100.0, step=0.5, key="vacancy_rate")
        with monthly:
            st.number_input("Assurances mensuelles ($)", min_value=0.0, step=25.0, key="insurance")
            st.number_input("Frais de copropriété mensuels ($)", min_value=0.0, step=25.0, key="condo_fees")
            st.number_input("Entretien courant mensuel ($)", min_value=0.0, step=25.0, key="maintenance")
            st.number_input("Frais de gestion mensuels ($)", min_value=0.0, step=25.0, key="management")
            st.number_input("Services publics mensuels ($)", min_value=0.0, step=25.0, key="utilities")
            st.number_input("Réserve mensuelle dépenses majeures ($)", min_value=0.0, step=25.0, key="capital_reserve")
            st.number_input("Autres dépenses mensuelles ($)", min_value=0.0, step=25.0, key="other_expenses")
        with annual:
            st.number_input("Taxes municipales annuelles ($)", min_value=0.0, step=100.0, key="municipal_taxes")
            st.number_input("Taxes scolaires annuelles ($)", min_value=0.0, step=50.0, key="school_taxes")

    with st.expander("Hypothèses de projection", expanded=False):
        growth, horizon = st.columns(2)
        with growth:
            st.number_input("Croissance annuelle hypothétique des loyers (%)", min_value=-25.0, max_value=25.0, step=0.25, key="rent_growth")
            st.number_input("Croissance annuelle hypothétique des dépenses (%)", min_value=-25.0, max_value=25.0, step=0.25, key="expense_growth")
        with horizon:
            st.number_input("Horizon de détention (années)", min_value=1, max_value=40, step=1, key="holding_period")
        st.caption("Ces projections utilisent uniquement vos taux de croissance déclarés. Elles ne prévoient pas le marché ni la valeur future de la propriété.")

    inputs = _inputs_from_state()
    errors = validate_inputs(inputs)
    if errors:
        for error in errors:
            st.error(error)
        return
    if is_authenticated():
        profile = current_user()["user_type"]
        st.caption(f"Profil ImmoEngine appliqué : {profile} (depuis Mon compte).")
    else:
        profile = st.selectbox("Profil ImmoEngine", list(PROFILE_WEIGHTS), key="analysis_engine_profile")
        st.caption("Créez un compte pour enregistrer votre profil et sauvegarder cette analyse.")
    _show_results(inputs, calculate_analysis(inputs), profile)


def _show_results(inputs: PropertyInputs, result: AnalysisResult, profile: str) -> None:
    st.subheader("Résultats de votre analyse")
    first, second, third = st.columns(3)
    first.metric("Paiement hypothécaire", _money(result.monthly_payment))
    second.metric("Revenus effectifs mensuels", _money(result.effective_rental_income_monthly))
    third.metric("Flux de trésorerie mensuel", _money(result.cash_flow_monthly))
    a, b, c = st.columns(3)
    a.metric("RNE annuel", _money(result.net_operating_income_annual))
    b.metric("Capital réellement investi", _money(result.actual_capital_invested))
    c.metric("Rendement sur capital", f"{result.cash_on_cash_return:.2f} %")
    d, e, f = st.columns(3)
    d.metric("Taux de capitalisation", f"{result.capitalization_rate:.2f} %")
    e.metric("DSCR", f"{result.debt_service_coverage_ratio:.2f}x")
    f.metric("Marge mensuelle de sécurité", _money(result.monthly_safety_margin))
    if result.housing_cost_ratio is not None:
        st.info(f"Ratio déclaré des coûts de logement et autres dettes : {result.housing_cost_ratio:.1f} %. Méthode : (paiement hypothécaire + dépenses d'exploitation + autres dettes) / revenu brut mensuel. Ce n'est pas un critère officiel de prêteur.")
    else:
        st.caption("Abordabilité indisponible : ajoutez le revenu brut annuel du ménage pour calculer le ratio déclaré des coûts de logement.")
    st.caption(f"Projection à {inputs.holding_period_years} ans : flux mensuel hypothétique {_money(result.projected_cash_flow_monthly)}, fondé seulement sur les croissances de loyers et dépenses saisies.")

    engine_result = evaluate_immoengine(inputs, result, profile)
    immovalue = _show_immovalue()
    show_immoengine_result(engine_result)
    scenarios, resilience = show_scenarios(inputs, engine_result.profile)

    st.markdown("<div class='save-analysis-panel'><h3>Sauvegarder cette analyse</h3>", unsafe_allow_html=True)
    if is_authenticated():
        property_name = st.text_input("Nom ou adresse de la propriété", key="saved_property_name", placeholder="Ex. Duplex - Montréal")
        if st.button("Sauvegarder dans Mes analyses", type="primary", key="save_analysis"):
            if not property_name.strip():
                st.error("Veuillez donner un nom ou une adresse à cette analyse.")
            else:
                save_analysis(current_user()["id"], property_name, {
                    "price": inputs.price, "down_payment": inputs.down_payment,
                    "rental_income": inputs.rental_income_monthly, "monthly_expenses": result.total_monthly_expenses,
                    "cash_flow": result.cash_flow_monthly, "cash_on_cash_return": result.cash_on_cash_return,
                    "capitalization_rate": result.capitalization_rate,
                    "debt_service_coverage_ratio": result.debt_service_coverage_ratio,
                    "financial_inputs": asdict(inputs), "scenarios": scenarios, "resilience": resilience,
                    "market_context": market_context_snapshot(str(DATABASE_PATH)),
                    "immovalue": immovalue,
                }, profile=engine_result.profile, engine_result=engine_result)
                st.success("Analyse, scénarios et tests de résistance sauvegardés dans Mes analyses.")
    else:
        st.write("Connectez-vous pour conserver cette analyse, ses scénarios et ses tests de résistance.")
        st.button("Créer un compte ou se connecter", on_click=go_to, args=("Mon compte",), key="save_analysis_login")
    st.markdown("</div>", unsafe_allow_html=True)


def _show_immovalue() -> dict:
    """A local-only workspace; declared comparables stay separate from financial scoring."""
    st.markdown("<div class='section-space'></div><h2>Estimation ImmoValue</h2>", unsafe_allow_html=True)
    st.warning("ImmoValue expérimental — fondé sur les informations et comparables fournis par l'utilisateur. Il ne constitue pas une évaluation officielle.")
    with st.expander("1. Informations sur la propriété et 3. Comparables manuels", expanded=False):
        a, b, c = st.columns(3)
        with a:
            name = st.text_input("Adresse ou nom déclaré", key="iv_name")
            property_type = st.selectbox("Type déclaré", ["", "Maison", "Condo", "Duplex", "Triplex", "Immeuble"], key="iv_type")
            units = st.number_input("Unités déclarées", 0, 20, key="iv_units")
        with b:
            living_area = st.number_input("Superficie habitable déclarée", 0.0, key="iv_area")
            land_area = st.number_input("Terrain déclaré", 0.0, key="iv_land")
            year = st.number_input("Année de construction déclarée", 0, 2100, key="iv_year")
        with c:
            asking = st.number_input("Prix demandé facultatif", 0.0, key="iv_asking")
            st.text_area("Rénovations et notes déclarées", key="iv_notes")
        st.caption("Tous les renseignements ci-dessus sont déclarés par l'utilisateur et non vérifiés.")
        st.download_button("Télécharger le modèle CSV", csv_template(), "comparables-immoradar.csv", "text/csv")
        uploaded = st.file_uploader("Importer un CSV local (jamais transmis à un service externe)", type="csv", key="comparables_csv")
        sales_confirmed = st.checkbox("Je confirme que les lignes représentent des ventes conclues", key="csv_sales_confirmed")
        import_rights = st.checkbox("Je confirme mon droit d'utilisation pour ce fichier", key="csv_import_rights")
        if uploaded:
            valid_rows, row_errors = validate_csv_rows(uploaded.getvalue().decode("utf-8-sig", errors="replace"), import_rights, sales_confirmed)
            st.caption(f"Prévisualisation locale : {len(valid_rows)} ligne(s) valide(s), {len(row_errors)} erreur(s).")
            if valid_rows: st.dataframe(valid_rows, hide_index=True, width="stretch")
            for error in row_errors: st.error(f"Ligne {error['line']} : {error['error']}")
            if st.button("Importer les lignes valides", disabled=not valid_rows, key="confirm_csv_import"):
                st.session_state["iv_csv_comparables"] = valid_rows; st.success("Lignes valides importées localement.")
            if st.button("Annuler l'import", key="cancel_csv_import"):
                st.session_state.pop("iv_csv_comparables", None); st.info("Import annulé sans sauvegarde.")
        comparables=list(st.session_state.get("iv_csv_comparables", []))
        for index in range(3):
            st.markdown(f"**Comparable {index + 1}**")
            x, y, z = st.columns(3)
            with x:
                address=st.text_input("Adresse ou identifiant", key=f"iv_address_{index}")
                sale_price=st.number_input("Prix de vente", 0.0, key=f"iv_price_{index}")
                area=st.number_input("Superficie", 0.0, key=f"iv_carea_{index}")
            with y:
                ctype=st.selectbox("Type", ["", "Maison", "Condo", "Duplex", "Triplex", "Immeuble"], key=f"iv_ctype_{index}")
                distance=st.number_input("Distance approximative (km)", 0.0, key=f"iv_distance_{index}")
                c_units=st.number_input("Unités", 0, 20, key=f"iv_cunits_{index}")
            with z:
                source=st.text_input("Source déclarée", key=f"iv_source_{index}")
                closed=st.checkbox("Vente conclue déclarée (pas une annonce active)", key=f"iv_closed_{index}")
                rights=st.checkbox("Je confirme disposer du droit d'utilisation", key=f"iv_rights_{index}")
            comparables.append({"address": address, "sale_date": "2026-01-01", "sale_price": sale_price, "living_area": area, "property_type": ctype, "units": c_units, "distance_km": distance, "source_declared": source, "declared_closed_sale": closed, "usage_right_confirmed": rights})
    subject=SubjectProperty(name=name, property_type=property_type, units=units or None, living_area=living_area or None, land_area=land_area or None, year_built=year or None, asking_price=asking or None, notes=st.session_state.get("iv_notes", ""))
    draft_key = f"immovalue:{hash((subject.name, subject.living_area, tuple(str(item) for item in comparables)))}"
    estimate = st.session_state.get("immovalue_generated_result")
    if is_authenticated():
        user=current_user(); quota=quota_status(user["id"],user,DATABASE_PATH)
        st.caption(quota["label"] + (" · Le quota est désactivé pendant la bêta." if not _quota_enforced() else ""))
        if st.button("Produire l'estimation ImmoValue", type="primary", key="generate_immovalue"):
            candidate=estimate_immovalue(subject, comparables)
            if not candidate["available"]:
                st.info("Estimation indisponible : ajoutez au moins trois comparables admissibles.")
            elif not _quota_enforced() or consume_estimation(user["id"],user,DATABASE_PATH,draft_key):
                st.session_state["immovalue_generated_result"]=candidate;estimate=candidate;st.success("Estimation produite.")
            else:
                st.warning("Votre estimation gratuite du mois est utilisée. L'analyse financière reste disponible.")
                st.button("Découvrir Premium",on_click=go_to,args=("Premium",))
    else:
        estimate=estimate_immovalue(subject, comparables)
    if estimate["available"]:
        one, two, three = st.columns(3); one.metric("Valeur expérimentale", f"{estimate['estimated_value']:,.0f} $".replace(',', ' ')); two.metric("Fourchette prudente", f"{estimate['low']:,.0f} $ à {estimate['high']:,.0f} $".replace(',', ' ')); three.metric("Confiance ImmoValue", f"{estimate['confidence']} / 100")
        st.caption(f"{estimate['used_count']} comparables utilisés · dispersion {estimate['dispersion_pct']} % · {estimate['method']}")
        if estimate["asking_comparison"]: st.info(f"Prix demandé : {estimate['asking_comparison']} (écart indicatif {estimate['asking_gap']:,.0f} $).")
    else: st.info("Aucune estimation : ajoutez au moins trois comparables admissibles et la superficie du sujet.")
    if estimate["comparables"]:
        st.dataframe([{"Comparable": item.get("address") or "Non renseigné", "Statut": item["status"], "Similarité": f"{item['similarity']:.0f} / 100", "Raison": item["reason"]} for item in estimate["comparables"]], hide_index=True, width="stretch")
    st.caption("ImmoValue est séparé d'ImmoScore : cette estimation n'influence pas le score financier et décisionnel.")
    return estimate


def _quota_enforced() -> bool:
    from repositories.sqlite_repository import SQLiteRepository
    with SQLiteRepository(DATABASE_PATH)._connect() as connection:
        row=connection.execute("SELECT quota_enforced FROM beta_settings WHERE id=1").fetchone()
    return bool(row and row[0])
