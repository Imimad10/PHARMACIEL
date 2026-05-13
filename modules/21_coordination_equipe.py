import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_sound import play_sound
from utils_ia import ask_ai, is_ia_enabled

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

# ─────────────────────────────────────────────────────────
# 🧑‍🤝‍🧑 SÉLECTEUR D'ÉQUIPE DU JOUR
# ─────────────────────────────────────────────────────────
st.markdown("#### 🧑‍🤝‍🧑 Équipe disponible aujourd'hui")

if "active_agents" not in st.session_state or not st.session_state.active_agents:
    st.session_state.active_agents = agents[:]

col_team1, col_team2 = st.columns([4, 1])
with col_team1:
    selected_agents = st.multiselect(
        "👥 Membres présents aujourd'hui :",
        options=agents,
        default=[a for a in st.session_state.active_agents if a in agents],
        placeholder="Sélectionner les agents disponibles..."
    )
with col_team2:
    st.write("")
    st.write("")
    if st.button("✅ Confirmer", use_container_width=True, type="primary"):
        if selected_agents:
            st.session_state.active_agents = selected_agents
            play_sound("notification")
            st.rerun()
        else:
            st.warning("Sélectionnez au moins un agent.")

active_agents = st.session_state.get("active_agents", agents) or agents
if active_agents:
    agents_present = " · ".join(active_agents)
    st.caption(f"🟢 Présents : **{agents_present}** ({len(active_agents)} agent(s))")

st.divider()

# ============================================================
# CATALOGUE COMPLET DES MISSIONS (basé sur tous les modules)
# ============================================================
MISSION_CATALOGUE = {
    "📦 Stocks & Inventaire": [
        "📦 Déchargement Camion (Arrivage Fournisseur)",
        "🔍 Vérification Vignettes & État des Produits (Réception)",
        "📋 Inventaire Triple — Comptage + Saisie Système",
        "📊 Mise à jour Liste Officielle des Lots (DDP)",
        "⏳ Analyse des Péremptions — Identifier Périmés & Critiques",
        "🏷️ Étiquetage Produits Zone Vrac / Sans Étiquette",
        "🔄 Transfert Stock Gros ➔ Stock Principal",
        "🗃️ Rangement & Organisation des Rayons par Zone",
        "📝 Rédaction Fiches de Vérification (Bon de Réception)",
        "🔢 Comptage Physique des Unités (Zone Détail)",
    ],
    "❄️ Chaîne du Froid": [
        "❄️ Relevé Températures Chambre Froide (Matin)",
        "❄️ Relevé Températures Chambre Froide (Après-midi)",
        "🌡️ Vérification Conformité Température < 8°C",
        "📋 Inventaire Complet Chambre Froide",
        "🚨 Alerte Rupture Chaîne Froide — Inspection Urgente",
        "🔧 Maintenance Matériel Réfrigération (Signalement)",
    ],
    "🚚 Expédition & Logistique": [
        "🚚 Pointage Expédition LogiPharm (Dispatching)",
        "📦 Préparation Colis Réclamations (DEPOSER / ECHANGE)",
        "🏷️ Génération Étiquettes Réclamation & Impression",
        "🗺️ Organisation Tournée Livreur (Ordre de Route)",
        "🖨️ Génération Feuille de Route PDF (par Secteur)",
        "📲 Scan QR Code Arrivage & Validation",
        "✅ Validation Dispatching par Région",
        "📊 Suivi Statut Livraisons (En cours / Livrés)",
    ],
    "💰 Recouvrement & Finance": [
        "💰 Pointage Factures Clients Non Réglées",
        "📞 Relance Téléphonique Clients en Retard",
        "💳 Encaissement & Validation Paiement Reçu",
        "📄 Archivage Dossier Recouvrement (Clôturé)",
        "📊 Rapport Mensuel des Créances",
        "🔁 Mise à jour Statut Paiement (Partiel / Réglé)",
    ],
    "⚠️ Qualité & Conformité": [
        "🛡️ Contrôle Qualité — Vérification Conformité Produits",
        "⏳ Retrait Produits Périmés (Quarantaine)",
        "📋 Rapport Litige Fournisseur (Produits Non Conformes)",
        "🏷️ Mise en Place Plan de Libération des Stocks Critiques",
        "📊 Analyse DDP — Rapport Péremptions PDF",
        "🔴 Zone Rouge — Destruction / Retour Produits Périmés",
    ],
    "🤖 IA & Numérique": [
        "🤖 Briefing IA — Consulter l'Assistant DarPharm",
        "☁️ Synchronisation Cloud GSheets (Export Données)",
        "📲 Vérification Mode Hors-Ligne / Connectivité",
        "📈 Consultation Tableau de Bord (KPIs du jour)",
        "🔔 Vérification Centre de Notifications IA",
    ],
    "👥 Administration & Équipe": [
        "📢 Briefing Matinal Équipe (Planification 8h)",
        "👤 Formation Nouveau Collaborateur (Prise en Main)",
        "🧹 Nettoyage & Rangement Zone de Travail",
        "📝 Rédaction Rapport Journalier d'Activité",
        "🏆 Évaluation Performance Mensuelle Équipe",
        "🔑 Gestion Accès Utilisateurs (Admin)",
    ],
}

