import streamlit as st
import pandas as pd
import os
import json
import unicodedata
from utils_ia import ask_ai, ask_ai_vision, is_ia_enabled, is_ia_scanner_enabled
import base64
import difflib
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Inventaire Triple - Pharmaciel", layout="wide")

from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui

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
COLS_INV_TRIPLE = ["produit", "lot", "tv", "tc", "mv", "mc", "col", "ddp", "ppa", "shp"]

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
    
    .entry-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #eef2f6;
        box-shadow: 0 10px 25px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    .section-header {
        color: #1877f2;
        font-weight: 800;
        font-size: 1.1rem;
        margin-bottom: 15px;
        border-bottom: 2px solid #e7f3ff;
        padding-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower()
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
    mapping = {
        'dépôt': 'depot', 'depot': 'depot',
        'produit': 'produit', 'désignation': 'produit',
        'n°lot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'quantité dépôt': 'qte_logi', 'qte.globale': 'qte_logi', 'quantité': 'qte_logi',
        'zone produit': 'zone', 'zone': 'zone',
        'colis': 'colissage', 'u/colis': 'colissage'
    }
    current_cols = {normalize_text(c): c for c in df.columns}
    rename_dict = {}
    for key, target in mapping.items():
        if key in current_cols:
            rename_dict[current_cols[key]] = target
    df = df.rename(columns=rename_dict)
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

# --- FONCTION FILTRAGE ZONES ---
def get_user_data(selected_zone_override=None):
    if df_master is None: return pd.DataFrame()
    df = df_master.copy()
    user_role = st.session_state.current_user.get('role', 'Saisie')
    user_zone = str(st.session_state.current_user.get('zone', 'Aucune')).strip().upper()
    
    # Si un Admin choisit une zone spécifique via le sélecteur
    if selected_zone_override and selected_zone_override != "Toutes":
        user_zone = selected_zone_override.strip().upper()
        user_role = 'Saisie' # On force le filtrage pour l'aperçu

    if user_role not in ['Admin', 'Superviseur']:
        if user_zone == 'AUCUNE' or not user_zone:
            return df.iloc[0:0]
        if 'zone' in df.columns:
            # Nettoyage des zones dans le DF pour un matching parfait
            df['zone_clean'] = df['zone'].astype(str).str.strip().str.upper()
            df = df[df['zone_clean'].str.contains(user_zone, na=False, regex=False)]
    return df

# Initialisation du work_df synchronisé
if "inv_work_df" not in st.session_state and df_master is not None:
    work_df = df_master.copy()
    work_df['Terrain (Vrac)'] = 0.0
    work_df['Terrain (Colis)'] = 0.0
    work_df['Mini (Colis)'] = 0.0
    work_df['ddp'] = ""
    work_df['ppa'] = 0.0
    work_df['shp'] = 0.0
    if not df_inv_triple.empty:
        for _, entry in df_inv_triple.iterrows():
            mask = (work_df['produit'] == entry.get('produit')) & (work_df['lot'] == entry.get('lot'))
            if mask.any():
                work_df.loc[mask, 'Terrain (Vrac)'] = entry.get('tv', 0.0)
                work_df.loc[mask, 'Terrain (Colis)'] = entry.get('tc', 0.0)
                work_df.loc[mask, 'Mini (Colis)'] = entry.get('mc', 0.0)
                work_df.loc[mask, 'ddp'] = entry.get('ddp', "")
                work_df.loc[mask, 'ppa'] = entry.get('ppa', 0.0)
                work_df.loc[mask, 'shp'] = entry.get('shp', 0.0)
                if 'col' in entry:
                    work_df.loc[mask, 'colissage'] = entry.get('col')
    st.session_state.inv_work_df = work_df

# SÉCURITÉ ET COMPATIBILITÉ : Force le reset si la structure est ancienne
if "inv_work_df" in st.session_state:
    required = ['Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'colissage']
    # Si une colonne vitale manque, on vide la session pour forcer la re-création propre
    if not all(c in st.session_state.inv_work_df.columns for c in required):
        del st.session_state.inv_work_df
        st.rerun()

col_t1, col_t2 = st.columns([4, 1])
with col_t1: 
    u_z = st.session_state.current_user.get('zone', 'Non définie')
    st.title("📋 Inventaire Triple & Confrontation")
    st.info(f"👤 Utilisateur : **{st.session_state.current_user.get('username')}** | 📍 Zone assignée : **{u_z}**")
with col_t2:
    if st.button("♻️ Actualiser", use_container_width=True):
        st.cache_data.clear()
        if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
        st.rerun()

if df_master is None:
    st.warning("⚠️ Aucun fichier Master détecté.")
    st.stop()

# --- FICHES VIERGES ---
with st.expander("🖨️ Impression des Fiches Terrain"):
    from utils_pdf import generate_blank_inventory_pdf
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        type_f = st.radio("Type :", ["Global", "Par Zone"], horizontal=True)
    df_p = df_master.copy()
    if type_f == "Par Zone":
        zs = sorted(df_p['zone'].unique())
        sz = col_p2.selectbox("Zone :", zs)
        df_p = df_p[df_p['zone'] == sz]
    
    if st.download_button("📥 Télécharger Fiche Vierge (PDF)", generate_blank_inventory_pdf(df_p, "Triple", [('produit','Produit',55),('lot','Lot',28)]), f"Fiche_{type_f}.pdf", "application/pdf"):
        st.success("Généré !")

tabs = st.tabs(["📊 Dashboard", "⚡ Saisie Inventaire", "📉 Analyse Écarts", "⚙️ Gestion"])

# --- DASHBOARD ---
with tabs[0]:
    # Sélecteur de zone pour Admin
    z_override = None
    if st.session_state.current_user.get('role') in ['Admin', 'Superviseur']:
        all_zs = ["Toutes"] + sorted(df_master['zone'].unique().tolist())
        z_override = st.selectbox("👁️ Voir une zone spécifique :", all_zs)

    dash_df = get_user_data(selected_zone_override=z_override)
    if dash_df.empty: st.info("Aucune zone assignée.")
    else:
        work = st.session_state.inv_work_df
        dash_df = dash_df.merge(work[['produit', 'lot', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)']], on=['produit', 'lot'], how='left')
        total = len(dash_df)
        counted = ((dash_df['Terrain (Vrac)'] > 0) | (dash_df['Terrain (Colis)'] > 0) | (dash_df['Mini (Colis)'] > 0)).sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Produits", total)
        c2.metric("✅ Comptés", counted)
        c3.progress(counted / total if total > 0 else 0)

# --- SAISIE ---
with tabs[1]:
    # Sélecteur de zone pour Admin en mode saisie
    z_s_override = None
    if st.session_state.current_user.get('role') in ['Admin', 'Superviseur']:
        all_zs = ["Toutes"] + sorted(df_master['zone'].unique().tolist())
        z_s_override = st.selectbox("📍 Travailler sur la zone :", all_zs, key="sb_z_saisie")

    # AI SCANNER
    if is_ia_scanner_enabled():
        with st.expander("📷 Scanner IA", expanded=False):
            img = st.camera_input("Prendre une photo")
            if img and st.button("🔍 Analyser"):
                b64 = base64.b64encode(img.getvalue()).decode()
                res = ask_ai_vision("Extrais JSON: {\"designation\": \"...\", \"lot\": \"...\"}", b64)
                try:
                    data = json.loads(re.search(r'\{.*\}', res, re.DOTALL).group())
                    st.session_state.ai_triple = data
                    st.success(f"Détecté: {data['designation']}")
                except: st.error("Échec lecture IA")

    available_data = get_user_data(selected_zone_override=z_s_override)
    if available_data.empty:
        st.error("❌ Aucune zone attribuée.")
    else:
        ai_d = st.session_state.get('ai_triple', {})
        list_prods = sorted(available_data['produit'].unique().tolist())
        
        # Recherche auto si scan IA
        idx_p = 0
        if ai_d.get('designation'):
            matches = difflib.get_close_matches(ai_d['designation'].upper(), list_prods, n=1, cutoff=0.3)
            if matches: idx_p = list_prods.index(matches[0])

        col_p1, col_p2 = st.columns([3, 1])
        selected_prod = col_p1.selectbox("🔍 Produit :", list_prods, index=idx_p)
        lots_avail = sorted(available_data[available_data['produit'] == selected_prod]['lot'].unique().tolist())
        
        idx_l = 0
        if ai_d.get('lot'):
            l_matches = difflib.get_close_matches(ai_d['lot'].upper(), lots_avail, n=1, cutoff=0.5)
            if l_matches: idx_l = lots_avail.index(l_matches[0])
            
        selected_lot = col_p2.selectbox("📦 Lot :", lots_avail, index=idx_l)

        if selected_prod and selected_lot:
            work = st.session_state.inv_work_df
            mask = (work['produit'] == selected_prod) & (work['lot'] == selected_lot)
            curr = work[mask].iloc[0]

            st.markdown('<div class="entry-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-header">📍 ZONE 1 : TERRAIN (VRAC)</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            tv = c1.number_input("Vrac (Unités)", value=float(curr['Terrain (Vrac)']), key="tv_v")
            tc = c2.number_input("Colis", value=float(curr['Terrain (Colis)']), key="tc_v")
            col_v = c3.number_input("U/Colis", value=float(curr['colissage']), key="col_v", min_value=1.0)

            st.markdown('<div class="section-header">📦 ZONE 2 : MINI STOCK</div>', unsafe_allow_html=True)
            c4, c5 = st.columns(2)
            mc = c4.number_input("Mini (Colis)", value=float(curr['Mini (Colis)']), key="mc_v")
            ddp = c5.text_input("DDP (MM/AAAA)", value=str(curr['ddp']), key="ddp_v")

            st.markdown('<div class="section-header">💰 PRIX</div>', unsafe_allow_html=True)
            c6, c7 = st.columns(2)
            ppa = c6.number_input("PPA", value=float(curr['ppa']), key="ppa_v")
            shp = c7.number_input("SHP", value=float(curr['shp']), key="shp_v")
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("✅ Valider", type="primary", use_container_width=True):
                st.session_state.inv_work_df.loc[mask, ['Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'colissage', 'ddp', 'ppa', 'shp']] = [tv, tc, mc, col_v, ddp, ppa, shp]
                entry = {'produit': selected_prod, 'lot': selected_lot, 'tv': tv, 'tc': tc, 'mv': 0.0, 'mc': mc, 'col': col_v, 'ddp': ddp, 'ppa': ppa, 'shp': shp}
                df_it = load_gs_data(INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK, COLS_INV_TRIPLE)
                m_save = (df_it['produit'] == selected_prod) & (df_it['lot'] == selected_lot)
                if m_save.any():
                    for k, v in entry.items(): df_it.loc[m_save, k] = v
                else: df_it = pd.concat([df_it, pd.DataFrame([entry])], ignore_index=True)
                save_gs_data(df_it, INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
                st.success("Enregistré !")
                if 'ai_triple' in st.session_state: del st.session_state.ai_triple
                st.rerun()

    with st.expander("🏁 Clôturer l'Inventaire de Zone"):
        st.write("Ceci génère votre bon de validation et met à zéro les produits non trouvés.")
        if st.button("🔴 Terminer ma zone et Générer Bon de Validation", use_container_width=True):
            # Logique de mise à zéro forcée
            user_d = get_user_data()
            work = st.session_state.inv_work_df
            df_final = user_d.merge(work[['produit', 'lot', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'colissage', 'ddp', 'ppa', 'shp']], on=['produit', 'lot'], how='left')
            
            # Génération Bon PDF (Utilise le rapport d'inventaire existant)
            from utils_pdf import generate_inventory_report_pdf
            pdf = generate_inventory_report_pdf(df_final, f"BON DE VALIDATION - ZONE {st.session_state.current_user.get('zone')}")
            st.download_button("📥 Télécharger votre Bon de Validation", pdf, "Bon_Validation.pdf", "application/pdf")
            st.success("Zone clôturée !")
            st.balloons()

# --- ANALYSE ---
with tabs[2]:
    res_df = get_user_data()
    if not res_df.empty:
        work = st.session_state.inv_work_df
        res_df = res_df.merge(work[['produit', 'lot', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'colissage']], on=['produit', 'lot'], how='left')
        res_df['Total'] = res_df['Terrain (Vrac)'] + (res_df['Terrain (Colis)'] * res_df['colissage']) + (res_df['Mini (Colis)'] * res_df['colissage'])
        res_df['Ecart'] = res_df['Total'] - res_df['qte_logi']
        diff = res_df[res_df['Ecart'] != 0]
        st.metric("Écarts détectés", len(diff))
        st.dataframe(diff[['depot', 'zone', 'produit', 'lot', 'qte_logi', 'Total', 'Ecart']], use_container_width=True)

# --- GESTION ---
with tabs[3]:
    if st.session_state.current_user.get('role') == 'Admin':
        if st.button("🗑️ Réinitialiser tout l'Inventaire Triple", type="secondary"):
            save_gs_data(pd.DataFrame(columns=COLS_INV_TRIPLE), INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
            st.rerun()
