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
st.set_page_config(page_title="Inventaire Triple Pro - Pharmaciel", layout="wide")

from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui

# --- CONFIGURATION DES BASES ---
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = "data_inventaire_detail/master_detail.csv"
WS_ZONE = "Triple_Saisie_Zone"
FB_ZONE = "data/db_triple_zone.csv"
WS_MINI = "Triple_Saisie_Mini"
FB_MINI = "data/db_triple_mini.csv"

COLS_MASTER = ["depot", "zone", "produit", "lot", "qte_logi", "colissage"]
COLS_ENTRY = ["zone", "produit", "lot", "qte", "ddp", "ppa", "shp", "agent"]

if 'current_user' not in st.session_state:
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

# --- STYLE CSS ---
st.markdown("""
    <style>
    .entry-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #eef2f6; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .section-title { color: #1877f2; font-weight: bold; border-bottom: 2px solid #e7f3ff; padding-bottom: 5px; margin-bottom: 15px; }
    .admin-box { background: #fffde7; padding: 10px; border-radius: 8px; border: 1px solid #fff59d; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').upper().strip()

# --- CHARGEMENT ---
@st.cache_data(ttl=600)
def get_master():
    df = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
    if df.empty: return pd.DataFrame(columns=COLS_MASTER)
    df.columns = [c.lower() for c in df.columns]
    mapping = {'dépôt':'depot', 'désignation':'produit', 'n°lot':'lot', 'quantité':'qte_logi', 'colis':'colissage'}
    df = df.rename(columns=mapping)
    for c in COLS_MASTER:
        if c not in df.columns: df[c] = ""
    df['produit'] = df['produit'].astype(str).str.upper()
    df['lot'] = df['lot'].astype(str).str.upper()
    df['zone'] = df['zone'].astype(str).str.upper()
    try: df['qte_logi'] = pd.to_numeric(df['qte_logi'], errors='coerce').fillna(0)
    except: df['qte_logi'] = 0
    return df[COLS_MASTER]

df_m = get_master()
df_z = load_gs_data(WS_ZONE, FB_ZONE, COLS_ENTRY)
df_mi = load_gs_data(WS_MINI, FB_MINI, COLS_ENTRY)

# --- LOGIQUE D'ACCÈS ---
user_role = st.session_state.current_user.get('role', 'Saisie')
is_admin = user_role in ['Admin', 'Superviseur']
user_zone = str(st.session_state.current_user.get('zone', '')).upper()

def filter_by_permissions(df, zone_col='zone'):
    if is_admin: return df
    if zone_col not in df.columns: return df
    return df[df[zone_col].astype(str).str.upper().str.contains(user_zone, na=False)]

# --- INTERFACE ---
st.title("📋 Inventaire Triple & Zonage")

# Sélecteur de zone global pour Admin
selected_zone_filter = "Toutes"
if is_admin:
    with st.container():
        st.markdown('<div class="admin-box">🛡️ **Mode Superviseur** : Vous voyez toutes les zones.</div>', unsafe_allow_html=True)
        zones_list = ["Toutes"] + sorted(df_m['zone'].unique().tolist())
        selected_zone_filter = st.selectbox("🎯 Filtrer la vue globale par Zone :", zones_list)

# Application du filtrage pour la session
def get_working_master():
    if is_admin and selected_zone_filter != "Toutes":
        return df_m[df_m['zone'] == selected_zone_filter]
    elif is_admin:
        return df_m
    else:
        return df_m[df_m['zone'].astype(str).str.upper().str.contains(user_zone, na=False)]

def get_working_entries(df):
    if is_admin and selected_zone_filter != "Toutes":
        return df[df['zone'].astype(str) == selected_zone_filter]
    elif is_admin:
        return df
    else:
        return df[df['zone'].astype(str).str.upper().str.contains(user_zone, na=False)]

t_zone, t_mini, t_final, t_conf = st.tabs(["📍 Saisie Zone", "📦 Saisie Mini", "📊 Compilation", "📉 Confrontation"])

# --- LOGIQUE DE SAISIE ---
def render_saisie(df_full, ws_name, fb_path, title, key_prefix):
    master_w = get_working_master()
    if master_w.empty:
        st.warning("Aucun produit à saisir dans ce périmètre.")
        return df_full

    prods = sorted(master_w['produit'].unique().tolist())
    c1, c2 = st.columns([3, 1])
    sel_p = c1.selectbox(f"Produit ({title})", prods, key=f"p_{key_prefix}")
    
    # On filtre les lots master pour ce produit et cette zone
    lots_m = sorted(master_w[master_w['produit'] == sel_p]['lot'].unique().tolist())
    # On récupère la zone du produit sélectionné
    p_zone = master_w[master_w['produit'] == sel_p]['zone'].iloc[0]
    
    sel_l_m = c2.selectbox(f"Lot Master", lots_m, key=f"lm_{key_prefix}")
    
    st.markdown('<div class="entry-card">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 1, 1])
    lot_r = f1.text_input("Lot Réel", value=sel_l_m, key=f"lr_{key_prefix}")
    qte = f2.number_input("Quantité", min_value=0.0, step=1.0, key=f"q_{key_prefix}")
    ddp = f3.text_input("DDP (MM/AAAA)", key=f"d_{key_prefix}")
    
    f4, f5 = st.columns(2)
    ppa = f4.number_input("PPA", min_value=0.0, key=f"pp_{key_prefix}")
    shp = f5.number_input("SHP", min_value=0.0, key=f"sh_{key_prefix}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button(f"💾 Enregistrer {title}", type="primary", use_container_width=True, key=f"btn_{key_prefix}"):
        new = {
            "zone": p_zone, "produit": sel_p, "lot": lot_r.upper(), 
            "qte": qte, "ddp": ddp, "ppa": ppa, "shp": shp, 
            "agent": st.session_state.current_user.get('username')
        }
        # Upsert global
        mask = (df_full['produit'] == sel_p) & (df_full['lot'] == lot_r.upper())
        if mask.any():
            for k, v in new.items(): df_full.loc[mask, k] = v
        else:
            df_full = pd.concat([df_full, pd.DataFrame([new])], ignore_index=True)
        
        save_gs_data(df_full, ws_name, fb_path)
        st.success(f"Saisie {title} enregistrée !")
        st.rerun()
    
    # Affichage historique local
    st.write(f"### Vos dernières saisies ({title})")
    hist = get_working_entries(df_full)
    st.dataframe(hist[hist['produit'] == sel_p], use_container_width=True)
    return df_full

with t_zone:
    df_z = render_saisie(df_z, WS_ZONE, FB_ZONE, "Zone (Vrac)", "z")

with t_mini:
    df_mi = render_saisie(df_mi, WS_MINI, FB_MINI, "Mini Stock (Colis)", "m")

# --- COMPILATION ---
with t_final:
    st.subheader("📊 Réconciliation Finale")
    w_z = get_working_entries(df_z)
    w_mi = get_working_entries(df_mi)
    
    df_comp = pd.merge(w_z, w_mi, on=['produit', 'lot'], how='outer', suffixes=('_z', '_m')).fillna(0)
    
    if df_comp.empty:
        st.info("Aucune donnée à compiler pour ce périmètre.")
    else:
        # Zone harmonisée (si absent d'un côté, on prend l'autre)
        df_comp['zone'] = df_comp.apply(lambda r: r['zone_z'] if r['zone_z'] != 0 else r['zone_m'], axis=1)
        df_comp['Total'] = df_comp['qte_z'] + df_comp['qte_m']
        
        def detect_err(r):
            if r['qte_z'] > 0 and r['qte_m'] > 0:
                errs = []
                if str(r['ddp_z']) != str(r['ddp_m']): errs.append("DDP")
                if r['ppa_z'] != r['ppa_m']: errs.append("PPA")
                if r['shp_z'] != r['shp_m']: errs.append("SHP")
                return ", ".join(errs) if errs else "OK"
            return "OK"
        
        df_comp['Incohérence'] = df_comp.apply(detect_err, axis=1)
        
        c_disp = ['zone', 'produit', 'lot', 'qte_z', 'qte_m', 'Total', 'Incohérence', 'ddp_z', 'ddp_m']
        st.dataframe(df_comp[c_disp].style.apply(lambda r: ['background-color: #ffebee' if r['Incohérence'] != "OK" else '' for _ in r], axis=1), use_container_width=True)
        
        if st.button("📥 Valider la compilation pour confrontation"):
            st.session_state.it_ready = df_comp
            st.success("Données compilées !")

# --- CONFRONTATION ---
with t_conf:
    st.subheader("📉 Confrontation avec Master Logipharm")
    if 'it_ready' not in st.session_state:
        st.info("Compilez d'abord les données.")
    else:
        comp = st.session_state.it_ready
        m_w = get_working_master()
        
        conf = pd.merge(m_w, comp[['produit', 'lot', 'Total', 'Incohérence']], on=['produit', 'lot'], how='left').fillna(0)
        conf['Ecart'] = conf['Total'] - conf['qte_logi']
        
        st.dataframe(conf[['zone', 'produit', 'lot', 'qte_logi', 'Total', 'Ecart', 'Incohérence']].style.applymap(lambda v: 'color: red' if v<0 else ('color: green' if v>0 else ''), subset=['Ecart']), use_container_width=True)
        
        if st.button("📄 Rapport Final PDF"):
            from utils_pdf import generate_inventory_report_pdf
            st.download_button("Télécharger PDF", generate_inventory_report_pdf(conf, f"RAPPORT TRIPLE - {selected_zone_filter}"), "Inventaire.pdf", "application/pdf")

    if is_admin:
        st.divider()
        if st.button("🗑️ Vider toutes les bases (Action Irréversible)"):
            save_gs_data(pd.DataFrame(columns=COLS_ENTRY), WS_ZONE, FB_ZONE)
            save_gs_data(pd.DataFrame(columns=COLS_ENTRY), WS_MINI, FB_MINI)
            st.rerun()
