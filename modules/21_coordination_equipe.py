import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
TASKS_WORKSHEET = "DB_Tasks_Team"
TASKS_FALLBACK = "data/db_tasks.csv"
COLS_TASKS = ["id", "creation_date", "task", "assigned_to", "priority", "status"]

st.title("🤝 Coordination de l'Équipe")
st.markdown("### Gérez vos 8h de travail efficacement")

# --- 1. CHARGEMENT DONNÉES ---
df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, COLS_TASKS)
agents = ["Tout le monde", "Ayoub", "Islem", "Imad", "Seif"]

# --- 2. ASSISTANT IA POUR LE CHEF D'ÉQUIPE ---
with st.expander("🤖 Assistant IA - Planification des Missions", expanded=True):
    st.info("Décrivez la situation actuelle (ex: '3 camions arrivés, 50 réclamations, inventaire frigo à faire') et l'IA va répartir le travail.")
    situation = st.text_area("Situation globale de l'entrepôt :", placeholder="Décrivez ce qu'il y a à faire aujourd'hui...")
    
    if st.button("🧠 Générer Plan d'Attaque IA", use_container_width=True):
        if situation:
            with st.spinner("L'IA analyse la charge de travail..."):
                prompt = f"""
                Tu es un expert en logistique. Voici la situation de l'entrepôt : {situation}.
                Tu as 4 agents : Ayoub, Islem, Imad, Seif.
                Suggère une répartition précise des tâches pour une journée de 8h.
                Sois direct, efficace et donne des ordres clairs.
                Format suggéré :
                - Ayoub : [Mission]
                - Islem : [Mission]
                - Imad : [Mission]
                - Seif : [Mission]
                """
                conseil = ask_ai(prompt)
                st.success("Plan suggéré par l'IA :")
                st.markdown(conseil)
        else:
            st.warning("Veuillez décrire la situation pour obtenir un conseil.")

st.divider()

# --- 3. AJOUT TÂCHE (SUR LA PAGE PRINCIPALE) ---
with st.expander("➕ Assigner une nouvelle tâche manuellement", expanded=False):
    with st.form("form_task", clear_on_submit=True):
        task_desc = st.text_area("Quelle est la mission ?", placeholder="Ex: Décharger le camion de 14h...")
        
        col1, col2 = st.columns(2)
        assigned = col1.selectbox("Assigner à", agents)
        priority = col2.select_slider("Priorité", options=["Basse", "Moyenne", "Haute", "Critique"], value="Moyenne")
        
        if st.form_submit_button("🚀 Lancer la mission", use_container_width=True):
            if task_desc:
                # Calcul de l'ID
                next_id = 1
                if not df_tasks.empty and 'id' in df_tasks.columns:
                    try:
                        next_id = int(df_tasks['id'].max()) + 1
                    except: next_id = len(df_tasks) + 1

                new_task = {
                    "id": next_id,
                    "creation_date": datetime.now().strftime("%d/%m/%Y"),
                    "task": task_desc,
                    "assigned_to": assigned,
                    "priority": priority,
                    "status": "À faire"
                }
                df_tasks = pd.concat([df_tasks, pd.DataFrame([new_task])], ignore_index=True)
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.success(f"Mission '{task_desc[:20]}...' assignée avec succès !")
                st.rerun()
            else:
                st.error("Veuillez décrire la tâche avant d'assigner.")

# --- 4. DASHBOARD KANBAN ---
col_todo, col_doing, col_done = st.columns(3)

with col_todo:
    st.markdown("#### 🟥 À faire")
    tasks = df_tasks[df_tasks['status'] == "À faire"]
    for idx, row in tasks.iterrows():
        with st.container(border=True):
            st.write(f"**{row['task']}**")
            st.caption(f"👤 {row['assigned_to']} | 🚩 {row['priority']}")
            if st.button("Démarrer", key=f"start_{row['id']}"):
                df_tasks.at[idx, 'status'] = "En cours"
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.rerun()

with col_doing:
    st.markdown("#### 🟧 En cours")
    tasks = df_tasks[df_tasks['status'] == "En cours"]
    for idx, row in tasks.iterrows():
        with st.container(border=True):
            st.write(f"**{row['task']}**")
            st.caption(f"👤 {row['assigned_to']}")
            if st.button("Terminer", key=f"done_{row['id']}"):
                df_tasks.at[idx, 'status'] = "Terminé"
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.rerun()

with col_done:
    st.markdown("#### 🟩 Terminé")
    tasks = df_tasks[df_tasks['status'] == "Terminé"]
    for idx, row in tasks.iterrows():
        with st.expander(f"✅ {row['task'][:30]}..."):
            st.write(row['task'])
            st.caption(f"Fait par : {row['assigned_to']}")
            if st.button("Supprimer", key=f"del_{row['id']}"):
                df_tasks = df_tasks.drop(idx)
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.rerun()
