import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION ---
RECLAM_WORKSHEET = "Analyse_Reclamations"
RECLAM_FALLBACK = "data/db_reclamations_analyse.csv"

# --- 1. CSS & STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
    
    .reclam-card {
        background: linear-gradient(145deg, #ffffff, #f8fafc);
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    .reclam-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(124, 58, 237, 0.1), 0 10px 10px -5px rgba(124, 58, 237, 0.04);
        border-color: rgba(124, 58, 237, 0.3);
    }
    
    .ia-report {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(30, 41, 59, 0.02) 100%);
        border-left: 5px solid #7c3aed;
        padding: 30px;
        border-radius: 16px;
        color: #1e293b;
        line-height: 1.6;
        font-family: 'Sora', sans-serif;
        border: 1px solid rgba(124, 58, 237, 0.1);
    }
    
    .stat-box { text-align: center; }
    .stat-val { font-size: 3rem; font-weight: 800; margin-bottom: 5px; }
    .val-neutral { background: linear-gradient(90deg, #1e293b, #475569); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .severity-high { background: linear-gradient(90deg, #ef4444, #b91c1c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .severity-med { background: linear-gradient(90deg, #f59e0b, #d97706); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stat-label { font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE TECHNIQUE ---
# ... (Gardons les fonctions clean_reclam_cols et categorize_motif identiques) ...

# (Fonction de nettoyage déplacée dans Admin Centrale)

def categorize_motif(motif_str):
    m = str(motif_str).upper()
    if any(k in m for k in ["COMMERCIAL", "SAISIE", "FORCE", "REVENU", "EXCUSE"]): return "Erreur Commerciale"
    if any(k in m for k in ["PHARMACIEN", "DOSAGE", "FORME", "DCI", "MARQUE"]): return "Erreur Pharmacien"
    if any(k in m for k in ["DEPOT", "PREPARATION", "BOITE", "PLUS", "MOIN", "QUANTITE", "MANQUE"]): return "Erreur Dépôt"
    if any(k in m for k in ["PNC", "CONFORME", "VIGNETTE", "ABIMEE", "CASSEE", "DETERIORE"]): return "PNC (Non Conforme)"
    if any(k in m for k in ["SUPERVISEUR", "MODIFICATION", "REFAIRE", "BON DEJA"]): return "Erreur Superviseur"
    return "Autre / Non Classé"

# --- 3. UI ---
st.title("🎯 Audit Stratégique des Réclamations")
st.write("Identifiez les points de friction, recadrez la performance commerciale et optimisez la qualité opérationnelle.")

# Chargement permanent
if "df_reclam_analysed" not in st.session_state:
    df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
    if not df_db.empty:
        st.session_state.df_reclam_analysed = df_db

tabs = st.tabs(["📊 Tableau de Bord", "📥 Import de Données", "🧠 Diagnostic IA Expert"])

with tabs[1]:
    st.markdown('<div class="reclam-card">', unsafe_allow_html=True)
    st.subheader("📥 Source de Données")
    st.info("L'importation de fichiers de réclamations se fait désormais via le module **Administration Centrale** pour garantir la cohérence des données avec l'ensemble de la plateforme.")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[0]:
    if "df_reclam_analysed" in st.session_state:
        df = st.session_state.df_reclam_analysed.copy()
        
        # Filtre Global: Exclure les réclamations "Refusées" de toute l'analyse
        if 'statut' in df.columns:
            df['statut_clean'] = df['statut'].astype(str).str.upper().str.strip()
            df = df[~df['statut_clean'].str.contains("REFUS", na=False)]
            
        # Fallback de sécurité si le dataframe provient d'un ancien cache ou DB
        if 'motif' not in df.columns: df['motif'] = "Non Renseigné"
        if 'categorie_motif' not in df.columns: df['categorie_motif'] = "Autre / Non Classé"
        if 'commercial' not in df.columns: df['commercial'] = "Inconnu"
        
        # Nettoyage strict des valeurs vides (NaN) qui font crasher Plotly Sunburst
        df['motif'] = df['motif'].fillna("Non Renseigné").astype(str)
        df['categorie_motif'] = df['categorie_motif'].fillna("Autre / Non Classé").astype(str)
        df['commercial'] = df['commercial'].fillna("Inconnu").astype(str)
        
        # Filtres
        st.sidebar.subheader("🎯 Pilotage")
        comm_list = ["Tous"]
        if 'commercial' in df.columns:
            comm_list += sorted([str(x) for x in df['commercial'].dropna().unique()])
            
        selected_comm = st.sidebar.selectbox("Commercial :", comm_list)
        df_p = df[df['commercial'] == selected_comm] if selected_comm != "Tous" else df
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">📋 Réclamations Validées</div><div class="stat-val val-neutral">{len(df_p)}</div></div>', unsafe_allow_html=True)
        with c2: 
            err_c = len(df_p[df_p['categorie_motif'] == "Erreur Commerciale"])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">❌ Fautes Commerciales</div><div class="stat-val severity-high">{err_c}</div></div>', unsafe_allow_html=True)
        with c3:
            manques = len(df_p[df_p['motif'].astype(str).str.upper().str.contains("MANQUE", na=False)])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">⚠️ Manques (Dépôt)</div><div class="stat-val severity-med">{manques}</div></div>', unsafe_allow_html=True)
        with c4:
            pnc = len(df_p[df_p['categorie_motif'] == "PNC (Non Conforme)"])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">🛡️ Qualité (PNC)</div><div class="stat-val severity-high">{pnc}</div></div>', unsafe_allow_html=True)

        col_g1, col_g2 = st.columns([1, 1])
        
        with col_g1:
            st.markdown('<div class="reclam-card">', unsafe_allow_html=True)
            st.markdown("#### 🍩 Hiérarchie des Motifs")
            
            df_p_plot = df_p.copy()
            df_p_plot['motif_plot'] = df_p_plot['motif'].astype(str) + " "
            
            fig_sun = px.sunburst(df_p_plot, path=['categorie_motif', 'motif_plot'], 
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_sun.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig_sun, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_g2:
            st.markdown('<div class="reclam-card">', unsafe_allow_html=True)
            st.markdown("#### 🏆 Top Responsables")
            comm_stats = df_p['commercial'].value_counts().reset_index()
            comm_stats.columns = ['Commercial', 'Nb']
            fig_bar = px.bar(comm_stats.head(8), x='Nb', y='Commercial', orientation='h',
                            color='Nb', color_continuous_scale='Purples')
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="reclam-card">', unsafe_allow_html=True)
        st.markdown("#### 🕵️ Matrice des Responsabilités (Commercial vs Catégorie)")
        if 'commercial' in df_p.columns and 'categorie_motif' in df_p.columns:
            pivot = df_p.groupby(['commercial', 'categorie_motif']).size().unstack(fill_value=0)
            fig_heat = px.imshow(pivot, text_auto=True, color_continuous_scale='YlOrRd')
            fig_heat.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, margin=dict(t=30, l=0, r=0, b=0))
            st.plotly_chart(fig_heat, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        col_alerte, col_detail = st.columns([1, 2])
        
        with col_alerte:
            st.markdown("#### 🚨 Alerte Tolérance (Max 5 Err. Comm)")
            if 'commercial' in df_p.columns and 'categorie_motif' in df_p.columns:
                err_by_comm = df_p[df_p['categorie_motif'] == "Erreur Commerciale"].groupby('commercial').size().reset_index(name='Nb_Erreurs')
                over_limit = err_by_comm[err_by_comm['Nb_Erreurs'] > 5]
                
                if not over_limit.empty:
                    for _, row in over_limit.iterrows():
                        st.error(f"⚠️ **{row['commercial']}** : **{row['Nb_Erreurs']}** erreurs (Dépassement de la limite de 5).")
                else:
                    st.success("✅ Aucun commercial ne dépasse la limite des 5 erreurs.")
        
        with col_detail:
            st.markdown("#### 📋 Base de Données des Retours")
            cat_filter = st.selectbox("Afficher spécifiquement :", ["Tous les retours", "PNC (Non Conforme)", "Erreur Commerciale", "Erreur Dépôt", "Erreur Pharmacien"], label_visibility="collapsed")
            
            cols_to_show = ['date', 'commercial', 'client', 'produit', 'categorie_motif', 'motif', 'quantite', 'remarque_ligne']
            cols_present = [c for c in cols_to_show if c in df_p.columns]
            
            df_details = df_p[cols_present].copy()
            if cat_filter != "Tous les retours" and 'categorie_motif' in df_details.columns:
                df_details = df_details[df_details['categorie_motif'] == cat_filter]
                
            st.dataframe(df_details, use_container_width=True, hide_index=True)
    else:
        st.warning("Aucune donnée disponible.")

with tabs[2]:
    if is_ia_enabled() and "df_reclam_analysed" in st.session_state:
        st.subheader("🧠 Intelligence Artificielle - Root Cause Analysis")
        if st.button("🚀 LANCER L'AUDIT DE PERFORMANCE", use_container_width=True, type="primary"):
            df = st.session_state.df_reclam_analysed
            summary = df.groupby(['commercial', 'categorie_motif']).size().reset_index(name='count').to_dict('records')
            
            prompt = f"Tu es un expert en audit logistique. Analyse ces réclamations : {summary}. Identifie les acteurs critiques et propose un plan d'action immédiat. Sois bref et percutant."
            
            with st.spinner("L'IA scanne les comportements..."):
                report = ask_ai(prompt)
                st.markdown(f'<div class="ia-report">{report}</div>', unsafe_allow_html=True)
                st.balloons()
    else:
        st.info("Importez des données pour activer le diagnostic IA.")
