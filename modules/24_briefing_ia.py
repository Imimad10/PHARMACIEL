import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils_gsheets import load_gs_data
from utils_ia import ask_ai, is_ia_enabled

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    .briefing-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .briefing-card:hover {
        border-color: #5b6cf9;
        box-shadow: 0 15px 50px rgba(91, 108, 249, 0.15);
    }
    .briefing-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 5px;
    }
    .briefing-subtitle {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 25px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .briefing-content {
        font-size: 1.15rem;
        line-height: 1.7;
        color: #334155;
        font-family: 'Outfit', sans-serif;
    }
    .stat-pill {
        display: block;
        padding: 10px 15px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 10px;
        border: 1px solid rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="briefing-title">☕ Le "Pulse" Quotidien</div>', unsafe_allow_html=True)
st.markdown('<div class="briefing-subtitle">Briefing Stratégique IA pour le Trio de Direction (Imad, Rami, Karim)</div>', unsafe_allow_html=True)

if not is_ia_enabled():
    st.warning("⚠️ L'IA n'est pas activée. Configurez l'API dans l'Administration Centrale.")
    st.stop()

# --- COLLECTE DES DATAS (Le carburant de l'IA) ---
# Tâches
df_tasks = load_gs_data("DB_Tasks_Team", "data/db_tasks.csv", ["creation_date", "task", "status", "assigned_to"])
# Frigo
df_frigo = load_gs_data("Suivi_Frigo", "suivi_data.csv", ["Date", "Statut", "Chambre", "Température"])
# Recouvrement
df_recouv = load_gs_data("Recouvrement", "data_recouvrement.csv", ["Client", "Statut", "Reste à payer"])

col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 Générer le Flash IA de 7h00", use_container_width=True, type="primary"):
        with st.spinner("L'IA compile les rapports des équipes et génère la synthèse stratégique..."):
            
            # --- 1. Agrégation des Statistiques ---
            aujourdhui = datetime.now().strftime("%d/%m/%Y")
            hier = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            
            # KPI Tâches
            if not df_tasks.empty and 'creation_date' in df_tasks.columns:
                tasks_hier = df_tasks[df_tasks['creation_date'] == hier]
                tasks_encours = df_tasks[df_tasks['status'].isin(['Accepté', 'En cours'])]
                nb_tasks_done = len(tasks_hier[tasks_hier['status'] == 'Terminé'])
                nb_tasks_tot = len(tasks_hier)
            else:
                nb_tasks_done = nb_tasks_tot = 0
                tasks_encours = []
                
            # KPI Frigo
            alertes_frigo = 0
            if not df_frigo.empty and 'Date' in df_frigo.columns:
                frigo_hier = df_frigo[df_frigo['Date'] == hier]
                alertes_frigo = len(frigo_hier[frigo_hier['Statut'] == 'ALERTE'])
                
            # KPI Recouvrement
            recouv_attente = 0
            if not df_recouv.empty and 'Statut' in df_recouv.columns:
                recouv_attente = len(df_recouv[df_recouv['Statut'] == 'En attente'])
                
            # --- 2. Prompt Hyper-Spécifique ---
            prompt = f"""
            Tu es l'Intelligence Artificielle d'assistance stratégique de DarPharm.
            Rédige un Briefing Matinal Flash (5 phrases maximum) exclusivement destiné au "Trio" de direction :
            - Imad (Toi, le Gestionnaire global et big boss)
            - Rami (Superviseur & Chef de Dépôt / Préparation)
            - Karim (Chef de Parc & Logistique)
            
            Voici les données de la veille et du matin :
            - Tâches équipe : {nb_tasks_done} terminées sur {nb_tasks_tot} hier.
            - Tâches critiques en attente ce matin : {len(tasks_encours)}.
            - Température Frigos : {alertes_frigo} alertes détectées hier.
            - Factures / Recouvrement : {recouv_attente} dossiers en attente.
            
            Consignes de rédaction :
            1. Commence par un "Bonjour Imad, Rami, Karim." très pro et dynamique.
            2. Donne les chiffres clés sans faire de liste à puces (paragraphe fluide).
            3. Si 0 alerte frigo, souligne que la chaîne du froid est parfaite, sinon demande une inspection immédiate.
            4. Finis par UNE recommandation stratégique hyper-précise et autoritaire (ex: "Karim, verrouille le recouvrement. Rami, surveille la préparation").
            5. Sois direct, impactant, format "Executive Summary". Zéro blabla, ton de leader.
            """
            
            briefing = ask_ai(prompt)
            
            # --- 3. Affichage Premium ---
            st.markdown(f"""
            <div class="briefing-card">
                <div style="font-weight: 800; color: #5b6cf9; margin-bottom: 10px; font-size: 1.2rem;">📅 SYNTHÈSE DU {aujourdhui}</div>
                <div class="briefing-content">
                    {briefing.replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("💡 **Astuce** : Prenez ce texte en capture ou copiez-le dans le groupe WhatsApp du Trio pour aligner tout le monde dès l'ouverture du dépôt.")

with col2:
    st.markdown('<div class="briefing-subtitle" style="margin-bottom:10px;">📊 Brut (24h)</div>', unsafe_allow_html=True)
    
    val_tasks = len(df_tasks[df_tasks["status"] == "Terminé"]) if not df_tasks.empty and "status" in df_tasks.columns else 0
    val_alertes = len(df_frigo[df_frigo["Statut"] == "ALERTE"]) if not df_frigo.empty and "Statut" in df_frigo.columns else 0
    val_litiges = len(df_recouv[df_recouv["Statut"] == "Litige"]) if not df_recouv.empty and "Statut" in df_recouv.columns else 0
    
    st.markdown(f'<div class="stat-pill" style="background: #eff6ff; color: #2563eb;">✅ Tâches (Hier) : {val_tasks}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-pill" style="background: #fef2f2; color: #ef4444;">🚨 Alertes Frigo : {val_alertes}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-pill" style="background: #fdf4ff; color: #c026d3;">💰 Litiges Recouv. : {val_litiges}</div>', unsafe_allow_html=True)
    
    st.divider()
    st.caption("Ce briefing est une compilation algorithmique générée par IA en fonction des entrées de l'ensemble de l'équipe sur DarPharm.")

