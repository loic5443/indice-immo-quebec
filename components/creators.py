"""Authenticated creator space and operator payout ledger."""
import os
from datetime import datetime, timezone
import streamlit as st
from components.account import current_user, is_authenticated
from components.sidebar import go_to
from data.database import DATABASE_PATH
from services import creator_service as creators

def capture_referral():
    import time
    code=st.query_params.get('ref')
    if code and not is_authenticated() and not st.session_state.get('creator_referral'):
        valid=creators.valid_code(code,DATABASE_PATH)
        if valid:
            st.session_state['creator_referral']=valid
            st.session_state['creator_referral_at']=time.time()
    if time.time()-st.session_state.get('creator_referral_at',time.time())>creators.WINDOW:
        st.session_state.pop('creator_referral',None)
    if st.query_params.get('createur')=='1':
        st.session_state['main_navigation']='Espace créateur'
        del st.query_params['createur']

def show_creators():
    st.caption('PROGRAMME CRÉATEURS CENLIO')
    st.title('Vos abonnés regardent des maisons. Aidez-les à analyser leurs chiffres.')
    st.write('Votre public regarde Centris, pense acheter ou possède déjà une propriété ? Montrez comment Cenlio aide à analyser le paiement hypothécaire, les taxes et les dépenses. Un contenu utile pour une grande décision. Gagnez 10 $ CA une seule fois par nouveau client Premium admissible.')
    columns=st.columns(3)
    for col,n in zip(columns,(10,100,1000)):
        col.metric(f'{n} nouveaux clients validés',f'{n*10:,} $'.replace(',',' '))
    st.caption('Exemples de calcul, pas une promesse de ventes. Aucun frais pour rejoindre le programme.')
    st.link_button('Lire les règles simples du programme','/createurs')
    if not is_authenticated():
        st.info('Créez votre compte gratuit ou connectez-vous pour obtenir votre lien et suivre vos commissions.')
        if st.button('Créer mon compte ou me connecter',type='primary'):
            st.session_state['creator_join_pending']=True
            go_to('Mon compte'); st.rerun()
        return
    user=current_user(); mode=os.environ.get('IMMORADAR_BILLING_MODE','test')
    data=creators.dashboard(user['id'],DATABASE_PATH,mode)
    if data is None:
        accepted=st.checkbox('J’accepte les règles : 10 $ une seule fois, premier paiement admissible, validation de 30 jours, paiements manuels chaque mois, publicité clairement annoncée.')
        if st.button('Obtenir mon lien gratuit',type='primary',disabled=not accepted):
            creators.join(user['id'],DATABASE_PATH,accepted);st.rerun()
        return
    st.subheader('Mon lien personnel')
    origin=os.environ.get('IMMORADAR_PUBLIC_URL','https://cenlio.onrender.com').rstrip('/')
    st.code(origin+'/?ref='+data['code'],language=None)
    st.caption('Le lien doit être utilisé au moment de créer le compte. Votre code peut aussi être saisi à l’inscription. L’achat doit avoir lieu dans les 30 jours suivants. Le client paie le même prix.')
    if mode!='live': st.warning('Espace de test : ces montants ne sont pas des commissions réelles.')
    rows=data['commissions']; cols=st.columns(4)
    cols[0].metric('Inscriptions avec mon code',data['registrations'])
    for col,state,label in zip(cols[1:],('En validation','À payer','Payée'),('En validation','À payer','Déjà payé')):
        amount=sum(x['amount_cents'] for x in rows if x['state']==state)/100
        col.metric(label,f'{amount:.0f} $ CA')
    st.write('Une ligne = un premier abonnement payé. Les renouvellements ne donnent pas une autre commission. Les paiements sont faits manuellement chaque mois; aucun virement n’est déclenché depuis cette page.')
    if rows:
        st.dataframe([{'Référence':x['id'],'Date':datetime.fromtimestamp(x['created_at'],timezone.utc).strftime('%Y-%m-%d'),'Commission':'10 $ CA','État':x['state']} for x in rows],hide_index=True,width='stretch')
    else: st.info('Votre première commission apparaîtra ici après un paiement admissible confirmé par Stripe.')
    st.download_button('Télécharger mon relevé',creators.export_csv(user['id'],DATABASE_PATH,mode),'mes-commissions.csv','text/csv')
    st.caption('Les noms, courriels et cartes des clients restent privés. Pour préparer votre versement, contactez Cenlio avec votre code. Ne partagez jamais vos mots de passe ou numéros de carte.')
    st.link_button('Contacter Cenlio','mailto:contactcenlio@gmail.com')

def show_creator_admin(actor):
    with st.expander('Créateurs et commissions'):
        st.caption('10 $ CA par premier abonnement admissible. Validation de 30 jours. Effectuez le versement séparément, puis notez sa référence ici. Aucun virement automatique.')
        st.dataframe(creators.admin_profiles(actor,DATABASE_PATH),hide_index=True,width='stretch')
        st.caption('Le code loic est le lien personnel de Cenlio : suivi des inscriptions, sans commission à verser à soi-même.')
        rows=creators.admin_rows(actor,DATABASE_PATH)
        if not rows: st.info('Aucune commission réelle enregistrée.')
        for x in rows:
            with st.container(border=True):
                st.write(f"{x['display_name']} · {x['creator_code']} · 10 $ CA · {x['status']} · {x['id']}")
                st.caption('Fin de validation : '+datetime.fromtimestamp(x['available_at'],timezone.utc).strftime('%Y-%m-%d'))
                reference=st.text_input('Référence du versement ou raison de décision',key='cref_'+x['id'],max_chars=200)
                choice=st.selectbox('Action',['paid','release','void'],format_func=lambda v:{'paid':'Confirmer un versement déjà effectué','release':'Vérification terminée : commission admissible','void':'Refuser une commission non admissible'}[v],key='caction_'+x['id'])
                checked=st.checkbox('J’ai vérifié le paiement Stripe et cette décision',key='ccheck_'+x['id'])
                if st.button('Enregistrer la décision',key='csave_'+x['id'],disabled=not checked):
                    try: creators.settle(actor,DATABASE_PATH,x['id'],choice,reference);st.rerun()
                    except ValueError as error: st.error(str(error))
