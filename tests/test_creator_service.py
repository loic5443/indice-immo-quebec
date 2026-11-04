"""Financial referral invariants, real migrations, signed billing events and scoped UI."""
import copy
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from data.database import initialize_database, create_user
from repositories.sqlite_repository import SQLiteRepository
from services import creator_service as cs
from services.beta_service import register_beta_user
from services.billing_service import billing_config, process_webhook
from tests.test_billing_service import ENV, signed_payload

class CreatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'qa.sqlite'
        initialize_database(self.db)
        create_user('Creator','creator@example.test','long-safe-password',self.db)
        self.code=cs.join(1,self.db,True)
        ok,msg=register_beta_user('Buyer','buyer@example.test','long-safe-password',self.db,referral_code=self.code)
        self.assertTrue(ok,msg);self.now=int(time.time())
        self.sub={'id':'sub_1','customer':'cus_1','livemode':False,'metadata':{'immoradar_user_id':'2'},'status':'active','items':{'data':[{'price':{'id':'price_premium'},'quantity':1,'current_period_end':self.now+86400}]}}
        self.invoice={'id':'in_1','customer':'cus_1','subscription':'sub_1','livemode':False,'status':'paid','paid':True,'currency':'cad','billing_reason':'subscription_create','amount_paid':1499,'created':self.now,'status_transitions':{'paid_at':self.now}}
        with self.conn() as c:
            c.execute("INSERT INTO billing_accounts(user_id,customer_id,mode,subscription_id,status) VALUES(2,'cus_1','test','sub_1','active')")
        self.config=billing_config(ENV)
    def tearDown(self): self.tmp.cleanup()
    def conn(self): return SQLiteRepository(self.db)._connect()
    def record(self, invoice=None):
        with self.conn() as c: cs.record_invoice(c,invoice or self.invoice,self.sub,self.config)
    def rows(self): return cs.dashboard(1,self.db,'test')['commissions']
    def test_once_not_on_renewals_and_mode_separation(self):
        self.record();self.record()
        other={**self.invoice,'id':'in_2','billing_reason':'subscription_cycle'};self.record(other)
        self.assertEqual(len(self.rows()),1)
        self.assertEqual(self.rows()[0]['amount_cents'],1000)
        self.assertEqual(cs.dashboard(1,self.db,'live')['commissions'],[])
        self.assertIsNone(cs.dashboard(2,self.db,'test'))
    def test_ineligible_provider_objects(self):
        for change in ({'status':'draft'},{'status':'open'},{'currency':'usd'},{'livemode':True},{'amount_paid':0},{'amount_paid':1498},{'customer':'cus_stranger'},{'subscription':'sub_stranger'},{'status_transitions':{'paid_at':self.now+cs.WINDOW+1}},{'status_transitions':{'paid_at':self.now-5}}):
            with self.subTest(change=change):
                self.record({**self.invoice,**change});self.assertEqual(self.rows(),[])
    def test_registration_rolls_back_invalid_code(self):
        ok,_=register_beta_user('Bad','bad@example.test','long-safe-password',self.db,referral_code='unknown')
        self.assertFalse(ok)
        with self.conn() as c: self.assertIsNone(c.execute("SELECT 1 FROM users WHERE email='bad@example.test'").fetchone())
    def test_creator_consent_identity_and_join_idempotence(self):
        self.assertEqual(cs.join(1,self.db,True),self.code)
        with self.assertRaises(ValueError): cs.join(2,self.db,False)
        with self.assertRaises(PermissionError): cs.join(999,self.db,True)
        with self.conn() as c:
            with self.assertRaises(ValueError): cs.attach(c,1,self.code)
    def test_risk_before_or_after_invoice_stays_on_hold(self):
        with self.conn() as c:
            c.execute("INSERT INTO billing_risk_reviews(event_id,subscription_id,reason,created_at) VALUES('risk','sub_1','charge.refunded',?)",(self.now,))
        self.record();self.assertEqual(self.rows()[0]['status'],'review')
        with self.conn() as c: cs.hold_subscription(c,'sub_1','test')
        self.record();self.assertEqual(self.rows()[0]['status'],'review')
    def test_dashboard_and_csv_never_show_customer_identity(self):
        self.record();data=str(cs.dashboard(1,self.db,'test'))+cs.export_csv(1,self.db,'test')
        for secret in ('buyer@example.test','Buyer','cus_1','sub_1','in_1'): self.assertNotIn(secret,data)
        with self.assertRaises(PermissionError): cs.dashboard(999,self.db)
    def test_operator_payment_requires_role_waiting_period_and_reference(self):
        self.record();row=self.rows()[0]
        with self.conn() as c: c.execute("UPDATE creator_commissions SET mode='live' WHERE id=?",(row['id'],))
        with self.assertRaises(PermissionError): cs.settle(2,self.db,row['id'],'paid','transfer-1',self.now+cs.WINDOW)
        with self.conn() as c: c.execute("UPDATE users SET role='admin' WHERE id=1")
        with self.assertRaises(ValueError): cs.settle(1,self.db,row['id'],'paid','transfer-1',self.now)
        cs.settle(1,self.db,row['id'],'paid','transfer-1',self.now+cs.WINDOW)
        with self.assertRaises(ValueError): cs.settle(1,self.db,row['id'],'paid','transfer-2',self.now+cs.WINDOW)
        with self.conn() as c: cs.hold_subscription(c,'sub_1','live')
        with self.assertRaises(ValueError): cs.settle(1,self.db,row['id'],'void','refunded',self.now+cs.WINDOW)
        cs.settle(1,self.db,row['id'],'release','review completed',self.now+cs.WINDOW)
        self.assertEqual(cs.dashboard(1,self.db,'live')['commissions'][0]['state'],'Payée')
    def test_signed_webhook_retrieves_invoice_and_deduplicates(self):
        client=SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(retrieve=Mock(return_value=self.sub)),invoices=SimpleNamespace(retrieve=Mock(return_value=self.invoice),list=Mock(return_value={'data':[self.invoice],'has_more':False}))))
        payload,sig=signed_payload('invoice.paid',self.invoice)
        self.assertEqual(process_webhook(payload,sig,self.db,ENV,client),'processed')
        self.assertEqual(process_webhook(payload,sig,self.db,ENV,client),'duplicate')
        self.assertEqual(len(self.rows()),1);client.v1.invoices.retrieve.assert_called_once_with('in_1')
    def test_previous_paid_subscription_does_not_qualify(self):
        prior={**self.invoice,'id':'old_invoice','created':self.now-1}
        client=SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(retrieve=Mock(return_value=self.sub)),invoices=SimpleNamespace(retrieve=Mock(return_value=self.invoice),list=Mock(return_value={'data':[prior,self.invoice],'has_more':False}))))
        payload,sig=signed_payload('invoice.paid',self.invoice)
        process_webhook(payload,sig,self.db,ENV,client);self.assertEqual(self.rows(),[])
    def test_house_link_tracks_without_commission(self):
        self.assertEqual(cs.valid_code('loic',self.db),'loic')
        with self.conn() as c: c.execute("UPDATE creator_referrals SET creator_code='loic' WHERE user_id=2")
        self.record();self.assertEqual(self.rows(),[])
    def test_creator_landing_plain_and_clear(self):
        from services.legal_pages import creator_landing
        html=creator_landing()
        for text in ('1 000 $','10 $ CA une seule fois','14,99','Aucun minimum','Publicité','pas des revenus garantis'): self.assertIn(text,html)
    def test_guest_creator_ui(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_string('from components.creators import show_creators\nshow_creators()').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Créer mon compte' in b.label for b in app.button))

    def test_current_sdk_invoice_without_paid_boolean(self):
        invoice={k:v for k,v in self.invoice.items() if k!='paid'}
        invoice['parent']={'subscription_details':{'subscription':'sub_1'}}
        invoice.pop('subscription')
        self.record(invoice)
        self.assertEqual(len(self.rows()),1)

    def test_authenticated_creator_ui_shows_only_own_link(self):
        from streamlit.testing.v1 import AppTest
        with patch('components.creators.DATABASE_PATH',self.db), patch('components.creators.is_authenticated',return_value=True), patch('components.creators.current_user',return_value={'id':1}):
            app=AppTest.from_string('from components.creators import show_creators\nshow_creators()').run()
        self.assertFalse(app.exception)
        self.assertIn(self.code,app.code[0].value)
