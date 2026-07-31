"""Local role management; never creates a user or changes credentials."""
import argparse,getpass,sqlite3,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.database import DATABASE_PATH
p=argparse.ArgumentParser();p.add_argument("action",choices=["promote","demote"]);p.add_argument("--email",required=True);p.add_argument("--confirm",action="store_true");a=p.parse_args()
if not a.confirm and getpass.getpass(f"Typez CONFIRMER pour {a.action} : ")!="CONFIRMER": raise SystemExit("Annulé")
with sqlite3.connect(DATABASE_PATH) as c:
 r=c.execute("UPDATE users SET role=? WHERE email=?",("admin" if a.action=="promote" else "user",a.email.lower())).rowcount
 if not r: raise SystemExit("Compte introuvable")
 c.execute("INSERT INTO admin_audit_log(action,metadata) VALUES(?,?)",(f"admin_{a.action}",'{"source":"local_command"}'))
print("Rôle mis à jour")
