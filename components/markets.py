"""Municipal comparisons based only on loaded official datasets."""
import streamlit as st
from data.database import DATABASE_PATH
from services.municipal_comparison_service import municipalities,comparison,selection_options

LABELS={"population":("Population","habitants","Indique la taille démographique; elle ne mesure pas la demande immobilière."),"uniformized_residential_assessment_average":("Valeur foncière moyenne uniformisée résidentielle","$","Repère fiscal officiel; ce n’est pas le prix moyen des ventes actuelles."),"uniformized_property_wealth":("Richesse foncière uniformisée","$","Indicateur municipal global; il ne prédit pas une valeur de propriété."),"uniformized_property_wealth_per_unit":("RFU par unité","$ par unité","Repère de fiscalité municipale; il ne mesure pas un rendement locatif.")}
def _reset_municipal_selection():
 st.session_state["municipal_selected"]=[]

def show_markets():
 st.markdown("<p class='eyebrow'>MARCHÉ</p>",unsafe_allow_html=True)
 st.title("Comparer les municipalités")
 st.markdown("<p class='section-intro'>Des repères municipaux officiels pour situer un territoire, sans prix de vente, rendement ou risque inventés.</p>",unsafe_allow_html=True)
 all_municipalities=municipalities(DATABASE_PATH)
 if not all_municipalities:
  st.warning("Aucune donnée municipale officielle n’est encore chargée dans cet environnement. Un administrateur peut importer une source MAMH autorisée; aucune valeur de remplacement n’est affichée.")
  return
 st.info("Ces repères officiels ne sont pas des prix de vente. Les prix de vente, rendements locatifs et niveaux de risque restent indisponibles sans source autorisée.")
 available, selected_count, limit = st.columns(3)
 available.metric("Municipalités disponibles", len(all_municipalities))
 selected_count.metric("Municipalités sélectionnées", f"{len(st.session_state.get('municipal_selected', []))} / 4")
 limit.metric("Comparaison utile", "2 à 4 villes")
 query=st.text_input("Rechercher et ajouter une municipalité",key="municipal_search",placeholder="Ex. Montréal")
 current=st.session_state.get("municipal_selected",[])
 choices=selection_options(current,municipalities(DATABASE_PATH,query))
 selected=st.multiselect("Sélectionnez de deux à quatre municipalités",choices,max_selections=4,key="municipal_selected",placeholder="Choisir des municipalités",help="Une recherche ne retire jamais les municipalités que vous avez déjà choisies.")
 st.button("Réinitialiser la comparaison",on_click=_reset_municipal_selection)
 result=comparison(DATABASE_PATH,selected)
 if not result["available"]:
  missing=result.get("missing",[])
  if missing and len(selected)>=2:
   st.info("Les données officielles sont incomplètes pour : "+", ".join(missing)+". Choisissez des municipalités couvertes par les mêmes indicateurs et la même année; aucune valeur manquante n’est remplacée par zéro.")
  else:
   st.info("Sélectionnez au moins deux municipalités couvertes par la même année. Les données manquantes restent indiquées comme indisponibles et ne sont jamais remplacées par zéro.")
  return
 st.caption(f"Données officielles disponibles · année commune : {result['year']} · Source : MAMH, Profil financier des municipalités locales, CC-BY 4.0 · données récupérées localement.")
 by_code={}
 for row in result['rows']:by_code.setdefault(row['indicator_code'],[]).append(row)
 for code,rows in by_code.items():
  label,unit,help_text=LABELS[code]
  st.subheader(label); cols=st.columns(len(rows))
  for col,row in zip(cols,rows):col.metric(row['municipality_name'],f"{row['value']:,.0f} {unit}".replace(","," "))
  st.caption(help_text+" Donnée officielle, attribuée au MAMH/Données Québec.")
 st.dataframe([{**{"Indicateur":LABELS[r['indicator_code']][0],"Municipalité":r['municipality_name'],"Valeur":r['value'],"Unité":r['unit'],"Année":r['year']}} for r in result['rows']],hide_index=True,use_container_width=True)
