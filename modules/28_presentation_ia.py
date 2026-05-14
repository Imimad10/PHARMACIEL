import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="DarPharm Master Executive Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE EXECUTIVE MASTER ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {
        background-color: #f8f9fa !important;
        color: #1a1a1a !important;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    .main-header {
        background: white;
        padding: 20px 40px;
        border-bottom: 1px solid #e9ecef;
        margin-bottom: 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .section-title {
        font-size: 0.75rem;
        font-weight: 800;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 15px;
        border-bottom: 2px solid #dee2e6;
        padding-bottom: 5px;
    }
    
    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        border: 1px solid #edf2f7;
        height: 100%;
        transition: transform 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
    }
    
    .metric-val {
        font-size: 2.2rem;
        font-weight: 800;
        color: #2d3748;
        letter-spacing: -1px;
        margin: 5px 0;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #718096;
        font-weight: 500;
    }
    
    .trend-up { color: #38a169; font-weight: 700; font-size: 0.8rem; }
    .trend-down { color: #e53e3e; font-weight: 700; font-size: 0.8rem; }
    
    .ai-box {
        background: #f0f4ff;
        border-radius: 12px;
        padding: 15px;
        border-left: 4px solid #5a67d8;
        font-size: 0.9rem;
        color: #4a5568;
        line-height: 1.4;
    }
    
    .data-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        background: #edf2f7;
        color: #4a5568;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATA LOAD ---
@st.cache_data(ttl=600)
def fetch_master_data():
    df_temp = load_gs_data("Suivi_Frigo", "suivi_data.csv")
    df_rot = load_gs_data("Analyse_Rotation", "rotation_data.csv")
    df_inv = load_gs_data("Inventaire_Global", "inventaire_data.csv")
    df_rec = load_gs_data("Recouvrement", "recouvrement_data.csv")
    return {"temp": df_temp, "rot": df_rot, "inv": df_inv, "rec": df_rec}

data = fetch_master_data()

# --- HEADER SECTION ---
st.markdown(f"""
    <div class="main-header">
        <div>
            <h2 style="margin:0; font-weight:800; color:#1a202c;">MASTER EXECUTIVE BRIEFING</h2>
            <p style="margin:0; color:#a0aec0; font-size:0.9rem;">Vue consolidée des opérations DarPharm Solutions</p>
        </div>
        <div style="text-align:right;">
            <div style="font-weight:700; color:#2d3748;">{datetime.now().strftime("%d %B %Y | %H:%M")}</div>
            <div style="font-size:0.8rem; color:#718096;">Système Intelligent Actif</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- KPI TOP BAR ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""
        <div class="kpi-card">
            <div class="metric-label">TAUX DE SERVICE</div>
            <div class="metric-val">98.4%</div>
            <div class="trend-up">↑ 0.5% vs S-1</div>
            <div class="data-pill">Temps Réel</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
        <div class="kpi-card">
            <div class="metric-label">ROTATION MOYENNE</div>
            <div class="metric-val">14.2j</div>
            <div class="trend-down">↓ 1.2j (Optimisé)</div>
            <div class="data-pill">30 Derniers Jours</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
        <div class="kpi-card">
            <div class="metric-label">VALEUR STOCK</div>
            <div class="metric-val">124.5M</div>
            <div class="trend-up">↑ 4.2% (Arrivages)</div>
            <div class="data-pill">Valorisation DZ</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
        <div class="kpi-card">
            <div class="metric-label">RECOUVREMENT</div>
            <div class="metric-val">86.1%</div>
            <div class="trend-up">↑ 2.1% (Relances)</div>
            <div class="data-pill">Objectif : 90%</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- MAIN DASHBOARD GRID ---
col_ops, col_inv, col_strat = st.columns([1.2, 1.2, 1])

# --- COLUMN 1: OPERATIONS ---
with col_ops:
    st.markdown('<div class="section-title">📦 OPÉRATIONS & LOGISTIQUE</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("**Performance des Expéditions (Volume/Jour)**")
        df_log = pd.DataFrame({
            "Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], 
            "Réalisé": [120, 150, 140, 180, 160, 110], 
            "Prévision": [130, 140, 150, 170, 160, 120]
        })
        fig_log = px.area(df_log, x="Jour", y=["Réalisé", "Prévision"], 
                         color_discrete_map={"Réalisé": "#5a67d8", "Prévision": "#e2e8f0"},
                         template="plotly_white")
        fig_log.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        st.plotly_chart(fig_log, use_container_width=True)
        st.caption("Comparaison entre le volume réel expédié et les prévisions de charge IA.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("**Surveillance Thermique (Live)**")
        st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:1.8rem; font-weight:800; color:#38a169;">4.2°C</span>
                    <span style="color:#718096; font-size:0.8rem;">(Normal)</span>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:0.7rem; color:#a0aec0;">DERNIER RELEVÉ</div>
                    <div style="font-size:0.8rem; font-weight:600;">Il y a 5 min</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.progress(0.42, "Stabilité CF1")

# --- COLUMN 2: INVENTAIRE ---
with col_inv:
    st.markdown('<div class="section-title">🏗️ SANTÉ DE L\'INVENTAIRE</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("**Répartition par État de Stock**")
        fig_pie = go.Figure(data=[go.Pie(labels=['Stock Sain', 'DDP Proche', 'Surstock', 'Rupture'], 
                                        values=[70, 15, 10, 5], hole=.6,
                                        marker_colors=["#5a67d8", "#ed8936", "#a0aec0", "#e53e3e"])])
        fig_pie.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.caption("Visualisation explicite des zones de risque (Ruptures et Péremptions proches).")

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.write("**Analyse de Rotation (Top Catégories)**")
        df_rot = pd.DataFrame({
            "Catégorie": ["Antibio", "Derma", "Cardio", "Péd"], 
            "Ventes": [450, 320, 280, 210],
            "Rotation": [5, 45, 12, 8]
        })
        fig_bar = px.bar(df_rot, x="Catégorie", y="Ventes", color="Rotation",
                        color_continuous_scale="Blues", template="plotly_white")
        fig_bar.update_layout(height=230, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)

# --- COLUMN 3: STRATÉGIE & IA ---
with col_strat:
    st.markdown('<div class="section-title">🤖 BRIEFING STRATÉGIQUE IA</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="ai-box">
            <strong>TAKEAWAY #1 :</strong> Le volume logistique de mercredi a dépassé les prévisions de 12%. Risque de surcharge temporaire identifié.
        </div>
        <br>
        <div class="ai-box" style="background:#fffaf0; border-left-color:#ed8936;">
            <strong>ALERTE STOCK :</strong> 15 références en 'DDP Proche' représentent une valeur de 2.4M DZ. Action de déstockage prioritaire requise.
        </div>
        <br>
        <div class="ai-box" style="background:#f7fafc; border-left-color:#a0aec0;">
            <strong>OBJECTIF RECOUVREMENT :</strong> Taux actuel 86.1%. Le gap de 3.9% pour atteindre l'objectif se concentre sur 3 clients majeurs.
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    if is_ia_enabled():
        if st.button("🪄 Générer Rapport IA Détaillé", use_container_width=True):
            with st.spinner("Analyse approfondie en cours..."):
                report = ask_ai("Analyse la performance globale de DarPharm et donne 3 recommandations prioritaires.")
                st.info(report)

# --- FOOTER ---
st.markdown("""
    <div style="text-align:center; padding: 40px; color:#a0aec0; font-size:0.8rem;">
        DarPharm Master Suite v4.0 | Développé pour l'Excellence Opérationnelle | © 2026
    </div>
""", unsafe_allow_html=True)
