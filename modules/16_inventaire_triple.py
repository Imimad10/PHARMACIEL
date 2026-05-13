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

# Séparation des bases Zone et Mini
WS_ZONE = "Triple_Saisie_Zone"
FB_ZONE = "data/db_triple_zone.csv"
WS_MINI = "Triple_Saisie_Mini"
FB_MINI = "data/db_triple_mini.csv"

COLS_MASTER = ["depot", "zone", "produit", "lot", "qte_logi", "colissage"]
# Structure commune pour les deux saisies
COLS_ENTRY = ["produit", "lot", "qte", "ddp", "ppa", "shp", "agent"]

if 'current_user' not in st.session_state:
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

# --- STYLE CSS ---
st.markdown("""
    <style>
    .entry-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #eef2f6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .error-row { background-color: #ffebee !important; color: #c62828 !important; }
    .section-title { color: #1877f2; font-weight: bold; border-bottom: 2px solid #e7f3ff; padding-bottom: 5px; margin-bottom: 15px; }
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
    # Nettoyage
    df.columns = [c.lower() for c in df.columns]
    mapping = {'dépôt':'depot', 'désignation':'produit', 'n°lot':'lot', 'quantité':'qte_logi', 'colis':'colissage'}
    df = df.rename(columns=mapping)
    for c in COLS_MASTER:
        if c not in df.columns: df[c] = ""
    df['produit'] = df['produit'].astype(str).str.upper()
    df['lot'] = df['lot'].astype(str).str.upper()
    try: df['qte_logi'] = pd.to_numeric(df['qte_logi'], errors='coerce').fillna(0)
    except: df['qte_logi'] = 0
    return df[COLS_MASTER]

df_m = get_master()
df_z = load_gs_data(WS_ZONE, FB_ZONE, COLS_ENTRY)
df_mi = load_gs_data(WS_MINI, FB_MINI, COLS_ENTRY)

def get_user_zone_df():
    u_z = str(st.session_state.current_user.get('zone', '')).upper()
    role = st.session_state.current_user.get('role')
    if role == 'Admin': return df_m
    return df_m[df_m['zone'].astype(str).str.upper().str.contains(u_z, na=False)]

# --- INTERFACE TABS ---
st.title("📋 Inventaire Triple Stratégique")
t_zone, t_mini, t_final, t_conf = st.tabs(["📍 Saisie en Zone", "📦 Saisie Mini Stock", "📊 Saisie Final", "📉 Confrontation"])

# --- TAB 1 & 2 : LOGIQUE COMMUNE ---
def render_saisie_tab(df_entries, ws_name, fb_path, title):
    st.subheader(title)
    u_df = get_user_zone_df()
    if u_df.empty:
        st.warning("Aucun produit dans votre zone.")
        return df_entries

    prods = sorted(u_df['produit'].unique().tolist())
    c1, c2 = st.columns([3, 1])
    sel_p = c1.selectbox(f"Produit ({title})", prods, key=f"p_{ws_name}")
    
    lots_m = sorted(u_df[u_df['produit'] == sel_p]['lot'].unique().tolist())
    sel_l_m = c2.selectbox(f"Lot Master", lots_m, key=f"l_m_{ws_name}")
    
    st.markdown('<div class="entry-card">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 1, 1])
    lot_r = f1.text_input("Lot Réel (Corriger si besoin)", value=sel_l_m, key=f"lr_{ws_name}")
    qte = f2.number_input("Quantité Saisie", min_value=0.0, step=1.0, key=f"q_{ws_name}")
    ddp = f3.text_input("DDP (MM/AAAA)", key=f"d_{ws_name}")
    
    f4, f5 = st.columns(2)
    ppa = f4.number_input("PPA", min_value=0.0, key=f"pp_{ws_name}")
    shp = f5.number_input("SHP", min_value=0.0, key=f"sh_{ws_name}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button(f"💾 Enregistrer {title}", type="primary", use_container_width=True, key=f"b_{ws_name}"):
        new = {
            "produit": sel_p, "lot": lot_r.upper(), "qte": qte, 
            "ddp": ddp, "ppa": ppa, "shp": shp, 
            "agent": st.session_state.current_user.get('username')
        }
        # Upsert
        mask = (df_entries['produit'] == sel_p) & (df_entries['lot'] == lot_r.upper())
        if mask.any():
            for k, v in new.items(): df_entries.loc[mask, k] = v
        else:
            df_entries = pd.concat([df_entries, pd.DataFrame([new])], ignore_index=True)
        
        save_gs_data(df_entries, ws_name, fb_path)
        st.success(f"Enregistré dans {title} !")
        st.rerun()
    
    st.divider()
    st.write(f"### Historique {title}")
    st.dataframe(df_entries[df_entries['produit'] == sel_p], use_container_width=True)
    return df_entries

with t_zone:
    df_z = render_saisie_tab(df_z, WS_ZONE, FB_ZONE, "Saisie en Zone (Vrac)")

with t_mini:
    df_mi = render_saisie_tab(df_mi, WS_MINI, FB_MINI, "Saisie Mini Stock (Colis)")

# --- TAB 3 : SAISIE FINAL ---
with t_final:
    st.subheader("📊 Compilation & Réconciliation Final")
    
    # On merge les deux bases
    df_final = pd.merge(
        df_z, df_mi, on=['produit', 'lot'], how='outer', suffixes=('_zone', '_mini')
    ).fillna(0)
    
    if df_final.empty:
        st.info("Aucune donnée saisie pour le moment.")
    else:
        # Calculs
        df_final['Total Qte'] = df_final['qte_zone'] + df_final['qte_mini']
        
        # Check incohérences (DDP, PPA, SHP)
        def check_diff(row):
            issues = []
            if str(row['ddp_zone']) != str(row['ddp_mini']) and row['qte_zone'] > 0 and row['qte_mini'] > 0: issues.append("DDP")
            if row['ppa_zone'] != row['ppa_mini'] and row['qte_zone'] > 0 and row['qte_mini'] > 0: issues.append("PPA")
            if row['shp_zone'] != row['shp_mini'] and row['qte_zone'] > 0 and row['qte_mini'] > 0: issues.append("SHP")
            return ", ".join(issues) if issues else "OK"

        df_final['Incohérence'] = df_final.apply(check_diff, axis=1)
        
        # Styling
        def style_final(row):
            return ['background-color: #ffebee' if row['Incohérence'] != "OK" else '' for _ in row]

        st.write("Détail des saisies compilées :")
        cols_disp = ['produit', 'lot', 'qte_zone', 'qte_mini', 'Total Qte', 'Incohérence', 'ddp_zone', 'ddp_mini', 'ppa_zone', 'ppa_mini']
        st.dataframe(df_final[cols_disp].style.apply(style_final, axis=1), use_container_width=True)
        
        if st.button("📥 Exporter la Saisie Final pour Confrontation", type="primary"):
            st.session_state.compiled_triple = df_final
            st.success("Données envoyées à l'onglet Confrontation !")

# --- TAB 4 : CONFRONTATION ---
with t_conf:
    st.subheader("📉 Confrontation Final avec Master Logipharm")
    
    if 'compiled_triple' not in st.session_state:
        st.info("Veuillez compiler les données dans l'onglet 'Saisie Final' d'abord.")
    else:
        comp = st.session_state.compiled_triple
        # On compare avec le Master
        master_zone = get_user_zone_df()
        
        final_table = pd.merge(
            master_zone, comp[['produit', 'lot', 'Total Qte', 'Incohérence']], 
            on=['produit', 'lot'], how='left'
        ).fillna(0)
        
        final_table['Ecart'] = final_table['Total Qte'] - final_table['qte_logi']
        
        st.write("Résultats de la confrontation :")
        c_disp = ['zone', 'produit', 'lot', 'qte_logi', 'Total Qte', 'Ecart', 'Incohérence']
        
        def highlight_ecart(val):
            color = 'red' if val < 0 else ('green' if val > 0 else 'black')
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            final_table[c_disp].style.applymap(highlight_ecart, subset=['Ecart']),
            use_container_width=True
        )
        
        # Export PDF
        if st.button("📄 Générer Rapport d'Inventaire Triple (PDF)"):
            from utils_pdf import generate_inventory_report_pdf
            pdf = generate_inventory_report_pdf(final_table, "RAPPORT D'INVENTAIRE TRIPLE RÉCONCILIÉ")
            st.download_button("📥 Télécharger le Rapport", pdf, "Inventaire_Triple.pdf", "application/pdf")

    # Bouton reset admin
    if st.session_state.current_user.get('role') == 'Admin':
        st.divider()
        if st.button("🗑️ Réinitialiser TOUTES les saisies (Zone & Mini)"):
            save_gs_data(pd.DataFrame(columns=COLS_ENTRY), WS_ZONE, FB_ZONE)
            save_gs_data(pd.DataFrame(columns=COLS_ENTRY), WS_MINI, FB_MINI)
            st.rerun()
