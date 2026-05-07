import streamlit as st
import pandas as pd
import os
import unicodedata
from datetime import datetime
from tinydb import TinyDB, Query
from utils import log_action

# --- 1. CONFIGURATION & STYLING ---
DATA_DIR = "data_inventaire_detail"
MASTER_PATH = os.path.join(DATA_DIR, "master_detail.xlsx")
os.makedirs(DATA_DIR, exist_ok=True)

db = TinyDB('db_pharmaciel.json')
table_inv = db.table('inventaire_triple')

# Custom CSS for Premium Design
st.markdown("""
<style>
    .stApp {
        background-color: #f4f7f6;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        color: #2c3e50;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
        color: #636e72;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b !important;
        color: white !important;
    }
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def robust_num(s):
    if pd.isna(s) or s == "": return 0.0
    try: return float(str(s).replace('\xa0', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

# --- 2. DATA LOADING & STATE MANAGEMENT ---
@st.cache_data(ttl=60)
def load_master():
    if not os.path.exists(MASTER_PATH): return None
    try:
        df = pd.read_excel(MASTER_PATH)
        mapping = {
            'designation': 'produit', 'produit': 'produit', 'article': 'produit',
            'lot': 'lot', 'n°lot': 'lot', 'batch': 'lot',
            'ppa': 'ppa', 'shp': 'shp', 'stock': 'shp', 'ddp': 'ddp', 'exp': 'ddp'
        }
        used_names = {}
        final_cols = []
        for col in df.columns:
            norm = normalize_text(col)
            mapped_name = norm
            for k, v in mapping.items():
                if k in norm:
                    mapped_name = v
                    break
            if mapped_name in used_names:
                used_names[mapped_name] += 1
                mapped_name = f"{mapped_name}_{used_names[mapped_name]}"
            else:
                used_names[mapped_name] = 0
            final_cols.append(mapped_name)
        df.columns = final_cols
        
        for col in ['produit', 'lot']:
            if col in df.columns: df[col] = df[col].astype(str).str.upper().str.strip()
        if 'shp' in df.columns: df['shp'] = df['shp'].apply(robust_num)
        if 'ppa' in df.columns: df['ppa'] = df['ppa'].apply(robust_num)
        return df
    except Exception as e: 
        st.error(f"Erreur Master: {e}")
        return None

df_master = load_master()

# Initialisation du DataFrame de travail (Merge Master + TinyDB)
if 'inv_work_df' not in st.session_state or st.sidebar.button("🔄 Actualiser Données"):
    if df_master is not None:
        # On part du master
        work_df = df_master.copy()
        work_df['Terrain (Vrac)'] = 0.0
        work_df['Terrain (Colis)'] = 0.0
        work_df['Mini (Vrac)'] = 0.0
        work_df['Mini (Colis)'] = 0.0
        
        # On injecte les données déjà sauvées dans TinyDB pour ce lot/produit
        saved_data = table_inv.all()
        if saved_data:
            df_s = pd.DataFrame(saved_data)
            # Pour chaque ligne du master, on cherche si on a une saisie
            # On utilise un dict pour l'indexation rapide
            for i, row in work_df.iterrows():
                match = df_s[(df_s['produit'] == row['produit']) & (df_s['lot_master'] == row['lot'])]
                if not match.empty:
                    # Note: Dans l'ancien format on stockait des totaux, ici on va essayer de restaurer ce qu'on peut
                    # Mais le but est surtout d'avoir une grille de travail persistante
                    work_df.at[i, 'Terrain (Vrac)'] = match.iloc[0].get('detail_terrain', 0.0)
                    work_df.at[i, 'Mini (Vrac)'] = match.iloc[0].get('mini_stock', 0.0)
        
        st.session_state.inv_work_df = work_df
    else:
        st.session_state.inv_work_df = pd.DataFrame()

# --- 3. HEADER & DASHBOARD ---
st.header("📋 Inventaire Triple & Confrontation Minutieuse", divider="orange")

if df_master is None:
    st.warning("⚠️ Aucun fichier Master détecté. Veuillez l'importer dans l'onglet Administration.")
    tabs = st.tabs(["⚙️ Administration"])
else:
    tabs = st.tabs(["⚡ Saisie Libre & Grille", "📊 Analyse & Confrontation", "⚙️ Administration"])

    # --- ONGLET 1 : SAISIE LIBRE (GRID) ---
    with tabs[0]:
        st.markdown("""
        <div class='card'>
            <h4>⚡ Mode Saisie Libre (Grille Interactive)</h4>
            <p style='color: #636e72;'>Saisissez les quantités Terrain et Mini Stock directement dans le tableau. 
            Utilisez la recherche (Ctrl+F) pour trouver un produit rapidement.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Filtres rapides
        col_f1, col_f2 = st.columns([2, 1])
        search_query = col_f1.text_input("🔍 Rechercher un produit ou un lot...", placeholder="Ex: PARACETAMOL")
        show_only_counted = col_f2.checkbox("Afficher uniquement les saisies en cours", value=False)
        
        # Filtrage du dataframe
        display_df = st.session_state.inv_work_df.copy()
        if search_query:
            display_df = display_df[
                display_df['produit'].str.contains(search_query, case=False, na=False) |
                display_df['lot'].str.contains(search_query, case=False, na=False)
            ]
        
        if show_only_counted:
            display_df = display_df[
                (display_df['Terrain (Vrac)'] > 0) | (display_df['Terrain (Colis)'] > 0) |
                (display_df['Mini (Vrac)'] > 0) | (display_df['Mini (Colis)'] > 0)
            ]

        # Calcul des totaux pour affichage dans la grille (colonnes virtuelles non éditables)
        display_df['Total Terrain'] = display_df['Terrain (Vrac)'] + display_df['Terrain (Colis)']
        display_df['Total Mini'] = display_df['Mini (Vrac)'] + display_df['Mini (Colis)']
        display_df['Total Global'] = display_df['Total Terrain'] + display_df['Total Mini']
        display_df['Écart (vs SHP)'] = display_df['Total Global'] - display_df['shp']

        # Configuration de l'éditeur
        edited_df = st.data_editor(
            display_df,
            column_config={
                "produit": st.column_config.TextColumn("Produit", width="medium", disabled=True),
                "lot": st.column_config.TextColumn("Lot", width="small", disabled=True),
                "shp": st.column_config.NumberColumn("Stock Theo", format="%.0f", disabled=True),
                "Terrain (Vrac)": st.column_config.NumberColumn("📍 Terrain Vrac", min_value=0, step=1),
                "Terrain (Colis)": st.column_config.NumberColumn("📍 Terrain Colis", min_value=0, step=1),
                "Mini (Vrac)": st.column_config.NumberColumn("🏢 Mini Vrac", min_value=0, step=1),
                "Mini (Colis)": st.column_config.NumberColumn("🏢 Mini Colis", min_value=0, step=1),
                "Total Terrain": st.column_config.NumberColumn("Total Terrain", format="%.0f", disabled=True),
                "Total Mini": st.column_config.NumberColumn("Total Mini", format="%.0f", disabled=True),
                "Total Global": st.column_config.NumberColumn("Total Global", format="%.0f", disabled=True),
                "Écart (vs SHP)": st.column_config.NumberColumn("Écart", format="%.0f", disabled=True),
                "ppa": None, "ddp": None # On cache les colonnes moins utiles ici
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key="inventory_editor"
        )

        # Mise à jour du session state quand l'utilisateur édite
        if not edited_df.equals(display_df):
            # On reporte les modifications dans le dataframe de travail principal
            for index, row in edited_df.iterrows():
                st.session_state.inv_work_df.loc[index, 'Terrain (Vrac)'] = row['Terrain (Vrac)']
                st.session_state.inv_work_df.loc[index, 'Terrain (Colis)'] = row['Terrain (Colis)']
                st.session_state.inv_work_df.loc[index, 'Mini (Vrac)'] = row['Mini (Vrac)']
                st.session_state.inv_work_df.loc[index, 'Mini (Colis)'] = row['Mini (Colis)']

        st.divider()
        c_save1, c_save2 = st.columns([3, 1])
        c_save1.info("💡 Les modifications sont enregistrées en mémoire vive. Cliquez sur le bouton à droite pour les figer en base de données.")
        if c_save2.button("💾 Figer et Sauvegarder en Base", type="primary", use_container_width=True):
            # On sauve uniquement les lignes où il y a une saisie
            work = st.session_state.inv_work_df
            to_save = work[(work['Terrain (Vrac)'] > 0) | (work['Terrain (Colis)'] > 0) |
                           (work['Mini (Vrac)'] > 0) | (work['Mini (Colis)'] > 0)]
            
            if to_save.empty:
                st.warning("Rien à sauvegarder (aucune quantité saisie).")
            else:
                # On vide l'ancienne table pour ce master (ou on fait des updates intelligents)
                # Ici on va simplement remplacer les entrées existantes pour ces produits/lots
                for _, row in to_save.iterrows():
                    table_inv.remove((Query().produit == row['produit']) & (Query().lot_master == row['lot']))
                    table_inv.insert({
                        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "produit": row['produit'],
                        "lot": row['lot'],
                        "lot_master": row['lot'],
                        "detail_terrain": row['Terrain (Vrac)'] + row['Terrain (Colis)'],
                        "mini_stock": row['Mini (Vrac)'] + row['Mini (Colis)'],
                        "total": row['Terrain (Vrac)'] + row['Terrain (Colis)'] + row['Mini (Vrac)'] + row['Mini (Colis)'],
                        "ppa": row.get('ppa', 0.0),
                        "shp": row.get('shp', 0.0),
                        "ddp": row.get('ddp', ''),
                        "agent": st.session_state.current_user.get('username', 'Inconnu')
                    })
                st.success(f"✅ {len(to_save)} lignes sauvegardées avec succès !")
                log_action(st.session_state.current_user['username'], f"Sauvegarde Triple Grille ({len(to_save)} items)", "Inventaire")

    # --- ONGLET 2 : ANALYSE & CONFRONTATION ---
    with tabs[1]:
        st.subheader("📊 Confrontation Minutieuse & Analyse des Écarts")
        
        work = st.session_state.inv_work_df
        work['Total Saisi'] = work['Terrain (Vrac)'] + work['Terrain (Colis)'] + work['Mini (Vrac)'] + work['Mini (Colis)']
        work['Ecart'] = work['Total Saisi'] - work['shp']
        
        # Statistiques Globales
        counted_df = work[work['Total Saisi'] > 0]
        discrepancies = counted_df[counted_df['Ecart'] != 0]
        total_val_ecart = (discrepancies['Ecart'] * discrepancies.get('ppa', 0)).sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Produits Comptés", len(counted_df))
        m2.metric("Écarts Détectés", len(discrepancies))
        m3.metric("Précision (%)", f"{((len(counted_df)-len(discrepancies))/len(counted_df)*100 if len(counted_df)>0 else 0):.1f}%")
        m4.metric("Valeur Écarts (Est.)", f"{total_val_ecart:,.2f} DA", delta=f"{total_val_ecart:,.2f}", delta_color="inverse")

        st.divider()
        
        # Filtre pour la confrontation
        conf_mode = st.radio("Vue de confrontation :", 
                           ["Tous les produits comptés", "Uniquement les écarts (Anomalies)", "Produits en surplus", "Produits en manque"], 
                           horizontal=True)
        
        view_df = counted_df.copy()
        if conf_mode == "Uniquement les écarts (Anomalies)":
            view_df = view_df[view_df['Ecart'] != 0]
        elif conf_mode == "Produits en surplus":
            view_df = view_df[view_df['Ecart'] > 0]
        elif conf_mode == "Produits en manque":
            view_df = view_df[view_df['Ecart'] < 0]
            
        if view_df.empty:
            st.info("Aucune donnée correspondant au filtre.")
        else:
            # Table de confrontation stylisée
            def color_ecart(val):
                color = 'red' if val < 0 else 'green' if val > 0 else 'black'
                return f'color: {color}; font-weight: bold'

            st.dataframe(
                view_df[['produit', 'lot', 'Terrain (Vrac)', 'Mini (Vrac)', 'Total Saisi', 'shp', 'Ecart']],
                column_config={
                    "produit": "Produit",
                    "lot": "Lot",
                    "Terrain (Vrac)": "Saisie Terrain",
                    "Mini (Vrac)": "Saisie Mini",
                    "Total Saisi": "Total Réel",
                    "shp": "Théorique (SHP)",
                    "Ecart": st.column_config.NumberColumn("Écart", format="%.0f")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Export
            csv = view_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Exporter cette confrontation (CSV)", csv, "confrontation_triple.csv", "text/csv")

    # --- ONGLET 3 : ADMINISTRATION ---
    with tabs[2]:
        st.subheader("⚙️ Gestion des données Master")
        st.write("Importez ici le fichier Master (Excel) contenant la liste des produits, lots et stocks théoriques.")
        
        up = st.file_uploader("📁 Choisir le fichier Master (Excel)", type="xlsx", key="up_triple")
        if up:
            if st.button("🚀 Valider l'importation et mettre à jour la base"):
                try:
                    with open(MASTER_PATH, "wb") as f:
                        f.write(up.getbuffer())
                    st.cache_data.clear()
                    if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
                    st.success(f"✅ Master importé avec succès !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Échec: {e}")

        st.divider()
        if st.session_state.current_user.get('role') == 'Admin':
            if st.button("🗑️ Vider l'historique des saisies (Base de données)", type="primary"):
                table_inv.truncate()
                if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
                st.success("Historique vidé.")
                st.rerun()
