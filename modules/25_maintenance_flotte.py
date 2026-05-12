import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
MAINT_WORKSHEET = "DB_Maintenance"
MAINT_FALLBACK = "data/db_maintenance.csv"
COLS_MAINT = ["id", "equipement", "type", "derniere_date", "prochaine_echeance", "alerte_kms", "statut"]

st.title("🚛 Maintenance & Flotte")
st.markdown("### Suivi des véhicules et équipements")

# --- 1. CHARGEMENT DONNÉES ---
df_maint = load_gs_data(MAINT_WORKSHEET, MAINT_FALLBACK, COLS_MAINT)

# --- 2. AJOUT MATÉRIEL ---
with st.expander("➕ Enregistrer un nouveau véhicule / matériel", expanded=False):
    with st.form("form_maint"):
        nom = st.text_input("Nom de l'équipement (ex: Camion Renault, Frigo Zone A)")
        t_equip = st.selectbox("Type", ["Véhicule", "Froid", "Informatique", "Autre"])
        last_d = st.date_input("Dernière maintenance")
        next_d = st.date_input("Prochaine échéance prévue")
        
        if st.form_submit_button("Ajouter"):
            if nom:
                new_row = {
                    "id": len(df_maint) + 1,
                    "equipement": nom,
                    "type": t_equip,
                    "derniere_date": last_d.strftime("%d/%m/%Y"),
                    "prochaine_echeance": next_d.strftime("%d/%m/%Y"),
                    "statut": "OK"
                }
                df_maint = pd.concat([df_maint, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_maint, MAINT_WORKSHEET, MAINT_FALLBACK)
                st.success(f"{nom} ajouté au suivi.")
                st.rerun()

# --- 3. ALERTES & ÉCHÉANCES ---
st.subheader("⚠️ Alertes de Maintenance")

if not df_maint.empty:
    today = datetime.now()
    # On convertit pour comparer
    df_maint['date_dt'] = pd.to_datetime(df_maint['prochaine_echeance'], format="%d/%m/%Y", errors='coerce')
    
    alertes = df_maint[df_maint['date_dt'] <= (today + pd.Timedelta(days=7))]
    
    if not alertes.empty:
        for _, row in alertes.iterrows():
            st.error(f"🚨 **{row['equipement']}** : Échéance le {row['prochaine_echeance']} !")
    else:
        st.success("Tout votre matériel est à jour pour les 7 prochains jours.")

# --- 4. LISTE GLOBALE ---
st.divider()
st.subheader("📋 État du parc matériel")
st.dataframe(df_maint.drop(columns=['date_dt'], errors='ignore'), use_container_width=True, hide_index=True)
