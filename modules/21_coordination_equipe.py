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

# --- 2. AJOUT TÂCHE ---
with st.sidebar.expander("➕ Assigner une tâche", expanded=False):
    with st.form("form_task"):
        task_desc = st.text_area("Description de la tâche")
        assigned = st.selectbox("Assigner à", ["Tout le monde", "Agent 1", "Agent 2", "Agent 3", "Agent 4"])
        priority = st.select_slider("Priorité", options=["Basse", "Moyenne", "Haute", "Critique"])
        
        if st.form_submit_button("Assigner"):
            if task_desc:
                new_task = {
                    "id": len(df_tasks) + 1,
                    "creation_date": datetime.now().strftime("%d/%m/%Y"),
                    "task": task_desc,
                    "assigned_to": assigned,
                    "priority": priority,
                    "status": "À faire"
                }
                df_tasks = pd.concat([df_tasks, pd.DataFrame([new_task])], ignore_index=True)
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.success("Tâche assignée !")
                st.rerun()

# --- 3. DASHBOARD KANBAN ---
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
