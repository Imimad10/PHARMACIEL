import streamlit as st
import pandas as pd
import os
import unicodedata
from datetime import datetime
from utils_gsheets import load_gs_data, show_sync_ui
from utils_pdf import generate_blank_inventory_pdf
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
# Worksheets sources
WS_MASTER_ZONE = "Master_Inventaire_Zone"
WS_SAISIE_ZONE = "Saisie_Inventaire_Zone"
WS_TRIPLE_ZONE = "Triple_Saisie_Zone"
WS_TRIPLE_MINI = "Triple_Saisie_Mini"
WS_MASTER_STOCK = "Master_Inventaire"
WS_SAISIE_STOCK = "Saisie_Inventaire"

# Path fallbacks
DATA_DIR = "data_inventaire_detail"
os.makedirs(DATA_DIR, exist_ok=True)

# --- 2. CHARGEMENT & NORMALISATION ---
def normalize_cols(df):
    if df is None or df.empty: return pd.DataFrame()
    mapping = {
        'produit': 'designation', 'article': 'designation', 'libelle': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'batch': 'lot',
        'emplacement': 'zone', 'sector': 'zone'
    }
    cols = []
    for c in df.columns:
        norm = c.lower().strip()
        cols.append(mapping.get(norm, norm))
    df.columns = cols
    return df

