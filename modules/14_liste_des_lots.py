import streamlit as st
import pandas as pd
import os
import unicodedata
import os

st.set_page_config(page_title="Liste des Lots", layout="wide")

# --- 1. CONFIGURATION ---
from utils_gsheets import load_gs_data, save_gs_data
from app import DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# --- 1. CONFIGURATION ---
DATA_DIR = "data_inventaire_detail"
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = os.path.join(DATA_DIR, "master_detail.csv")
COLS_MASTER = ["designation", "lot", "zone", "ddp", "ppa", "shp", "stock_theorique"]

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_cols_v5(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation', 'article': 'designation', 'libelle': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp', 'date': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone', 'sector': 'zone'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte', 'dispo']
    new_cols = []
    found = set()
    for col in df.columns:
        norm = normalize_text(col)
        target = None
        for k, v in mapping.items():
            if k in norm and v not in found:
                target = v; found.add(v); break
        if not target and any(key in norm for key in stock_keywords) and 'stock_theorique' not in found:
            target = 'stock_theorique'; found.add(target)
        new_cols.append(target if target else norm)
    df.columns = new_cols
    return df

@st.cache_data(ttl=60)
def load_master_v5(path, mtime):
    try:
        df = pd.read_excel(path, engine='openpyxl')
        df = clean_cols_v5(df)
        req = ['designation', 'lot', 'zone']
        if not all(c in df.columns for c in req): return f"Colonnes manquantes : {[c for c in req if c not in df.columns]}"
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
        
        for col in ['designation', 'lot', 'zone']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        
        return df
    except Exception as e: return str(e)

# --- 3. UI ---
st.title("📑 Liste des Lots")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
user_zone = user.get('zone', 'Aucune')
is_admin = user.get('role') in ["Admin", "Superviseur"]

df_master = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
if not df_master.empty:
    df_master = clean_cols_v5(df_master)
else:
    df_master = None

if df_master is None:
    st.info("Aucun Master Détail trouvé sur GSheets. Veuillez l'importer depuis l'onglet Admin de 'Inventaire Détail'.")
    st.stop()

# Filtrer par zone si non-admin
if not is_admin and user_zone != "Aucune":
    df_filtered = df_master[df_master['zone'] == user_zone]
    st.sidebar.success(f"📍 Affichage restreint à votre zone : **{user_zone}**")
else:
    df_filtered = df_master
    if is_admin:
        st.sidebar.info("👑 Vue Globale (Toutes Zones)")

tabs = st.tabs(["📋 Liste des Lots", "📊 Tableau de Bord", "⚙️ Admin"])

with tabs[0]:
    st.subheader("Consultation des Produits et Lots")
    
    col_search, col_zone = st.columns(2)
    search_term = col_search.text_input("🔍 Rechercher un produit ou un lot :", "")
    
    if is_admin:
        zones_opt = ["Toutes"] + sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
        zone_filter = col_zone.selectbox("Filtrer par Zone :", zones_opt)
        if zone_filter != "Toutes":
            df_display = df_filtered[df_filtered['zone'] == zone_filter]
        else:
            df_display = df_filtered
    else:
        df_display = df_filtered
        
    if search_term:
        df_display = df_display[
            df_display['designation'].str.contains(search_term, case=False, na=False) |
            df_display['lot'].str.contains(search_term, case=False, na=False)
        ]
        
    st.write(f"Affichage de **{len(df_display)}** résultats.")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("📊 Tableau de Bord")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Produits Distincts", df_filtered['designation'].nunique())
    c2.metric("Total Lots Différents", len(df_filtered))
    
    if 'stock_theorique' in df_filtered.columns:
        total_stock = pd.to_numeric(df_filtered['stock_theorique'], errors='coerce').sum()
        c3.metric("Stock Théorique Cumulé", f"{total_stock:,.0f}")
    
    st.divider()
    if is_admin:
        st.write("#### Répartition par Zone")
        zone_counts = df_filtered['zone'].value_counts().reset_index()
        zone_counts.columns = ['Zone', 'Nombre de Lots']
        st.bar_chart(zone_counts, x='Zone', y='Nombre de Lots')
    else:
        st.write(f"**Zone active :** {user_zone}")
        st.write("Seules les données de votre zone sont affichées.")

with tabs[2]:
    if is_admin:
        st.subheader("👥 Affectation des Zones aux Utilisateurs")
        df_u = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "role", "pages", "zone"])
        
        # Filtrer les utilisateurs qui ont accès à "Liste des Lots" ou "Inventaire Détail"
        target_users = df_u['username'].tolist() if not df_u.empty else []
        
        col_u1, col_u2, col_u3 = st.columns([2, 1, 1])
        target_user = col_u1.selectbox("Sélectionner un utilisateur :", target_users)
        
        if target_user:
            u_record = df_u[df_u['username'] == target_user].iloc[0]
            current_z = u_record.get('zone', 'Aucune')
            
            z_list = ["Aucune"] + sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
            new_z = col_u2.selectbox(f"Assigner Zone (Actuelle: {current_z})", z_list, index=z_list.index(current_z) if current_z in z_list else 0)
            
            if col_u3.button("✅ Confirmer l'affectation", use_container_width=True):
                df_u.loc[df_u['username'] == target_user, 'zone'] = new_z
                save_gs_data(df_u, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                st.success(f"Zone de **{target_user}** mise à jour : **{new_z}**")
                st.rerun()
            
        st.divider()
        st.info("Pour importer ou gérer le fichier Master, veuillez vous rendre dans l'onglet Admin du module **Inventaire Détail**.")
    else:
        st.warning("Accès réservé aux Administrateurs et Superviseurs.")
