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
db_users = TinyDB('data/db_users.json')
df_master = load_master()

# Reset forcé si changement de logique
if 'it_v9_zones' not in st.session_state:
    st.cache_data.clear()
    if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
    st.session_state.it_v9_zones = True
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
            if 'col' in entry:
                work_df.loc[mask, 'colissage'] = entry.get('col')
    
    st.session_state.inv_work_df = work_df

# --- INTERFACE ---
st.title("📋 Inventaire Triple & Confrontation Logipharm")

if df_master is None:
    st.warning("⚠️ Aucun fichier Master détecté. Veuillez l'importer dans l'onglet Administration.")
    tabs = st.tabs(["⚙️ Administration"])
    tab_dash, tab_saisie, tab_analyse, tab_admin = None, None, None, tabs[0]
else:
    tabs = st.tabs(["📈 Tableau de Bord", "⚡ Saisie & Grille", "📊 Analyse Écarts", "⚙️ Administration"])
    tab_dash, tab_saisie, tab_analyse, tab_admin = tabs[0], tabs[1], tabs[2], tabs[3]

# --- FONCTION FILTRAGE ZONES ---
def get_user_data():
    df = st.session_state.inv_work_df.copy()
    user_role = st.session_state.current_user.get('role', 'Saisie')
    allowed_zones = st.session_state.current_user.get('inv_zones', [])
    
    if user_role not in ['Admin', 'Superviseur']:
        if not allowed_zones:
            # Si aucune zone assignée, on retourne un DF vide
            return df.iloc[0:0]
        df = df[df['zone'].isin(allowed_zones)]
    return df

