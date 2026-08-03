"""User-scoped progressive analysis workflow and resumable local draft."""
import json
from contextlib import closing
from datetime import datetime, timezone
from repositories.sqlite_repository import SQLiteRepository
STEPS=("Profil et objectif","Propriété","Financement","Exploitation","Comparables","ImmoValue","ImmoScore et ImmoDNA","Scénarios et résistance","Sauvegarde et rapport")

def normalize_step(step):
 """Return the only valid step number used by UI, progress and drafts."""
 try: step=int(step)
 except (TypeError,ValueError): step=1
 return max(1,min(len(STEPS),step))

def transition(current_step,target_step,completed_steps,values):
 """Move one workflow state forward/backward without stale UI state.

 A completed step can always be revisited. Moving forward validates the step
 being left and records it as complete; a selection cannot skip unfinished
 steps.
 """
 current=normalize_step(current_step);target=normalize_step(target_step)
 completed={normalize_step(step) for step in completed_steps or {1}}
 if target==current:return {"step":current,"completed":completed,"errors":[]}
 if target<current and target in completed:return {"step":target,"completed":completed,"errors":[]}
 if target>current:
  errors=validate_step(current,values)
  if errors:return {"step":current,"completed":completed,"errors":errors}
  completed.add(current)
  # Direct selection is useful only for already completed steps or the next one.
  if target<=max(completed)+1:return {"step":target,"completed":completed,"errors":[]}
 return {"step":current,"completed":completed,"errors":["Complétez les étapes précédentes avant de poursuivre."]}
def validate_step(step, values):
 if step==1 and (not values.get("profile") or not values.get("objective")): return ["Profil et objectif requis."]
 if step==2 and (not values.get("property_name") or not values.get("property_type")): return ["Nom/adresse descriptive et type requis."]
 if step==3 and (values.get("price",0)<=0 or values.get("down_payment",0)<=0 or values.get("down_payment",0)>=values.get("price",0)): return ["Prix et mise de fonds valides requis."]
 return []
def save_draft(user_id,values,step,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as con,con: con.execute("INSERT INTO analysis_drafts(user_id,payload_json,current_step,updated_at) VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET payload_json=excluded.payload_json,current_step=excluded.current_step,updated_at=excluded.updated_at",(user_id,json.dumps(values,ensure_ascii=False),step,datetime.now(timezone.utc).isoformat()))
def load_draft(user_id,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as con: row=con.execute("SELECT payload_json,current_step FROM analysis_drafts WHERE user_id=?",(user_id,)).fetchone()
 return (json.loads(row[0]),row[1]) if row else ({},1)
def abandon_draft(user_id,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as con,con: con.execute("DELETE FROM analysis_drafts WHERE user_id=?",(user_id,))
