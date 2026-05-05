import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from tinydb import TinyDB, Query
from datetime import datetime

# Configuration du template Plotly selon le thème global
plotly_template = "plotly_white" if st.session_state.get("theme", "Clair") == "Clair" else "plotly_dark"
chart_color = "#1a1c21" if st.session_state.get("theme", "Clair") == "Clair" else "#e0e6ed"

st.title("👥 Ressources Humaines & Performance")
st.markdown("### Cartographie et Qualité de Travail du Personnel")

# --- CHARGEMENT DES DONNÉES MULTI-SOURCES ---
@st.cache_data(ttl=60)
def get_rh_data():
    data = {
        'logs': [],
        'inventaire': pd.DataFrame(),
        'recouvrement': pd.DataFrame(),
        'pointages': [],
        'reclamations': [],
        'users': []
    }
    
    # 1. Logs d'activité
    try:
        db_logs = TinyDB('data/db_logs.json')
        data['logs'] = db_logs.all()
    except: pass

    # 2. Inventaires
    try:
        if os.path.exists("data_inventaire/saisie.csv"):
            data['inventaire'] = pd.read_csv("data_inventaire/saisie.csv", sep=';', encoding='utf-8-sig')
    except: pass

    # 3. Recouvrement
    try:
        if os.path.exists("data_recouvrement.csv"):
            df_rec = pd.read_csv("data_recouvrement.csv", sep=',', encoding='utf-8-sig')
            # Nettoyage des colonnes et montants
            cols_map = {c.lower(): c for c in df_rec.columns}
            for target in ["Montant Réglé", "Montant Initial", "Reste à payer"]:
                # Chercher une correspondance insensible à la casse
                for k, v in cols_map.items():
                    if target.lower() in k:
                        df_rec[target] = pd.to_numeric(df_rec[v].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                        break
            data['recouvrement'] = df_rec
    except: pass

    # 4. Pointages & Réclamations (Logistique)
    try:
        db_pharma = TinyDB("db_pharmaciel.json")
        data['pointages'] = db_pharma.table('pointages').all()
        data['reclamations'] = db_pharma.table('reclamations').all()
    except: pass

    # 5. Liste des utilisateurs
    try:
        db_users = TinyDB('data/db_users.json')
        data['users'] = db_users.all()
    except: pass

    return data

rh_data = get_rh_data()
users_list = [u['username'] for u in rh_data['users']]

# --- FILTRES ---
col_f1, col_f2 = st.columns([1, 2])
with col_f1:
    selected_user = st.selectbox("👤 Sélectionner un employé", ["Tous le personnel"] + users_list)
with col_f2:
    st.write("") # Alignement

st.divider()

if selected_user == "Tous le personnel":
    # --- VUE GLOBALE COMPARATIVE ---
    st.subheader("📊 Comparaison des Performances")
    
    c1, c2, c3 = st.columns(3)
    
    # KPI 1 : Activité (Logs)
    df_logs = pd.DataFrame(rh_data['logs'])
    if not df_logs.empty and 'user' in df_logs.columns:
        act_counts = df_logs['user'].value_counts().reset_index()
        act_counts.columns = ['Employé', 'Nb Actions']
        fig_act = px.bar(act_counts, x='Employé', y='Nb Actions', title="Intensité de Travail (Total Actions)",
                         color='Nb Actions', color_continuous_scale='Blues', template=plotly_template)
        st.plotly_chart(fig_act, use_container_width=True)
    
    # KPI 2 : Inventaires par Agent
    df_inv = rh_data['inventaire']
    if not df_inv.empty and 'user_saisie' in df_inv.columns:
        inv_counts = df_inv['user_saisie'].value_counts().reset_index()
        inv_counts.columns = ['Agent', 'Nb Saisies']
        fig_inv = px.bar(inv_counts, x='Agent', y='Nb Saisies', title="Productivité Inventaire",
                         color='Nb Saisies', color_continuous_scale='Greens', template=plotly_template)
        st.plotly_chart(fig_inv, use_container_width=True)

    # KPI 3 : Recouvrement par Livreur
    df_rec = rh_data['recouvrement']
    if not df_rec.empty and 'Livreur' in df_rec.columns and 'Montant Réglé' in df_rec.columns:
        rec_val = df_rec.groupby('Livreur')['Montant Réglé'].sum().reset_index()
        fig_rec = px.pie(rec_val, values='Montant Réglé', names='Livreur', title="Efficacité Recouvrement (DA encaissés)",
                         hole=0.4, template=plotly_template)
        st.plotly_chart(fig_rec, use_container_width=True)
    else:
        st.info("📊 Données de recouvrement insuffisantes pour le graphique.")

else:
    # --- FOCUS INDIVIDUEL ---
    user_info = next((u for u in rh_data['users'] if u['username'] == selected_user), {})
    role = user_info.get('role', 'N/A')
    
    st.markdown(f"## {selected_user} <span style='font-size: 15px; color: grey;'>({role})</span>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    
    # 1. Activité Logs
    u_logs = [l for l in rh_data['logs'] if l.get('user') == selected_user]
    m1.metric("Actions Système", len(u_logs))
    
    # 2. Performance selon le rôle
    if role == "Saisie":
        u_inv = rh_data['inventaire'][rh_data['inventaire']['user_saisie'] == selected_user] if not rh_data['inventaire'].empty else pd.DataFrame()
        m2.metric("Articles Inventoriés", len(u_inv))
        
        u_temp = len([l for l in u_logs if "temperature" in str(l.get('action')).lower()])
        m3.metric("Prises Température", u_temp)
        
    elif role == "Livreur" or role == "Superviseur":
        u_rec = rh_data['recouvrement'][rh_data['recouvrement']['Livreur'] == selected_user] if not rh_data['recouvrement'].empty else pd.DataFrame()
        m2.metric("Dossiers Recouvrement", len(u_rec))
        
        u_pts = len([p for p in rh_data['pointages'] if p.get('livreur') == selected_user])
        m3.metric("Factures Pointées", u_pts)
        
        u_recs = len([r for r in rh_data['reclamations'] if r.get('livreur') == selected_user])
        m4.metric("Réclamations Gérées", u_recs, delta=f"{u_recs} litiges", delta_color="inverse")

    st.divider()
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 Chronologie d'Activité")
        if u_logs:
            df_u_logs = pd.DataFrame(u_logs)
            df_u_logs['date'] = pd.to_datetime(df_u_logs['timestamp']).dt.date
            daily_act = df_u_logs.groupby('date').size().reset_index(name='Actions')
            fig_trend = px.line(daily_act, x='date', y='Actions', markers=True, template=plotly_template)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Aucune donnée chronologique.")

    with col_right:
        st.subheader("🎯 Spécialisation")
        if u_logs:
            df_u_logs = pd.DataFrame(u_logs)
            mod_dist = df_u_logs['module'].value_counts().reset_index()
            fig_mod = px.pie(mod_dist, values='count', names='module', hole=0.5, template=plotly_template)
            st.plotly_chart(fig_mod, use_container_width=True)

    st.subheader("📜 Dernières actions significatives")
    if u_logs:
        st.table(pd.DataFrame(u_logs[::-1]).head(10)[['timestamp', 'module', 'action']])

# --- SECTION SUGGESTIONS ---
with st.expander("💡 Suggestions pour une cartographie RH complète"):
    st.info("""
    **Pour aller plus loin dans l'analyse de la qualité de travail :**
    
    1. **Taux d'Erreur (Qualité)** : Analyser combien de fois un inventaire a été corrigé par un superviseur après la saisie d'un agent.
    2. **Respect des Délais (Vitesse)** : Calculer le temps moyen entre l'apparition d'un litige client et sa résolution par le livreur.
    3. **Taux de Recouvrement (Efficacité)** : Ratio entre le montant total assigné à un livreur et le montant réellement encaissé.
    4. **Assiduité Numérique** : Fréquence de connexion à l'application et utilisation des outils IA (Automatisation).
    5. **Score de Fiabilité** : Un score calculé combinant la ponctualité des pointages et l'absence de réclamations sur les zones livrées.
    """)