# --- TABLEAU DE BORD ---
if df_master is not None and tab_dash:
    with tab_dash:
        st.subheader("📈 Tableau de Bord - Inventaire")
        dash_df = get_user_data()
        
        if dash_df.empty:
            st.info("Aucune donnée disponible ou aucune zone ne vous est assignée.")
        else:
            total_items = len(dash_df)
            
            # Un item est considéré "compté" s'il a une quantité saisie
            dash_df['Saisi'] = (dash_df['Terrain (Vrac)'] > 0) | (dash_df['Terrain (Colis)'] > 0) | (dash_df['Mini (Vrac)'] > 0) | (dash_df['Mini (Colis)'] > 0)
            items_counted = dash_df['Saisi'].sum()
            progress = (items_counted / total_items) * 100 if total_items > 0 else 0
            
            st.markdown(f"**Progression du comptage ({items_counted} / {total_items} produits)**")
            st.progress(progress / 100)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("📦 Produits Totaux (Votre zone)", total_items)
            c2.metric("✅ Produits Comptés", items_counted)
            c3.metric("⏳ Reste à compter", total_items - items_counted)
            
            st.divider()
            st.write("### 📍 Répartition par Zone")
            zone_counts = dash_df.groupby('zone')['produit'].count().reset_index()
            zone_counts.columns = ['Zone', 'Nombre de Produits']
            st.dataframe(zone_counts, use_container_width=True)

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
    
    if st.session_state.current_user.get('role') in ['Admin', 'Superviseur']:
        st.divider()
        st.subheader("👥 Affectation des Zones")
        st.write("Assignez les zones de préparation (A, B, C...) à vos préparateurs.")
        
        all_users = db_users.all()
        # Liste des zones uniques du master
        avail_zones = []
        if df_master is not None and 'zone' in df_master.columns:
            avail_zones = sorted([str(z) for z in df_master['zone'].dropna().unique()])
            
        if not avail_zones:
            st.warning("Aucune zone trouvée dans le fichier Master.")
        else:
            with st.form("form_zones"):
                user_zones_updates = {}
                for u in all_users:
                    if u.get('role') not in ['Admin', 'Superviseur']:
                        curr = u.get('inv_zones', [])
                        valid_curr = [z for z in curr if z in avail_zones]
                        sel = st.multiselect(f"Zones pour {u['username']}", avail_zones, default=valid_curr)
                        user_zones_updates[u['username']] = sel
                
                if st.form_submit_button("💾 Sauvegarder les affectations", type="primary"):
                    for uname, zones in user_zones_updates.items():
                        db_users.update({'inv_zones': zones}, Query().username == uname)
                        if st.session_state.current_user['username'] == uname:
                            st.session_state.current_user['inv_zones'] = zones
                    st.success("Affectations mises à jour !")
                    st.rerun()

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
        # En-tête avec bouton de rafraîchissement
        col_title, col_refresh = st.columns([3, 1])
        with col_title:
            st.markdown("### ⚡ Saisie Libre & Grille")
        with col_refresh:
            if st.button("♻️ Rafraîchir les données", use_container_width=True, help="Recharge les données depuis le fichier Master"):
                st.cache_data.clear()
                if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
                st.rerun()

        # Diagnostic
        with st.expander("🔍 Diagnostic Colonnes"):
            st.write("Colonnes identifiées :", list(df_master.columns))
            st.dataframe(df_master[['depot', 'produit', 'lot', 'qte_logi']].head())

        # Filtres
        f1, f2, f3 = st.columns(3)
        disp_df = get_user_data()
        
        if disp_df.empty:
            st.warning("Aucun produit à afficher. Vérifiez qu'une zone vous a été assignée.")
        else:
            depots = ["Tous"] + sorted(disp_df['depot'].dropna().unique().tolist()) if 'depot' in disp_df.columns else ["Tous"]
            sel_depot = f1.selectbox("Filtrer Dépôt", depots)
            
            zones = ["Toutes"] + sorted(disp_df['zone'].dropna().unique().tolist()) if 'zone' in disp_df.columns else ["Toutes"]
            sel_zone = f2.selectbox("Filtrer Zone", zones)
            
            search = st.text_input("Recherche Produit / Lot")
            
            # Filtrage
            if sel_depot != "Tous": disp_df = disp_df[disp_df['depot'] == sel_depot]
            if sel_zone != "Toutes": disp_df = disp_df[disp_df['zone'] == sel_zone]
            if search: disp_df = disp_df[disp_df['produit'].str.contains(search, case=False) | disp_df['lot'].str.contains(search, case=False)]
            
            # Calculs
            c = disp_df['colissage']
            disp_df['Total Réel'] = disp_df['Terrain (Vrac)'] + (disp_df['Terrain (Colis)'] * c) + disp_df['Mini (Vrac)'] + (disp_df['Mini (Colis)'] * c)
            disp_df['Écart'] = disp_df['Total Réel'] - disp_df['qte_logi']
            
            # Grille
            mcols = ['depot', 'zone', 'produit', 'lot', 'qte_logi', 'colissage', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Vrac)', 'Mini (Colis)', 'Total Réel', 'Écart']
            # Sécurité si une colonne manque
            mcols = [c for c in mcols if c in disp_df.columns]
            disp_df = disp_df[mcols]
            
            edited = st.data_editor(
                disp_df,
                column_config={
                    "depot": st.column_config.TextColumn("Dépôt", disabled=True),
                    "zone": st.column_config.TextColumn("Zone", disabled=True),
                    "produit": st.column_config.TextColumn("Produit", disabled=True),
                "lot": st.column_config.TextColumn("Lot", disabled=True),
                "qte_logi": st.column_config.NumberColumn("Stock Logi", disabled=True, help="Quantité Dépôt du Master"),
                "colissage": st.column_config.NumberColumn("U/Colis ✏️", disabled=False, min_value=1, help="Modifiable si l'export Logipharm est faux"),
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
                st.session_state.inv_work_df.loc[idx, 'colissage'] = row['colissage']
                
                # Update TinyDB
                table_inv.upsert({
                    'produit': row['produit'], 'lot': row['lot'],
                    'tv': row['Terrain (Vrac)'], 'tc': row['Terrain (Colis)'],
                    'mv': row['Mini (Vrac)'], 'mc': row['Mini (Colis)'],
                    'col': row['colissage']
                }, (Query().produit == row['produit']) & (Query().lot == row['lot']))
            st.success("Modifications enregistrées !")
            st.rerun()

# --- ANALYSE ---
if df_master is not None and tab_analyse:
    with tab_analyse:
        st.subheader("📊 Analyse des Écarts")
        res_df = get_user_data()
        
        if res_df.empty:
            st.warning("Aucune donnée à analyser pour vos zones.")
        else:
            c = res_df['colissage']
            res_df['Total'] = res_df['Terrain (Vrac)'] + (res_df['Terrain (Colis)'] * c) + res_df['Mini (Vrac)'] + (res_df['Mini (Colis)'] * c)
            res_df['Ecart'] = res_df['Total'] - res_df['qte_logi']
            
            diff = res_df[res_df['Ecart'] != 0].copy()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("📦 Nombre d'écarts", len(diff))
            col_m2.metric("🔴 Manquants (Valeur négative)", len(diff[diff['Ecart'] < 0]))
            col_m3.metric("🟢 Excédents (Valeur positive)", len(diff[diff['Ecart'] > 0]))
            
            st.write("Détail des écarts (Surligné en rouge = Manquant, Vert = Surplus) :")
            
            def highlight_ecart(row):
                if row['Ecart'] < 0: return ['background-color: rgba(255, 99, 132, 0.2)'] * len(row)
                elif row['Ecart'] > 0: return ['background-color: rgba(75, 192, 192, 0.2)'] * len(row)
                return [''] * len(row)
                
            disp_diff = diff[['depot', 'zone', 'produit', 'lot', 'qte_logi', 'colissage', 'Total', 'Ecart']]
            # Si zone n'existe pas, on l'enlève
            disp_diff = disp_diff[[col for col in disp_diff.columns if col in diff.columns]]
            
            st.dataframe(disp_diff.style.apply(highlight_ecart, axis=1), use_container_width=True)
