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

# --- AJOUT TÂCHE MANUELLE ---
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
        assigned = col1.selectbox("👤 Assigner à", agents)
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

# --- ASSISTANT IA PLANIFICATION ---
with st.expander("🤖 Assistant IA - Planification & Équité", expanded=True):
    agents_str = ", ".join(agents) if agents else "Ayoub, Islem, Seif, Imad"
    st.info(f"L'IA planifie et répartit le travail équitablement entre : **{agents_str}**")

    col_ia1, col_ia2 = st.columns([2, 1])
    with col_ia1:
        situation = st.text_area(
            "📋 Situation globale de l'entrepôt :",
            placeholder="Ex: Arrivage de 200 colis ce matin, 3 livreurs disponibles, chambre froide à vérifier, 15 réclamations en attente..."
        )
    with col_ia2:
        st.markdown("**🎯 Missions rapides à inclure**")
        quick_missions = []
        for cat, missions in MISSION_CATALOGUE.items():
            if st.checkbox(cat, key=f"qm_{cat}"):
                quick_missions.append(cat)

    if st.button("🧠 Répartir Équitablement les Missions", use_container_width=True, type="primary"):
        if situation or quick_missions:
            with st.spinner("L'IA calcule la meilleure répartition..."):
                missions_context = ""
                if quick_missions:
                    missions_context = "\nMissions prioritaires demandées : " + ", ".join(quick_missions)

                all_missions_list = "\n".join(
                    [f"  - {m}" for cat in MISSION_CATALOGUE.values() for m in cat]
                )
                prompt = f"""Tu es un expert en management logistique d'un grossiste pharmaceutique en Algérie.

Situation du jour : {situation}{missions_context}

Agents disponibles : {agents_str}

Catalogue complet des missions disponibles :
{all_missions_list}

Règles de répartition :
1. Priorise les missions CRITIQUE avant tout le reste.
2. Chaque agent doit avoir un maximum de 3 missions actives simultanément.
3. Les missions Chambre Froide et Péremptions sont prioritaires pour la conformité.
4. Les missions Expédition/Dispatching doivent être finies avant 14h.
5. Répartis équitablement la charge de travail.

Donne un plan de journée clair par agent avec les missions assignées et l'ordre d'exécution recommandé. Utilise des emojis et sois concis."""
                conseil = ask_ai(prompt)
                play_sound("ai")
                st.success("🗓️ Plan de journée IA suggéré :")
                st.markdown(conseil)
        else:
            st.warning("Décrivez la situation ou cochez des catégories de missions.")

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
                available_next = [a for a in agents if a != row['assigned_to']]
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
                available_agents = [a for a in agents if a != row['assigned_to']]
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
            
        if is_admin_coord and st.button("📄 Générer Rapport de Primes (PDF)"):
            st.success("Rapport mensuel généré. Vous pouvez le présenter à la direction.")
    else:
        st.info("Aucune donnée disponible.")