# Flatten pour le selectbox
ALL_MISSIONS_FLAT = ["Personnalisé..."]
for cat, missions in MISSION_CATALOGUE.items():
    ALL_MISSIONS_FLAT.append(f"── {cat} ──")  # Séparateur de catégorie
    ALL_MISSIONS_FLAT.extend(missions)

# --- AJOUT TÂCHE MANUELLE (ADMIN SEULEMENT) ---
if is_admin_coord:
    with st.expander("➕ Assigner une nouvelle tâche manuellement", expanded=False):
        with st.form("form_task", clear_on_submit=True):
            cat_choice = st.selectbox("📂 Catégorie de mission", list(MISSION_CATALOGUE.keys()))
            selected_template = st.selectbox(
                "📋 Modèle de mission",
                ["Personnalisé..."] + MISSION_CATALOGUE[cat_choice]
            )
            task_input = st.text_area("✏️ Détails supplémentaires :", placeholder="Zone concernée, quantité, priorité spéciale...")

            final_task = task_input if selected_template == "Personnalisé..." else selected_template
            if selected_template != "Personnalisé..." and task_input:
                final_task = f"{selected_template} : {task_input}"

            col1, col2 = st.columns(2)
            assigned = col1.selectbox("👤 Assigner à", active_agents)
            priority = col2.select_slider("🎯 Priorité", options=["Basse", "Moyenne", "Haute", "Critique"], value="Moyenne")

            if st.form_submit_button("🚀 Lancer la mission", use_container_width=True, type="primary"):
                if final_task and final_task != "Personnalisé..." and not final_task.startswith("──"):
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
                    play_sound("mission")
                    st.success(f"✅ Mission assignée à **{assigned}** !")
                    st.rerun()
                else:
                    st.warning("Veuillez saisir ou choisir une description de mission valide.")
else:
    st.info("💡 Vous pouvez consulter, accepter ou terminer vos missions ci-dessous. Seul l'administrateur peut assigner de nouvelles tâches.")

