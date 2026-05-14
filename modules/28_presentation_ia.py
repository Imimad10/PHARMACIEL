import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import time
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="DarPharm Keynote Engine", layout="wide", initial_sidebar_state="collapsed")

# --- CSS: EBLOUISSANTES TRANSITIONS & ANIMATIONS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700&display=swap');
    
    .stApp {
        background: #f8f9fa !important;
        color: #1d1d1f !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Light Bokeh Background */
    .bokeh-bg {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: radial-gradient(circle at 10% 20%, rgba(124, 58, 237, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 90% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 40%);
        z-index: -1;
    }

    /* Slide Transitions */
    .slide-container {
        animation: slideInRight 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
        padding: 40px;
        min-height: 80vh;
    }
    
    @keyframes slideInRight {
        from { transform: translateX(30px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .slide-title {
        font-family: 'Playfair Display', serif;
        font-size: 4rem;
        margin-bottom: 30px;
        color: #1d1d1f;
        font-weight: 800;
    }
    
    /* Executive Light Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(124, 58, 237, 0.1);
        border-radius: 32px;
        padding: 40px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.03);
    }
    
    .metric-hero {
        font-size: 5.5rem;
        font-weight: 800;
        letter-spacing: -3px;
        color: #7c3aed;
        text-shadow: 2px 2px 0px rgba(124, 58, 237, 0.05);
    }
    
    /* Navigation Bar Light */
    .nav-dock {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(15px);
        padding: 10px 30px;
        border-radius: 50px;
        border: 1px solid rgba(124, 58, 237, 0.2);
        display: flex;
        gap: 20px;
        z-index: 1000;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    .stButton button {
        border-radius: 50px !important;
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        color: #1d1d1f !important;
        padding: 10px 25px !important;
        height: 50px !important;
        font-weight: 600 !important;
    }
    .stButton button:hover {
        border-color: #7c3aed !important;
        color: #7c3aed !important;
        transform: translateY(-2px);
    }
    
    /* Table Styling */
    .stTable {
        background: white;
        border-radius: 15px;
        overflow: hidden;
    }
</style>
<div class="bokeh-bg"></div>
""", unsafe_allow_html=True)

# --- INITIALISATION SESSION STATE ---
if "keynote_mode" not in st.session_state:
    st.session_state.keynote_mode = "BUILDER"
if "selected_slides" not in st.session_state:
    st.session_state.selected_slides = []
if "current_slide_idx" not in st.session_state:
    st.session_state.current_slide_idx = 0

# --- MODULES DISPONIBLES ---
MODULE_CONFIG = {
    "📊 Performance Globale": "GLOBAL",
    "🚚 Opérations Logistique": "LOGISTIQUE",
    "📦 Santé Inventaire": "STOCKS",
    "⚠️ Réclamations Fournisseurs": "CLAIMS",
    "⚖️ Litiges & Recouvrement": "FINANCE",
    "👷 Performance Agents": "HR_AGENTS",
    "🚛 Rendement Livreurs": "HR_DRIVERS",
    "🤖 Vision IA Stratégique": "AI_VISION"
}

# --- AUDIO FX (Invisible Trigger) ---
def play_slide_fx():
    st.markdown("""
        <audio autoplay>
            <source src="https://www.soundjay.com/buttons/sounds/button-20.mp3" type="audio/mpeg">
        </audio>
    """, unsafe_allow_html=True)

# --- RENDERER: BUILDER MODE ---
if st.session_state.keynote_mode == "BUILDER":
    st.markdown("<h1 style='text-align:center; font-family:Playfair Display;'>KEYNOTE BUILDER</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#94a3b8;'>Sélectionnez les modules à inclure dans votre présentation stratégique.</p>", unsafe_allow_html=True)
    
    col_c, col_p = st.columns([1, 2])
    
    with col_c:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🛠️ Configuration")
        selected = []
        for label, key in MODULE_CONFIG.items():
            if st.checkbox(label, value=True, key=f"chk_{key}"):
                selected.append(key)
        
        st.divider()
        if st.button("🎬 LANCER LA PRÉSENTATION", use_container_width=True):
            if selected:
                st.session_state.selected_slides = selected
                st.session_state.keynote_mode = "PRESENTATION"
                st.session_state.current_slide_idx = 0
                st.rerun()
            else:
                st.error("Sélectionnez au moins un module.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_p:
        st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop", caption="DarPharm Executive Suite 2026")

# --- RENDERER: PRESENTATION MODE ---
elif st.session_state.keynote_mode == "PRESENTATION":
    slides = st.session_state.selected_slides
    current_key = slides[st.session_state.current_slide_idx]
    
    # --- SLIDE CONTENT ---
    st.markdown('<div class="slide-container">', unsafe_allow_html=True)
    
    if current_key == "GLOBAL":
        st.markdown('<h1 class="slide-title">Performance<br>Générale</h1>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.markdown('<div class="glass-card"><p>Taux de Service</p><div class="metric-hero">98.4%</div></div>', unsafe_allow_html=True)
        c2.markdown('<div class="glass-card"><p>Rotation Moyenne</p><div class="metric-hero" style="color:#a855f7;">12j</div></div>', unsafe_allow_html=True)
        c3.markdown('<div class="glass-card"><p>Satisfaction Clients</p><div class="metric-hero" style="color:#38a169;">4.8/5</div></div>', unsafe_allow_html=True)

    elif current_key == "LOGISTIQUE":
        st.markdown('<h1 class="slide-title">Efficacité<br>Logistique</h1>', unsafe_allow_html=True)
        col_c, col_m = st.columns([2, 1])
        with col_c:
            df = pd.DataFrame({"J": ["L","M","M","J","V","S"], "V": [120,150,140,180,160,110]})
            fig = px.line(df, x="J", y="V", template="plotly_dark", color_discrete_sequence=["#5b6cf9"])
            fig.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        with col_m:
            st.markdown('<div class="glass-card" style="height:100%;"><h3>Analyse Flux</h3><p>Optimisation des tournées réussie.</p><div class="metric-hero" style="font-size:3rem;">+15%</div></div>', unsafe_allow_html=True)

    elif current_key == "STOCKS":
        st.markdown('<h1 class="slide-title">Santé de<br>l\'Inventaire</h1>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(data=[go.Pie(labels=['Sain', 'Critique', 'Périmé'], values=[85, 12, 3], hole=.7)])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="glass-card"><h3>Valorisation</h3><p>Total Actif</p><div class="metric-hero">124M</div><p>DZ</p></div>', unsafe_allow_html=True)

    elif current_key == "CLAIMS":
        st.markdown('<h1 class="slide-title">Réclamations<br>Fournisseurs</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Suivi des Réclamations")
        df_claims = pd.DataFrame({"Fournisseur": ["BIOPHARM", "SAIDAL", "FRATER"], "Réclamations": [4, 1, 2], "Gravité": ["Haute", "Basse", "Moyenne"]})
        st.table(df_claims)
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_key == "FINANCE":
        st.markdown('<h1 class="slide-title">Litiges &<br>Recouvrement</h1>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.markdown('<div class="glass-card"><p>Recouvré</p><div class="metric-hero" style="color:#38a169;">84.2M</div></div>', unsafe_allow_html=True)
        c2.markdown('<div class="glass-card"><p>En Attente</p><div class="metric-hero" style="color:#ed8936;">12.8M</div></div>', unsafe_allow_html=True)

    elif current_key == "HR_AGENTS":
        st.markdown('<h1 class="slide-title">Performance<br>Agents</h1>', unsafe_allow_html=True)
        cols = st.columns(3)
        agents = [("Yassine", "450 lignes", "99%"), ("Amine", "420 lignes", "98%"), ("Sara", "380 lignes", "100%")]
        for i, (name, perf, acc) in enumerate(agents):
            cols[i].markdown(f'<div class="glass-card" style="text-align:center;"><h3>{name}</h3><div class="metric-hero" style="font-size:2rem;">{perf}</div><p>Précision: {acc}</p></div>', unsafe_allow_html=True)

    elif current_key == "HR_DRIVERS":
        st.markdown('<h1 class="slide-title">Rendement<br>Livreurs</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Top Livreurs (Livraisons/Jour)")
        df_drivers = pd.DataFrame({"Livreur": ["Ahmed", "Karim", "Zaki"], "Livraisons": [24, 21, 19], "Respect Délais": ["95%", "92%", "98%"]})
        st.table(df_drivers)
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_key == "AI_VISION":
        st.markdown('<h1 class="slide-title">Vision IA<br>Stratégique</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        if is_ia_enabled():
            with st.spinner("Analyse stratégique en cours..."):
                report = ask_ai("Analyse tous ces modules et donne une conclusion stratégique pour 2026.")
                st.write(report)
        else:
            st.info("Activez l'IA pour générer la vision stratégique.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # --- DOCK NAVIGATION ---
    st.markdown('<div class="nav-dock">', unsafe_allow_html=True)
    c_p, c_h, c_n = st.columns([1,1,1])
    
    if c_p.button("⬅️", key="k_prev"):
        if st.session_state.current_slide_idx > 0:
            st.session_state.current_slide_idx -= 1
            play_slide_fx()
            st.rerun()
            
    if c_h.button("🏠", key="k_home"):
        st.session_state.keynote_mode = "BUILDER"
        st.rerun()
        
    if c_n.button("➡️", key="k_next"):
        if st.session_state.current_slide_idx < len(slides) - 1:
            st.session_state.current_slide_idx += 1
            play_slide_fx()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
