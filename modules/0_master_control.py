import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils_gsheets import load_gs_data, get_gs_url

# Sécurité
user = st.session_state.get('current_user')
if not user or user.get('role') != 'Admin':
    st.error("⛔ Accès réservé aux Administrateurs Système.")
    st.stop()

st.set_page_config(page_title="Master Control - Dashboard Global", layout="wide", page_icon="🌐")

# --- STYLE PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;900&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    
    .master-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 40px; border-radius: 30px; color: white;
        margin-bottom: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        display: flex; justify-content: space-between; align-items: center;
    }
    .kpi-card-master {
        background: white; border-radius: 20px; padding: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: 1px solid #f1f5f9;
        transition: all 0.3s ease;
    }
    .kpi-card-master:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
    .kpi-title { font-size: 0.8rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; }
    .kpi-value { font-size: 2.2rem; font-weight: 900; color: #1e293b; margin: 10px 0; }
    .kpi-delta { font-size: 0.85rem; font-weight: 600; }
    
    .etab-badge {
        padding: 5px 15px; border-radius: 30px; font-size: 0.75rem; font-weight: 800;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="master-header">
    <div>
        <h1 style="margin:0; font-size:2.8rem; font-weight:900;">🌐 Master Control</h1>
        <p style="margin:5px 0 0; opacity:0.7; font-size:1.1rem;">Supervision Stratégique — DarPharm & Pharmaciel</p>
    </div>
    <div style="text-align:right;">
        <span class="etab-badge" style="background:#6366f1; color:white;">ADMIN GLOBAL</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES CROISÉES ---
@st.cache_data(ttl=300)
def load_global_stats():
    urls = {
        "DarPharm": st.secrets.get("GS_URL"),
        "Pharmaciel": st.secrets.get("GS_URL_PHARMACIEL")
    }
    
    stats = {}
    
    for name, url in urls.items():
        if not url: continue
        
        # 1. Recouvrement
        df_rec = load_gs_data("Recouvrement", "data_recouvrement.csv", ["Reste à payer", "Statut"], override_url=url)
        if not df_rec.empty:
            for col in ["Reste à payer"]:
                if col in df_rec.columns:
                    df_rec[col] = pd.to_numeric(df_rec[col].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
            stats[f'{name}_ca'] = df_rec['Reste à payer'].sum()
            stats[f'{name}_dossiers'] = len(df_rec)
        else:
            stats[f'{name}_ca'] = 0
            stats[f'{name}_dossiers'] = 0
            
        # 2. Inventaire
        df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", ["designation"], override_url=url)
        stats[f'{name}_inv'] = len(df_inv) if not df_inv.empty else 0
        
        # 3. Logs (Activité)
        df_logs = load_gs_data("Logs", "data/db_logs.csv", ["timestamp"], override_url=url)
        today = datetime.now().strftime("%Y-%m-%d")
        stats[f'{name}_activity'] = len(df_logs[df_logs['timestamp'].astype(str).str.contains(today)]) if not df_logs.empty else 0

    return stats

with st.spinner("Fusion des données des établissements..."):
    g_stats = load_global_stats()

# --- AFFICHAGE KPIs ---
c1, c2, c3, c4 = st.columns(4)

def master_kpi(col, label, dar_val, pharm_val, unit=""):
    with col:
        st.markdown(f"""
        <div class="kpi-card-master">
            <div class="kpi-title">{label}</div>
            <div class="kpi-value">{(dar_val + pharm_val):,.0f} {unit}</div>
            <div style="display:flex; justify-content:space-between; margin-top:15px; border-top:1px solid #f1f5f9; padding-top:10px;">
                <div>
                    <span style="font-size:0.7rem; color:#94a3b8; font-weight:700;">DARPHARM</span><br>
                    <span style="font-weight:800; color:#1877f2;">{dar_val:,.0f}</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:0.7rem; color:#94a3b8; font-weight:700;">PHARMACIEL</span><br>
                    <span style="font-weight:800; color:#6B46C1;">{pharm_val:,.0f}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

master_kpi(c1, "Encours Global", g_stats.get('DarPharm_ca',0), g_stats.get('Pharmaciel_ca',0), "DA")
master_kpi(c2, "Dossiers Actifs", g_stats.get('DarPharm_dossiers',0), g_stats.get('Pharmaciel_dossiers',0))
master_kpi(c3, "Saisies Inventaire", g_stats.get('DarPharm_inv',0), g_stats.get('Pharmaciel_inv',0))
master_kpi(c4, "Actions du Jour", g_stats.get('DarPharm_activity',0), g_stats.get('Pharmaciel_activity',0))

st.markdown("<br>", unsafe_allow_html=True)

# --- GRAPHIQUES COMPARATIFS ---
st.subheader("📊 Comparaison de Performance")
g_col1, g_col2 = st.columns(2)

with g_col1:
    df_comp = pd.DataFrame({
        "Établissement": ["DarPharm", "Pharmaciel"],
        "Encours": [g_stats.get('DarPharm_ca',0), g_stats.get('Pharmaciel_ca',0)]
    })
    fig_ca = px.pie(df_comp, values='Encours', names='Établissement', 
                   title="Répartition du Chiffre d'Affaires (Encours)",
                   color_discrete_sequence=["#1877f2", "#6B46C1"],
                   hole=0.4)
    st.plotly_chart(fig_ca, use_container_width=True)

with g_col2:
    df_act = pd.DataFrame({
        "Établissement": ["DarPharm", "Pharmaciel"],
        "Actions": [g_stats.get('DarPharm_activity',0), g_stats.get('Pharmaciel_activity',0)]
    })
    fig_act = px.bar(df_act, x='Établissement', y='Actions', 
                    title="Activité Opérationnelle du Jour",
                    color='Établissement',
                    color_discrete_map={"DarPharm": "#1877f2", "Pharmaciel": "#6B46C1"})
    st.plotly_chart(fig_act, use_container_width=True)

st.divider()
st.caption("Données synchronisées en temps réel depuis les deux instances Google Sheets.")
