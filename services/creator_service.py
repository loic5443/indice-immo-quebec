"""First-payment referral ledger. No automatic payouts and no customer PII in creator views."""
import csv
import io
import secrets
import time
from contextlib import closing
from repositories.sqlite_repository import SQLiteRepository
from services.beta_service import _admin

TERMS_VERSION = "2026-11-04"
WINDOW = 30 * 86400

def _user(c, actor):
    row = c.execute("SELECT id,email,name FROM users WHERE id=?", (actor,)).fetchone()
    if row is None: raise PermissionError("Connectez-vous à votre compte.")
    return row

def valid_code(code, database_path):
    if not isinstance(code, str) or len(code)>50: return None
    with closing(SQLiteRepository(database_path)._connect()) as c:
        row=c.execute("SELECT code FROM creator_profiles WHERE code=? AND active=1",(code.strip().lower(),)).fetchone()
    return row[0] if row else None

def join(actor, database_path, accepted=False):
    if not accepted: raise ValueError("Acceptez les conditions du programme.")
    with closing(SQLiteRepository(database_path)._connect()) as c, c:
        c.execute("BEGIN IMMEDIATE")
        user=_user(c,actor)
        existing=c.execute("SELECT code FROM creator_profiles WHERE user_id=?",(actor,)).fetchone()
        if existing: return existing[0]
        code=secrets.token_hex(6)
        c.execute("INSERT INTO creator_profiles(code,user_id,display_name,kind,accepted_at,terms_version) VALUES(?,?,?,'creator',?,?)",(code,actor,user['name'],int(time.time()),TERMS_VERSION))
    return code

def attach(c, user_id, code, now=None):
    """Called inside the new-account transaction; never reassign an existing customer."""
    if not code: return
    now=int(time.time() if now is None else now)
    p=c.execute("SELECT * FROM creator_profiles WHERE code=? AND active=1",(str(code).strip().lower(),)).fetchone()
    if p is None: raise ValueError("Code créateur inconnu. Corrigez-le ou retirez-le.")
    if p['user_id']==user_id: raise ValueError("Votre propre abonnement ne donne pas de commission.")
    c.execute("INSERT INTO creator_referrals VALUES(?,?,?,?)",(user_id,p['code'],now,now+WINDOW))

def referral_metadata(c, user_id):
    row=c.execute("SELECT creator_code FROM creator_referrals WHERE user_id=?",(user_id,)).fetchone()
    return {"cenlio_creator_code":row[0]} if row else {}

def record_invoice(c, invoice, subscription, config, now=None):
    """Only a server-retrieved first subscription invoice can create a commission."""
    now=int(time.time() if now is None else now)
    def ident(v): return v if isinstance(v,str) else (v or {}).get('id')
    if (invoice.get('livemode') is not (config.mode=='live') or invoice.get('status')!='paid'
        or invoice.get('currency')!='cad'
        or invoice.get('billing_reason')!='subscription_create'
        or not isinstance(invoice.get('amount_paid'),int) or invoice['amount_paid']<1499): return
    account=c.execute("SELECT * FROM billing_accounts WHERE customer_id=? AND mode=?",(ident(invoice.get('customer')),config.mode)).fetchone()
    if not account or account['customer_id']!=ident(subscription.get('customer')) or account['status']!='active': return
    invoice_sub=ident(invoice.get('subscription')) or ident((invoice.get('parent') or {}).get('subscription_details',{}).get('subscription'))
    if invoice_sub!=subscription.get('id') or account['subscription_id']!=subscription['id']: return
    items=(subscription.get('items') or {}).get('data',[])
    if len(items)!=1 or ident(items[0].get('price'))!=config.price_id or items[0].get('quantity')!=1: return
    ref=c.execute("SELECT r.*,p.user_id AS owner,p.kind,p.active FROM creator_referrals r JOIN creator_profiles p ON p.code=r.creator_code WHERE r.user_id=?",(account['user_id'],)).fetchone()
    paid_at=(invoice.get('status_transitions') or {}).get('paid_at')
    if (not ref or ref['kind']!='creator' or not ref['active'] or ref['owner']==account['user_id']
        or not isinstance(paid_at,int) or not ref['created_at']<=paid_at<=ref['expires_at']): return
    # Also reject the same email if an imported account has an alternate ID.
    owner=c.execute("SELECT email FROM users WHERE id=?",(ref['owner'],)).fetchone()
    buyer=c.execute("SELECT email FROM users WHERE id=?",(account['user_id'],)).fetchone()
    if not owner or not buyer or owner[0].lower()==buyer[0].lower(): return
    # Risk events can precede invoice.paid. Never erase a hold with a late invoice.
    risk=c.execute("SELECT 1 FROM billing_risk_reviews WHERE subscription_id=?",(subscription['id'],)).fetchone()
    c.execute("INSERT OR IGNORE INTO creator_commissions VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
        (secrets.token_hex(8),ref['creator_code'],account['user_id'],config.mode,account['customer_id'],subscription['id'],invoice['id'],1000,paid_at,paid_at+WINDOW,'review' if risk else 'pending'))