def robust_num(s):
    if pd.isna(s) or s == "": return 0.0
    try: return float(str(s).replace('\xa0', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

@st.cache_data(ttl=60)
def load_all_inventory_data():
    m_z = normalize_cols(load_gs_data(WS_MASTER_ZONE, os.path.join(DATA_DIR, "m_zone.csv")))
    s_z = normalize_cols(load_gs_data(WS_SAISIE_ZONE, os.path.join(DATA_DIR, "s_zone.csv")))
    t_z = normalize_cols(load_gs_data(WS_TRIPLE_ZONE, os.path.join(DATA_DIR, "t_zone.csv")))
    t_m = normalize_cols(load_gs_data(WS_TRIPLE_MINI, os.path.join(DATA_DIR, "t_mini.csv")))
    m_s = normalize_cols(load_gs_data(WS_MASTER_STOCK, os.path.join(DATA_DIR, "m_stock.csv")))
    s_s = normalize_cols(load_gs_data(WS_SAISIE_STOCK, os.path.join(DATA_DIR, "s_stock.csv")))
    return m_z, s_z, t_z, t_m, m_s, s_s

m_z, s_z, t_z, t_m, m_s, s_s = load_all_inventory_data()

def get_progression(df_master, df_saisie, zone_val=None):
    if df_master.empty: return 0, 0, 0
    
    m_f = df_master
    if zone_val and 'zone' in df_master.columns:
        m_f = df_master[df_master['zone'] == zone_val]
    
    total = len(m_f)
    if total == 0: return 0, 0, 0
    
    done = 0
    if not df_saisie.empty and 'designation' in df_saisie.columns:
        s_f = df_saisie
        if zone_val and 'zone' in df_saisie.columns:
            s_f = df_saisie[df_saisie['zone'] == zone_val]
        done = s_f['designation'].nunique()
        
    pct = (done / total) if total > 0 else 0
    return done, total, pct

# --- 3. UI DASHBOARD ---
st.title("🔍 Supervision & Dashboard Inventaires")
st.markdown("### Suivi en temps réel des inventaires (Détail, Triple, Stock)")

tabs = st.tabs(["📊 Dashboard de Progression", "📦 État des Stocks", "🖨️ Fiches Vierges", "⚙️ Admin"])

# --- TAB 0 : DASHBOARD ---
with tabs[0]:
    st.subheader("🚀 Avancement Global par Système")
    
    col_met1, col_met2, col_met3 = st.columns(3)
    
    # -- 1. INVENTAIRE DÉTAIL (PAR ZONE) --
    with st.expander("📌 PROGRESSION INVENTAIRE DÉTAIL (PAR ZONE)", expanded=True):
        if not m_z.empty and 'zone' in m_z.columns:
            zones = sorted(m_z['zone'].dropna().unique())
            for z in zones:
                done, total, pct = get_progression(m_z, s_z, z)
                c_l, c_b = st.columns([1, 4])
                c_l.write(f"**Zone {z}**")
                c_b.progress(min(pct, 1.0), text=f"{done} / {total} ({pct*100:.1f}%)")
        else:
            st.info("Données Master Zone indisponibles ou colonne 'zone' manquante.")

    # -- 2. INVENTAIRE TRIPLE --
    with st.expander("🛡️ PROGRESSION INVENTAIRE TRIPLE (ZONE + MINI)", expanded=True):
        if not m_z.empty and 'zone' in m_z.columns:
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                st.write("**Progression Zone (Triple)**")
                for z in zones:
                    done, total, pct = get_progression(m_z, t_z, z)
                    st.caption(f"Zone {z}: {done}/{total}")
                    st.progress(min(pct, 1.0))
            with c_t2:
                st.write("**Progression Mini Stock (Triple)**")
                for z in zones:
                    done, total, pct = get_progression(m_z, t_m, z)
                    st.caption(f"Mini {z}: {done}/{total}")
                    st.progress(min(pct, 1.0))

    # -- 3. INVENTAIRE DE STOCK (GLOBAL) --
    with st.expander("📋 PROGRESSION INVENTAIRE DE STOCK", expanded=True):
        done_s, total_s, pct_s = get_progression(m_s, s_s)
        if total_s > 0:
            st.metric("Total Articles Stock", f"{total_s}", f"{done_s} comptés")
            st.progress(min(pct_s, 1.0), text=f"{pct_s*100:.1f}% complété")
        else:
            st.info("Aucune donnée Master Stock chargée.")

# --- TAB 1 : ÉTAT DES STOCKS ---
with tabs[1]:
    st.subheader("📦 Consultation des Articles & Zones")
    
    if not m_z.empty:
        search = st.text_input("🔍 Rechercher un article (Désignation, Lot, Zone)...")
        df_display = m_z.copy()
        if search:
            df_display = df_display[
                df_display['designation'].str.contains(search, case=False, na=False) |
                df_display['lot'].str.contains(search, case=False, na=False) |
                df_display['zone'].str.contains(search, case=False, na=False)
            ]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.warning("Données Master non disponibles.")

# --- TAB 2 : FICHES VIERGES ---
with tabs[2]:
    st.subheader("🖨️ Génération de Fiches Inventaire Vierges")
    st.write("Imprimez des listes triées par zone ou par laboratoire pour les équipes terrain.")
    
    if not m_z.empty:
        c1, c2 = st.columns(2)
        with c1:
            z_sel = st.selectbox("Filtrer par Zone :", ["Toutes"] + sorted(m_z['zone'].dropna().unique().tolist()))
        with c2:
            labos = ["Tous"]
            if 'labo' in m_z.columns:
                labos += sorted(m_z['labo'].dropna().unique().tolist())
            lab_sel = st.selectbox("Filtrer par Laboratoire :", labos)
            
        df_print = m_z.copy()
        if z_sel != "Toutes":
            df_print = df_print[df_print['zone'] == z_sel]
        if lab_sel != "Tous":
            df_print = df_print[df_print['labo'] == lab_sel]
            
        # TRI ALPHABÉTIQUE
        df_print = df_print.sort_values(by='designation')
        
        st.write(f"📄 **Articles à imprimer :** {len(df_print)}")
        
        if st.button("📥 Générer le PDF (Fiche Vierge)", type="primary", use_container_width=True):
            cols_to_print = [('designation', 'Produit', 60), ('lot', 'Lot', 30), ('zone', 'Zone', 10)]
            pdf_bytes = generate_blank_inventory_pdf(df_print, f"Fiche Inventaire - {z_sel} - {lab_sel}", cols_to_print)
            
            st.download_button(
                "💾 Télécharger le PDF",
                pdf_bytes,
                f"Fiche_Vierge_{z_sel}_{lab_sel}.pdf",
                "application/pdf",
                use_container_width=True
            )
    else:
        st.info("Importez un Master Zone pour générer des fiches.")

# --- TAB 3 : ADMIN ---
with tabs[3]:
    st.subheader("⚙️ Maintenance du Dashboard")
    st.write("Ce volet a été vidé des fonctions de saisie terrain. Il sert uniquement à la maintenance visuelle.")
    
    if st.button("🔄 Forcer la synchronisation des données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.caption("Pharmaciel Pro — Dashboard Supervision Inventaire v2.0")
