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

# --- CSS: EBLOUISSANTES TRANSITIONS & ANIMATIONS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Sora:wght@400;700&display=swap');
    
    :root {
        --accent: #7c3aed;
        --accent-glow: rgba(124, 58, 237, 0.4);
        --bg: #0f172a;
    }

    .stApp {
        background: var(--bg) !important;
        color: #f8fafc !important;
        font-family: 'Outfit', sans-serif;
    }

    /* Animated Mesh Background */
    .mesh-bg {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: 
            radial-gradient(at 0% 0%, rgba(124, 58, 237, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.1) 0px, transparent 50%),
            radial-gradient(at 0% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
        filter: blur(80px);
        z-index: -1;
        animation: meshFlow 20s infinite alternate linear;
    }

    @keyframes meshFlow {
        0% { transform: scale(1); }
        100% { transform: scale(1.2); }
    }

    /* Hide Streamlit Noise */
    header, footer, [data-testid="stSidebarNav"] { visibility: hidden !important; height: 0 !important; }
    div[data-testid="stDecoration"] { background: none !important; }

    /* Fix for squeezed checkbox labels & readability */
    div[data-testid="stCheckbox"] label p {
        color: #f1f5f9 !important;
        font-size: 1.2rem !important;
        font-weight: 500 !important;
    }
    
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #f8fafc !important;
    }

    /* Slide Container */
    .slide-container {
        animation: slideReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1);
        padding: 6vh 5vw;
        padding-bottom: 150px;
        min-height: 90vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    @keyframes slideReveal {
        0% { transform: scale(0.95); filter: blur(10px); opacity: 0; }
        100% { transform: scale(1); filter: blur(0); opacity: 1; }
    }

    .slide-title {
        font-family: 'Sora', sans-serif;
        font-size: 5.5rem;
        line-height: 0.95;
        margin-bottom: 40px;
        background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        letter-spacing: -4px;
    }
    
    .card-subtitle {
        color: #94a3b8;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }

    .card-detail {
        color: #38bdf8;
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 5px;
    }
    
    /* Ultra-Premium Glass Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(25px) saturate(180%);
        -webkit-backdrop-filter: blur(25px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 40px;
        padding: 40px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.4);
        transition: all 0.5s cubic-bezier(0.19, 1, 0.22, 1);
        position: relative;
        overflow: hidden;
    }
    .glass-card::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%);
        opacity: 0; transition: opacity 0.5s;
    }
    .glass-card:hover::before { opacity: 1; }
    .glass-card:hover {
        transform: translateY(-10px) scale(1.02);
        border-color: rgba(255,255,255,0.2);
        background: rgba(255, 255, 255, 0.05);
    }
    
    .metric-hero {
        font-size: 7rem;
        font-weight: 900;
        letter-spacing: -6px;
        margin: 10px 0;
        filter: drop-shadow(0 0 30px var(--accent-glow));
    }
    
    /* Apple-Style Floating Buttons (No Background Dock) */
    div[data-testid="stBaseButton-k_prev"], 
    div[data-testid="stBaseButton-k_home"], 
    div[data-testid="stBaseButton-k_next"] {
        position: fixed !important;
        bottom: 40px !important;
        z-index: 10000 !important;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1) !important;
    }

    div[data-testid="stBaseButton-k_prev"] { left: calc(50% - 130px) !important; }
    div[data-testid="stBaseButton-k_home"] { left: 50% !important; transform: translateX(-50%) !important; }
    div[data-testid="stBaseButton-k_next"] { left: calc(50% + 130px) !important; }

    div[data-testid="stBaseButton-k_prev"] button, 
    div[data-testid="stBaseButton-k_home"] button, 
    div[data-testid="stBaseButton-k_next"] button {
        border-radius: 25px !important;
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: white !important;
        width: 80px !important;
        height: 75px !important;
        font-size: 2.2rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        backdrop-filter: blur(15px) !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3) !important;
    }

    div[data-testid="stBaseButton-k_prev"] button:hover, 
    div[data-testid="stBaseButton-k_home"] button:hover, 
    div[data-testid="stBaseButton-k_next"] button:hover {
        background: var(--accent) !important;
        transform: translateY(-10px) scale(1.1) !important;
        box-shadow: 0 0 30px var(--accent-glow) !important;
        border-color: white !important;
        animation: neonPulse 1.5s infinite alternate !important;
    }

    @keyframes neonPulse {
        from { box-shadow: 0 0 10px var(--accent-glow); }
        to { box-shadow: 0 0 30px var(--accent-glow), 0 0 10px white; }
    }

    /* Luminous Progress Line */
    .progress-bar {
        position: fixed;
        top: 0; left: 0;
        height: 3px;
        background: linear-gradient(90deg, #7c3aed, #3b82f6, #10b981, #7c3aed);
        background-size: 200% 100%;
        z-index: 10002;
        transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        box-shadow: 0 0 15px rgba(124, 58, 237, 0.8), 0 0 5px rgba(59, 130, 246, 0.5);
        animation: gradientFlow 3s linear infinite;
    }
    
    @keyframes gradientFlow {
        0% { background-position: 0% 50%; }
        100% { background-position: 200% 50%; }
    }
</style>
<div class="mesh-bg"></div>
<div class="progress-bar" id="pbar"></div>
<script>
    // Update progress bar
    const updateBar = (pct) => {
        document.getElementById('pbar').style.width = pct + '%';
    }
    
    // Keyboard Navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight') {
            window.parent.document.querySelector('button[key="k_next"]').click();
        } else if (e.key === 'ArrowLeft') {
            window.parent.document.querySelector('button[key="k_prev"]').click();
        }
    });
