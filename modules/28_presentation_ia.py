import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data
from utils_themes import apply_theme_css, load_themes_db, get_active_themes

# --- CONFIGURATION DES THÈMES ---
THEMES_CONFIG = {
    "Dark Pro": {
        "bg": "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        "card": "rgba(255, 255, 255, 0.05)",
        "accent": "#60a5fa",
        "text": "#f8fafc",
        "secondary": "#94a3b8"
    },
    "USMH (Yellow)": {
        "bg": "linear-gradient(135deg, #000000 0%, #1a1a1a 100%)",
        "card": "rgba(250, 204, 21, 0.08)",
        "accent": "#facc15",
        "text": "#ffffff",
        "secondary": "#a1a1aa"
    },
    "CRB (Red)": {
        "bg": "linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%)",
        "card": "rgba(255, 255, 255, 0.05)",
        "accent": "#ef4444",
        "text": "#ffffff",
        "secondary": "#fca5a5"
    },
    "MCA (Green)": {
        "bg": "linear-gradient(135deg, #064e3b 0%, #065f46 100%)",
        "card": "rgba(220, 38, 38, 0.1)",
        "accent": "#16a34a",
        "text": "#ffffff",
        "secondary": "#bbf7d0"
    }
}

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DarPharm Présentation - Mode Meeting", layout="wide", page_icon="📽️")

# --- SIDEBAR DE CONTRÔLE ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3061/3061457.png", width=100)
    st.title("⚙️ Paramètres")
    
    selected_theme = st.selectbox("🎨 Thème Visuel", list(THEMES_CONFIG.keys()), index=0)
    t = THEMES_CONFIG[selected_theme]
    
    selected_model = st.radio("📊 Modèle de Présentation", ["Slide Narratif", "Centre de Commandement", "Analyse Comparative"])
    
    st.divider()
    st.info("💡 Utilisez le 'Centre de Commandement' pour une vue globale rapide.")

