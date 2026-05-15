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

# --- 2. LOGIQUE TECHNIQUE ---

def clean_reclam_cols(df):
    """Mappe intelligemment les colonnes du fichier importé."""
    mapping = {
        'reference': ['ref', 'bon', 'commande', 'document'],
        'client': ['client', 'pharmacie', 'destinataire'],
        'commercial': ['commercial', 'cree par', 'créé par', 'vendeur', 'user'],
        'produit': ['produit', 'designation', 'article'],
        'motif': ['motif', 'cause', 'raison', 'type'],
        'date_creation': ['date de creation', 'date creation', 'cree le', 'date_crea'],
        'date_facture': ['date de facture', 'date facture', 'date_fac']
    }
    
    new_cols = {}
    found = []
    for target, alts in mapping.items():
        for col in df.columns:
            if any(alt in str(col).lower() for alt in alts):
                new_cols[col] = target
                found.append(target)
                break
    return df.rename(columns=new_cols), found

def categorize_motif(motif_str):
    """Catégorise le motif brut dans l'une des 5 catégories DarPharm."""
    m = str(motif_str).upper()
    if any(k in m for k in ["COMMERCIAL", "SAISIE", "FORCE", "REVENU", "EXCUSE"]):
        return "Erreur Commerciale"
    if any(k in m for k in ["PHARMACIEN", "DOSAGE", "FORME", "DCI", "MARQUE"]):
        return "Erreur Pharmacien"
    if any(k in m for k in ["DEPOT", "PREPARATION", "BOITE", "PLUS", "MOIN", "QUANTITE"]):
        return "Erreur Dépôt"
    if any(k in m for k in ["PNC", "CONFORME", "VIGNETTE", "ABIMEE", "CASSEE", "DETERIORE"]):
        return "PNC (Non Conforme)"
    if any(k in m for k in ["SUPERVISEUR", "MODIFICATION", "REFAIRE", "BON DEJA"]):
        return "Erreur Superviseur"
    return "Autre / Non Classé"

# --- 3. UI ---

st.title("🎯 Analyse Stratégique des Réclamations")
st.info("Outil de tracking de la performance commerciale et opérationnelle. Identifiez l'origine des erreurs pour réduire les retours.")

tabs = st.tabs(["📊 Tableau de Bord", "📥 Import & Données", "🤖 Analyse IA"])

with tabs[1]:
    st.subheader("Chargement des Réclamations")
    uploaded_file = st.file_uploader("Importez votre fichier Excel ou CSV de réclamations", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
            
            df_clean, found = clean_reclam_cols(df_raw)
            
            if 'motif' in df_clean.columns:
                df_clean['categorie_motif'] = df_clean['motif'].apply(categorize_motif)
            
            st.success(f"✅ Fichier chargé : {len(df_clean)} réclamations détectées.")
            st.session_state.df_reclam_analysed = df_clean
            
            with st.expander("Aperçu des données nettoyées"):
                st.dataframe(df_clean.head(10), use_container_width=True)
                
            if st.button("💾 Enregistrer ces données pour le suivi global", use_container_width=True):
                save_gs_data(df_clean, RECLAM_WORKSHEET, RECLAM_FALLBACK, force_cloud=True)
                st.success("Données synchronisées !")
                
        except Exception as e:
            st.error(f"Erreur lors de l'import : {e}")

# Chargement permanent
if "df_reclam_analysed" not in st.session_state:
    df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
    if not df_db.empty:
        st.session_state.df_reclam_analysed = df_db

with tabs[0]:
    if "df_reclam_analysed" in st.session_state:
        df = st.session_state.df_reclam_analysed
        
        # Filtres
        st.sidebar.subheader("🎯 Filtres d'Analyse")
        comm_list = ["Tous"] + sorted(df['commercial'].unique().tolist()) if 'commercial' in df.columns else ["Tous"]
        selected_comm = st.sidebar.selectbox("Filtrer par Commercial :", comm_list)
        
        df_plot = df.copy()
        if selected_comm != "Tous":
            df_plot = df_plot[df_plot['commercial'] == selected_comm]

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Réclamations", len(df_plot))
        if 'categorie_motif' in df_plot.columns:
            top_motif = df_plot['categorie_motif'].mode()[0] if not df_plot.empty else "N/A"
            c2.metric("Motif Principal", top_motif)
        
        if 'commercial' in df_plot.columns:
            c3.metric("Nb Commerciaux", df_plot['commercial'].nunique())
            
        # Graphiques
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("#### 📊 Répartition par Catégorie")
            if 'categorie_motif' in df_plot.columns:
                fig_pie = px.pie(df_plot, names='categorie_motif', hole=0.5, 
                                color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_g2:
            st.markdown("#### 🏆 Top Commerciaux (Nb Réclamations)")
            if 'commercial' in df_plot.columns:
                comm_counts = df_plot['commercial'].value_counts().reset_index()
                comm_counts.columns = ['Commercial', 'Nombre']
                fig_bar = px.bar(comm_counts.head(10), x='Nombre', y='Commercial', orientation='h',
                                color='Nombre', color_continuous_scale='Reds')
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.markdown("#### 🕵️ Analyse des Erreurs Commerciales")
        col_e1, col_e2 = st.columns([2, 1])
        
        with col_e1:
            if 'categorie_motif' in df_plot.columns and 'commercial' in df_plot.columns:
                # Matrice Commercial / Catégorie
                pivot = df_plot.groupby(['commercial', 'categorie_motif']).size().unstack(fill_value=0)
                st.write("**Répartition détaillée par acteur :**")
                st.dataframe(pivot, use_container_width=True)
        
        with col_e2:
            if 'categorie_motif' in df_plot.columns:
                err_comm = len(df_plot[df_plot['categorie_motif'] == "Erreur Commerciale"])
                st.warning(f"⚠️ {err_comm} erreurs de saisie ou ventes forcées détectées.")
                if err_comm > 0:
                    st.write("L'erreur commerciale représente **{:.1f}%** de vos retours.".format(err_comm/len(df_plot)*100))

    else:
        st.warning("Veuillez importer des données dans l'onglet 'Import & Données' pour commencer l'analyse.")

with tabs[2]:
    if is_ia_enabled() and "df_reclam_analysed" in st.session_state:
        st.subheader("🧠 Diagnostic IA - Root Cause Analysis")
        if st.button("🚀 Lancer l'Audit Intelligent", use_container_width=True, type="primary"):
            df = st.session_state.df_reclam_analysed
            # Préparer un résumé pour l'IA
            summary = df.groupby(['commercial', 'categorie_motif']).size().reset_index(name='count').to_dict('records')
            
            prompt = f"""Tu es un consultant expert en excellence opérationnelle pharmaceutique.
            Voici les données de réclamations de la période : {summary[:30]}.
            Analyse spécifiquement :
            1. Quels commerciaux ont le plus de comportements à risque (ventes forcées, erreurs de saisie) ?
            2. La balance entre Erreur Commerciale vs Erreur Dépôt.
            3. Propose 3 mesures correctives concrètes (ex: blocage de commande, formation dosage, double contrôle).
            Sois percutant, utilise des emojis et structure ta réponse."""
            
            with st.spinner("L'IA examine les motifs et les acteurs..."):
                report = ask_ai(prompt)
                st.success("Audit IA Terminé")
                st.markdown(report)
    else:
        st.info("Activez l'IA ou importez des données pour accéder à l'audit.")
