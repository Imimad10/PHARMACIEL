import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils_gsheets import load_gs_data
from utils_ia import ask_ai, is_ia_enabled

st.title("📈 Prévision de Charge IA")
st.markdown("### Anticipez vos besoins en personnel et matériel")

# --- 1. COLLECTE DONNÉES HISTORIQUES ---
TASKS_WORKSHEET = "DB_Tasks_Team"
TASKS_FALLBACK = "data/db_tasks.csv"
COLS_TASKS = ["id", "creation_date", "task", "assigned_to", "priority", "status"]
df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, COLS_TASKS)

# --- 2. ANALYSE PRÉDICTIVE ---
st.subheader("🔮 Prévisions pour les 7 prochains jours")

if not df_tasks.empty:
    with st.spinner("Analyse des tendances historiques..."):
        # On simule une analyse de tendance basée sur les jours de la semaine
        # Dans un vrai système, on utiliserait Prophet ou un modèle de série temporelle
        
        # Exemple de prompt pour l'IA
        stats_par_jour = df_tasks.groupby('creation_date').size().to_dict()
        
        prompt = f"""
        Tu es un analyste prédictif. Voici l'historique du nombre de tâches par jour : {stats_par_jour}.
        En te basant sur ces données, prédis la charge de travail pour la semaine prochaine.
        Identifie quel jour sera le plus chargé et donne des conseils de planification.
        Sois précis et utile pour un chef d'entrepôt.
        """
        
        if is_ia_enabled():
            prediction = ask_ai(prompt)
            st.success("Analyse Prédictive de l'IA :")
            st.markdown(prediction)
        
        # Graphique de tendance simulé
        st.divider()
        st.markdown("#### 📊 Tendance de volume projetée")
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        # On simule des données basées sur un cycle hebdo
        data_sim = pd.DataFrame({
            'Jour': jours,
            'Charge Estimée (%)': [65, 85, 95, 75, 100, 40, 20]
        })
        st.line_chart(data_sim.set_index('Jour'))
else:
    st.info("Pas assez de données pour générer une prévision. Continuez à utiliser le module 'Coordination Équipe' pour alimenter l'historique.")

st.divider()
st.info("💡 Conseil : Utilisez ces prévisions pour décider si Islem doit se concentrer uniquement sur la préparation ou s'il pourra aider Ayoub et Seif.")
