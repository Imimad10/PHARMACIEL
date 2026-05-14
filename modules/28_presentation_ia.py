import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="DarPharm Executive Presentation", layout="wide", initial_sidebar_state="collapsed")

# --- STYLE HOLOGRAPHIQUE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Outfit:wght@300;400;600&display=swap');
    
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a) !important;
        color: #f8fafc !important;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Holographic Navigation */
    .nav-container {
        display: flex;
        justify(content: center;
        gap: 15px;
        margin-bottom: 40px;
        flex-wrap: wrap;
    }
    
    .nav-btn {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 12px 25px;
        border-radius: 12px;
        color: #94a3b8;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-weight: 600;
        backdrop-filter: blur(10px);
    }
    
    .nav-btn.active {
        background: rgba(96, 165, 250, 0.15);
        border-color: #60a5fa;
        color: #60a5fa;
        box-shadow: 0 0 20px rgba(96, 165, 250, 0.3);
        transform: scale(1.05);
    }
    
    /* Presentation Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 35px;
        backdrop-filter: blur(15px);
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        animation: zoomIn 0.8s ease-out;
    }
    
    @keyframes zoomIn {
        from { transform: scale(0.95); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }
    
    .hero-metric {
        font-family: 'Orbitron', sans-serif;
        font-size: 4.5rem;
        font-weight: 900;
        background: linear-gradient(to bottom, #60a5fa, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 10px 30px rgba(59, 130, 246, 0.2);
    }
    
    .ai-terminal {
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid #60a5fa44;
        border-radius: 15px;
        padding: 20px;
        font-family: 'Courier New', Courier, monospace;
        color: #60a5fa;
        border-left: 5px solid #60a5fa;
        margin-top: 30px;
        animation: pulse-border 2s infinite;
    }
    
    @keyframes pulse-border {
        0% { border-color: #60a5fa44; }
        50% { border-color: #60a5fa88; }
        100% { border-color: #60a5fa44; }
    }
    
    h1 {
        font-family: 'Orbitron', sans-serif;
        text-align: center;
        letter-spacing: 5px;
        text-transform: uppercase;
        margin-bottom: 5px !important;
    }
</style>
""", unsafe_allow_html=True)

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
