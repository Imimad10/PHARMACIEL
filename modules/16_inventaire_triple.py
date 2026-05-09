import streamlit as st
import pandas as pd
import os
import json
import unicodedata
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
st.set_page_config(page_title="Inventaire Triple - Pharmaciel", layout="wide")

from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
# --- CONFIGURATION ---
st.set_page_config(page_title="Inventaire Triple - Pharmaciel", layout="wide")

MASTER_DIR = "data_inventaire_detail"
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = os.path.join(MASTER_DIR, "master_detail.csv")
INV_TRIPLE_WORKSHEET = "Inventaire_Triple"
INV_TRIPLE_FALLBACK = "data/db_inv_triple.csv"
os.makedirs(MASTER_DIR, exist_ok=True)

if 'current_user' not in st.session_state:
    st.warning("⚠️ Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

COLS_MASTER = ["depot", "zone", "produit", "lot", "qte_logi", "colissage"]
COLS_INV_TRIPLE = ["produit", "lot", "tv", "tc", "mv", "mc", "col"]

show_sync_ui(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
show_sync_ui(INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK, COLS_INV_TRIPLE)

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
def get_master_df():
    df = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
    if df.empty: return None
    
    # Nettoyage et mapping intelligent pour Excel
    mapping = {
        'dépôt': 'depot', 'depot': 'depot',
        'produit': 'produit', 'désignation': 'produit',
        'n°lot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'quantité dépôt': 'qte_logi', 'qte.globale': 'qte_logi', 'quantité': 'qte_logi',
        'zone produit': 'zone', 'zone': 'zone',
        'colis': 'colissage', 'u/colis': 'colissage'
    }
    
    # On normalise les colonnes actuelles pour comparer
    current_cols = {normalize_text(c): c for c in df.columns}
    rename_dict = {}
    for key, target in mapping.items():
        if key in current_cols:
            rename_dict[current_cols[key]] = target
            
    df = df.rename(columns=rename_dict)
    
    # Si après renommage il manque des colonnes essentielles, on les crée vides
    for c in COLS_MASTER:
        if c not in df.columns: df[c] = ""
        
    df['produit'] = df['produit'].astype(str).str.upper()
    df['lot'] = df['lot'].astype(str).str.upper()
    df['qte_logi'] = df['qte_logi'].apply(robust_num)
    df['colissage'] = df['colissage'].apply(robust_num).replace(0, 1)
    return df[COLS_MASTER]

# --- INITIALISATION ---
df_master = get_master_df()
df_inv_triple = load_gs_data(INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK, COLS_INV_TRIPLE)

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
    
    # Fusion avec GSheets data
    if not df_inv_triple.empty:
        for _, entry in df_inv_triple.iterrows():
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
        if 'zone' in df.columns:
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
            df_up = pd.read_excel(up)
            # Normalisation et nettoyage avant envoi
            # (Ici on pourrait rajouter la logique de mapping si besoin)
            save_gs_data(df_up, MASTER_WORKSHEET, MASTER_FALLBACK)
            st.cache_data.clear()
            if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
            st.success("Master synchronisé sur GSheets !")
            st.rerun()
    
        if st.session_state.current_user.get('role') in ['Admin', 'Superviseur']:
            st.divider()
            st.subheader("👥 Affectation des Zones")
        
        from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
        df_users_it = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "password", "role", "pages", "inv_zones"])
        
        # Liste des zones uniques du master
        avail_zones = []
        if df_master is not None and 'zone' in df_master.columns:
            avail_zones = sorted([str(z) for z in df_master['zone'].dropna().unique()])
            
        if not avail_zones:
            st.warning("Aucune zone trouvée dans le fichier Master.")
        else:
            with st.form("form_zones_triple"):
                # On filtre les utilisateurs qui ont accès à cette page
                for idx, u in df_users_it.iterrows():
                    if u.get('role') not in ['Admin', 'Superviseur']:
                        # inv_zones peut être stocké comme une chaîne JSON dans GSheets
                        curr = u.get('inv_zones', [])
                        if isinstance(curr, str):
                            try: curr = json.loads(curr.replace("'", '"'))
                            except: curr = []
                        
                        valid_curr = [z for z in curr if z in avail_zones]
                        sel = st.multiselect(f"Zones pour {u['username']}", avail_zones, default=valid_curr)
                        df_users_it.at[idx, 'inv_zones'] = str(sel)
                
                if st.form_submit_button("💾 Sauvegarder les affectations", type="primary"):
                    save_gs_data(df_users_it, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                    st.success("Affectations mises à jour sur GSheets !")
                    st.rerun()

        st.divider()
        st.subheader("🚨 Danger Zone")
        c1, c2 = st.columns(2)
        if c1.button("🗑️ Vider TOUTES les saisies (GSheets)", use_container_width=True):
            save_gs_data(pd.DataFrame(columns=COLS_INV_TRIPLE), INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
            if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
            st.rerun()
        if c2.button("📁 Vider le Master sur GSheets", use_container_width=True):
            save_gs_data(pd.DataFrame(columns=COLS_MASTER), MASTER_WORKSHEET, MASTER_FALLBACK)
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
            
            # Filtrage sécurisé
            if sel_depot != "Tous" and 'depot' in disp_df.columns: 
                disp_df = disp_df[disp_df['depot'] == sel_depot]
            if sel_zone != "Toutes" and 'zone' in disp_df.columns: 
                disp_df = disp_df[disp_df['zone'] == sel_zone]
            if search: 
                disp_df = disp_df[disp_df['produit'].str.contains(search, case=False, na=False) | disp_df['lot'].str.contains(search, case=False, na=False)]
            
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
            # Comparaison pour ne sauvegarder que les lignes modifiées
            try:
                # pandas compare() faille si les types ne sont pas strictement identiques, on utilise un check manuel
                # On compare edited et disp_df sur les colonnes modifiables
                cols_to_check = ['Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Vrac)', 'Mini (Colis)', 'colissage']
                
                # S'assurer que les index sont alignés
                changed_indices = []
                for idx in edited.index:
                    if idx in disp_df.index:
                        for col in cols_to_check:
                            if col in edited.columns and col in disp_df.columns:
                                if edited.loc[idx, col] != disp_df.loc[idx, col]:
                                    changed_indices.append(idx)
                                    break
                                    
                if not changed_indices:
                    st.info("Aucune modification détectée.")
                else:
                    for idx in changed_indices:
                        row = edited.loc[idx]
                        # Update session state
                        st.session_state.inv_work_df.loc[idx, 'Terrain (Vrac)'] = row['Terrain (Vrac)']
                        st.session_state.inv_work_df.loc[idx, 'Terrain (Colis)'] = row['Terrain (Colis)']
                        st.session_state.inv_work_df.loc[idx, 'Mini (Vrac)'] = row['Mini (Vrac)']
                        st.session_state.inv_work_df.loc[idx, 'Mini (Colis)'] = row['Mini (Colis)']
                        if 'colissage' in row:
                            st.session_state.inv_work_df.loc[idx, 'colissage'] = row['colissage']
                        
                        # Update df_inv_triple for saving
                        new_entry = {
                            'produit': row['produit'], 'lot': row['lot'],
                            'tv': float(row['Terrain (Vrac)']), 'tc': float(row['Terrain (Colis)']),
                            'mv': float(row['Mini (Vrac)']), 'mc': float(row['Mini (Colis)']),
                            'col': float(row['colissage']) if 'colissage' in row else 1.0
                        }
                        
                        # Upsert in df_inv_triple
                        mask = (df_inv_triple['produit'] == row['produit']) & (df_inv_triple['lot'] == row['lot'])
                        if mask.any():
                            for k, v in new_entry.items():
                                df_inv_triple.loc[mask, k] = v
                        else:
                            df_inv_triple = pd.concat([df_inv_triple, pd.DataFrame([new_entry])], ignore_index=True)
                    
                    save_gs_data(df_inv_triple, INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
                    st.success(f"✅ {len(changed_indices)} modification(s) enregistrée(s) sur GSheets !")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde: {e}")

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

            # --- ANALYSE IA ---
            if is_ia_enabled():
                st.markdown("---")
                st.container(border=True)
                st.subheader("🤖 Assistant IA d'Analyse (BETA)")
                st.info("L'Intelligence Artificielle peut analyser vos écarts pour détecter des anomalies récurrentes (vols, erreurs de lot, problèmes de colissage).")
                if st.button("🧠 Générer un rapport d'analyse IA", use_container_width=True, type="primary"):
                    with st.spinner("L'IA examine vos données (cela peut prendre quelques secondes)..."):
                        # On limite à 20 écarts pour ne pas surcharger le prompt
                        ecarts_json = diff[['produit', 'lot', 'qte_logi', 'Total', 'Ecart']].head(20).to_dict('records')
                        prompt = f"Tu es un expert en logistique pharmaceutique. Voici les écarts de stock constatés aujourd'hui : {ecarts_json}. Identifie les causes probables (erreur de conversion unité/colis, erreur de saisie, péremption, etc.) et donne 3 conseils précis pour régler ces écarts."
                        reponse = ask_ai(prompt)
                        st.success("✅ Analyse terminée")
                        st.write(reponse)
