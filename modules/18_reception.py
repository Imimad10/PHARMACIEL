import streamlit as st
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_pdf import generate_reception_pdf
from utils_ia import ask_ai_vision, is_ia_enabled
from utils_themes import apply_theme_css, load_themes_db
import difflib
import base64
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Réception Premium - Pharmaciel", layout="wide")

# Application du thème Fluffy
_tdb = load_themes_db()
fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
apply_theme_css(fluffy)

DB_RECEPTIONS = "data/db_receptions.csv"
DB_PRODUITS_RECEPTION = "data/db_reception_produits.csv"
COLS_RECEPTIONS = ["id", "date", "fournisseur", "facture_num", "statut", "items", "created_by"]
COLS_PRODUITS = ["Designation", "PPA", "SHP", "Colissage"]

# --- CSS ADDITIONNEL RÉCEPTION ---
st.markdown("""
<style>
    .reception-header {
        background: #eef0f8; padding: 25px; border-radius: 30px;
        box-shadow: 7px 7px 18px #c0c5dc, -7px -7px 18px #ffffff;
        margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;
    }
    .facture-card {
        background: #eef0f8; padding: 20px; border-radius: 20px;
        box-shadow: inset 4px 4px 10px #c0c5dc, inset -4px -4px 10px #ffffff;
        margin-bottom: 20px;
    }
    .item-row {
        background: white; padding: 15px; border-radius: 15px;
        margin-bottom: 10px; display: flex; justify-content: space-between;
        align-items: center; box-shadow: 4px 4px 10px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

def load_produits_reception():
    if os.path.exists(DB_PRODUITS_RECEPTION):
        try: return pd.read_csv(DB_PRODUITS_RECEPTION, encoding='utf-8-sig')
        except: return pd.read_csv(DB_PRODUITS_RECEPTION)
    return pd.DataFrame(columns=COLS_PRODUITS)

def save_reception(reception_data):
    df_old = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    if not reception_data.get('id'):
        reception_data['id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    
    new_row = pd.DataFrame([{
        "id": reception_data['id'], "date": reception_data['date'],
        "fournisseur": reception_data['fournisseur'], "facture_num": reception_data['facture_num'],
        "statut": reception_data['statut'], "items": json.dumps(reception_data['items']),
        "created_by": reception_data['created_by']
    }])
    df_old = pd.concat([df_old, new_row], ignore_index=True)
    save_gs_data(df_old, "Receptions", DB_RECEPTIONS)

if "current_reception" not in st.session_state:
    st.session_state.current_reception = {
        "id": None, "date": datetime.now().strftime("%Y-%m-%d"),
        "fournisseur": "", "facture_num": "", "statut": "En cours", "items": [], "created_by": "Utilisateur"
    }

st.markdown('<div class="reception-header"><div><h1 style="color:#5b6cf9; font-weight:900;">Réception & Pointage 📦</h1><p style="color:#6b7299; font-weight:700;">Gérez vos arrivages avec précision</p></div><div style="background:#d4f5ea; padding:10px 20px; border-radius:15px; color:#2db88a; font-weight:900;">⚡ MODE PREMIUM ACTIF</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["⚡ Nouvelle Réception", "📋 Historique", "🏛️ Administration"])

with tabs[0]:
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        st.subheader("📝 Infos Facture")
        with st.container(border=True):
            st.session_state.current_reception['fournisseur'] = st.text_input("Fournisseur", value=st.session_state.current_reception['fournisseur'])
            st.session_state.current_reception['facture_num'] = st.text_input("N° Facture / BL", value=st.session_state.current_reception['facture_num'])
            st.session_state.current_reception['date'] = st.date_input("Date Réception").strftime("%Y-%m-%d")

        if is_ia_enabled():
            st.markdown("### 🤖 Assistant IA")
            if st.button("📸 OUVRIR LE SCANNER IA VIGNETTES", use_container_width=True):
                st.session_state.current_page = "7_scanneur_qr"
                st.rerun()

    with col_f2:
        st.subheader("🔍 Saisie des Produits")
        df_prod = load_produits_reception()
        search_list = sorted(df_prod['Designation'].dropna().unique().tolist()) if not df_prod.empty else []
        
        with st.form("add_item_form"):
            selected_prod = st.selectbox("Rechercher un produit", [""] + search_list)
            c1, c2, c3 = st.columns(3)
            qte = c1.number_input("Quantité", min_value=1, step=1)
            lot = c2.text_input("Lot").upper()
            ddp = c3.text_input("DDP (MM/AAAA)")
            
            c4, c5, c6 = st.columns(3)
            ppa = c4.number_input("PPA", min_value=0.0, step=0.01)
            shp = c5.selectbox("SHP", [2.5, 1.5, 0.0])
            colis = c6.number_input("Colissage", min_value=1, value=1)
            
            if st.form_submit_button("➕ AJOUTER À LA LISTE", use_container_width=True):
                if selected_prod:
                    st.session_state.current_reception['items'].append({
                        "produit": selected_prod, "lot": lot, "ddp": ddp, "qte": qte,
                        "ppa": ppa, "shp": shp, "colissage": colis
                    })
                    st.rerun()

        # Liste des produits pointés
        if st.session_state.current_reception['items']:
            st.markdown("### 📑 Récapitulatif Pointage")
            for i, it in enumerate(st.session_state.current_reception['items']):
                st.markdown(f"""
                <div class="item-row">
                    <div><b>{it['produit']}</b><br><small style="color:#6b7299">Lot: {it['lot']} | Exp: {it['ddp']}</small></div>
                    <div style="font-weight:900; color:#5b6cf9;">{it['qte']} Unités</div>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("💾 CLÔTURER ET ENREGISTRER LA RÉCEPTION", type="primary", use_container_width=True):
                save_reception(st.session_state.current_reception)
                st.balloons()
                st.success("Réception clôturée avec succès !")
                st.session_state.current_reception['items'] = []
                st.rerun()

with tabs[1]:
    st.subheader("📋 Historique des Réceptions")
    df_rec = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    if not df_rec.empty:
        st.dataframe(df_rec.sort_values("date", ascending=False), use_container_width=True)
    else:
        st.info("Aucune réception enregistrée.")

with tabs[2]:
    show_sync_ui("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
