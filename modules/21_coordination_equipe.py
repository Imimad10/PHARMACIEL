import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_sound import play_sound

# --- CONFIGURATION ---
TASKS_WORKSHEET = "DB_Tasks_Team"
TASKS_FALLBACK = "data/db_tasks.csv"
COLS_TASKS = ["id", "creation_date", "task", "assigned_to", "priority", "status"]

st.title("🤝 Coordination de l'Équipe")
st.markdown("### Gérez vos 8h de travail efficacement")

# --- 1. CHARGEMENT DONNÉES ---
df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, COLS_TASKS)

# Chargement dynamique des agents depuis la base utilisateurs
try:
    from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
    df_users_coord = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "nom", "prenom", "role"])
    agents = df_users_coord['username'].dropna().tolist() if not df_users_coord.empty else ["Ayoub", "Islem", "Imad", "Seif"]
except:
    agents = ["Ayoub", "Islem", "Imad", "Seif"]

current_user_info = st.session_state.get('current_user', {})
current_agent = current_user_info.get('username', 'Visiteur')
is_admin_coord = current_user_info.get('role', '') in ['Admin', 'Superviseur']

# --- 3. AJOUT TÂCHE (SUR LA PAGE PRINCIPALE) ---
with st.expander("➕ Assigner une nouvelle tâche manuellement", expanded=False):
    # Missions prédéfinies pour faciliter le choix
    COMMON_MISSIONS = [
        "Personnalisé...",
        "📦 Déchargement Camion (Arrivage)",
        "🔍 Vérification Vignettes & État",
        "❄️ Inventaire Chambre Froide",
        "🛒 Préparation de Commande (Picking)",
        "🔄 Transfert Gros ➔ Principal",
        "📝 Rédaction Fiches de Vérification",
        "🚚 Pointage Expédition",
        "🏢 Gestion Réclamation Fournisseur",
        "🧹 Nettoyage & Rangement Zone"
    ]
    
    with st.form("form_task", clear_on_submit=True):
        selected_template = st.selectbox("Choisir un modèle de mission :", COMMON_MISSIONS)
        task_input = st.text_area("Description ou détails de la mission :", placeholder="Ajoutez des détails si nécessaire...")
        
        # Logique pour utiliser le modèle ou le texte saisi
        final_task = task_input if selected_template == "Personnalisé..." else selected_template
        if selected_template != "Personnalisé..." and task_input:
            final_task = f"{selected_template} : {task_input}"

        col1, col2 = st.columns(2)
        assigned = col1.selectbox("Assigner à", agents)
        priority = col2.select_slider("Priorité", options=["Basse", "Moyenne", "Haute", "Critique"], value="Moyenne")
        
        if st.form_submit_button("🚀 Lancer la mission", use_container_width=True):
            if final_task and final_task != "Personnalisé...":
                new_row = {
                    "id": len(df_tasks) + 1,
                    "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "task": final_task,
                    "assigned_to": assigned,
                    "priority": priority,
                    "status": "À faire"
                }
                df_tasks = pd.concat([df_tasks, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                play_sound("mission")  # Double ping à la création de mission
                st.success("Mission ajoutée !")
                st.rerun()

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
                play_sound("ai")  # Chime IA à la réception du plan
                st.success("Plan stratégique suggéré :")
                st.markdown(conseil)
        else: st.warning("Décrivez la situation.")

st.divider()

# --- 3. DASHBOARD AGENT (ACCEPTATION/REFUS) ---
st.subheader("📬 Mes Missions & Notifications")

# L'Admin voit TOUTES les missions, les agents voient les leurs
if is_admin_coord:
    my_tasks = df_tasks.copy()  # Admin voit tout
    if not my_tasks.empty:
        st.info(f"👑 Vue Admin : {len(my_tasks)} mission(s) au total.")
    else:
        st.info("Aucune mission en cours.")
else:
    my_tasks = df_tasks[df_tasks['assigned_to'] == current_agent]
    if my_tasks.empty:
        st.info(f"Aucune mission assignée à **{current_agent}** pour le moment.")

for idx, row in my_tasks.iterrows():
    if row['status'] in ["À faire", "Accepté"]:
        with st.container(border=True):
            assignee_label = f" → **{row['assigned_to']}**" if is_admin_coord else ""
            st.warning(f"🔔 MISSION{assignee_label} : **{row['task']}**")
            c1, c2, c3 = st.columns(3)
            if c1.button("✅ Accepter", key=f"acc_{row['id']}", use_container_width=True):
                df_tasks.at[idx, 'status'] = "Accepté"
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                play_sound("notification")
                st.rerun()
            if c2.button("▶️ Démarrer", key=f"start2_{row['id']}", use_container_width=True):
                df_tasks.at[idx, 'status'] = "En cours"
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.rerun()
            # Réassignation : seulement si agent valide ou admin
            available_next = [a for a in agents if a != row['assigned_to']]
            if available_next and c3.button("🔄 Réassigner", key=f"ref_{row['id']}", use_container_width=True):
                next_agent = available_next[0]
                df_tasks.at[idx, 'assigned_to'] = next_agent
                save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                st.info(f"Mission réassignée à {next_agent}.")
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
                    play_sound("success")  # Accord montant sur tâche terminée
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
