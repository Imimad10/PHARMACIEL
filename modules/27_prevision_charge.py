import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from utils_gsheets import load_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK
from utils_ia import ask_ai, is_ia_enabled

# st.set_page_config() might already be called by app.py if this is run via st.navigation, so we skip it to prevent Double Set Page Config errors.
# Actually, since it's a module, st.set_page_config is usually handled by app.py.

st.title("📈 Prévision de Charge IA Globale")
st.markdown("### Anticipez vos besoins en personnel et matériel à partir de l'ensemble de vos données")

# --- 1. COLLECTE DES DONNÉES DE TOUS LES MODULES ---
with st.spinner("Collecte des données depuis l'Admin Centrale..."):
    # Historique des tâches
    df_tasks = load_gs_data("DB_Tasks_Team", "data/db_tasks.csv", ["id", "creation_date", "task", "assigned_to", "priority", "status"])
    
    # Volumes de Stock
    df_stock = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", [])
    vol_stock = len(df_stock) if not df_stock.empty else 0
    
    # Ventes et Expéditions (Factures à préparer)
    df_ventes = load_gs_data("Analyse_Ventes_Perf", "data/db_ventes_performance.csv", [])
    vol_ventes = df_ventes['quantite'].sum() if not df_ventes.empty and 'quantite' in df_ventes.columns else len(df_ventes)
    
    # Réclamations en cours
    df_reclam = load_gs_data("Reclamations", "data/db_reclamations.csv", [])
    vol_reclam = len(df_reclam) if not df_reclam.empty else 0
    
    # Équipe disponible
    df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username"])
    vol_users = len(df_users) if not df_users.empty else 4

# --- 2. AFFICHAGE DES KPIs GLOBAUX ---
st.subheader("📊 Métriques de Charge Actuelle")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Volume Stock (Lots)", f"{vol_stock:,}")
c2.metric("Volume Ventes (Mouvements)", f"{vol_ventes:,.0f}")
attente = (len(df_tasks[df_tasks['status'] != 'Terminé']) if not df_tasks.empty and 'status' in df_tasks.columns else 0) + vol_reclam
c3.metric("Dossiers/Tâches en attente", attente)
c4.metric("Capacité Équipe", f"{vol_users} agents")

st.divider()

# --- 3. ANALYSE PRÉDICTIVE IA ---
st.subheader("🔮 Analyse Multidimensionnelle par l'IA")
st.write("L'IA croise les données de tous vos modules (Ventes, Stocks, Réclamations, Équipe) pour prédire vos besoins.")

if st.button("🧠 Lancer la prévision complète (IA)", type="primary"):
    with st.spinner("Le Cortex IA analyse l'ensemble des flux de l'entreprise..."):
        
        # Préparation du contexte pour l'IA
        stats_taches = df_tasks.groupby('creation_date').size().tail(7).to_dict() if not df_tasks.empty and 'creation_date' in df_tasks.columns else "Pas d'historique de tâches récentes"
        
        prompt = f"""
        Tu es le directeur des opérations Supply Chain de DarPharm. Fais une prévision de la charge de travail pour les prochains jours en te basant sur ces indicateurs multi-modules que je viens de synchroniser :
        
        1. **Inventaire Actif** : {vol_stock} lots en stock à gérer et auditer.
        2. **Activité d'Expédition/Ventes** : {vol_ventes} unités récemment mouvementées (indicateur de la charge de préparation).
        3. **Équipe Logistique** : {vol_users} collaborateurs disponibles.
        4. **Litiges/Réclamations/SAV** : {vol_reclam} dossiers en cours (nécessite du temps administratif).
        5. **Historique de coordination** : {stats_taches} (Tâches créées par jour).
        
        Ta mission :
        - Prédis la charge de travail globale pour les 3 prochains jours.
        - Identifie le goulot d'étranglement probable (ex: l'équipe est trop petite par rapport au volume de ventes, ou les réclamations vont ralentir la logistique).
        - Propose 3 actions concrètes de management (Ex: assigner la matinée aux préparations, l'après-midi aux inventaires).
        Sois professionnel, très analytique, et utilise le markdown et des emojis.
        """
        
        if is_ia_enabled():
            prediction = ask_ai(prompt)
            st.success("✅ Rapport Prédictif du Cortex IA généré :")
            st.markdown(f'<div style="background:rgba(255,255,255,0.05); padding:25px; border-radius:15px; border-left:5px solid #7c3aed; line-height:1.6;">{prediction}</div>', unsafe_allow_html=True)
        else:
            st.warning("L'IA est désactivée. Impossible de générer la prévision experte.")

# --- 4. VISUALISATION DES DONNÉES CROISÉES ---
st.divider()
st.markdown("#### 📈 Modélisation de la Charge Hebdomadaire")

jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
# Modèle dynamique basé sur les KPI réels
base_charge = 40
if vol_ventes > 1000: base_charge += 25
elif vol_ventes > 100: base_charge += 15
if vol_reclam > 10: base_charge += 15
if vol_users < 5: base_charge += 20

charge_estimee = [
    min(100, base_charge + 15),  # Lun (Reprise)
    min(100, base_charge + 20),  # Mar (Pic)
    min(100, base_charge + 25),  # Mer (Pic)
    min(100, base_charge + 5),   # Jeu
    min(100, base_charge + 10),  # Ven (Expéditions fin de semaine)
    min(100, max(10, base_charge - 20)), # Sam (Permanence)
    min(100, max(5, base_charge - 40))  # Dim (Repos)
]

data_sim = pd.DataFrame({
    'Jour': jours,
    'Charge de Travail (%)': charge_estimee
})

fig = px.area(data_sim, x="Jour", y="Charge de Travail (%)", 
              title="Projection de la Charge de Travail Globale (Modèle Dynamique)",
              color_discrete_sequence=["#5b6cf9"],
              markers=True)
fig.update_layout(yaxis=dict(range=[0, 105]), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig, use_container_width=True)

st.info("💡 **Astuce de l'Admin Centrale** : Les prévisions s'affinent automatiquement à chaque fois que vous importez de nouvelles données de Ventes ou d'Inventaire depuis le Master Data.")