</script>
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
    "🤖 Vision IA Stratégique": "AI_VISION",
    "✨ Conclusion & Remerciements": "CONCLUSION"
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
    idx = st.session_state.current_slide_idx
    current_key = slides[idx]
    
    # Mise à jour de la barre de progression (CSS Direct pour fiabilité maximale)
    progress_pct = (idx + 1) / len(slides) * 100
    st.markdown(f"<style>.progress-bar {{ width: {progress_pct}% !important; }}</style>", unsafe_allow_html=True)
    
    # --- SLIDE CONTENT ---
    st.markdown('<div class="slide-container">', unsafe_allow_html=True)
    
    # --- SLIDE CONTENT ---
    st.markdown('<div class="slide-container">', unsafe_allow_html=True)
    
    if current_key == "GLOBAL":
        st.markdown(f"""
            <h1 class="slide-title">Performance<br>Générale</h1>
            <div style="display: flex; gap: 20px;">
                <div class="glass-card" style="flex:1;">
                    <div class="card-subtitle">Flux Sortant</div>
                    <div class="metric-hero" style="color:#7c3aed;">98.4%</div>
                    <div class="card-detail">1,240 Commandes/Semaine</div>
                    <p>🎯 Taux de service optimal</p>
                </div>
                <div class="glass-card" style="flex:1;">
                    <div class="card-subtitle">Vitesse de Rotation</div>
                    <div class="metric-hero" style="color:#3b82f6;">12j</div>
                    <div class="card-detail">Croissance: +2.4j</div>
                    <p>⚡ Flux logistique accéléré</p>
                </div>
                <div class="glass-card" style="flex:1;">
                    <div class="card-subtitle">Engagement Client</div>
                    <div class="metric-hero" style="color:#10b981;">4.8/5</div>
                    <div class="card-detail">Base: 450 Pharmacies</div>
                    <p>⭐ Excellence relationnelle</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    elif current_key == "LOGISTIQUE":
        st.markdown('<h1 class="slide-title">Efficacité<br>Logistique</h1>', unsafe_allow_html=True)
        col_c, col_m = st.columns([2, 1])
        with col_c:
            df = pd.DataFrame({"J": ["Lun","Mar","Mer","Jeu","Ven","Sam"], "V": [120,150,140,180,160,110]})
            fig = px.area(df, x="J", y="V", title="Volume de Livraison Journalier")
            fig.update_traces(line_color='#7c3aed', fillcolor='rgba(124, 58, 237, 0.2)')
            fig.update_layout(
                height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False), font=dict(color="white")
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        with col_m:
            st.markdown('<div class="glass-card" style="height:100%;"><div class="card-subtitle">Analyse des Temps</div><h3>Délai Moyen</h3><div class="metric-hero" style="font-size:4rem; color:#7c3aed;">2.4h</div><div class="card-detail">Zone: Alger-Centre</div><p>Préparation & Dispatch</p></div>', unsafe_allow_html=True)

    elif current_key == "STOCKS":
        st.markdown('<h1 class="slide-title">Santé de<br>l\'Inventaire</h1>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="card-subtitle" style="color:white; margin-bottom:10px;">Répartition Qualité</div>', unsafe_allow_html=True)
            fig = go.Figure(data=[go.Pie(labels=['Sain', 'Critique', 'Périmé'], values=[85, 12, 3], hole=.8)])
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
            fig.update_traces(marker=dict(colors=['#10b981', '#f59e0b', '#ef4444']))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="glass-card"><div class="card-subtitle">Valorisation Actuelle</div><div class="metric-hero" style="color:#7c3aed;">124M</div><div class="card-detail">Stock Dormant: 8.4M</div><p>Dinar Algérien (DZ)</p></div>', unsafe_allow_html=True)

    elif current_key == "CLAIMS":
        st.markdown('<h1 class="slide-title">Qualité<br>Fournisseurs</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-subtitle">Top Réclamations en cours</div>', unsafe_allow_html=True)
        df_claims = pd.DataFrame({
            "Fournisseur": ["BIOPHARM", "SAIDAL", "FRATER", "SANOFI"], 
            "Réclamations": [4, 1, 2, 1], 
            "Gravité": ["🔴 Haute", "🟢 Basse", "🟡 Moyenne", "🔴 Haute"],
            "Délai": ["48h", "12h", "24h", "72h"]
        })
        st.dataframe(df_claims, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_key == "FINANCE":
        st.markdown('<h1 class="slide-title">Performance<br>Financière</h1>', unsafe_allow_html=True)
        st.markdown(f"""
            <div style="display: flex; gap: 20px;">
                <div class="glass-card" style="flex:1;">
                    <div class="card-subtitle">Trésorerie Entrante</div>
                    <div class="metric-hero" style="color:#10b981;">84.2M</div>
                    <div class="card-detail">Objectif: 90M</div>
                    <p>Encaissements validés</p>
                </div>
                <div class="glass-card" style="flex:1;">
                    <div class="card-subtitle">Risque Client</div>
                    <div class="metric-hero" style="color:#f59e0b;">12.8M</div>
                    <div class="card-detail">Litiges: 14 dossiers</div>
                    <p>Relances en cours</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    elif current_key == "HR_AGENTS":
        st.markdown('<h1 class="slide-title">Productivité<br>Équipe</h1>', unsafe_allow_html=True)
        cols = st.columns(3)
        agents = [("Yassine", "450 lignes", "99%"), ("Amine", "420 lignes", "98%"), ("Sara", "380 lignes", "100%")]
        for i, (name, perf, acc) in enumerate(agents):
            cols[i].markdown(f'<div class="glass-card" style="text-align:center;"><div class="card-subtitle">Performance Agent</div><h3>{name}</h3><div class="metric-hero" style="font-size:3rem; color:#7c3aed;">{perf}</div><div class="card-detail">Précision: {acc}</div></div>', unsafe_allow_html=True)

    elif current_key == "HR_DRIVERS":
        st.markdown('<h1 class="slide-title">Logistique<br>Dernier KM</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        df_drivers = pd.DataFrame({"Livreur": ["Ahmed", "Karim", "Zaki"], "Livraisons": [24, 21, 19], "Ponctualité": ["95%", "92%", "98%"]})
        st.dataframe(df_drivers, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_key == "AI_VISION":
        st.markdown('<h1 class="slide-title">Vision IA<br>Stratégique</h1>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        if is_ia_enabled():
            with st.spinner("Analyse des tendances 2026..."):
                report = ask_ai("Analyse la performance globale (98.4% service) et donne 3 axes stratégiques pour le board.")
                st.write(f"### 🤖 Rapport Exécutif\n\n{report}")
        else:
            st.info("Module IA désactivé.")
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_key == "CONCLUSION":
        msg_placeholder = st.empty()
        with st.spinner("Rédaction du message final..."):
            msg = ask_ai("Rédige un message de conclusion TRÈS BREF et inspirant pour une réunion logistique. Utilise beaucoup d'emojis. Remercie pour le 98.4% de service et souhaite un bon week-end.")
            st.markdown(f"""
                <h1 class="slide-title">Conclusion &<br>Remerciements</h1>
                <div class="glass-card" style="text-align:center;">
                    <div style="font-size:2.2rem; line-height:1.4; font-family:Sora; color:#f8fafc; margin-bottom:40px;">
                        {msg}
                    </div>
                    <div style="font-weight:800; color:#7c3aed; font-size:2.2rem; filter: drop-shadow(0 0 10px var(--accent-glow));">
                        DARPHARM PRO — Ensemble vers 2026 🚀
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # --- DOCK NAVIGATION ---
    st.markdown('<div class="bottom-indicator"></div>', unsafe_allow_html=True)
    
    c_p, c_h, c_n = st.columns(3)
    
    with c_p:
        if st.button("⬅️", key="k_prev"):
            if st.session_state.current_slide_idx > 0:
                st.session_state.current_slide_idx -= 1
                play_slide_fx()
                st.rerun()
            
    with c_h:
        if st.button("🏠", key="k_home"):
            st.session_state.keynote_mode = "BUILDER"
            st.rerun()
        
    with c_n:
        if st.button("➡️", key="k_next"):
            if st.session_state.current_slide_idx < len(slides) - 1:
                st.session_state.current_slide_idx += 1
                play_slide_fx()
                st.rerun()
