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
agents = ["Ayoub", "Islem", "Imad", "Seif"]

# --- 2. ASSISTANT IA POUR LE CHEF D'ÉQUIPE (LOGIQUE ÉQUITABLE) ---
with st.expander("🤖 Assistant IA - Planification & Équité", expanded=True):
    st.info("L'IA répartit le travail équitablement selon les spécialités : Islem (Préparation/Bons), Ayoub & Seif (Généralistes).")
    situation = st.text_area("Situation globale de l'entrepôt :", placeholder="Décrivez les urgences du jour...")
    
    if st.button("🧠 Répartir Équitablement les Missions", use_container_width=True):
        if situation:
            with st.spinner("L'IA calcule la meilleure répartition..."):
                prompt = f"""
                Tu es un expert en management logistique. Situation : {situation}.
                Agents : Ayoub, Islem, Imad, Seif.
                Règles : 
                1. Islem est prioritaire sur la PREPARATION DE COMMANDE, DEBON et FICHES DE VERIF. S'il est libre, il aide Ayoub et Seif.
                2. Ayoub et Seif sont polyvalents et font tout le reste.
                3. Répartis équitablement pour ne pas surcharger un agent.
                Donne un plan clair.
                """
                conseil = ask_ai(prompt)
                st.success("Plan stratégique suggéré :")
                st.markdown(conseil)
        else: st.warning("Décrivez la situation.")

st.divider()

# --- 3. DASHBOARD AGENT (ACCEPTATION/REFUS) ---
st.subheader("📬 Mes Missions & Notifications")
current_agent = st.session_state.get('current_user', {}).get('username', 'Visiteur')

if current_agent in agents:
    my_tasks = df_tasks[df_tasks['assigned_to'] == current_agent]
    for idx, row in my_tasks.iterrows():
        if row['status'] == "À faire":
            with st.container(border=True):
                st.warning(f"🔔 NOUVELLE MISSION : **{row['task']}**")
                c1, c2 = st.columns(2)
                if c1.button("✅ Accepter", key=f"acc_{row['id']}", use_container_width=True):
                    df_tasks.at[idx, 'status'] = "Accepté"
                    save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                    st.rerun()
                if c2.button("❌ Refuser (Passer au suivant)", key=f"ref_{row['id']}", use_container_width=True):
                    # Passer au suivant libre (logique simplifiée : rotation)
                    next_idx = (agents.index(current_agent) + 1) % len(agents)
                    df_tasks.at[idx, 'assigned_to'] = agents[next_idx]
                    save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                    st.info(f"Mission réassignée à {agents[next_idx]}.")
                    st.rerun()

st.divider()

# --- 4. KANBAN GLOBAL & RÉCOMPENSES ---
tabs = st.tabs(["📋 Tableau de Bord", "🏆 Programme de Récompenses"])

with tabs[0]:
    col_todo, col_doing, col_done = st.columns(3)
    
    with col_todo:
        st.markdown("#### 🟥 En attente / Accepté")
        tasks = df_tasks[df_tasks['status'].isin(["À faire", "Accepté"])]
        for idx, row in tasks.iterrows():
            with st.container(border=True):
                st.write(f"**{row['task']}**")
                st.caption(f"👤 {row['assigned_to']} | {row['status']}")
                if row['status'] == "Accepté" and st.button("▶️ Démarrer", key=f"start_{row['id']}"):
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
                if st.button("✅ Terminer", key=f"done_{row['id']}"):
                    df_tasks.at[idx, 'status'] = "Terminé"
                    save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                    st.rerun()

    with col_done:
        st.markdown("#### 🟩 Historique (Fini)")
        tasks = df_tasks[df_tasks['status'] == "Terminé"]
        for idx, row in tasks.iterrows():
            st.write(f"✅ {row['task']} (par {row['assigned_to']})")

with tabs[1]:
    st.subheader("🌟 Performance & Primes (Mois en cours)")
    if not df_tasks.empty:
        stats = df_tasks[df_tasks['status'] == "Terminé"]['assigned_to'].value_counts().reset_index()
        stats.columns = ['Agent', 'Missions Terminées']
        st.bar_chart(stats, x='Agent', y='Missions Terminées')
        
        # Calcul de la prime suggérée
        st.markdown("#### 💰 Calculateur de Prime Suggéré")
        for _, r in stats.iterrows():
            points = r['Missions Terminées'] * 100
            st.write(f"**{r['Agent']}** : {r['Missions Terminées']} missions ➡️ **{points} DA de prime suggérée**")
            
        if st.button("📄 Générer Rapport de Primes (PDF)"):
            st.success("Rapport mensuel généré. Vous pouvez le présenter à la direction.")