# --- ASSISTANT IA PLANIFICATION (ADMIN SEULEMENT) ---
if is_admin_coord:
    with st.expander("🤖 Assistant IA - Planification Stratégique", expanded=True):
        agents_str = ", ".join(active_agents) if active_agents else "Ayoub, Islem, Seif, Imad"
        st.info(f"L'IA planifie le travail selon les spécialités. Équipe actuelle : **{agents_str}**")

        col_ia1, col_ia2 = st.columns([2, 1])
        with col_ia1:
            situation = st.text_area(
                "📋 Situation globale de l'entrepôt :",
                placeholder="Ex: Arrivage important de 300 colis, Islem doit finir les bons avant midi..."
            )
        with col_ia2:
            st.markdown("**🎯 Priorités équipe**")
            st.caption("- Islem : Bons/Factures/Expédition (9h-17h)\n- Autres : Stocks/Inventaire/Rangement")
            quick_missions = []
            for cat, missions in MISSION_CATALOGUE.items():
                if st.checkbox(cat, key=f"ia_cat_{cat}"):
                    quick_missions.append(cat)

        if st.button("🧠 Générer Plan Stratégique", use_container_width=True, type="primary"):
            if situation or quick_missions:
                with st.spinner("L'IA analyse la situation et prépare les ordres..."):
                    missions_context = ""
                    if quick_missions:
                        missions_context = "\nMissions prioritaires demandées : " + ", ".join(quick_missions)

                    all_missions_list = "\n".join(
                        [f"  - {m}" for cat in MISSION_CATALOGUE.values() for m in cat]
                    )
                    prompt = f"""Tu es un expert en management logistique pharmaceutique.
    Situation du jour : {situation}{missions_context}
    Équipe présente : {agents_str}

    RÈGLES MÉTIER :
    1. ISLEM : Uniquement : Bons de commande, Factures, Expédition/Logistique (9h-17h).
    2. AYOUB, SEIF, IMAD : Tout le reste (Stock, Inventaire, Froid, etc.).
    3. Max 3 missions actives par agent.

    Catalogue des missions :
    {all_missions_list}

    TA MISSION :
    1. Propose un plan de journée stratégique en français avec des emojis.
    2. À la fin de ta réponse, ajoute IMPÉRATIVEMENT un bloc JSON contenant la liste technique des missions à créer, exactement sous ce format :
    ```json
    [
      {{"agent": "Nom", "task": "Nom exact de la mission du catalogue", "priority": "Haute"}},
      ...
    ]
    ```
    N'utilise que les noms de missions présents dans le catalogue."""
                    
                    conseil = ask_ai(prompt)
                    play_sound("ai")
                    st.session_state["ia_suggestion"] = conseil
            else:
                st.warning("Veuillez décrire la situation.")

        if "ia_suggestion" in st.session_state:
            conseil_raw = st.session_state["ia_suggestion"]
            
            # Séparer le texte du JSON
            import re
            json_match = re.search(r"```json\s*(.*?)\s*```", conseil_raw, re.DOTALL)
            text_plan = conseil_raw
            suggested_tasks = []
            
            if json_match:
                text_plan = conseil_raw.replace(json_match.group(0), "").strip()
                try:
                    import json
                    suggested_tasks = json.loads(json_match.group(1))
                except: pass

            st.markdown("---")
            st.markdown("### 📋 Plan Stratégique Suggéré")
            st.markdown(text_plan)
            
            if suggested_tasks:
                st.markdown(f"#### ⚡ Action Rapide : {len(suggested_tasks)} missions détectées")
                cols = st.columns([2, 1])
                with cols[0]:
                    st.info("L'IA a préparé les ordres de mission pour l'équipe.")
                with cols[1]:
                    if st.button("🚀 Appliquer & Affecter Automatiquement", use_container_width=True, type="primary"):
                        new_rows = []
                        for task_data in suggested_tasks:
                            # Vérifier si l'agent est présent
                            if task_data.get("agent") in active_agents:
                                new_rows.append({
                                    "id": len(df_tasks) + len(new_rows) + 1,
                                    "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "task": task_data.get("task", "Mission personnalisée"),
                                    "assigned_to": task_data.get("agent"),
                                    "priority": task_data.get("priority", "Moyenne"),
                                    "status": "À faire"
                                })
                        
                        if new_rows:
                            df_tasks = pd.concat([df_tasks, pd.DataFrame(new_rows)], ignore_index=True)
                            save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                            play_sound("mission")
                            st.success(f"✅ {len(new_rows)} missions ont été créées et envoyées aux agents !")
                            del st.session_state["ia_suggestion"]
                            st.rerun()
            else:
                st.warning("⚠️ L'IA n'a pas pu générer le format technique automatique. Veuillez utiliser l'ajout manuel.")