def hold_subscription(c, subscription_id, mode):
    c.execute("UPDATE creator_commissions SET status='review' WHERE subscription_id=? AND mode=? AND status!='void'",(subscription_id,mode))

def dashboard(actor, database_path, mode='live', now=None):
    if mode not in {'test','live'}: raise ValueError('Mode invalide.')
    now=int(time.time() if now is None else now)
    with closing(SQLiteRepository(database_path)._connect()) as c:
        _user(c,actor)
        p=c.execute("SELECT code FROM creator_profiles WHERE user_id=?",(actor,)).fetchone()
        if not p: return None
        rows=[dict(x) for x in c.execute("SELECT id,amount_cents,created_at,available_at,status,paid_at FROM creator_commissions WHERE creator_code=? AND mode=? ORDER BY created_at DESC",(p[0],mode))]
        count=c.execute("SELECT COUNT(*) FROM creator_referrals WHERE creator_code=?",(p[0],)).fetchone()[0]
    for row in rows:
        row['state']=('À payer' if now>=row['available_at'] else 'En validation') if row['status']=='pending' else {'paid':'Payée','review':'À vérifier','void':'Non admissible'}[row['status']]
    return {'code':p[0],'registrations':count,'commissions':rows,'mode':mode}

def export_csv(actor, database_path, mode='live'):
    data=dashboard(actor,database_path,mode)
    out=io.StringIO(); w=csv.writer(out); w.writerow(['Référence','Montant CAD','État','Date paiement'])
    for x in (data or {}).get('commissions',[]): w.writerow([x['id'],f"{x['amount_cents']/100:.2f}",x['state'],x['paid_at'] or ''])
    return out.getvalue()

def admin_rows(actor, database_path):
    _admin(actor,database_path)
    with closing(SQLiteRepository(database_path)._connect()) as c:
        return [dict(x) for x in c.execute("SELECT l.*,p.display_name FROM creator_commissions l JOIN creator_profiles p ON p.code=l.creator_code WHERE l.mode='live' ORDER BY l.created_at DESC LIMIT 500")]

def settle(actor, database_path, commission_id, action, reference='', now=None):
    _admin(actor,database_path)
    now=int(time.time() if now is None else now)
    if action not in {'paid','void','release'}: raise ValueError('Action invalide.')
    if not 3<=len(reference.strip())<=200: raise ValueError('Ajoutez une référence ou une raison (3 à 200 caractères).')
    with closing(SQLiteRepository(database_path)._connect()) as c,c:
        c.execute('BEGIN IMMEDIATE')
        x=c.execute("SELECT * FROM creator_commissions WHERE id=? AND mode='live'",(commission_id,)).fetchone()
        if not x: raise ValueError('Commission introuvable.')
        if action=='paid':
            if x['status']!='pending' or now<x['available_at'] or x['paid_at']: raise ValueError('Cette commission ne peut pas être marquée payée.')
            c.execute("UPDATE creator_commissions SET status='paid',paid_at=?,payment_reference=? WHERE id=?",(now,reference.strip(),commission_id))
        elif action=='release':
            if x['status']!='review': raise ValueError('Aucune vérification en attente.')
            c.execute("UPDATE creator_commissions SET status=? WHERE id=?",('paid' if x['paid_at'] else 'pending',commission_id))
        else:
            if x['paid_at']: raise ValueError('Une commission déjà versée doit être réglée avec le créateur; conservez sa trace.')
            c.execute("UPDATE creator_commissions SET status='void',payment_reference=? WHERE id=?",(reference.strip(),commission_id))
        import json
        c.execute("INSERT INTO admin_audit_log(actor_id,action,metadata) VALUES(?,?,?)",(actor,'creator_'+action,json.dumps({'commission':commission_id,'reference':reference.strip()})))


def admin_profiles(actor, database_path):
    _admin(actor,database_path)
    with closing(SQLiteRepository(database_path)._connect()) as c:
        return [dict(x) for x in c.execute("SELECT p.code,p.display_name,p.kind,p.active,COUNT(r.user_id) AS registrations FROM creator_profiles p LEFT JOIN creator_referrals r ON r.creator_code=p.code GROUP BY p.code ORDER BY p.accepted_at DESC")]
