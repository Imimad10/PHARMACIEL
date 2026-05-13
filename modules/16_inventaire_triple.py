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

# --- SÉCURITÉ CRITIQUE : RESET SESSION SI ANCIENNE VERSION ---
REQUIRED_COLS = ['Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'mv', 'colissage']
if "inv_work_df" in st.session_state:
    if not all(c in st.session_state.inv_work_df.columns for c in REQUIRED_COLS):
        # On force la suppression et le reload si la structure est obsolète
        del st.session_state.inv_work_df
        st.cache_data.clear()
        st.rerun()

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
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def robust_num(val):
    try: return float(val) if not pd.isna(val) else 0.0
    except: return 0.0

@st.cache_data(ttl=3600)
def get_master_df():
    df = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
    if df.empty: return None
    mapping = {
        'dépôt': 'depot', 'depot': 'depot', 'produit': 'produit', 'désignation': 'produit',
        'n°lot': 'lot', 'lot': 'lot', 'batch': 'lot', 'quantité': 'qte_logi', 'zone': 'zone', 'colis': 'colissage'
    }
    current_cols = {normalize_text(c): c for c in df.columns}
    rename_dict = {}
    for key, target in mapping.items():
        if key in current_cols: rename_dict[current_cols[key]] = target
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
    if selected_zone_override and selected_zone_override != "Toutes":
        user_zone = selected_zone_override.strip().upper()
        user_role = 'Saisie'
    if user_role not in ['Admin', 'Superviseur']:
        if not user_zone or user_zone == 'AUCUNE': return df.iloc[0:0]
        if 'zone' in df.columns:
            df['z_c'] = df['zone'].astype(str).str.strip().str.upper()
            df = df[df['z_c'].str.contains(user_zone, na=False, regex=False)]
    return df

# Initialisation du work_df
if "inv_work_df" not in st.session_state and df_master is not None:
    wdf = df_master.copy()
    for c in REQUIRED_COLS: wdf[c] = 0.0 if c != 'colissage' else 1.0
    wdf['ddp'] = ""; wdf['ppa'] = 0.0; wdf['shp'] = 0.0
    if not df_inv_triple.empty:
        for _, e in df_inv_triple.iterrows():
            m = (wdf['produit'] == e.get('produit')) & (wdf['lot'] == e.get('lot'))
            if m.any():
                wdf.loc[m, 'Terrain (Vrac)'] = e.get('tv', 0.0)
                wdf.loc[m, 'Terrain (Colis)'] = e.get('tc', 0.0)
                wdf.loc[m, 'Mini (Colis)'] = e.get('mc', 0.0)
                wdf.loc[m, 'mv'] = e.get('mv', 0.0)
                wdf.loc[m, 'ddp'] = e.get('ddp', "")
                wdf.loc[m, 'ppa'] = e.get('ppa', 0.0)
                wdf.loc[m, 'shp'] = e.get('shp', 0.0)
                if 'col' in e: wdf.loc[m, 'colissage'] = e.get('col')
    st.session_state.inv_work_df = wdf

col_t1, col_t2 = st.columns([4, 1])
with col_t1: 
    uz = st.session_state.current_user.get('zone', 'Aucune')
    st.title("📋 Inventaire Triple & Confrontation")
    st.info(f"📍 Zone : **{uz}**")
with col_t2:
    if st.button("♻️ Actualiser", use_container_width=True):
        st.cache_data.clear(); del st.session_state.inv_work_df; st.rerun()

tabs = st.tabs(["📊 Dashboard", "⚡ Saisie", "📉 Analyse Écarts", "⚙️ Gestion"])

# --- DASHBOARD ---
with tabs[0]:
    zo = None
    if st.session_state.current_user.get('role') in ['Admin', 'Superviseur']:
        zo = st.selectbox("👁️ Voir zone :", ["Toutes"] + sorted(df_master['zone'].unique().tolist()))
    ddf = get_user_data(zo)
    if ddf.empty: st.info("Aucune donnée.")
    else:
        work = st.session_state.inv_work_df
        ddf = ddf.merge(work[['produit', 'lot', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'mv']], on=['produit', 'lot'], how='left')
        total = len(ddf)
        cnt = ((ddf['Terrain (Vrac)'] > 0) | (ddf['Terrain (Colis)'] > 0) | (ddf['Mini (Colis)'] > 0) | (ddf['mv'] > 0)).sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Produits", total); c2.metric("✅ Comptés", cnt); c3.progress(cnt/total if total>0 else 0)

# --- SAISIE ---
with tabs[1]:
    zso = None
    if st.session_state.current_user.get('role') in ['Admin', 'Superviseur']:
        zso = st.selectbox("📍 Travailler zone :", ["Toutes"] + sorted(df_master['zone'].unique().tolist()), key="zss")
    adv = get_user_data(zso)
    if adv.empty: st.error("❌ Aucune zone.")
    else:
        aid = st.session_state.get('ai_triple', {})
        lp = sorted(adv['produit'].unique().tolist())
        idx_p = 0
        if aid.get('designation'):
            m = difflib.get_close_matches(aid['designation'].upper(), lp, n=1, cutoff=0.3)
            if m: idx_p = lp.index(m[0])
        cp1, cp2 = st.columns([3, 1])
        sp = cp1.selectbox("🔍 Produit :", lp, index=idx_p)
        la = sorted(adv[adv['produit'] == sp]['lot'].unique().tolist())
        idx_l = 0
        if aid.get('lot'):
            lm = difflib.get_close_matches(aid['lot'].upper(), la, n=1, cutoff=0.5)
            if lm: idx_l = la.index(lm[0])
        sl = cp2.selectbox("📦 Lot :", la, index=idx_l)
        if sp and sl:
            work = st.session_state.inv_work_df
            mask = (work['produit'] == sp) & (work['lot'] == sl)
            curr = work[mask].iloc[0]
            st.markdown('<div class="entry-card"><div class="section-header">📍 ZONE 1 : VRAC</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            tv = c1.number_input("Vrac", value=float(curr['Terrain (Vrac)']), key="tvv")
            tc = c2.number_input("Colis", value=float(curr['Terrain (Colis)']), key="tcv")
            clv = c3.number_input("U/Colis", value=float(curr['colissage']), key="clv", min_value=1.0)
            st.markdown('<div class="section-header">📦 ZONE 2 : MINI</div>', unsafe_allow_html=True)
            mmini = st.radio("Mode :", ["Colis", "Unités"], horizontal=True, key="mm")
            c4, c5, cx = st.columns([1,1,1])
            if mmini == "Colis":
                mc = c4.number_input("Colis Mini", value=float(curr['Mini (Colis)']), key="mcv")
                clm = c5.number_input("U/Colis Mini", value=float(curr['colissage']), key="clm", min_value=1.0)
                mv = mc * clm; cx.metric("Total Mini", f"{mv:,.0f}")
            else:
                mv = c4.number_input("Unités Mini", value=float(curr['mv']), key="mvv"); mc = 0.0; cx.info("Direct")
            ddp = st.text_input("DDP", value=str(curr['ddp']), key="ddpv")
            st.markdown('<div class="section-header">💰 PRIX</div>', unsafe_allow_html=True)
            c6, c7 = st.columns(2)
            ppa = c6.number_input("PPA", value=float(curr['ppa']), key="ppv")
            shp = c7.number_input("SHP", value=float(curr['shp']), key="shv")
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("✅ Valider", type="primary", use_container_width=True):
                st.session_state.inv_work_df.loc[mask, REQUIRED_COLS+['ddp','ppa','shp']] = [tv, tc, mc, mv, clv, ddp, ppa, shp]
                e = {'produit': sp, 'lot': sl, 'tv': tv, 'tc': tc, 'mv': mv, 'mc': mc, 'col': clv, 'ddp': ddp, 'ppa': ppa, 'shp': shp}
                dit = load_gs_data(INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK, COLS_INV_TRIPLE)
                ms = (dit['produit'] == sp) & (dit['lot'] == sl)
                if ms.any():
                    for k, v in e.items(): dit.loc[ms, k] = v
                else: dit = pd.concat([dit, pd.DataFrame([e])], ignore_index=True)
                save_gs_data(dit, INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
                st.success("Enregistré !"); st.rerun()

# --- ANALYSE ---
with tabs[2]:
    rdf = get_user_data(zo)
    if not rdf.empty:
        work = st.session_state.inv_work_df
        rdf = rdf.merge(work[['produit', 'lot', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'mv', 'colissage']], on=['produit', 'lot'], how='left')
        rdf['Total'] = rdf['Terrain (Vrac)'] + (rdf['Terrain (Colis)'] * rdf['colissage']) + rdf['mv'] + (rdf['Mini (Colis)'] * rdf['colissage'])
        rdf['Ecart'] = rdf['Total'] - rdf['qte_logi']
        diff = rdf[rdf['Ecart'] != 0]
        st.metric("Écarts", len(diff))
        st.dataframe(diff[['depot', 'zone', 'produit', 'lot', 'qte_logi', 'Total', 'Ecart']], use_container_width=True)

# --- GESTION ---
with tabs[3]:
    if st.session_state.current_user.get('role') == 'Admin':
        if st.button("🗑️ Réinitialiser tout", type="secondary"):
            save_gs_data(pd.DataFrame(columns=COLS_INV_TRIPLE), INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK); st.rerun()