# Injection CSS Dynamique selon le thème
st.markdown(f"""
    <style>
        .stApp {{
            background: {t['bg']} !important;
            color: {t['text']} !important;
        }}
        .main .block-container {{
            padding: 2rem 5rem !important;
        }}
        h1 {{
            font-size: 4rem !important;
            font-weight: 900 !important;
            text-align: center;
            background: linear-gradient(to right, {t['accent']}, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem !important;
        }}
        h2 {{
            font-size: 2.5rem !important;
            color: {t['secondary']} !important;
            border-bottom: 2px solid rgba(148, 163, 184, 0.2);
            padding-bottom: 1rem;
            margin-top: 3rem !important;
        }}
        .presentation-card {{
            background: {t['card']};
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 2.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }}
        .presentation-card:hover {{
            border-color: {t['accent']};
            transform: translateY(-5px);
        }}
        .ai-insight {{
            font-size: 1.5rem !important;
            line-height: 1.6;
            color: #e2e8f0;
            font-style: italic;
            border-left: 6px solid #a855f7;
            padding-left: 2rem;
            margin: 2rem 0;
            background: rgba(168, 85, 247, 0.05);
            padding: 2rem;
            border-radius: 0 20px 20px 0;
        }}
        .metric-big {{
            font-size: 5rem !important;
            font-weight: 800;
            color: {t['accent']};
            text-shadow: 0 0 20px rgba(96, 165, 250, 0.3);
        }}
        .metric-label {{
            font-size: 1.5rem;
            color: {t['secondary']};
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        .stButton button {{
            width: 100% !important;
            height: 60px !important;
            font-size: 1.2rem !important;
            border-radius: 15px !important;
            background: linear-gradient(135deg, {t['accent']} 0%, #2563eb 100%) !important;
            border: none !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2) !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=300)
def get_meeting_data():
    # Simulation/Chargement des données réelles
    data_summary = {
        "logistique": load_gs_data("Suivi_Frigo", "data_expedition/suivi.csv"),
        "inventaire": load_gs_data("Inventaire_Global", "data_inventaire/global.csv"),
        "rotation": load_gs_data("Analyse_Rotation", "data/rotation.csv")
    }
    return data_summary

def get_ai_presentation_summary(context):
    if not is_ia_enabled():
        return "L'IA est désactivée. Activez-la pour obtenir des analyses stratégiques."
    
    prompt = f"""
    En tant qu'analyste stratégique senior pour DarPharm Solutions, prépare un résumé de 3 phrases marquantes pour une réunion avec la direction.
    Le ton doit être professionnel, confiant et axé sur les résultats.
    Contexte des données : {context}
    Utilise des termes comme 'optimisation', 'croissance', 'efficacité opérationnelle'.
    Réponds en français.
    """
    return ask_ai(prompt)

# --- INITIALISATION ---
if "current_slide" not in st.session_state:
    st.session_state.current_slide = 0

data = get_meeting_data()

# --- HEADER DE PRÉSENTATION ---
st.markdown(f"<h1>PRÉSENTATION STRATÉGIQUE</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; font-size:1.5rem; color:#64748b;'>{datetime.now().strftime('%d %B %Y')} | DarPharm Solutions - Executive View</p>", unsafe_allow_html=True)

# --- ROUTAGE DES MODÈLES ---
if selected_model == "Slide Narratif":
    # --- NAVIGATION SLIDES ---
    cols_nav = st.columns([1, 1, 1, 1, 1, 1])
    slides = ["Vue d'ensemble", "Performance Logistique", "État des Stocks", "Analyse Rotation", "Recouvrement", "Vision IA"]

    for i, s_title in enumerate(slides):
        if cols_nav[i].button(s_title, key=f"btn_slide_{i}"):
            st.session_state.current_slide = i
            st.rerun()

    st.divider()

    # --- CONTENU DES SLIDES ---
    current = st.session_state.current_slide

    if current == 0: # VUE D'ENSEMBLE
        st.markdown("<h2>Synthèse Executive</h2>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="presentation-card"><p class="metric-label">Taux de Service</p><p class="metric-big">98.4%</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="presentation-card"><p class="metric-label">Rotation Moyenne</p><p class="metric-big">12.5j</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="presentation-card"><p class="metric-label">Précision Inventaire</p><p class="metric-big">99.1%</p></div>', unsafe_allow_html=True)

        if st.checkbox("Générer l'analyse stratégique IA", value=True):
            with st.spinner("L'IA prépare votre briefing..."):
                context = "Performance globale stable avec une légère hausse du volume logistique (+5%) et une précision d'inventaire record."
                insight = get_ai_presentation_summary(context)
                st.markdown(f'<div class="ai-insight">“ {insight} ”</div>', unsafe_allow_html=True)

    elif current == 1: # LOGISTIQUE
        st.markdown("<h2>Performance Opérationnelle & Logistique</h2>", unsafe_allow_html=True)
        df_perf = pd.DataFrame({"Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], "Livraisons": [120, 150, 140, 180, 160, 110], "Objectif": [130, 130, 130, 130, 130, 130]})
        fig = px.line(df_perf, x="Jour", y=["Livraisons", "Objectif"], template="plotly_dark", color_discrete_map={"Livraisons": t['accent'], "Objectif": "#ef4444"})
        fig.update_layout(height=500, font=dict(size=18), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    elif current == 2: # STOCKS
        st.markdown("<h2>État des Stocks & Précision</h2>", unsafe_allow_html=True)
        col_chart, col_txt = st.columns([2, 1])
        with col_chart:
            fig_pie = go.Figure(data=[go.Pie(labels=['Conforme', 'Écart Mineur', 'Investigation'], values=[4500, 120, 15], hole=.6)])
            fig_pie.update_layout(template="plotly_dark", height=600, font=dict(size=20), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_txt:
            st.markdown('<div class="presentation-card" style="height:100%;"><h3>Focus Inventaire</h3><p>Réduction des pertes de 22%.</p><h2 style="color:#10b981;">+12%</h2></div>', unsafe_allow_html=True)

    elif current == 3: # ROTATION
        st.markdown("<h2>Analyse de la Rotation</h2>", unsafe_allow_html=True)
        df_rot = pd.DataFrame({"Catégorie": ["Antibiotiques", "Cardio", "Derma", "Pédiatrie", "Urgences"], "Rotation (Jours)": [5, 12, 45, 8, 2], "Valeur (MDZD)": [12, 8, 4, 15, 6]})
        fig_bar = px.bar(df_rot, x="Catégorie", y="Rotation (Jours)", color="Valeur (MDZD)", template="plotly_dark", height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

    elif current == 4: # RECOUVREMENT
        st.markdown("<h2>Santé Financière</h2>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="presentation-card"><p class="metric-label">Recouvré</p><p class="metric-big" style="color:#10b981;">84.2M</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="presentation-card"><p class="metric-label">Attente</p><p class="metric-big" style="color:#f59e0b;">12.8M</p></div>', unsafe_allow_html=True)

    elif current == 5: # VISION IA
        st.markdown("<h2>Vision Stratégique IA</h2>", unsafe_allow_html=True)
        st.markdown(f'<div class="ai-insight">Recommandation : "Automatisation du module de pointage pour libérer 15% de temps."</div>', unsafe_allow_html=True)

elif selected_model == "Centre de Commandement":
    st.markdown("<h2>📊 Centre de Commandement Stratégique</h2>", unsafe_allow_html=True)
    st.info("Vue globale consolidée de tous les indicateurs de performance.")
    
    # KPIs en haut
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="presentation-card" style="padding:1.5rem;"><p style="font-size:0.9rem;opacity:0.8;">SERVICE</p><h3 style="color:{t["accent"]};margin:0;">98.4%</h3></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="presentation-card" style="padding:1.5rem;"><p style="font-size:0.9rem;opacity:0.8;">ROTATION</p><h3 style="color:{t["accent"]};margin:0;">12.5j</h3></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="presentation-card" style="padding:1.5rem;"><p style="font-size:0.9rem;opacity:0.8;">PRÉCISION</p><h3 style="color:{t["accent"]};margin:0;">99.1%</h3></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="presentation-card" style="padding:1.5rem;"><p style="font-size:0.9rem;opacity:0.8;">RECOUVREMENT</p><h3 style="color:#10b981;margin:0;">86%</h3></div>', unsafe_allow_html=True)

    col_main1, col_main2 = st.columns([2, 1])
    with col_main1:
        st.markdown('<div class="presentation-card" style="height:550px;">', unsafe_allow_html=True)
        st.write("📈 **Volume Logistique & Objectifs**")
        df_perf = pd.DataFrame({"Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], "Livraisons": [120, 150, 140, 180, 160, 110], "Objectif": [130, 130, 130, 130, 130, 130]})
        fig = px.area(df_perf, x="Jour", y="Livraisons", template="plotly_dark", color_discrete_sequence=[t['accent']])
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_main2:
        st.markdown('<div class="presentation-card" style="height:550px;">', unsafe_allow_html=True)
        st.write("🎯 **Répartition Stocks**")
        fig_pie = go.Figure(data=[go.Pie(labels=['Bon', 'DDP Proche', 'Périmé'], values=[85, 12, 3], hole=.5)])
        fig_pie.update_layout(template="plotly_dark", height=300, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)
        st.divider()
        st.write("🤖 **Dernier Insight IA :**")
        st.caption("Optimisation des stocks critiques suggérée en Zone B.")
        st.markdown('</div>', unsafe_allow_html=True)

elif selected_model == "Analyse Comparative":
    st.markdown("<h2>🔄 Analyse Comparative & Tendances</h2>", unsafe_allow_html=True)
    
    col_sel1, col_sel2 = st.columns(2)
    p1 = col_sel1.selectbox("Période A", ["Mai 2026", "Avril 2026", "Mars 2026"])
    p2 = col_sel2.selectbox("Période B", ["Avril 2026", "Mai 2026", "Mars 2026"], index=1)
    
    comp_col1, comp_col2 = st.columns(2)
    
    with comp_col1:
        st.markdown(f'<div class="presentation-card"><h3>{p1}</h3><p class="metric-label">Volume</p><h2 style="color:{t["accent"]};">4,250</h2><p>Taux de service : 97.2%</p></div>', unsafe_allow_html=True)
    with comp_col2:
        st.markdown(f'<div class="presentation-card"><h3>{p2}</h3><p class="metric-label">Volume</p><h2 style="color:{t["accent"]};">4,480</h2><p>Taux de service : 98.4%</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="ai-insight">Analyse Différentielle : "On observe une amélioration de 1.2% du taux de service entre les deux périodes, principalement due à la nouvelle gestion des tournées."</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("<div style='text-align:center; padding: 20px; color:#475569;'>Appuyez sur F11 pour passer en plein écran | DarPharm Solution Meeting Mode v2.0</div>", unsafe_allow_html=True)
