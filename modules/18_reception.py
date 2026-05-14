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
from PIL import Image
from io import BytesIO

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
        try:
            # Essayer plusieurs encodages et séparateurs avec une tolérance accrue
            df = None
            for sep in [',', ';']:
                for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(DB_PRODUITS_RECEPTION, sep=sep, encoding=enc, engine='python', on_bad_lines='skip')
                        if len(df.columns) > 1: break
                    except: continue
                if df is not None and len(df.columns) > 1: break
            
            if df is None:
                # Dernier recours : lecture brute sans séparateur
                df = pd.read_csv(DB_PRODUITS_RECEPTION, sep='\t', on_bad_lines='skip')

            # Normalisation des colonnes
            mapping = {
                'designation': 'Designation', 'produit': 'Designation', 'article': 'Designation',
                'ppa': 'PPA', 'shp': 'SHP', 'colissage': 'Colissage', 'colis': 'Colissage'
            }
            new_cols = []
            for c in df.columns:
                norm = str(c).lower().strip()
                target = c
                for k, v in mapping.items():
                    if k in norm: target = v; break
                new_cols.append(target)
            df.columns = new_cols
            
            # Vérifier si Designation existe
            if 'Designation' not in df.columns:
                if len(df.columns) == 1: df.columns = ['Designation']
            
            return df
        except Exception as e:
            st.error(f"Erreur lecture produits : {e}")
            return pd.DataFrame(columns=COLS_PRODUITS)
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
            
            # Paramètres IA
            ia_mode = st.radio("Mode de détection", ["Base Système 🔍", "Libre (Nouveau produit) ✨"], horizontal=True)
            
            # Upload d'images
            uploaded_files = st.file_uploader("📸 Scanner des vignettes (Images)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="ia_uploader")
            
            if uploaded_files:
                if st.button("🚀 ANALYSER TOUTES LES IMAGES", use_container_width=True, type="primary"):
                    st.session_state.ia_results = []
                    progress_bar = st.progress(0)
                    
                    for i, file in enumerate(uploaded_files):
                        # Conversion image en base64
                        img = Image.open(file)
                        buffered = BytesIO()
                        img.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        prompt = """
                        Extrais les informations de cette vignette de médicament. 
                        Retourne UNIQUEMENT un JSON brut (sans markdown) avec ces clés:
                        - designation: (ex: PARACETAMOL 500mg CP B/20)
                        - lot: (numéro de lot)
                        - ddp: (Format MM/AAAA)
                        - ddf: (Format MM/AAAA)
                        - ppa: (Nombre décimal)
                        - shp: (Nombre décimal)
                        - qte: (Nombre entier)
                        """
                        
                        try:
                            res_raw = ask_ai_vision(prompt, img_str)
                            # Nettoyage JSON si markdown présent
                            if "```json" in res_raw: res_raw = res_raw.split("```json")[1].split("```")[0].strip()
                            elif "```" in res_raw: res_raw = res_raw.split("```")[1].split("```")[0].strip()
                            
                            data = json.loads(res_raw)
                            
                            # Matching Base Système si activé
                            if "Base Système" in ia_mode:
                                lp = df_prod['Designation'].dropna().unique().tolist()
                                if lp:
                                    matches = difflib.get_close_matches(data.get('designation', '').upper(), lp, n=1, cutoff=0.4)
                                    if matches:
                                        target_prod = matches[0]
                                        data['designation'] = target_prod
                                        
                                        # Récupération PPA/SHP depuis la base
                                        prod_info = df_prod[df_prod['Designation'] == target_prod].iloc[0]
                                        if pd.notna(prod_info.get('PPA')): data['ppa'] = float(prod_info['PPA'])
                                        if pd.notna(prod_info.get('SHP')): data['shp'] = float(prod_info['SHP'])
                            
                            st.session_state.ia_results.append(data)
                        except Exception as e:
                            st.warning(f"Erreur sur {file.name} : {e}")
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    st.success(f"{len(st.session_state.ia_results)} vignettes analysées !")

            # Affichage des résultats IA pour validation
            if "ia_results" in st.session_state and st.session_state.ia_results:
                st.markdown("#### ✅ Validation des scans")
                df_res = pd.DataFrame(st.session_state.ia_results)
                
                # Édition des résultats avant ajout
                edited_df = st.data_editor(
                    df_res, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "designation": st.column_config.SelectboxColumn("Produit", options=df_prod['Designation'].unique() if not df_prod.empty else []),
                        "ddp": st.column_config.TextColumn("DDP (MM/AAAA)"),
                        "ppa": st.column_config.NumberColumn("PPA", format="%.2f DA"),
                        "shp": st.column_config.NumberColumn("SHP", format="%.2f DA"),
                        "qte": st.column_config.NumberColumn("Quantité"),
                    }
                )
                
                if st.button("➕ AJOUTER TOUT À LA RÉCEPTION", use_container_width=True):
                    for _, row in edited_df.iterrows():
                        new_row = {
                            "Designation": row.get('designation', ''),
                            "Quantité": row.get('qte', 1),
                            "Lot": row.get('lot', ''),
                            "DDP": row.get('ddp', ''),
                            "PPA": row.get('ppa', 0.0),
                            "SHP": row.get('shp', 0.0),
                            "Colissage": 1
                        }
                        st.session_state.reception_items.append(new_row)
                    st.session_state.ia_results = []
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
