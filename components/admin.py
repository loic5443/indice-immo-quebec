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

def show_admin():
 if not is_authenticated() or current_user().get("role")!="admin": st.error("Accès Administration refusé.");return
 repo=SQLiteRepository(DATABASE_PATH); actor=current_user()["id"]
 with repo._connect() as c:
  settings=dict(c.execute("SELECT * FROM beta_settings WHERE id=1").fetchone()); accounts=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
 st.title("Administration")
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
