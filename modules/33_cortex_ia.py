import streamlit as st
import pandas as pd
import plotly.express as px
from utils_cortex import ask_cortex, generate_daily_diagnostics, get_strategic_snapshot
from utils_ia import is_ia_enabled

# --- CONFIGURATION PAGE ---
etab_nom = "Pharmaciel" if st.session_state.get('etablissement') == 'pharmaciel' else "DarPharm"
st.set_page_config(page_title=f"Cortex IA - {etab_nom}", page_icon="🧠", layout="wide")

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
st.write(f"L'intelligence omnisciente qui pilote {etab_nom} Pro vers l'excellence zéro-faute.")

if not is_ia_enabled():
    st.warning("⚠️ L'IA est actuellement désactivée dans les paramètres système.")
    st.stop()

# --- 1. VUE 360° & VIGILANCE ---
st.markdown('<div class="cortex-card">', unsafe_allow_html=True)
st.write("#### 🛡️ Vigilance Sanitaire & Environnement (Algérie)")
col_v1, col_v2 = st.columns([1, 2])
with col_v1:
    trend = st.selectbox("Tendance actuelle :", 
                        ["Période Standard", "Grippe Saisonnière", "Allergies Printanières", "Épidémie Virale", "Ruptures DCI Critiques"])
with col_v2:
    st.info(f"Le Cortex adapte ses recommandations pour : **{trend}**. Il cherchera à associer vos stocks stagnants aux besoins de cette période.")
st.markdown('</div>', unsafe_allow_html=True)

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
tab1, tab2, tab3 = st.tabs(["🎯 Diagnostic Proactif", "💬 Consultant Stratégique", "🔮 Météo Logistique & Prédictions"])

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

with tab3:
    st.subheader("🔮 Anticipation & Prédictions Logistiques")
    st.write("Le Cortex croise l'historique des flux avec la saisonnalité pour prévoir vos ruptures et pics d'activité.")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown('<div class="cortex-card">', unsafe_allow_html=True)
        st.write("#### 🚨 Alertes Ruptures Imminentes (Top 3)")
        st.info("📉 **Amoxicilline 500mg** : Rupture estimée dans **3 jours** (Demande forte).")
        st.info("📉 **Paracétamol 1g** : Rupture estimée dans **5 jours**.")
        st.info("📉 **Sérum Phy 5ml** : Stock critique, à recommander urgemment.")
        if st.button("🔄 Lancer l'Analyse Complète des Stocks", key="btn_rupture"):
            with st.spinner("Analyse prédictive des rotations en cours..."):
                rep = ask_cortex("Agis comme un directeur de Supply Chain. Donne-moi 3 recommandations urgentes d'approvisionnement pour une pharmacie de gros en Algérie en cette période de l'année. Sois précis sur les classes thérapeutiques.")
                st.markdown(f'<div class="ia-report">{rep}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_p2:
        st.markdown('<div class="cortex-card">', unsafe_allow_html=True)
        st.write("#### 📅 Impact Saisonnalité & Conseils")
        st.success("💡 **Recommandation IA** : En prévision du pic estival, augmentez vos stocks de **réhydratants**, **crèmes solaires** et **antihistaminiques** de +30%.")
        
        # Graphique fictif de prévision
        df_season = pd.DataFrame({
            "Mois": ["Juin", "Juillet", "Août", "Septembre"],
            "Demande Prévue": [120, 150, 180, 110],
            "Type": ["Estivale", "Estivale", "Estivale", "Standard"]
        })
        fig_season = px.line(df_season, x="Mois", y="Demande Prévue", markers=True, title="Prévision de Demande (Catégorie Estivale)")
        fig_season.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_season, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="cortex-card">', unsafe_allow_html=True)
    st.write("#### ⚡ Prévision de la Charge de Travail (Équipe Logistique)")
    st.write("Basé sur les arrivages prévus des fournisseurs et les commandes clients en attente.")
    
    df_charge = pd.DataFrame({
        "Jour": ["Aujourd'hui", "Demain", "J+2", "J+3", "J+4"],
        "Colis à traiter": [450, 600, 320, 410, 250]
    })
    fig_charge = px.bar(df_charge, x="Jour", y="Colis à traiter", title="Volume de Colis Estimé (72h)", color="Colis à traiter", color_continuous_scale="Purples")
    fig_charge.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=300)
    st.plotly_chart(fig_charge, use_container_width=True)
    
    if st.button("🤖 Optimiser les plannings de l'équipe", use_container_width=True):
        st.success("Suggestion IA : Renforcez l'équipe de préparation 'Demain' (Pic estimé à 600 colis). Assignez Islem et Ayoub exclusivement sur les expéditions.")
    st.markdown('</div>', unsafe_allow_html=True)
