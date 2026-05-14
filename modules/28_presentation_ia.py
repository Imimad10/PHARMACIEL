import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="DarPharm Executive Briefing", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE EXECUTIVE MINIMALIST ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background-color: #f5f5f7 !important;
        color: #1d1d1f !important;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Elegant Pill Navigation */
    .nav-pill {
        display: flex;
        justify-content: center;
        background: rgba(255, 255, 255, 0.8);
        padding: 8px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        backdrop-filter: blur(20px);
        margin-bottom: 40px;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    /* Executive Cards */
    .executive-card {
        background: #ffffff;
        border-radius: 24px;
        padding: 40px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.02);
        transition: transform 0.3s ease;
    }
    .executive-card:hover {
        transform: translateY(-2px);
    }
    
    .metric-title {
        color: #86868b;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    
    .metric-value {
        font-size: 4rem;
        font-weight: 700;
        color: #1d1d1f;
        letter-spacing: -2px;
    }
    
    .ai-briefing {
        background: #fbfbfd;
        border-radius: 20px;
        padding: 30px;
        border-left: 4px solid #5b6cf9;
        margin-top: 30px;
        font-style: italic;
        color: #424245;
        line-height: 1.6;
        font-size: 1.1rem;
    }
    
    h1 {
        font-weight: 700 !important;
        font-size: 2.8rem !important;
        text-align: center;
        margin-bottom: 10px !important;
        color: #1d1d1f !important;
    }
    
    .stButton button {
        background-color: #ffffff !important;
        color: #1d1d1f !important;
        border-radius: 12px !important;
        border: 1px solid #d2d2d7 !important;
        font-weight: 500 !important;
        padding: 10px 20px !important;
    }
    .stButton button:hover {
        background-color: #f5f5f7 !important;
        border-color: #86868b !important;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
if "active_slide" not in st.session_state:
    st.session_state.active_slide = "Synthèse"

st.markdown("<h1>Rapport Stratégique</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:#86868b; font-size:1.1rem; margin-bottom:40px;'>{datetime.now().strftime('%d %B %Y')} | Vue Direction Générale</p>", unsafe_allow_html=True)

slides = ["Synthèse", "Logistique", "Inventaire", "Recouvrement", "Perspectives IA"]
cols_nav = st.columns(len(slides))

for i, s in enumerate(slides):
    if cols_nav[i].button(s, use_container_width=True, key=f"nav_{s}"):
        st.session_state.active_slide = s
        st.rerun()

current = st.session_state.active_slide

# --- CONTENT ---
st.markdown("<br>", unsafe_allow_html=True)

if current == "Synthèse":
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="executive-card"><div class="metric-title">Taux de Service</div><div class="metric-value">98.4%</div><div style="color:#10b981; font-weight:600;">+1.2% vs mois dernier</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="executive-card"><div class="metric-title">Rotation Stocks</div><div class="metric-value">12.5j</div><div style="color:#10b981; font-weight:600;">Optimisation stable</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="executive-card"><div class="metric-title">Fiabilité Inventaire</div><div class="metric-value">99.1%</div><div style="color:#5b6cf9; font-weight:600;">Record annuel</div></div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="ai-briefing">
            <strong>Résumé Stratégique IA :</strong> "La performance opérationnelle atteint un plateau d'excellence. L'accent doit maintenant être mis sur la réduction des coûts de stockage dormants identifiés en Zone C pour maximiser le flux de trésorerie."
        </div>
    """, unsafe_allow_html=True)

elif current == "Logistique":
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.subheader("Performance des Flux")
    df_perf = pd.DataFrame({
        "Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], 
        "Réalisé": [120, 150, 140, 180, 160, 110], 
        "Objectif": [130, 130, 130, 130, 130, 130]
    })
    fig = px.line(df_perf, x="Jour", y=["Réalisé", "Objectif"], 
                 color_discrete_map={"Réalisé": "#5b6cf9", "Objectif": "#e5e5e7"},
                 template="plotly_white")
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
        height=500, font_family="Inter", margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "Inventaire":
    col_pie, col_text = st.columns([1.5, 1])
    with col_pie:
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        st.subheader("État Global des Stocks")
        fig_pie = go.Figure(data=[go.Pie(labels=['Sain', 'Critique', 'Périmé'], 
                                        values=[85, 12, 3], hole=.7,
                                        marker_colors=["#5b6cf9", "#ff9f0a", "#ff3b30"])])
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=450, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_text:
        st.markdown('<div class="executive-card" style="height:100%;"><h3>Analyse Audit</h3><p>La mise en place du triple comptage a réduit les écarts de valeur de 34% ce trimestre.</p><div style="font-size:3rem; font-weight:700; color:#5b6cf9;">-34%</div><p>d\'écarts financiers.</p></div>', unsafe_allow_html=True)

elif current == "Recouvrement":
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.subheader("Situation Financière")
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        st.markdown('<div style="text-align:center;"><p class="metric-title">Montant Encaissé</p><div class="metric-value" style="color:#34c759;">84.2M</div><p>DZ</p></div>', unsafe_allow_html=True)
    with c_f2:
        st.markdown('<div style="text-align:center;"><p class="metric-title">Reste à Recouvrer</p><div class="metric-value" style="color:#ff9f0a;">12.8M</div><p>DZ</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "Perspectives IA":
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.subheader("Orientations IA & Automatisation")
    st.write("Nos modèles prédictifs suggèrent trois axes majeurs pour le semestre à venir :")
    st.markdown("""
    *   **Réapprovisionnement Intelligent** : Réduction de 15% des ruptures de stock.
    *   **Optimisation des Tournées** : Économie de 8% sur les frais logistiques.
    *   **Détection Précoce des Litiges** : Archivage automatisé et gain de temps RH.
    """)
    st.markdown("""
        <div class="ai-briefing">
            <strong>Conseil IA :</strong> "L'intégration des données fournisseurs en temps réel permettrait d'anticiper les retards de livraison de 48h supplémentaires."
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br><p style='text-align:center; color:#86868b; font-size:0.8rem;'>DarPharm Solutions | Excellence Opérationnelle 2026</p>", unsafe_allow_html=True)

# --- NAVIGATION ---
if "active_slide" not in st.session_state:
    st.session_state.active_slide = "Vue d'ensemble"

st.markdown("<h1>Strategic Vision</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:#64748b; margin-bottom:40px;'>{datetime.now().strftime('%d %B %Y')} | EXECUTIVE BRIEFING</p>", unsafe_allow_html=True)

slides = ["Vue d'ensemble", "Logistique", "Stocks", "Finances", "Vision IA"]
cols_nav = st.columns(len(slides))

for i, s in enumerate(slides):
    if cols_nav[i].button(s, use_container_width=True, key=f"nav_{s}"):
        st.session_state.active_slide = s
        st.rerun()

current = st.session_state.active_slide

# --- CONTENT ---
st.markdown("<br>", unsafe_allow_html=True)

if current == "Vue d'ensemble":
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="glass-card"><div style="color:#94a3b8; font-size:0.9rem; letter-spacing:2px;">SERVICE RATE</div><div class="hero-metric">98.4%</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glass-card"><div style="color:#94a3b8; font-size:0.9rem; letter-spacing:2px;">ROTATION</div><div class="hero-metric">12.5j</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="glass-card"><div style="color:#94a3b8; font-size:0.9rem; letter-spacing:2px;">PRECISION</div><div class="hero-metric">99.1%</div></div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="ai-terminal">
            > IA SYSTEM READY...<br>
            > ANALYZING GLOBAL KPI...<br>
            > STATUS: EXCELLENT. TRENDS SHOW 5% INCREASE IN OPERATIONAL EFFICIENCY.
        </div>
    """, unsafe_allow_html=True)

elif current == "Logistique":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    df_perf = pd.DataFrame({
        "Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], 
        "Volume": [120, 150, 140, 180, 160, 110], 
        "Objectif": [130, 130, 130, 130, 130, 130]
    })
    fig = px.area(df_perf, x="Jour", y="Volume", template="plotly_dark", 
                 color_discrete_sequence=["#60a5fa"])
    fig.add_hline(y=130, line_dash="dot", line_color="#ef4444", annotation_text="Target")
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "Stocks":
    col_pie, col_text = st.columns([2, 1])
    with col_pie:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        fig_pie = go.Figure(data=[go.Pie(labels=['Conforme', 'Investigation', 'Périmé'], 
                                        values=[4500, 120, 15], hole=.6)])
        fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=500)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_text:
        st.markdown('<div class="glass-card" style="height:100%;"><h3>Audit Stock</h3><p>Optimisation des zones de stockage terminée.</p><h1 style="color:#10b981;">+12%</h1><p>de gain de place.</p></div>', unsafe_allow_html=True)

elif current == "Finances":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    c_f1, c_f2 = st.columns(2)
    c_f1.markdown('<div style="text-align:center;"><p style="letter-spacing:2px; color:#94a3b8;">RECOUVRÉ</p><div class="hero-metric" style="color:#10b981;">84.2M</div></div>', unsafe_allow_html=True)
    c_f2.markdown('<div style="text-align:center;"><p style="letter-spacing:2px; color:#94a3b8;">EN ATTENTE</p><div class="hero-metric" style="color:#f59e0b;">12.8M</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif current == "Vision IA":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.write("### Stratégie Prédictive 2026")
    st.info("L'IA suggère une transition vers l'automatisation complète du module de réception pour réduire les erreurs de saisie de 20%.")
    st.markdown("""
        <div class="ai-terminal">
            > RUNNING PREDICTIVE MODEL v4.0...<br>
            > FORECAST: STABLE GROWTH FOR Q3.<br>
            > RECOMMENDATION: EXPAND COLD STORAGE CAPACITY.
        </div>
    """, unsafe_allow_html=True)


st.markdown("<br><p style='text-align:center; color:#475569; font-size:0.8rem;'>F11 for Fullscreen | DarPharm Executive Hub v3.0</p>", unsafe_allow_html=True)