st.divider()

# --- 3. MES MISSIONS PERSONNELLES (filtré par utilisateur, même pour l'Admin) ---
st.subheader("📬 Mes Missions & Notifications")

my_tasks = df_tasks[df_tasks['assigned_to'] == current_agent]

if my_tasks.empty:
    st.info(f"Aucune mission assignée à **{current_agent}** pour le moment.")
else:
    pending = my_tasks[my_tasks['status'].isin(["À faire", "Accepté"])]
    if pending.empty:
        st.success("✅ Toutes vos missions sont en cours ou terminées.")
    
    for idx, row in pending.iterrows():
        with st.container(border=True):
            st.warning(f"🔔 **{row['task']}**")
            st.caption(f"🎯 Priorité : {row.get('priority', '—')} | Créé le : {row.get('creation_date', '—')}")
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
            if c3.button("❌ Refuser", key=f"ref_{row['id']}", use_container_width=True):
                available_next = [a for a in active_agents if a != row['assigned_to']]
                if available_next:
                    df_tasks.at[idx, 'assigned_to'] = available_next[0]
                    save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                    st.info(f"Mission réassignée à {available_next[0]}.")
                    st.rerun()

# --- VUE ADMIN : Gestion de toute l'équipe ---
if is_admin_coord:
    with st.expander("👑 Vue Admin — Gestion de toutes les missions", expanded=False):
        df_all_pending = df_tasks[df_tasks['status'].isin(["À faire", "Accepté", "En cours"])]
        if df_all_pending.empty:
            st.info("Aucune mission active dans l'équipe.")
        else:
            for idx, row in df_all_pending.iterrows():
                col_a, col_b, col_c, col_d = st.columns([3, 1.5, 1.5, 1.5])
                col_a.write(f"**{row['task']}** — 👤 {row['assigned_to']}")
                col_b.write(f"🎯 {row.get('priority','—')}")
                col_c.write(f"📌 {row['status']}")
                # Réassignation admin
                available_agents = [a for a in active_agents if a != row['assigned_to']]
                if available_agents:
                    new_agent = col_d.selectbox(
                        "Réassigner", 
                        ["—"] + available_agents, 
                        key=f"admin_reassign_{row['id']}", 
                        label_visibility="collapsed"
                    )
                    if new_agent != "—":
                        df_tasks.at[idx, 'assigned_to'] = new_agent
                        save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                        st.success(f"Réassigné à {new_agent} !")
                        st.rerun()


st.divider()

# --- 4. KANBAN GLOBAL & RÉCOMPENSES ---
# Filtrage selon le rôle : Admin voit tout, les autres voient leurs tâches uniquement
if is_admin_coord:
    df_kanban = df_tasks.copy()
    st.caption("👑 Vue Admin — Toutes les missions de tous les agents.")
else:
    df_kanban = df_tasks[df_tasks['assigned_to'] == current_agent].copy()
    st.caption(f"👤 Vos missions personnelles — **{current_agent}**")

tabs = st.tabs(["📋 Tableau de Bord", "🏆 Programme de Récompenses"])

