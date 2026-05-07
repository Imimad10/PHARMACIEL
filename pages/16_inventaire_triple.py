import streamlit as st
import pandas as pd
import os
import json
from tinydb import TinyDB, Query
import unicodedata

# --- CONFIGURATION ---
st.set_page_config(page_title="Inventaire Triple - Pharmaciel", layout="wide")

MASTER_DIR = "data_inventaire_detail"
MASTER_PATH = os.path.join(MASTER_DIR, "master_detail.xlsx")
DB_PATH = "db_pharmaciel.json"
os.makedirs(MASTER_DIR, exist_ok=True)

db = TinyDB(DB_PATH)
table_inv = db.table('inventaire_triple')

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 4px 4px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: #e7f3ff !important; color: #1877f2 !important; }
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f1f8ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1877f2;
    }
    </style>
""", unsafe_allow_html=True)

import re

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    # Enlever les accents
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower()
    # Remplacer les espaces multiples, retours à la ligne, etc. par un seul espace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def robust_num(val):
    try:
        if pd.isna(val): return 0.0
        return float(val)
    except: return 0.0

@st.cache_data(ttl=3600)
def load_master():
    if not os.path.exists(MASTER_PATH): return None
    try:
        # On lit toutes les feuilles pour aider au diagnostic
        xl = pd.ExcelFile(MASTER_PATH)
        df = xl.parse(xl.sheet_names[-1]) # On prend la DERNIÈRE feuille par défaut (souvent l'export le plus récent)
        
        df.columns = [str(c) for c in df.columns]
        
        # MAPPING STRICT LOGIPHARM
        search_patterns = {
            'produit': ['designation', 'produit', 'article', 'nom'],
            'lot': ['lot', 'n°lot', 'batch', 'n lot'],
            'qte_logi': ['quantite depot', 'qte depot', 'quantite globale', 'qte globale'], # PRIORITÉ ABSOLUE
            'colissage': ['colis', 'colissage', 'unit per box'],
            'depot': ['depot', 'warehouse', 'magasin'],
            'zone': ['zone produit', 'zone']
        }
        
        # Secours si 'quantite depot' est absent
        fallback_shp = ['shp', 'theorique', 'stock']
        
        source_mapping = {}
        used_cols = set()
        
        # 1. Mapping des champs critiques
        for target, patterns in search_patterns.items():
            for p in patterns:
                for col in df.columns:
                    if col not in used_cols:
                        norm = normalize_text(col)
                        if p == norm or p in norm:
                            source_mapping[target] = col
                            used_cols.add(col)
                            break
                if target in source_mapping: break
        
        # 2. Fallback pour le stock si toujours pas trouvé
        if 'qte_logi' not in source_mapping:
            for p in fallback_shp:
                for col in df.columns:
                    if col not in used_cols:
                        if p in normalize_text(col):
                            source_mapping['qte_logi'] = col
                            used_cols.add(col)
                            break
                if 'qte_logi' in source_mapping: break

        # Renommage
        rename_dict = {v: k for k, v in source_mapping.items()}
        df = df.rename(columns=rename_dict)
        
        # Nettoyage
        if 'produit' not in df.columns: df['produit'] = "SANS NOM"
        if 'lot' not in df.columns: df['lot'] = "SANS LOT"
        if 'qte_logi' not in df.columns: df['qte_logi'] = 0.0
        if 'colissage' not in df.columns: df['colissage'] = 1.0
        
        df['produit'] = df['produit'].astype(str).str.upper()
        df['lot'] = df['lot'].astype(str).str.upper()
        df['qte_logi'] = df['qte_logi'].apply(robust_num)
        df['colissage'] = df['colissage'].apply(robust_num).replace(0, 1)
        
        return df
    except Exception as e:
        st.error(f"Erreur Lecture Excel: {e}")
        return None

# --- INITIALISATION ---
df_master = load_master()

# Reset forcé si changement de logique
if 'it_v8_regex_fix' not in st.session_state:
    st.cache_data.clear()
    if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
    st.session_state.it_v8_regex_fix = True
    st.rerun()

if "inv_work_df" not in st.session_state and df_master is not None:
    work_df = df_master.copy()
    work_df['Terrain (Vrac)'] = 0.0
    work_df['Terrain (Colis)'] = 0.0
    work_df['Mini (Vrac)'] = 0.0
    work_df['Mini (Colis)'] = 0.0
    
    # Fusion avec TinyDB
    saved = table_inv.all()
    for entry in saved:
        mask = (work_df['produit'] == entry.get('produit')) & (work_df['lot'] == entry.get('lot'))
        if mask.any():
            work_df.loc[mask, 'Terrain (Vrac)'] = entry.get('tv', 0.0)
            work_df.loc[mask, 'Terrain (Colis)'] = entry.get('tc', 0.0)
            work_df.loc[mask, 'Mini (Vrac)'] = entry.get('mv', 0.0)
            work_df.loc[mask, 'Mini (Colis)'] = entry.get('mc', 0.0)
    
    st.session_state.inv_work_df = work_df

# --- INTERFACE ---
st.title("📋 Inventaire Triple & Confrontation Logipharm")

if df_master is None:
    st.warning("⚠️ Aucun fichier Master détecté. Veuillez l'importer dans l'onglet Administration.")
    tabs = st.tabs(["⚙️ Administration"])
    tab_saisie, tab_analyse, tab_admin = None, None, tabs[0]
else:
    tabs = st.tabs(["⚡ Saisie & Grille", "📊 Analyse Écarts", "⚙️ Administration"])
    tab_saisie, tab_analyse, tab_admin = tabs[0], tabs[1], tabs[2]

# --- ADMINISTRATION ---
with tab_admin:
    st.subheader("⚙️ Importation Logipharm")
    up = st.file_uploader("Fichier Excel Export Logipharm", type="xlsx", key="up_v7")
    if up:
        if st.button("🚀 Importer ce fichier", type="primary"):
            with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
            st.cache_data.clear()
            if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
            st.success("Fichier importé !")
            st.rerun()
    
    if st.session_state.current_user.get('role') == 'Admin':
        st.divider()
        st.subheader("🚨 Danger Zone")
        c1, c2 = st.columns(2)
        if c1.button("🗑️ Vider TOUTES les saisies (DB)", use_container_width=True):
            table_inv.truncate()
            if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
            st.rerun()
        if c2.button("📁 Supprimer le fichier Master", use_container_width=True):
            if os.path.exists(MASTER_PATH): os.remove(MASTER_PATH)
            st.cache_data.clear()
            if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
            st.rerun()

# --- SAISIE ---
if df_master is not None and tab_saisie:
    with tab_saisie:
        # Diagnostic
        with st.expander("🔍 Diagnostic Colonnes"):
            st.write("Colonnes identifiées :", list(df_master.columns))
            st.dataframe(df_master[['depot', 'produit', 'lot', 'qte_logi']].head())

        # Filtres
        f1, f2, f3 = st.columns(3)
        depots = ["Tous"] + sorted(st.session_state.inv_work_df['depot'].dropna().unique().tolist()) if 'depot' in st.session_state.inv_work_df.columns else ["Tous"]
        sel_depot = f1.selectbox("Filtrer Dépôt", depots)
        
        search = st.text_input("Recherche Produit / Lot")
        
        # Filtrage
        disp_df = st.session_state.inv_work_df.copy()
        if sel_depot != "Tous": disp_df = disp_df[disp_df['depot'] == sel_depot]
        if search: disp_df = disp_df[disp_df['produit'].str.contains(search, case=False) | disp_df['lot'].str.contains(search, case=False)]
        
        # Calculs
        c = disp_df['colissage']
        disp_df['Total Réel'] = disp_df['Terrain (Vrac)'] + (disp_df['Terrain (Colis)'] * c) + disp_df['Mini (Vrac)'] + (disp_df['Mini (Colis)'] * c)
        disp_df['Écart'] = disp_df['Total Réel'] - disp_df['qte_logi']
        
        # Grille
        mcols = ['depot', 'produit', 'lot', 'qte_logi', 'colissage', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Vrac)', 'Mini (Colis)', 'Total Réel', 'Écart']
        disp_df = disp_df[mcols]
        
        edited = st.data_editor(
            disp_df,
            column_config={
                "depot": st.column_config.TextColumn("Dépôt", disabled=True),
                "produit": st.column_config.TextColumn("Produit", disabled=True),
                "lot": st.column_config.TextColumn("Lot", disabled=True),
                "qte_logi": st.column_config.NumberColumn("Stock Logi", disabled=True, help="Quantité Dépôt du Master"),
                "colissage": st.column_config.NumberColumn("U/Colis", disabled=True),
                "Total Réel": st.column_config.NumberColumn("Total", disabled=True),
                "Écart": st.column_config.NumberColumn("Écart", disabled=True, format="%+.0f"),
            },
            num_rows="fixed",
            key="editor_v7",
            use_container_width=True
        )
        
        if st.button("💾 Enregistrer les modifications", type="primary"):
            # Update session state
            for idx, row in edited.iterrows():
                st.session_state.inv_work_df.loc[idx, 'Terrain (Vrac)'] = row['Terrain (Vrac)']
                st.session_state.inv_work_df.loc[idx, 'Terrain (Colis)'] = row['Terrain (Colis)']
                st.session_state.inv_work_df.loc[idx, 'Mini (Vrac)'] = row['Mini (Vrac)']
                st.session_state.inv_work_df.loc[idx, 'Mini (Colis)'] = row['Mini (Colis)']
                
                # Update TinyDB
                table_inv.upsert({
                    'produit': row['produit'], 'lot': row['lot'],
                    'tv': row['Terrain (Vrac)'], 'tc': row['Terrain (Colis)'],
                    'mv': row['Mini (Vrac)'], 'mc': row['Mini (Colis)']
                }, (Query().produit == row['produit']) & (Query().lot == row['lot']))
            st.success("Modifications enregistrées !")
            st.rerun()

# --- ANALYSE ---
if df_master is not None and tab_analyse:
    with tab_analyse:
        st.subheader("Analyse des Écarts")
        res_df = st.session_state.inv_work_df.copy()
        c = res_df['colissage']
        res_df['Total'] = res_df['Terrain (Vrac)'] + (res_df['Terrain (Colis)'] * c) + res_df['Mini (Vrac)'] + (res_df['Mini (Colis)'] * c)
        res_df['Ecart'] = res_df['Total'] - res_df['qte_logi']
        
        diff = res_df[res_df['Ecart'] != 0]
        st.metric("Nombre d'écarts détectés", len(diff))
        st.dataframe(diff[['depot', 'produit', 'lot', 'qte_logi', 'Total', 'Ecart']], use_container_width=True)
