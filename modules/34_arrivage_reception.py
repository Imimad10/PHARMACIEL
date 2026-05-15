import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
import json

# --- CONFIGURATION ---
DB_ARRIVAGES = "data/db_arrivages.csv"
DB_FOURNISSEURS = "data/db_fournisseurs.csv"
COLS_ARRIVAGES = ["id", "date", "fournisseur", "facture_num", "statut", "heure_arrivee", "heure_debut", "heure_fin", "agents", "created_by"]

st.markdown("""
<style>
    .arrivage-header {
        background: #f0fdf4; padding: 25px; border-radius: 30px;
        box-shadow: 7px 7px 18px #d1d5db, -7px -7px 18px #ffffff;
        margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;
        border-left: 6px solid #22c55e;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="arrivage-header"><div><h1 style="color:#15803d; font-weight:900;">Réception Fournisseurs 🚚</h1><p style="color:#166534; font-weight:700;">Journal de log des arrivages et traçabilité des camions</p></div></div>', unsafe_allow_html=True)

def save_arrivage(arrivage_data):
    df_old = load_gs_data("Arrivages", DB_ARRIVAGES, COLS_ARRIVAGES)
    if not arrivage_data.get('id'):
        arrivage_data['id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    
    new_row = pd.DataFrame([{
        "id": arrivage_data['id'],
        "date": arrivage_data['date'],
        "fournisseur": arrivage_data['fournisseur'],
        "facture_num": arrivage_data['facture_num'],
        "statut": arrivage_data['statut'],
        "heure_arrivee": arrivage_data.get('heure_arrivee', ''),
        "heure_debut": arrivage_data.get('heure_debut', ''),
        "heure_fin": arrivage_data.get('heure_fin', ''),
        "agents": json.dumps(arrivage_data.get('agents', [])),
        "created_by": st.session_state.get('current_user', {}).get('username', 'Utilisateur')
    }])
    df_old = pd.concat([df_old, new_row], ignore_index=True)
    save_gs_data(df_old, "Arrivages", DB_ARRIVAGES)

# Initialisation
if "current_arrivage" not in st.session_state:
    st.session_state.current_arrivage = {
        "id": None, "date": datetime.now().strftime("%Y-%m-%d"),
        "fournisseur": "", "facture_num": "", "statut": "Planifiée",
        "heure_arrivee": "", "heure_debut": "", "heure_fin": "", "agents": []
    }

# Données
df_fourn = load_gs_data("Fournisseurs", DB_FOURNISSEURS, ["ID", "Fournisseur", "Contact", "N_RC", "N_ART", "N_NIF", "N_NIS", "Dette"])
liste_fournisseurs = df_fourn['Fournisseur'].dropna().unique().tolist() if not df_fourn.empty else []

try:
    from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
    df_users_coord = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "nom", "prenom", "role"])
    active_agents = df_users_coord['username'].dropna().tolist() if not df_users_coord.empty else ["Ayoub", "Islem", "admin_imad", "Seif"]
except:
    active_agents = ["Ayoub", "Islem", "admin_imad", "Seif"]

tabs = st.tabs(["📝 Planification & Journal", "📋 Historique des Arrivages"])

with tabs[0]:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Nouvel Arrivage (Log)")
        with st.container(border=True):
            f_index = 0
            if st.session_state.current_arrivage['fournisseur'] in liste_fournisseurs:
                f_index = liste_fournisseurs.index(st.session_state.current_arrivage['fournisseur']) + 1
            
            st.session_state.current_arrivage['fournisseur'] = st.selectbox("Fournisseur", [""] + liste_fournisseurs, index=f_index)
            if not st.session_state.current_arrivage['fournisseur']:
                st.session_state.current_arrivage['fournisseur'] = st.text_input("Fournisseur (Manuel)", placeholder="Saisir manuellement...")
                
            st.session_state.current_arrivage['facture_num'] = st.text_input("N° de Commande / BL / Facture")
            st.session_state.current_arrivage['date'] = st.date_input("Date Prévue/Réelle").strftime("%Y-%m-%d")
            
            st.markdown("---")
            st.markdown("##### ⏱️ Suivi du Temps")
            c_h1, c_h2, c_h3 = st.columns(3)
            st.session_state.current_arrivage['heure_arrivee'] = c_h1.time_input("Heure d'arrivage", value=None)
            st.session_state.current_arrivage['heure_debut'] = c_h2.time_input("Début vérification", value=None)
            st.session_state.current_arrivage['heure_fin'] = c_h3.time_input("Clôture", value=None)
            
            # Format strings
            for k in ['heure_arrivee', 'heure_debut', 'heure_fin']:
                if st.session_state.current_arrivage[k]:
                    st.session_state.current_arrivage[k] = st.session_state.current_arrivage[k].strftime("%H:%M")
                    
            st.session_state.current_arrivage['agents'] = st.multiselect("Agents Responsables de la réception", active_agents, default=st.session_state.current_arrivage.get('agents', []))
            st.session_state.current_arrivage['statut'] = st.selectbox("Statut", ["Planifiée", "Camion sur place", "En cours de vérification", "Clôturée"])
            
            if st.button("💾 ENREGISTRER L'ARRIVAGE", use_container_width=True, type="primary"):
                save_arrivage(st.session_state.current_arrivage)
                st.success("Arrivage enregistré avec succès !")
                st.balloons()
                st.session_state.current_arrivage = {
                    "id": None, "date": datetime.now().strftime("%Y-%m-%d"),
                    "fournisseur": "", "facture_num": "", "statut": "Planifiée",
                    "heure_arrivee": "", "heure_debut": "", "heure_fin": "", "agents": []
                }
                st.rerun()

    with col2:
        st.subheader("Arrivages du jour en cours")
        df_arr = load_gs_data("Arrivages", DB_ARRIVAGES, COLS_ARRIVAGES)
        if not df_arr.empty:
            today = datetime.now().strftime("%Y-%m-%d")
            df_today = df_arr[(df_arr['date'] == today) & (df_arr['statut'] != "Clôturée")]
            if not df_today.empty:
                for _, row in df_today.iterrows():
                    color = "#3b82f6" if row['statut'] == "Planifiée" else ("#f59e0b" if row['statut'] == "Camion sur place" else "#8b5cf6")
                    st.markdown(f"""
                    <div style="border-left:4px solid {color}; padding:10px 15px; margin-bottom:10px; background:#f8fafc; border-radius:5px;">
                        <strong>{row['fournisseur']}</strong> - <span style="color:{color}">{row['statut']}</span><br>
                        <small>Prévu le : {row['date']} | Arrivée : {row.get('heure_arrivee','—')}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucun arrivage en attente pour aujourd'hui.")
        else:
            st.info("Base d'arrivages vide.")

with tabs[1]:
    st.subheader("Historique Complet")
    df_arr = load_gs_data("Arrivages", DB_ARRIVAGES, COLS_ARRIVAGES)
    if not df_arr.empty:
        st.dataframe(df_arr.sort_values("date", ascending=False), use_container_width=True)
    else:
        st.info("Aucun historique.")