with tabs[0]:
    col_todo, col_doing, col_done = st.columns(3)
    
    with col_todo:
        st.markdown("#### 🟥 En attente / Accepté")
        tasks = df_kanban[df_kanban['status'].isin(["À faire", "Accepté"])]
        if tasks.empty:
            st.info("Aucune tâche.")
        for idx, row in tasks.iterrows():
            with st.container(border=True):
                st.write(f"**{row['task']}**")
                if is_admin_coord:
                    st.caption(f"👤 {row['assigned_to']} | {row['priority']} | {row['status']}")
                else:
                    st.caption(f"🎯 {row['priority']} | {row['status']}")
                if row['status'] == "Accepté" and st.button("▶️ Démarrer", key=f"start_{row['id']}"):
                    df_tasks.at[idx, 'status'] = "En cours"
                    save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                    st.rerun()

    with col_doing:
        st.markdown("#### 🟧 En cours")
        tasks = df_kanban[df_kanban['status'] == "En cours"]
        if tasks.empty:
            st.info("Aucune tâche.")
        for idx, row in tasks.iterrows():
            with st.container(border=True):
                st.write(f"**{row['task']}**")
                if is_admin_coord:
                    st.caption(f"👤 {row['assigned_to']}")
                if st.button("✅ Terminer", key=f"done_{row['id']}"):
                    df_tasks.at[idx, 'status'] = "Terminé"
                    save_gs_data(df_tasks, TASKS_WORKSHEET, TASKS_FALLBACK)
                    play_sound("success")
                    st.rerun()

    with col_done:
        st.markdown("#### 🟩 Terminées")
        tasks = df_kanban[df_kanban['status'] == "Terminé"]
        if tasks.empty:
            st.info("Aucune tâche terminée.")
        for idx, row in tasks.iterrows():
            agent_label = f" (par {row['assigned_to']})" if is_admin_coord else ""
            st.write(f"✅ {row['task']}{agent_label}")

with tabs[1]:
    st.subheader("🌟 Performance & Primes (Mois en cours)")
    
    if is_admin_coord:
        # L'Admin voit les stats de toute l'équipe
        df_stats_base = df_tasks
        st.info("📊 Vue globale de l'équipe.")
    else:
        # Chaque agent ne voit que ses propres stats
        df_stats_base = df_tasks[df_tasks['assigned_to'] == current_agent]
        st.info(f"📊 Vos statistiques personnelles — **{current_agent}**")
    
    if not df_stats_base.empty:
        stats = df_stats_base[df_stats_base['status'] == "Terminé"]['assigned_to'].value_counts().reset_index()
        stats.columns = ['Agent', 'Missions Terminées']
        
        if not stats.empty:
            st.bar_chart(stats, x='Agent', y='Missions Terminées')
            
            st.markdown("#### 💰 Calculateur de Prime Suggéré")
            for _, r in stats.iterrows():
                points = r['Missions Terminées'] * 100
                prime_label = f"**{r['Agent']}** : " if is_admin_coord else "Vous : "
                st.write(f"{prime_label}{r['Missions Terminées']} missions ➡️ **{points} DA de prime suggérée**")
        else:
            st.info("Aucune mission terminée pour le moment.")
            
        if is_admin_coord:
            st.divider()
            st.markdown("### 📝 Rapport de Fin de Journée (IA)")
            if st.button("📊 Générer le Bilan Quotidien", use_container_width=True, type="secondary"):
                with st.spinner("L'IA analyse les performances de la journée..."):
                    done_count = len(df_tasks[df_tasks['status'] == "Terminé"])
                    pending_count = len(df_tasks[df_tasks['status'].isin(["À faire", "En cours", "Accepté"])])
                    
                    # Détails par agent
                    agent_summary = ""
                    for agent in active_agents:
                        a_done = len(df_tasks[(df_tasks['assigned_to'] == agent) & (df_tasks['status'] == "Terminé")])
                        a_total = len(df_tasks[df_tasks['assigned_to'] == agent])
                        agent_summary += f"- {agent} : {a_done}/{a_total} missions terminées.\n"

                    prompt_eod = f"""Tu es un expert en management logistique. 
                    Bilan de la journée :
                    - Total missions terminées : {done_count}
                    - Missions restantes : {pending_count}
                    
                    Détail par agent :
                    {agent_summary}
                    
                    Donne un résumé motivant, analyse l'efficacité de l'équipe et donne 2 conseils pour demain pour améliorer la cadence. Utilise des emojis."""
                    
                    report = ask_ai(prompt_eod)
                    play_sound("ai")
                    st.success("📉 Bilan Stratégique du Jour :")
                    st.markdown(report)
            
            if st.button("📄 Exporter Rapport de Primes (PDF)", use_container_width=True):
                st.success("Rapport mensuel généré. Vous pouvez le présenter à la direction.")
    else:
        st.info("Aucune donnée disponible.")
