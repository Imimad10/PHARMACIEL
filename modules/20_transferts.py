import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
TRANSFER_WORKSHEET = "DB_Transferts"
TRANSFER_FALLBACK = "data/db_transferts.csv"
COLS_TRANSFER = ["id", "date", "produit", "lot", "quantite", "source_etab", "source_depot", "dest_etab", "dest_depot", "agent", "statut"]

st.set_page_config(page_title="Transferts Inter-Filiales", layout="wide")

st.markdown("""
<style>
    .transfer-header {
        background: linear-gradient(135deg, #6366f1, #a855f7);
        padding: 30px; border-radius: 20px; color: white;
        margin-bottom: 30px; box-shadow: 0 10px 20px rgba(99, 102, 241, 0.2);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="transfer-header">
    <h1 style="margin:0; font-weight:900;">🔄 Transferts Inter-Filiales</h1>
    <p style="margin:5px 0 0; opacity:0.8; font-weight:600;">Flux Zéro Papier entre DarPharm & Pharmaciel</p>
</div>
""", unsafe_allow_html=True)

# --- 1. CHARGEMENT DONNÉES ---
df_transfers = load_gs_data(TRANSFER_WORKSHEET, TRANSFER_FALLBACK, COLS_TRANSFER)

# --- 2. FORMULAIRE DE TRANSFERT ---
with st.expander("➕ Créer un nouveau bon de transfert", expanded=True):
    with st.form("form_transfer_inter"):
        c1, c2 = st.columns(2)
        produit = c1.text_input("📦 Désignation du produit")
        lot = c2.text_input("🔢 Numéro de Lot")
        
        c3, c4, c5 = st.columns([1, 1, 1])
        qte = c3.number_input("🔢 Quantité", min_value=1, step=1)
        agent = c4.text_input("👤 Agent préparateur", value=st.session_state.get('current_user', {}).get('username', ''))
        
        st.markdown("---")
        c_src, c_arrow, c_dest = st.columns([2, 1, 2])
        
        with c_src:
            st.markdown("##### 📤 SOURCE")
            src_etab = st.selectbox("Établissement", ["DarPharm", "Pharmaciel"], key="src_etab")
            src_depot = st.selectbox("Dépôt", ["Gros", "Principal", "Retours"], key="src_depot")
            
        with c_arrow:
            st.markdown("<div style='text-align:center; font-size:3rem; margin-top:20px;'>➡️</div>", unsafe_allow_html=True)
            
        with c_dest:
            st.markdown("##### 📥 DESTINATION")
            # Logique par défaut : si source est DarPharm, destination est Pharmaciel
            default_dest_idx = 1 if src_etab == "DarPharm" else 0
            dest_etab = st.selectbox("Établissement", ["DarPharm", "Pharmaciel"], index=default_dest_idx, key="dest_etab")
            dest_depot = st.selectbox("Dépôt", ["Principal", "Gros", "Quarantaine"], key="dest_depot")
            
        submit = st.form_submit_button("🚀 VALIDER LE TRANSFERT", use_container_width=True, type="primary")
        
        if submit:
            if not produit or not lot:
                st.error("Désignation et Lot obligatoires.")
            elif src_etab == dest_etab and src_depot == dest_depot:
                st.error("La source et la destination doivent être différentes.")
            else:
                new_id = len(df_transfers) + 1
                new_row = {
                    "id": new_id,
                    "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "produit": produit.upper(),
                    "lot": lot.upper(),
                    "quantite": qte,
                    "source_etab": src_etab,
                    "source_depot": src_depot,
                    "dest_etab": dest_etab,
                    "dest_depot": dest_depot,
                    "agent": agent,
                    "statut": "En transit"
                }
                
                # Mise à jour locale + cloud (On écrit dans la base de l'établissement actif)
                df_transfers = pd.concat([df_transfers, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_transfers, TRANSFER_WORKSHEET, TRANSFER_FALLBACK)
                
                # OPTIONNEL: On pourrait aussi écrire dans la base de l'établissement de destination
                # pour qu'il voie le transfert "En transit" dans son propre module.
                dest_url = st.secrets.get("GS_URL" if dest_etab == "DarPharm" else "GS_URL_PHARMACIEL")
                if dest_url:
                    try:
                        df_dest = load_gs_data(TRANSFER_WORKSHEET, TRANSFER_FALLBACK, COLS_TRANSFER, override_url=dest_url)
                        df_dest = pd.concat([df_dest, pd.DataFrame([new_row])], ignore_index=True)
                        save_gs_data(df_dest, TRANSFER_WORKSHEET, TRANSFER_FALLBACK, override_url=dest_url)
                    except: pass
                
                st.success(f"Transfert de {src_etab} vers {dest_etab} enregistré ! ✅")
                st.balloons()
                st.rerun()

# --- 3. HISTORIQUE ---
st.divider()
st.subheader("📋 Suivi des flux inter-filiales")

if not df_transfers.empty:
    st.dataframe(df_transfers.sort_index(ascending=False), use_container_width=True, hide_index=True)
    
    # Réception
    st.markdown("---")
    c_rec1, c_rec2 = st.columns([2, 1])
    with c_rec1:
        target_id = st.selectbox("ID du transfert à réceptionner", 
                                df_transfers[df_transfers['statut'] == "En transit"]['id'].tolist())
    with c_rec2:
        if st.button("📥 CONFIRMER LA RÉCEPTION", use_container_width=True, type="primary"):
            df_transfers.loc[df_transfers['id'] == target_id, 'statut'] = "Reçu"
            save_gs_data(df_transfers, TRANSFER_WORKSHEET, TRANSFER_FALLBACK)
            
            # Mettre à jour l'établissement source aussi pour synchroniser le statut ?
            # (Optionnel selon le besoin de synchro parfaite)
            
            st.success("Transfert réceptionné et intégré au stock destination.")
            st.rerun()
else:
    st.info("Aucun transfert en cours.")
