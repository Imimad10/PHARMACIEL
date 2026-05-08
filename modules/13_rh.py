import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# Configuration du template Plotly selon le thème global
plotly_template = "plotly_white" if st.session_state.get("theme", "Clair") == "Clair" else "plotly_dark"
chart_color = "#1a1c21" if st.session_state.get("theme", "Clair") == "Clair" else "#e0e6ed"

st.title("👥 Ressources Humaines & Performance")
st.markdown("### Cartographie et Qualité de Travail du Personnel")

from utils_gsheets import load_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# Configuration GSheets pour RH
LOGS_WORKSHEET = "Logs"
LOGS_FALLBACK = "data/db_logs.csv"
INV_WORKSHEET = "Saisie_Inventaire"
INV_FALLBACK = "data_inventaire/saisie.csv"
RECOUV_WORKSHEET = "Recouvrement"
RECOUV_FALLBACK = "data_recouvrement.csv"
POINTAGES_WORKSHEET = "Pointages"
POINTAGES_FALLBACK = "data/db_pointages.csv"
RECLAM_WORKSHEET = "Litiges_SAV"
RECLAM_FALLBACK = "data/db_reclamations.csv"

# --- CHARGEMENT DES DONNÉES MULTI-SOURCES ---
@st.cache_data(ttl=60)
def get_rh_data():
    data = {
        'logs': load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp", "user", "module", "action"]),
        'inventaire': load_gs_data(INV_WORKSHEET, INV_FALLBACK, ['designation', 'qte_saisie', 'agent']),
        'recouvrement': load_gs_data(RECOUV_WORKSHEET, RECOUV_FALLBACK, ["Client", "Montant Réglé", "Livreur", "Statut", "Mode Paiement"]),
        'pointages': load_gs_data(POINTAGES_WORKSHEET, POINTAGES_FALLBACK, ['livreur', 'reference']),
        'reclamations': load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK, ['livreur', 'motif']),
        'users': load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "role"])
    }
    
    # Nettoyage spécifique pour le recouvrement
    if not data['recouvrement'].empty:
        df_rec = data['recouvrement']
        if 'Montant Réglé' in df_rec.columns:
            df_rec['Montant Réglé'] = pd.to_numeric(df_rec['Montant Réglé'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        data['recouvrement'] = df_rec
        
    return data

rh_data = get_rh_data()
users_list = rh_data['users']['username'].tolist() if not rh_data['users'].empty else []

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
    df_logs = rh_data['logs']
    if not df_logs.empty and 'user' in df_logs.columns:
        act_counts = df_logs['user'].value_counts().reset_index()
        act_counts.columns = ['Employé', 'Nb Actions']
        fig_act = px.bar(act_counts, x='Employé', y='Nb Actions', title="Intensité de Travail (Total Actions)",
                         color='Nb Actions', color_continuous_scale='Blues', template=plotly_template)
        st.plotly_chart(fig_act, use_container_width=True)
    
    # KPI 2 : Inventaires par Agent
    df_inv = rh_data['inventaire']
    if not df_inv.empty:
        if 'user_saisie' in df_inv.columns: df_inv.rename(columns={'user_saisie': 'agent'}, inplace=True)
        if 'agent' in df_inv.columns:
            inv_counts = df_inv['agent'].value_counts().reset_index()
            inv_counts.columns = ['Agent', 'Nb Saisies']
            fig_inv = px.bar(inv_counts, x='Agent', y='Nb Saisies', title="Productivité Inventaire",
                             color='Nb Saisies', color_continuous_scale='Greens', template=plotly_template)
            st.plotly_chart(fig_inv, use_container_width=True)

    # KPI 3 : Recouvrement par Livreur
    df_rec = rh_data['recouvrement']
    try:
        if not df_rec.empty and 'Livreur' in df_rec.columns:
            # S'assurer que Montant Réglé est numérique
            if 'Montant Réglé' in df_rec.columns:
                df_rec['Montant Réglé'] = pd.to_numeric(df_rec['Montant Réglé'], errors='coerce').fillna(0)
                rec_val = df_rec.groupby('Livreur')['Montant Réglé'].sum().reset_index()
                if not rec_val.empty and rec_val['Montant Réglé'].sum() > 0:
                    fig_rec = px.pie(rec_val, values='Montant Réglé', names='Livreur', title="Efficacité Recouvrement (DA encaissés)",
                                     hole=0.4, template=plotly_template)
                    st.plotly_chart(fig_rec, use_container_width=True)
                else:
                    st.info("📊 Aucun encaissement enregistré pour le moment.")
            else:
                st.info("📊 Colonne 'Montant Réglé' non détectée.")
        else:
            st.info("📊 Données de recouvrement insuffisantes.")
    except Exception as e:
        st.error(f"Erreur graphique Recouvrement : {e}")

else:
    # --- FOCUS INDIVIDUEL ---
    user_info = rh_data['users'][rh_data['users']['username'] == selected_user].iloc[0] if not rh_data['users'].empty else {}
    role = user_info.get('role', 'N/A')
    
    st.markdown(f"## {selected_user} <span style='font-size: 15px; color: grey;'>({role})</span>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    
    # 1. Activité Logs
    u_logs_df = rh_data['logs'][rh_data['logs']['user'] == selected_user] if not rh_data['logs'].empty else pd.DataFrame()
    u_logs = u_logs_df.to_dict('records')
    m1.metric("Actions Système", len(u_logs_df))
    
    # 2. Performance selon le rôle
    if role == "Saisie":
        df_inv_full = rh_data['inventaire']
        if not df_inv_full.empty:
            if 'user_saisie' in df_inv_full.columns: df_inv_full.rename(columns={'user_saisie': 'agent'}, inplace=True)
            u_inv = df_inv_full[df_inv_full['agent'] == selected_user] if 'agent' in df_inv_full.columns else pd.DataFrame()
        else:
            u_inv = pd.DataFrame()
        m2.metric("Articles Inventoriés", len(u_inv))
        
        u_temp = len([l for l in u_logs if "temperature" in str(l.get('action')).lower()])
        m3.metric("Prises Température", u_temp)
        
    elif role == "Livreur" or role == "Superviseur":
        u_rec = rh_data['recouvrement'][rh_data['recouvrement']['Livreur'] == selected_user] if not rh_data['recouvrement'].empty else pd.DataFrame()
        total_encaisse = u_rec['Montant Réglé'].sum() if not u_rec.empty and 'Montant Réglé' in u_rec.columns else 0
        m2.metric("Total Encaissé", f"{total_encaisse:,.0f} DA")
        
        u_pts = rh_data['pointages'][rh_data['pointages']['livreur'] == selected_user] if not rh_data['pointages'].empty else pd.DataFrame()
        m3.metric("Factures Pointées", len(u_pts))
        
        # Taux de succès recouvrement
        if not u_rec.empty and 'Statut' in u_rec.columns:
            success_rate = (len(u_rec[u_rec['Statut'] == 'Réglé']) / len(u_rec)) * 100
            m4.metric("Taux de Succès", f"{success_rate:.1f}%")
        else:
            m4.metric("Taux de Succès", "0%")

    st.divider()
    
    col_left, col_right = st.columns(2)
    
    if role == "Livreur":
        with col_left:
            st.subheader("🚩 Analyse des Réclamations (Qualité)")
            u_recs_df = rh_data['reclamations'][rh_data['reclamations']['livreur'] == selected_user] if not rh_data['reclamations'].empty else pd.DataFrame()
            if not u_recs_df.empty and 'motif' in u_recs_df.columns:
                fig_reclam = px.bar(u_recs_df['motif'].value_counts().reset_index(), x='motif', y='count', 
                                    title="Motifs de litiges clients", template=plotly_template, color_discrete_sequence=['#ef4444'])
                st.plotly_chart(fig_reclam, use_container_width=True)
            else:
                st.success("✅ Aucune réclamation client pour ce livreur.")
        
        with col_right:
            st.subheader("💰 Répartition des Paiements")
            if not u_rec.empty and 'Mode Paiement' in u_rec.columns:
                fig_pay = px.pie(u_rec['Mode Paiement'].value_counts().reset_index(), values='count', names='Mode Paiement', 
                                 hole=0.4, title="Modes de règlement encaissés", template=plotly_template)
                st.plotly_chart(fig_pay, use_container_width=True)
            else:
                st.info("Données de paiement indisponibles.")
    else:
        with col_left:
            st.subheader("📈 Chronologie d'Activité")
            if not u_logs_df.empty:
                df_u_logs = u_logs_df.copy()
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
    if not u_logs_df.empty:
        st.table(u_logs_df.sort_values('timestamp', ascending=False).head(10)[['timestamp', 'module', 'action']])

# --- SECTION SUGGESTIONS AVANCÉES ---
with st.expander("🚀 Suggestions Stratégiques pour la Cartographie du Personnel"):
    st.markdown("""
    ### 🛡️ Qualité & Rigueur
    - **Taux de Litiges (Livreurs)** : Analyser le ratio de réclamations par rapport au nombre de BL livrés. Un livreur avec beaucoup de litiges peut nécessiter une formation sur la remise des colis.
    - **Intégrité du Pointage** : Comparer les pointages faits par le livreur avec les validations finales en comptabilité pour détecter les écarts de caisse.
    - **Précision Inventaire** : Calculer le pourcentage d'erreurs (écarts) trouvées lors de la confrontation pour chaque agent de saisie.

    ### ⚡ Productivité & Vitesse
    - **Temps de Livraison Moyen** : Calculer le temps entre le départ en mission et le retour du recouvrement.
    - **Réactivité SAV** : Délai moyen de traitement d'une réclamation client par le personnel concerné.

    ### 📊 Analyse Comportementale
    - **Score d'Engagement Numérique** : Utilisation des outils d'IA pour l'analyse et la saisie mobile (plus l'agent utilise le scan, plus son score augmente).
    - **Fiabilité Sanitaire** : Pour les agents de saisie, régularité des relevés de température (température oubliée = baisse du score).
    
    ### 🧠 Intelligence & Bien-être (Vision Futuriste)
    - **Détection du Risque de Burnout** : Identifier les employés dont la charge de travail (nombre d'actions/jour) dépasse de 50% la moyenne de l'équipe sur une longue période.
    - **Matrice de Polyvalence** : Cartographier qui sait tout faire (Inventaire + Logistique + Températures) pour identifier vos futurs superviseurs.
    - **Analyse de Ponctualité Numérique** : Heure de première action vs heure de début théorique pour suivre l'assiduité sans badgeuse physique.
    - **Prédiction de Performance (IA)** : Utiliser l'historique pour prédire si un livreur atteindra ses objectifs de recouvrement avant la fin du mois.
    - **Score de Cohésion** : Analyser les binômes (Livreur + Aide livreur) qui ont le moins de litiges pour créer les meilleures équipes.
    
    **💡 Astuce :** Nous pourrions intégrer un petit bouton "Humeur du jour" sur l'app mobile pour suivre le climat social en temps réel !
    """)
