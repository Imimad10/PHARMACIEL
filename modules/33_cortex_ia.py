import streamlit as st
import pandas as pd
import plotly.express as px
from utils_cortex import ask_cortex, generate_daily_diagnostics, get_strategic_snapshot
from utils_ia import is_ia_enabled

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Cortex IA - DarPharm", page_icon="🧠", layout="wide")

# --- CSS: EXECUTIVE GLASSMORPHISM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
    
    .cortex-card {
        background: rgba(124, 58, 237, 0.05);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(124, 58, 237, 0.1);
        border-radius: 24px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }
    
    .insight-label {
        font-size: 0.9rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
    }
    
    .insight-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1e293b;
        margin-top: 10px;
    }
    
    .ia-report {
        background: white;
        border-radius: 16px;
        padding: 20px;
        border-left: 5px solid #7c3aed;
        color: #1e293b;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Cortex Stratégique IA")
st.write("L'intelligence omnisciente qui pilote DarPharm Pro vers l'excellence zéro-faute.")

if not is_ia_enabled():
    st.warning("⚠️ L'IA est actuellement désactivée dans les paramètres système.")
    st.stop()

# --- 1. VUE 360° (Snapshot) ---
snapshot = get_strategic_snapshot()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f'<div class="cortex-card"><div class="insight-label">Santé Équipe</div><div class="insight-value">{snapshot.get("users_count", 0)}</div><p>Collaborateurs actifs</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="cortex-card"><div class="insight-label">Volume Fautes</div><div class="insight-value" style="color:#ef4444;">{snapshot.get("total_reclamations", 0)}</div><p>Réclamations à résoudre</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="cortex-card"><div class="insight-label">Rentabilité</div><div class="insight-value" style="color:#10b981;">{snapshot.get("total_marge", 0):,.0f}</div><p>Marge nette cumulée (DA)</p></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="cortex-card"><div class="insight-label">Cœur IA</div><div class="insight-value">ACTIVE</div><p>Auto-apprentissage activé</p></div>', unsafe_allow_html=True)

st.divider()

# --- 2. ANALYSE ET RÉSOLUTION ---
tab1, tab2 = st.tabs(["🎯 Diagnostic Proactif", "💬 Consultant Stratégique"])

with tab1:
    st.subheader("🛠️ Rapport de Résolution Automatique")
    st.write("L'IA analyse vos données en temps réel pour minimiser les pertes.")
    
    if st.button("🚀 GÉNÉRER LE DIAGNOSTIC DU JOUR"):
        with st.spinner("Le Cortex analyse les flux de données..."):
            report = generate_daily_diagnostics()
            st.markdown(f'<div class="ia-report">{report}</div>', unsafe_allow_html=True)
            
    st.markdown('<div style="margin-top:30px;"></div>', unsafe_allow_html=True)
    
    # Visualisation des "Points Chauds" (Erreurs récurrentes)
    st.write("#### 🔍 Zones de Pertes et Fautes (Points Chauds)")
    df_mock_hot = pd.DataFrame({
        "Zone": ["Saisie Commerciale", "Préparation Dépôt", "Livraison", "Erreur Client"],
        "Impact Financier": [45, 30, 15, 10]
    })
    fig = px.treemap(df_mock_hot, path=['Zone'], values='Impact Financier', 
                     color='Impact Financier', color_continuous_scale='RdYlGn_r')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("💬 Consultant IA Multi-Modules")
    st.write("Posez une question sur n'importe quel aspect de votre business. Le Cortex connaît tout.")
    
    user_query = st.text_area("Votre question stratégique :", 
                             placeholder="Ex: 'Comment réduire les erreurs de l'agent X ?' ou 'Quelles sont les périodes où je perds le plus de marge ?'")
    
    if st.button("🧠 INTERROGER LE CORTEX", type="primary"):
        if user_query:
            with st.spinner("Consultation de la base de connaissances DarPharm..."):
                answer = ask_cortex(user_query)
                st.markdown(f'<div class="ia-report"><b>💡 Solution proposée :</b><br><br>{answer}</div>', unsafe_allow_html=True)
        else:
            st.error("Veuillez saisir une question.")
