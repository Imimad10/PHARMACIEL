import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_ia import ask_ai
from utils_sound import play_sound

# --- CONFIGURATION ---
WORKSHEET_NAME = "DB_RH_Gestion"
FALLBACK_PATH = "data/db_rh.csv"
UPLOAD_DIR = "data/justificatifs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

COLUMNS = ["ID", "Date_Debut", "Date_Fin", "Agent", "Type", "Statut", "Commentaire", "Justificatif_Path", "Date_Creation"]

# --- UI ---
st.title("📅 Gestion RH & Planning")
st.markdown("### Permanences, Vacances et Absences")

show_sync_ui(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)
df_rh = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

# --- 1. LOGIQUE WEEKEND & PERMANENCE ---
def is_weekend(dt):
    # En Algérie (ou selon la demande), Vendredi (4) et Samedi (5) sont weekend
    # Dans Python datetime: Lundi=0, Mardi=1, ..., Vendredi=4, Samedi=5, Dimanche=6
    return dt.weekday() in [4, 5]

today = datetime.now()


tabs = st.tabs(["🕒 Permanence Samedi", "🏥 Absences & Congés", "📋 Planning Global", "🛡️ Validation Admin"])

# --- RÉCUPÉRATION AGENTS ---
from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username"])
agents_list = sorted(df_users['username'].unique().tolist()) if not df_users.empty else ["Ayoub", "Islem", "Seif", "admin_imad"]

# --- TAB 1 : PERMANENCE SAMEDI ---
with tabs[0]:
    st.subheader("🕒 Planifier la permanence du Samedi (09h-15h)")
    st.info("Utilisez ce formulaire pour désigner l'agent qui assurera le service minimal ce samedi.")
    
    with st.form("form_permanence"):
        c1, c2 = st.columns(2)
        agent_p = c1.selectbox("Collaborateur désigné", agents_list, key="p_agent")
        date_p = c2.date_input("Samedi concerné", value=today + timedelta(days=(5 - today.weekday()) % 7))
        
        obs_p = st.text_input("Commentaire (Optionnel)")
        
        if st.form_submit_button("📅 Enregistrer la Permanence", use_container_width=True, type="primary"):
            new_row = {
                "ID": len(df_rh) + 1,
                "Date_Debut": date_p.strftime("%Y-%m-%d"),
                "Date_Fin": date_p.strftime("%Y-%m-%d"),
                "Agent": agent_p,
                "Type": "Permanence Samedi",
                "Statut": "Validé",
                "Commentaire": obs_p,
                "Justificatif_Path": "",
                "Date_Creation": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            df_rh = pd.concat([df_rh, pd.DataFrame([new_row])], ignore_index=True)
            save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
            st.success(f"✅ Permanence enregistrée pour **{agent_p}** le {date_p}")
            st.rerun()

# --- TAB 2 : ABSENCES & CONGÉS ---
with tabs[1]:
    st.subheader("🏥 Déclarer une Absence ou un Congé")
    with st.form("form_absences"):
        c1, c2 = st.columns(2)
        agent_a = c1.selectbox("Collaborateur concerné", agents_list, key="a_agent")
        type_a = c2.selectbox("Type d'absence", ["Congé Annuel", "Maladie", "Récupération", "Absence Autorisée", "Urgence"])
        
        d1 = c1.date_input("Date de début", value=today, key="a_d1")
        d2 = c2.date_input("Date de fin (Inclus)", value=today, key="a_d2")
        
        uploaded_file = st.file_uploader("📎 Justificatif (PDF, JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])
        comm_a = st.text_area("Motif / Observations")
        
        if st.form_submit_button("🚀 Envoyer la demande", use_container_width=True, type="primary"):
            file_path = ""
            if uploaded_file:
                fname = f"JUST_{agent_a}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                file_path = os.path.join(UPLOAD_DIR, fname)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            new_row = {
                "ID": len(df_rh) + 1,
                "Date_Debut": d1.strftime("%Y-%m-%d"),
                "Date_Fin": d2.strftime("%Y-%m-%d"),
                "Agent": agent_a,
                "Type": type_a,
                "Statut": "En attente",
                "Commentaire": comm_a,
                "Justificatif_Path": file_path,
                "Date_Creation": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            df_rh = pd.concat([df_rh, pd.DataFrame([new_row])], ignore_index=True)
            save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
            st.success("✅ Demande envoyée pour validation admin.")
            st.rerun()

# --- TAB 3 : PLANNING GLOBAL ---
with tabs[2]:
    st.subheader("📊 Suivi du Personnel")
    df_view = df_rh.copy()
    
    # Filtres simples
    c_f1, c_f2 = st.columns(2)
    f_agent = c_f1.multiselect("Filtrer par agent", agents_list)
    f_type = c_f2.multiselect("Type d'événement", df_rh['Type'].unique() if not df_rh.empty else [])
    
    if f_agent: df_view = df_view[df_view['Agent'].isin(f_agent)]
    if f_type: df_view = df_view[df_view['Type'].isin(f_type)]
    
    st.dataframe(df_view.sort_values("Date_Debut", ascending=False), use_container_width=True, hide_index=True)
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🤖 Analyser la couverture (IA)", use_container_width=True):
            with st.spinner("Analyse..."):
                res = ask_ai(f"Analyse ce planning : {df_view.to_string()}. Y a-t-il des anomalies ?")
                st.info(res)
                
    with c_btn2:
        from utils_pdf import generate_rh_planning_pdf
        pdf_bytes = generate_rh_planning_pdf(df_view)
        st.download_button(
            "📥 Télécharger le Planning (PDF)",
            pdf_bytes,
            f"Planning_RH_{datetime.now().strftime('%Y%m%d')}.pdf",
            "application/pdf",
            use_container_width=True
        )

# --- TAB 4 : VALIDATION ADMIN ---
with tabs[3]:
    st.subheader("🛡️ Espace de Validation")
    if st.session_state.current_user.get('role') != 'Admin':
        st.warning("Accès réservé aux administrateurs.")
    else:
        df_pending = df_rh[df_rh['Statut'] == "En attente"]
        if df_pending.empty:
            st.success("Aucune demande en attente.")
        else:
            for idx, row in df_pending.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{row['Agent']}** - {row['Type']}")
                    c1.caption(f"Du {row['Date_Debut']} au {row['Date_Fin']}")
                    
                    if row['Justificatif_Path'] and os.path.exists(row['Justificatif_Path']):
                        with open(row['Justificatif_Path'], "rb") as f:
                            c2.download_button("📂 Justificatif", f, file_name=os.path.basename(row['Justificatif_Path']), key=f"dl_{idx}")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Valider", key=f"v_{idx}", use_container_width=True):
                        df_rh.at[idx, 'Statut'] = "Validé"
                        save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH); st.rerun()
                    if b2.button("❌ Rejeter", key=f"r_{idx}", use_container_width=True):
                        df_rh.at[idx, 'Statut'] = "Rejeté"
                        save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH); st.rerun()

st.divider()
st.caption("Pharmaciel RH — Organisation & Rigueur.")
