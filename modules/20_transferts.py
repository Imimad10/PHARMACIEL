import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
TRANSFER_WORKSHEET = "DB_Transferts"
TRANSFER_FALLBACK = "data/db_transferts.csv"
COLS_TRANSFER = ["id", "date", "produit", "lot", "quantite", "source", "destination", "agent", "statut"]

st.title("🔄 Transferts Inter-Dépôts")
st.markdown("### Du 'Gros' vers le 'Principal' (Zéro Papier)")

# --- 1. CHARGEMENT DONNÉES ---
df_transfers = load_gs_data(TRANSFER_WORKSHEET, TRANSFER_FALLBACK, COLS_TRANSFER)

# --- 2. NOUVEAU TRANSFERT ---
with st.expander("➕ Enregistrer un nouveau transfert", expanded=True):
    with st.form("form_transfer"):
        col1, col2 = st.columns(2)
        produit = col1.text_input("📦 Produit (Désignation)")
        lot = col2.text_input("🔢 Numéro de Lot")
        
        col3, col4 = st.columns(2)
        qte = col3.number_input("🔢 Quantité", min_value=1, step=1)
        agent = col4.text_input("👤 Agent préparateur", value=st.session_state.get('current_user', {}).get('username', ''))
        
        col5, col6 = st.columns(2)
        source = col5.selectbox("📍 Source", ["Gros", "Principal", "Retours"])
        dest = col6.selectbox("🎯 Destination", ["Principal", "Gros", "Quarantaine"])
        
        submit = st.form_submit_button("✅ Valider le Transfert", use_container_width=True)
        
        if submit:
            if not produit or not lot:
                st.error("Veuillez remplir le produit et le lot.")
            else:
                new_id = len(df_transfers) + 1
                new_row = {
                    "id": new_id,
                    "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "produit": produit.upper(),
                    "lot": lot.upper(),
                    "quantite": qte,
                    "source": source,
                    "destination": dest,
                    "agent": agent,
                    "statut": "En attente"
                }
                df_transfers = pd.concat([df_transfers, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_transfers, TRANSFER_WORKSHEET, TRANSFER_FALLBACK)
                st.success("Transfert enregistré avec succès !")
                st.rerun()

# --- 3. HISTORIQUE & SUIVI ---
st.divider()
st.subheader("📋 Historique des transferts")

if not df_transfers.empty:
    # Filtres rapides
    f_statut = st.multiselect("Filtrer par statut", ["En attente", "Reçu", "Annulé"], default=["En attente"])
    df_disp = df_transfers[df_transfers['statut'].isin(f_statut)] if f_statut else df_transfers
    
    # Affichage
    st.dataframe(df_disp.sort_index(ascending=False), use_container_width=True, hide_index=True)
    
    # Validation réception
    st.markdown("---")
    st.markdown("#### ✅ Confirmer la réception")
    target_id = st.selectbox("Sélectionner l'ID du transfert reçu", df_transfers[df_transfers['statut'] == "En attente"]['id'].tolist() if not df_transfers.empty else [])
    if st.button("Confirmer la réception (Mise en stock)", use_container_width=True):
        df_transfers.loc[df_transfers['id'] == target_id, 'statut'] = "Reçu"
        save_gs_data(df_transfers, TRANSFER_WORKSHEET, TRANSFER_FALLBACK)
        st.success(f"Transfert {target_id} marqué comme REÇU.")
        st.rerun()
else:
    st.info("Aucun transfert enregistré pour le moment.")
