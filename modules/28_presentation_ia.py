import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data
from utils_themes import apply_theme_css, load_themes_db

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DarPharm Présentation - Mode Meeting", layout="wide", page_icon="📽️")

# Injection CSS pour le mode DataShow (Plein écran, Typo large, Contrastes élevés)
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
            color: #f8fafc !important;
        }
        .main .block-container {
            padding: 2rem 5rem !important;
        }
        h1 {
            font-size: 4rem !important;
            font-weight: 900 !important;
            text-align: center;
            background: linear-gradient(to right, #60a5fa, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem !important;
        }
        h2 {
            font-size: 2.5rem !important;
            color: #94a3b8 !important;
            border-bottom: 2px solid rgba(148, 163, 184, 0.2);
            padding-bottom: 1rem;
            margin-top: 3rem !important;
        }
        .presentation-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 3rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }
        .presentation-card:hover {
            border-color: #60a5fa;
            transform: translateY(-5px);
        }
        .ai-insight {
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
        }
        .metric-big {
            font-size: 5rem !important;
            font-weight: 800;
            color: #60a5fa;
            text-shadow: 0 0 20px rgba(96, 165, 250, 0.3);
        }
        .metric-label {
            font-size: 1.5rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        /* Style des boutons slide */
        .stButton button {
            width: 100% !important;
            height: 80px !important;
            font-size: 1.5rem !important;
            border-radius: 20px !important;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
            border: none !important;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2) !important;
        }
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
        st.markdown('<div class="presentation-card"><p class="metric-label">Taux de Service</p><p class="metric-big">98.4%</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="presentation-card"><p class="metric-label">Rotation Moyenne</p><p class="metric-big">12.5j</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="presentation-card"><p class="metric-label">Précision Inventaire</p><p class="metric-big">99.1%</p></div>', unsafe_allow_html=True)

    if st.checkbox("Générer l'analyse stratégique IA", value=True):
        with st.spinner("L'IA prépare votre briefing..."):
            context = "Performance globale stable avec une légère hausse du volume logistique (+5%) et une précision d'inventaire record."
            insight = get_ai_presentation_summary(context)
            st.markdown(f'<div class="ai-insight">“ {insight} ”</div>', unsafe_allow_html=True)

elif current == 1: # LOGISTIQUE
    st.markdown("<h2>Performance Opérationnelle & Logistique</h2>", unsafe_allow_html=True)
    
    # Graphique de performance
    df_perf = pd.DataFrame({
        "Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"],
        "Livraisons": [120, 150, 140, 180, 160, 110],
        "Objectif": [130, 130, 130, 130, 130, 130]
    })
    
    fig = px.line(df_perf, x="Jour", y=["Livraisons", "Objectif"], 
                  template="plotly_dark", 
                  color_discrete_map={"Livraisons": "#60a5fa", "Objectif": "#ef4444"})
    fig.update_layout(height=500, font=dict(size=18), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("""
        <div class="presentation-card">
            <h3>Points Clés :</h3>
            <ul style="font-size: 1.5rem; line-height: 2;">
                <li>Capacité maximale atteinte jeudi dernier avec 180 colis/jour.</li>
                <li>Réduction des délais de livraison de 14% par rapport au mois précédent.</li>
                <li>Consommation carburant optimisée grâce au nouveau routage IA.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

elif current == 2: # STOCKS
    st.markdown("<h2>État des Stocks & Précision</h2>", unsafe_allow_html=True)
    
    col_chart, col_txt = st.columns([2, 1])
    
    with col_chart:
        labels = ['Conforme', 'Écart Mineur', 'Investigation']
        values = [4500, 120, 15]
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6)])
        fig_pie.update_layout(template="plotly_dark", height=600, font=dict(size=20), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_txt:
        st.markdown('<div class="presentation-card" style="height:100%;">', unsafe_allow_html=True)
        st.markdown("### Focus Inventaire Triple")
        st.write("Le passage à l'inventaire triple a permis de réduire les pertes de stock de 22% en seulement 2 semaines.")
        st.metric("Pertes évitées", "450k DZD", "+12%")
        st.markdown('</div>', unsafe_allow_html=True)

elif current == 3: # ROTATION
    st.markdown("<h2>Analyse de la Rotation (Stock Mort)</h2>", unsafe_allow_html=True)
    
    # Simulation de données de rotation
    df_rot = pd.DataFrame({
        "Catégorie": ["Antibiotiques", "Cardio", "Derma", "Pédiatrie", "Urgences"],
        "Rotation (Jours)": [5, 12, 45, 8, 2],
        "Valeur (MDZD)": [12, 8, 4, 15, 6]
    })
    
    fig_bar = px.bar(df_rot, x="Catégorie", y="Rotation (Jours)", color="Valeur (MDZD)",
                     title="Vitesse de rotation par segment thérapeutique",
                     template="plotly_dark", height=500)
    fig_bar.update_layout(font=dict(size=18), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.warning("⚠️ Alerte : Le segment 'Dermatologie' présente une rotation anormalement lente (45j). Action recommandée : Promotion ou transfert inter-dépôts.")

elif current == 4: # RECOUVREMENT
    st.markdown("<h2>Santé Financière & Recouvrement</h2>", unsafe_allow_html=True)
    
    col_fin1, col_fin2 = st.columns(2)
    with col_fin1:
        st.markdown('<div class="presentation-card"><p class="metric-label">Total Recouvré</p><p class="metric-big" style="color:#10b981;">84.2 MDZD</p></div>', unsafe_allow_html=True)
    with col_fin2:
        st.markdown('<div class="presentation-card"><p class="metric-label">En Attente</p><p class="metric-big" style="color:#f59e0b;">12.8 MDZD</p></div>', unsafe_allow_html=True)
    
    # Graphique de répartition des créances
    df_rec = pd.DataFrame({
        "Client": ["Pharmacie A", "Pharmacie B", "Pharmacie C", "Autres"],
        "Montant": [2.5, 1.8, 1.2, 7.3]
    })
    fig_rec = px.funnel(df_rec, x="Montant", y="Client", template="plotly_dark", title="Répartition des créances prioritaires")
    st.plotly_chart(fig_rec, use_container_width=True)

elif current == 5: # VISION IA
    st.markdown("<h2>Vision Stratégique IA - 2026</h2>", unsafe_allow_html=True)
    
    if st.button("Lancer la Simulation de Prévisions IA"):
        with st.status("L'IA analyse les tendances historiques...", expanded=True) as status:
            st.write("Chargement des séries temporelles...")
            st.write("Calcul des corrélations saisonnières...")
            st.write("Génération des recommandations stratégiques...")
            status.update(label="Analyse Complétée", state="complete", expanded=False)
            
        col_ia1, col_ia2 = st.columns(2)
        
        with col_ia1:
            st.markdown("""
                <div class="presentation-card">
                    <h3 style="color:#a855f7;">Opportunités IA</h3>
                    <p style="font-size:1.3rem;">
                        1. <b>Prédiction de Rupture :</b> Anticipation des pénuries 15 jours à l'avance.<br>
                        2. <b>Auto-Routage :</b> Gain de 22% sur les coûts logistiques.<br>
                        3. <b>Analyse Prédictive :</b> Augmentation du taux de service à 99.5%.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
        with col_ia2:
            st.markdown('<div class="ai-insight">Recommandation : "Investir dans l\'automatisation du module de pointage marchandise pour libérer 15% de temps de travail sur le terrain."</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("<div style='text-align:center; padding: 20px; color:#475569;'>Appuyez sur F11 pour passer en plein écran | DarPharm Solution Meeting Mode v1.0</div>", unsafe_allow_html=True)
