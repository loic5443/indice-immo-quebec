"""Protected local beta administration."""
import streamlit as st
from components.account import current_user,is_authenticated
from data.database import DATABASE_PATH
from migrations.runner import applied_migrations
from repositories.sqlite_repository import SQLiteRepository
from services.beta_service import create_invitation,revoke_invitation,invitation_status
from services.feedback_service import list_feedback,update_status,export_feedback_csv
from services.telemetry_service import aggregate_events

def show_admin():
 if not is_authenticated() or current_user().get("role")!="admin": st.error("Accès Administration refusé.");return
 repo=SQLiteRepository(DATABASE_PATH); actor=current_user()["id"]
 with repo._connect() as c:
  settings=dict(c.execute("SELECT * FROM beta_settings WHERE id=1").fetchone()); accounts=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]; invitations=[dict(x) for x in c.execute("SELECT rowid,* FROM beta_invitations ORDER BY created_at DESC").fetchall()]
 st.title("Administration")
 st.metric("Comptes bêta",accounts);st.write(f"Inscriptions : {'ouvertes' if settings['registrations_open'] else 'fermées'} · limite {settings['max_participants']}");st.caption("Migrations : "+", ".join(applied_migrations(DATABASE_PATH)))
 with st.expander("Invitations",expanded=True):
  label=st.text_input("Libellé interne"); uses=st.number_input("Utilisations",1,100,1)
  if st.button("Créer une invitation"):
   st.success("Copiez ce code maintenant (il ne sera plus affiché) : "+create_invitation(actor,DATABASE_PATH,label,int(uses)))
  for item in invitations: st.write(f"{item.get('label') or 'Invitation'} — {invitation_status(item)} — {item['uses_count']}/{item['max_uses']}")
 with st.expander("Configuration bêta"):
  if st.button("Ouvrir / fermer les inscriptions"):
   with repo._connect() as c,c: c.execute("UPDATE beta_settings SET registrations_open=? WHERE id=1",(0 if settings['registrations_open'] else 1,));c.execute("INSERT INTO admin_audit_log(actor_id,action) VALUES(?,?)",(actor,"registration_toggle"));st.rerun()
  st.checkbox("Invitation obligatoire",value=bool(settings['invitation_required']),key="beta_invitation_required")
 with st.expander("Retours bêta",expanded=True):
  feedback=list_feedback(actor,DATABASE_PATH,True);st.metric("Retours",len(feedback));st.download_button("Exporter les retours expurgés",export_feedback_csv(actor,DATABASE_PATH),"retours-beta.csv","text/csv")
  for item in feedback:
   with st.container(border=True):
    st.write(f"#{item['id']} · {item['category']} · {item['usefulness']}/5 · {item['status']}");st.write(item['comment'])
    status=st.selectbox("Statut",["new","in_review","resolved","closed"],key=f"status_{item['id']}")
    if st.button("Mettre à jour",key=f"update_{item['id']}"): update_status(actor,item['id'],status,"",DATABASE_PATH);st.rerun()
 with st.expander("Mesures agrégées"):
  st.json(aggregate_events(DATABASE_PATH))
 st.info("Diagnostics sûrs : base SQLite disponible; aucun secret ni donnée d'analyse n'est affiché.")
