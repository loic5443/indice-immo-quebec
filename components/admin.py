"""Protected local beta administration."""
import streamlit as st
from components.account import current_user,is_authenticated
from data.database import DATABASE_PATH
from migrations.runner import applied_migrations
from repositories.sqlite_repository import SQLiteRepository
from services.beta_service import create_invitation,revoke_invitation,invitation_status,invitations,export_invitations,admin_log,export_admin_log,update_beta_settings
from services.feedback_service import list_feedback,update_status,export_feedback_csv
from services.telemetry_service import aggregate_events
from services.diagnostics_service import set_source_enabled
from providers.source_registry import load_source_registry
from services.quebec_role_admin_service import refresh_index,territories,import_territory,set_territory_enabled,remove_local_cache,coverage_summary

def _show_role_data_admin(actor):
 with st.expander("Données foncières du Québec",expanded=True):
  st.caption("MAMH / Données Québec · rôle d’évaluation foncière ouvert · consultation locale seulement.")
  summary=coverage_summary(actor,DATABASE_PATH)
  st.caption(f"Index : {summary['indexed']} territoires · synchronisés : {summary['synced']} · unités locales : {summary['units']} · dernière réussite : {summary['last_success'] or '—'}")
  confirmed=st.checkbox("Je confirme l’actualisation de l’index officiel",key="role_index_confirm")
  if st.button("Actualiser la liste des municipalités",key="role_index_refresh"):
   if not confirmed: st.error("Confirmation requise.")
   else:
    try: st.success(f"Index actualisé : {refresh_index(actor,DATABASE_PATH)['territories']} territoires.")
    except Exception: st.error("Index indisponible; le dernier index valide est conservé.")
  query=st.text_input("Municipalité ou code",key="role_query");state=st.selectbox("État",["","synchronized","not_synchronized"],key="role_state");page=st.number_input("Page territoires",1,1000,1,key="role_page")
  try:
   listing=territories(actor,DATABASE_PATH,query,state,int(page));st.caption(f"{listing['total']} territoires · import explicite d’une municipalité seulement.")
   for item in listing['items']:
    with st.container(border=True):
     st.write(f"**{item['municipality']}** ({item['territory_code']}) · {item['source_updated_at']}")
     st.caption(f"{item['imported_units'] or 0} unités · XML {item['source_version'] or '—'} · {'actif' if item['enabled'] else 'désactivé'}")
     confirm=st.checkbox("Je confirme le téléchargement et l’import",key=f"role_confirm_{item['territory_code']}")
     if st.button("Télécharger et importer",key=f"role_import_{item['territory_code']}"):
      if not confirm: st.error("Confirmation requise.")
      else:
       try:
        with st.spinner("Téléchargement et import en cours..."): result=import_territory(actor,DATABASE_PATH,item['territory_code'])
        st.success(f"Import terminé : {result['imported_units']} unités, {result['rejected_units']} rejet.")
       except Exception: st.error("Import indisponible; la version locale précédente reste active.")
     if st.button("Activer / désactiver",key=f"role_toggle_{item['territory_code']}"):
      set_territory_enabled(actor,DATABASE_PATH,item['territory_code'],not bool(item['enabled']));st.rerun()
     remove=st.checkbox("Je confirme le retrait local",key=f"role_remove_confirm_{item['territory_code']}")
     if st.button("Retirer le cache local",key=f"role_remove_{item['territory_code']}"):
      if not remove: st.error("Double confirmation requise.")
      else: remove_local_cache(actor,DATABASE_PATH,item['territory_code']);st.success("Cache local retiré; les analyses utilisateur sont conservées.");st.rerun()
  except Exception: st.info("Actualisez d’abord la liste officielle des municipalités.")

