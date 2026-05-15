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
day_name = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][today.weekday()]

st.sidebar.markdown(f"#### 📅 Aujourd'hui : {day_name}")
if today.weekday() == 4: # Vendredi
    st.sidebar.error("🔴 Aujourd'hui est un Vendredi (Weekend)")
elif today.weekday() == 5: # Samedi
    st.sidebar.warning("🟡 Aujourd'hui : Samedi (Permanence 9h - 15h)")
else:
    st.sidebar.success("🟢 Jour de semaine opérationnel")

tabs = st.tabs(["📝 Déclarer une Absence/Permanence", "📋 Planning Global", "🏥 Justificatifs & Validation"])

# --- TAB 1 : DÉCLARATION ---
with tabs[0]:
    st.subheader("Enregistrer un événement RH")
    
    # Récupération de la liste des agents (utilisateurs)
    from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
    df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username"])
    agents_list = df_users['username'].unique().tolist() if not df_users.empty else ["Ayoub", "Islem", "Seif", "admin_imad"]
    
    with st.form("form_rh"):
        col1, col2 = st.columns(2)
        agent = col1.selectbox("Collaborateur concerné", agents_list)
        type_event = col2.selectbox("Type d'événement", ["Permanence Samedi", "Congé Annuel", "Maladie", "Récupération", "Absence Autorisée"])
        
        d1 = col1.date_input("Date de début", value=today)
        d2 = col2.date_input("Date de fin (Inclus)", value=today)
        
        comm = st.text_area("Observations / Motif")
        
        uploaded_file = st.file_uploader("📎 Justificatif (PDF, JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])
        
        if st.form_submit_button("🚀 Enregistrer la demande", use_container_width=True, type="primary"):
            file_path = ""
            if uploaded_file:
                fname = f"JUST_{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                file_path = os.path.join(UPLOAD_DIR, fname)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            new_row = {
                "ID": len(df_rh) + 1,
                "Date_Debut": d1.strftime("%Y-%m-%d"),
                "Date_Fin": d2.strftime("%Y-%m-%d"),
                "Agent": agent,
                "Type": type_event,
                "Statut": "Validé" if type_event == "Permanence Samedi" else "En attente",
                "Commentaire": comm,
                "Justificatif_Path": file_path,
                "Date_Creation": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            df_rh = pd.concat([df_rh, pd.DataFrame([new_row])], ignore_index=True)
            save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
            play_sound("notification")
            st.success(f"Événement enregistré pour **{agent}** !")
            st.rerun()

# --- TAB 2 : PLANNING GLOBAL ---
with tabs[1]:
    st.subheader("Vue Calendrier des Présences")
    
    # Filtres
    f_agent = st.multiselect("Filtrer par agent", agents_list, default=[])
    
    df_view = df_rh.copy()
    if f_agent:
        df_view = df_view[df_view['Agent'].isin(f_agent)]
    
    st.dataframe(df_view.sort_values("Date_Debut", ascending=False), use_container_width=True, hide_index=True)
    
    # Assistant IA Planning
    if st.button("🤖 Analyser la couverture d'équipe (IA)"):
        with st.spinner("L'IA analyse le planning..."):
            summary = df_view.to_string()
            prompt = f"Voici le planning RH actuel : {summary}. Analyse s'il y a des risques de sous-effectif dans les 15 prochains jours. Vérifie aussi si les permanences du samedi sont bien couvertes. Sois direct et pro."
            res = ask_ai(prompt)
            st.info(res)

# --- TAB 3 : VALIDATION (ADMIN) ---
with tabs[2]:
    st.subheader("Validation des justificatifs & Absences")
    
    df_pending = df_rh[df_rh['Statut'] == "En attente"]
    
    if df_pending.empty:
        st.success("Aucune demande en attente de validation.")
    else:
        for idx, row in df_pending.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{row['Agent']}** - {row['Type']} ({row['Date_Debut']} au {row['Date_Fin']})")
                c1.caption(f"Motif : {row['Commentaire']}")
                
                if row['Justificatif_Path'] and os.path.exists(row['Justificatif_Path']):
                    if c2.button("👁️ Voir Justificatif", key=f"view_{idx}"):
                        # Streamlit ne peut pas ouvrir de PDF directement facilement, on donne le lien ou on l'affiche si image
                        if row['Justificatif_Path'].lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(row['Justificatif_Path'], width=300)
                        else:
                            with open(row['Justificatif_Path'], "rb") as f:
                                st.download_button("Télécharger le PDF", f, file_name=os.path.basename(row['Justificatif_Path']), key=f"dl_{idx}")
                
                if c3.button("✅ Valider", key=f"val_{idx}", type="primary"):
                    df_rh.at[idx, 'Statut'] = "Validé"
                    save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                    st.rerun()
                if c3.button("❌ Rejeter", key=f"rej_{idx}"):
                    df_rh.at[idx, 'Statut'] = "Rejeté"
                    save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                    st.rerun()

st.divider()
st.caption("Note : Les samedis, le service est assuré en permanence de 09:00 à 15:00 par l'agent désigné.")
