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
        background: rgba(124, 58, 237, 0.04);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .ia-report {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(30, 41, 59, 0.05) 100%);
        border-left: 5px solid #7c3aed;
        padding: 30px;
        border-radius: 12px;
        color: #1e293b;
        line-height: 1.6;
        font-family: 'Sora', sans-serif;
        border: 1px solid rgba(124, 58, 237, 0.1);
    }
    
    .stat-box { text-align: center; }
    .stat-val { font-size: 2.2rem; font-weight: 800; color: #1e293b; margin-bottom: 0px; }
    .stat-label { font-size: 0.8rem; color: #475569; text-transform: uppercase; letter-spacing: 1px; }
    
    .severity-high { color: #ef4444; }
    .severity-med { color: #f59e0b; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE TECHNIQUE ---
# ... (Gardons les fonctions clean_reclam_cols et categorize_motif identiques) ...

def clean_reclam_cols(df):
    mapping = {
        'client': ['client', 'pharmacie', 'destinataire'],
        'reference': ['référence', 'reference', 'ref', 'bon', 'commande', 'document'],
        'type': ['type'],
        'date': ['date'],
        'code_client': ['code client'],
        'region': ['région', 'region'],
        'produit': ['produit', 'designation', 'article'],
        'statut_bon': ['statut bon'],
        'num_lot': ['n°lot', 'lot', 'num lot'],
        'motif': ['motif', 'cause', 'raison'],
        'prix_vente': ['prix vente', 'prix'],
        'ppa': ['ppa'],
        'date_exp': ['date exp.', 'date exp'],
        'quantite': ['quantité', 'quantite', 'qte'],
        'tx_vente': ['tx vente'],
        'valeur_vente': ['valeur vente'],
        'statut': ['statut'],
        'remarque_ligne': ['remarque ligne', 'remarque'],
        'commercial': ['crée par', 'cree par', 'créé par', 'commercial', 'vendeur', 'user'],
        'date_creation': ['date création', 'date creation', 'cree le', 'date_crea'],
        'psycho': ['psycho.', 'psycho'],
        'frigo': ['frigo.', 'frigo'],
        'chere': ['chère', 'chere'],
        'date_cloture': ['date clôture', 'date cloture'],
        'cloturer_par': ['clôturer par', 'cloturer par'],
        'cout_revient': ['cout de revient', 'coût de revient'],
        'ref_facture': ['réf. facture', 'ref. facture', 'ref facture'],
        'date_facture': ['date facture', 'date de facture', 'date_fac'],
        'categorie': ['catégorie', 'categorie'],

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
        with c1: st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Réclam. Validées</div><div class="stat-val">{len(df_p)}</div></div>', unsafe_allow_html=True)
        with c2: 
            err_c = len(df_p[df_p['categorie_motif'] == "Erreur Commerciale"])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Fautes Comm.</div><div class="stat-val severity-high">{err_c}</div></div>', unsafe_allow_html=True)
        with c3:
            manques = len(df_p[df_p['motif'].astype(str).str.upper().str.contains("MANQUE", na=False)])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Manques (Dépôt)</div><div class="stat-val severity-med">{manques}</div></div>', unsafe_allow_html=True)
        with c4:
            pnc = len(df_p[df_p['categorie_motif'] == "PNC (Non Conforme)"])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Qualité (PNC)</div><div class="stat-val severity-high">{pnc}</div></div>', unsafe_allow_html=True)

        col_g1, col_g2 = st.columns([1, 1])
        
        with col_g1:
            st.markdown("#### 🍩 Hiérarchie des Motifs")
            
            # Anti-Crash Plotly: Si un motif a exactement le même nom que sa catégorie, Plotly crashe (A -> A).
            # On ajoute un espace invisible à la fin pour rendre le noeud unique sans perturber l'affichage.
            df_p_plot = df_p.copy()
            df_p_plot['motif_plot'] = df_p_plot['motif'].astype(str) + " "
            
            fig_sun = px.sunburst(df_p_plot, path=['categorie_motif', 'motif_plot'], 
                                 color_discrete_sequence=px.colors.qualitative.Pastel,
                                 template="plotly_dark")
            st.plotly_chart(fig_sun, use_container_width=True)
            
        with col_g2:
            st.markdown("#### 🏆 Top Responsables")
            comm_stats = df_p['commercial'].value_counts().reset_index()
            comm_stats.columns = ['Commercial', 'Nb']
            fig_bar = px.bar(comm_stats.head(8), x='Nb', y='Commercial', orientation='h',
                            color='Nb', color_continuous_scale='Reds', template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.markdown("#### 🕵️ Matrice des Responsabilités (Commercial vs Catégorie)")
        if 'commercial' in df_p.columns and 'categorie_motif' in df_p.columns:
            pivot = df_p.groupby(['commercial', 'categorie_motif']).size().unstack(fill_value=0)
            # Heatmap pour plus de "WOW"
            fig_heat = px.imshow(pivot, text_auto=True, color_continuous_scale='YlOrRd', template="plotly_dark")
            st.plotly_chart(fig_heat, use_container_width=True)

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