def show_admin():
 if not is_authenticated() or current_user().get("role")!="admin": st.error("Accès Administration refusé.");return
 repo=SQLiteRepository(DATABASE_PATH); actor=current_user()["id"]
 with repo._connect() as c:
  settings=dict(c.execute("SELECT * FROM beta_settings WHERE id=1").fetchone()); accounts=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
 st.title("Administration")
 _show_role_data_admin(actor)
 st.metric("Comptes bêta",accounts);st.write(f"Inscriptions : {'ouvertes' if settings['registrations_open'] else 'fermées'} · limite {settings['max_participants']}");st.caption("Migrations : "+", ".join(applied_migrations(DATABASE_PATH)))
 with st.expander("Invitations",expanded=True):
  label=st.text_input("Libellé interne"); uses=st.number_input("Utilisations",1,100,1); expires=st.date_input("Expiration facultative",value=None)
  if st.button("Créer une invitation"):
   st.success("Copiez ce code maintenant (il ne sera plus affiché) : "+create_invitation(actor,DATABASE_PATH,label,int(uses),expires.isoformat() if expires else None))
  status=st.selectbox("Statut invitation",["","active","expired","exhausted","revoked"]);ipage=st.number_input("Page invitations",1,100,1)
  st.download_button("Exporter invitations expurgées",export_invitations(actor,DATABASE_PATH),"invitations.csv","text/csv")
  for item in invitations(actor,DATABASE_PATH,status or None,page=int(ipage)): st.write(f"{item.get('label') or 'Invitation'} — {item['status']} — {item['uses_count']}/{item['max_uses']} · expiration {item['expires_at'] or '—'}")
 with st.expander("Journal administratif"):
  st.download_button("Exporter le journal expurgé",export_admin_log(actor,DATABASE_PATH),"journal-admin.csv","text/csv")
  st.dataframe(admin_log(actor,DATABASE_PATH),hide_index=True,width="stretch")
 with st.expander("Configuration bêta"):
  opened=st.checkbox("Inscriptions ouvertes",value=bool(settings['registrations_open']))
  required=st.checkbox("Invitation obligatoire",value=bool(settings['invitation_required']))
  limit=st.number_input("Limite maximale",1,10000,int(settings['max_participants']))
  banner=st.checkbox("Bannière Bêta privée active",value=bool(settings['banner_active']))
  message=st.text_area("Message de bannière",value=settings['message'])
  confirm=st.checkbox("Je confirme cette modification")
  if st.button("Enregistrer la configuration"):
   if not confirm: st.error("Confirmation requise.")
   else: update_beta_settings(actor,DATABASE_PATH,opened,required,limit,banner,message);st.success("Configuration sauvegardée.");st.rerun()
 with st.expander("Retours bêta",expanded=True):
  category=st.text_input("Filtrer catégorie");status_filter=st.selectbox("Filtrer statut",["","new","in_review","resolved","closed"]);page=st.number_input("Page",1,100,1)
  feedback=list_feedback(actor,DATABASE_PATH,True,category=category or None,status=status_filter or None,page=int(page));st.metric("Résultats",len(feedback));st.download_button("Exporter les retours expurgés",export_feedback_csv(actor,DATABASE_PATH),"retours-beta.csv","text/csv")
  for item in feedback:
   with st.container(border=True):
    st.write(f"#{item['id']} · {item['category']} · {item['usefulness']}/5 · {item['status']}");st.write(item['comment'])
    status=st.selectbox("Statut",["new","in_review","resolved","closed"],key=f"status_{item['id']}")
    if st.button("Mettre à jour",key=f"update_{item['id']}"): update_status(actor,item['id'],status,"",DATABASE_PATH);st.rerun()
 with st.expander("Mesures agrégées"):
  measures=aggregate_events(DATABASE_PATH)
  st.json({key:(value if value is not None else "données insuffisantes") for key,value in measures.items()})
 with st.expander("Sources et diagnostics"):
  st.write("Base disponible · diagnostics expurgés · aucune donnée utilisateur affichée.")
  for source in load_source_registry().values():
   st.write(f"{source['source_id']} — {source['name']} — {source['status']}")
   reason=st.text_input("Raison",key=f"reason_{source['source_id']}")
   if st.button("Activer/désactiver",key=f"toggle_{source['source_id']}"):
    try:set_source_enabled(actor,source['source_id'],False,reason,DATABASE_PATH);st.success("Source désactivée.")
    except ValueError as error:st.error(str(error))
 st.info("Diagnostics sûrs : base SQLite disponible; aucun secret ni donnée d'analyse n'est affiché.")
