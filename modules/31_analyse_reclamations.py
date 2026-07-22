import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION ---
RECLAM_WORKSHEET = "reclamation"
RECLAM_FALLBACK = "data/db_reclamations.csv"

# --- 2. CSS & STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    body {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .reclam-title {
        font-family: 'Sora', sans-serif;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        margin-bottom: 0.1rem;
    }
    
    .reclam-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 400;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        margin-bottom: 15px;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 20px 45px rgba(99, 102, 241, 0.15);
    }
    .metric-val {
        font-family: 'Sora', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        margin: 5px 0;
        background: linear-gradient(90deg, #ffffff, #e2e8f0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-val-vibrant {
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.75rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .metric-desc {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 5px;
        font-weight: 500;
    }
    
    .reclam-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.3), rgba(15, 23, 42, 0.3));
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }
    
    .alert-card {
        background: rgba(239, 68, 68, 0.05);
        border-left: 5px solid #ef4444;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        border-top: 1px solid rgba(239, 68, 68, 0.1);
        border-right: 1px solid rgba(239, 68, 68, 0.1);
        border-bottom: 1px solid rgba(239, 68, 68, 0.1);
    }
    
    .success-card {
        background: rgba(16, 185, 129, 0.05);
        border-left: 5px solid #10b981;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        border-top: 1px solid rgba(16, 185, 129, 0.1);
        border-right: 1px solid rgba(16, 185, 129, 0.1);
        border-bottom: 1px solid rgba(16, 185, 129, 0.1);
    }
    
    .info-card {
        background: rgba(99, 102, 241, 0.04);
        border-left: 5px solid #6366f1;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        border-top: 1px solid rgba(99, 102, 241, 0.08);
        border-right: 1px solid rgba(99, 102, 241, 0.08);
        border-bottom: 1px solid rgba(99, 102, 241, 0.08);
    }
    
    .ia-report {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.06) 0%, rgba(30, 41, 59, 0.02) 100%);
        border-left: 5px solid #7c3aed;
        padding: 30px;
        border-radius: 16px;
        color: #e2e8f0;
        line-height: 1.7;
        font-family: 'Plus Jakarta Sans', sans-serif;
        border: 1px solid rgba(124, 58, 237, 0.15);
    }

    /* === STATUS WORKFLOW === */
    .status-pipeline {
        display: flex;
        align-items: center;
        gap: 0;
        padding: 18px 0;
        margin-bottom: 20px;
    }
    .status-step {
        flex: 1;
        text-align: center;
        padding: 14px 8px;
        border-radius: 0;
        font-family: 'Sora', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        position: relative;
        transition: all 0.3s ease;
    }
    .status-step:first-child { border-radius: 14px 0 0 14px; }
    .status-step:last-child  { border-radius: 0 14px 14px 0; }
    .status-step.done {
        background: linear-gradient(135deg, #10b981, #059669);
        color: #ffffff;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    }
    .status-step.active {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #ffffff;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.45);
        transform: scaleY(1.06);
    }
    .status-step.pending {
        background: rgba(255,255,255,0.04);
        color: #64748b;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .status-step .step-icon { font-size: 1.4rem; display: block; margin-bottom: 4px; }
    .status-step .step-label { display: block; }
    .status-arrow {
        width: 0; height: 0;
        border-top: 22px solid transparent;
        border-bottom: 22px solid transparent;
        flex-shrink: 0;
    }
    .status-table-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .badge-valide   { background: rgba(234, 179, 8,  0.15); color: #eab308; border: 1px solid rgba(234,179,8,0.3); }
    .badge-imprime  { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }
    .badge-expedie  { background: rgba(249, 115, 22, 0.15); color: #f97316; border: 1px solid rgba(249,115,22,0.3); }
    .badge-cloturer { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
    .badge-encours  { background: rgba(100,116,139,  0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }
</style>
""", unsafe_allow_html=True)

# --- 3. UTILS & CATEGORISATION ---
def categorize_motif(motif_str):
    m = str(motif_str).upper()
    if any(k in m for k in ["COMMERCIAL", "SAISIE", "FORCE", "REVENU", "EXCUSE", "PRODUIT NON COMMANDE"]): 
        return "Erreur Commerciale"
    if any(k in m for k in ["PHARMACIEN", "DOSAGE", "FORME", "DCI", "MARQUE", "RETOUR CLIENT"]): 
        return "Erreur Pharmacien"
    if any(k in m for k in ["DEPOT", "PREPARATION", "BOITE", "PLUS", "MOIN", "QUANTITE", "MANQUE"]): 
        return "Erreur Dépôt"
    if any(k in m for k in ["PNC", "CONFORME", "VIGNETTE", "ABIMEE", "CASSEE", "DETERIORE", "PRODUIT ABIME"]): 
        return "PNC (Non Conforme)"
    if any(k in m for k in ["SUPERVISEUR", "MODIFICATION", "REFAIRE", "BON DEJA"]): 
        return "Erreur Superviseur"
    return "Autre / Non Classé"

def parse_date_robust(date_str):
    for fmt in ('%d-%m-%y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d %H:%M:%S'):
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            pass
    return pd.to_datetime(date_str, errors='coerce')

# --- 4. HEADER ---
st.markdown('<h1 class="reclam-title">🎯 Centre de Contrôle & Résolution des Réclamations</h1>', unsafe_allow_html=True)
st.markdown('<p class="reclam-subtitle">Auditez la performance, réduisez les litiges clients et pilotez les résolutions opérationnelles.</p>', unsafe_allow_html=True)

# Chargement permanent
df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK, None)

if df_db.empty:
    st.info("Aucune réclamation active ou historique trouvé dans la Data Centrale.")
    st.stop()

import unicodedata
def clean_col(c):
    c = str(c).strip().lower()
    return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')

df_db.columns = [clean_col(c) for c in df_db.columns]
st.session_state.df_reclam_analysed = df_db

if "df_reclam_analysed" in st.session_state:
    df_raw = st.session_state.df_reclam_analysed.copy()
    
    # Mapping des colonnes réelles (Valeur / Montant, Code Client, etc.)
    if 'code' in df_raw.columns and 'code_client' not in df_raw.columns: df_raw['code_client'] = df_raw['code']
    if 'categorie' in df_raw.columns and 'motif' not in df_raw.columns: df_raw['motif'] = df_raw['categorie']
    if 'categorie de reclamation' in df_raw.columns and 'motif' not in df_raw.columns: df_raw['motif'] = df_raw['categorie de reclamation']
    
    # Impact financier (Valeur / Montant)
    if 'valeur' in df_raw.columns and 'valeur_vente' not in df_raw.columns: df_raw['valeur_vente'] = df_raw['valeur']
    if 'montant' in df_raw.columns and 'valeur_vente' not in df_raw.columns: df_raw['valeur_vente'] = df_raw['montant']
    
    # Prétraitement
    for col, default_val in [
        ('motif', 'Non Renseigné'), ('commercial', 'Inconnu'), ('client', 'Inconnu'),
        ('produit', 'Inconnu'), ('region', 'Inconnu'), ('statut_bon', 'En Cours'), 
        ('statut', 'EN COURS'), ('date', ''), ('code_client', 'Inconnu'),
        ('date_exp', ''), ('prix_vente', 0.0), ('remarque_ligne', ''),
        ('cree_par', 'Inconnu'), ('date_creation', ''), ('ref_facture', ''),
        ('date_facture', ''), ('reponse', ''), ('reference', 'Inconnu')
    ]:
        if col not in df_raw.columns:
            df_raw[col] = default_val
            
    df_raw['motif'] = df_raw['motif'].fillna("Non Renseigné").astype(str)
    df_raw['categorie_motif'] = df_raw['motif'].apply(categorize_motif)
    df_raw['commercial'] = df_raw['commercial'].fillna("Inconnu").astype(str)
    df_raw['client'] = df_raw['client'].fillna("Inconnu").astype(str)
    df_raw['code_client'] = df_raw['code_client'].fillna("Inconnu").astype(str)
    df_raw['reponse'] = df_raw['reponse'].fillna("").astype(str)
    df_raw['reference'] = df_raw['reference'].fillna("Inconnu").astype(str)
    df_raw['date_exp'] = df_raw['date_exp'].fillna("").astype(str)
    df_raw['remarque_ligne'] = df_raw['remarque_ligne'].fillna("").astype(str)
    df_raw['cree_par'] = df_raw['cree_par'].fillna("Inconnu").astype(str)
    df_raw['date_creation'] = df_raw['date_creation'].fillna("").astype(str)
    df_raw['ref_facture'] = df_raw['ref_facture'].fillna("").astype(str)
    df_raw['date_facture'] = df_raw['date_facture'].fillna("").astype(str)
    df_raw['prix_vente'] = pd.to_numeric(df_raw['prix_vente'], errors='coerce').fillna(0.0)
    df_raw['produit'] = df_raw['produit'].fillna("Inconnu").astype(str)
    df_raw['region'] = df_raw['region'].fillna("Inconnu").astype(str)
    df_raw['preparateur'] = df_raw.get('preparateur', df_raw.get('preparateurs', pd.Series(['Inconnu']*len(df_raw)))).fillna("Inconnu").astype(str)
    df_raw['lot'] = df_raw.get('lot', pd.Series(['Inconnu']*len(df_raw))).fillna("Inconnu").astype(str)
    df_raw['frigo'] = df_raw.get('frigo', pd.Series(['Non']*len(df_raw))).fillna("Non").astype(str)
    df_raw['psycho'] = df_raw.get('psycho', pd.Series(['Non']*len(df_raw))).fillna("Non").astype(str)
    df_raw['chere'] = df_raw.get('chere', pd.Series(['Non']*len(df_raw))).fillna("Non").astype(str)
    df_raw['zone_produit'] = df_raw.get('zone_produit', pd.Series(['Inconnu']*len(df_raw))).fillna("Inconnu").astype(str)
    df_raw['quantite'] = pd.to_numeric(df_raw.get('quantite', df_raw.get('qte_reclam', pd.Series([0]*len(df_raw)))), errors='coerce').fillna(0).astype(int)
    
    if 'valeur_vente' not in df_raw.columns: df_raw['valeur_vente'] = 0.0
    df_raw['valeur_vente'] = pd.to_numeric(df_raw['valeur_vente'], errors='coerce').fillna(0.0)
    
    if 'cout_revient' not in df_raw.columns: df_raw['cout_revient'] = 0.0
    df_raw['cout_revient'] = pd.to_numeric(df_raw['cout_revient'], errors='coerce').fillna(0.0)
    
    if 'delai_reclam' not in df_raw.columns: df_raw['delai_reclam'] = 0
    df_raw['delai_reclam'] = pd.to_numeric(df_raw['delai_reclam'], errors='coerce')
    
    if 'nbr_jours' not in df_raw.columns: df_raw['nbr_jours'] = 0
    df_raw['nbr_jours'] = pd.to_numeric(df_raw['nbr_jours'], errors='coerce')
    
    df_raw['statut_bon'] = df_raw['statut_bon'].fillna("En Cours").astype(str)
    df_raw['statut'] = df_raw['statut'].fillna("EN COURS").astype(str)
    df_raw['datetime_parsed'] = df_raw['date'].apply(parse_date_robust)

    # --- FILTRES EN BARRE LATÉRALE ---
    st.sidebar.markdown("### 🎛️ Filtres Globaux")
    
    # Filtres régionaux
    regions = ["Toutes"] + sorted(df_raw['region'].unique().tolist())
    selected_region = st.sidebar.selectbox("Région :", regions)
    
    # Filtres commerciaux
    commerciaux = ["Tous"] + sorted(df_raw['commercial'].unique().tolist())
    selected_comm = st.sidebar.selectbox("Commercial :", commerciaux)
    
    # Filtres Motifs
    motifs = ["Tous"] + sorted(df_raw['categorie_motif'].unique().tolist())
    selected_motif = st.sidebar.selectbox("Catégorie Motif :", motifs)
    
    # Filtres Produits Spécifiques
    frigo_filter = st.sidebar.checkbox("❄️ Produits Frigo uniquement", value=False)
    psycho_filter = st.sidebar.checkbox("💊 Psychotropes uniquement", value=False)
    chere_filter = st.sidebar.checkbox("💎 Produits Chers uniquement", value=False)
    
    # Appliquer le filtrage
    df_filtered = df_raw.copy()
    if selected_region != "Toutes":
        df_filtered = df_filtered[df_filtered['region'] == selected_region]
    if selected_comm != "Tous":
        df_filtered = df_filtered[df_filtered['commercial'] == selected_comm]
    if selected_motif != "Tous":
        df_filtered = df_filtered[df_filtered['categorie_motif'] == selected_motif]
    if frigo_filter:
        df_filtered = df_filtered[df_filtered['frigo'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)]
    if psycho_filter:
        df_filtered = df_filtered[df_filtered['psycho'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)]
    if chere_filter:
        df_filtered = df_filtered[df_filtered['chere'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)]

    # --- TABS SYSTEM ---
    tabs = st.tabs([
        "📊 Analyses & KPIs",
        "🚨 Audit & Alertes",
        "⚙️ Centre de Résolution",
        "🔄 Gestion des Statuts",
        "🔍 Profiling & Détails",
        "🧠 Diagnostic IA Expert"
    ])

    # ----------------- TAB 1 : ANALYSES & KPIS -----------------
    with tabs[0]:
        # Calculs KPIs
        total_claims = len(df_filtered)
        valeur_vente_totale = df_filtered['valeur_vente'].sum()
        cout_revient_total = df_filtered['cout_revient'].sum()
        marge_perdue = valeur_vente_totale - cout_revient_total
        
        avg_delai_resol = df_filtered[df_filtered['delai_reclam'].notna()]['delai_reclam'].mean()
        avg_nbr_jours = df_filtered[df_filtered['nbr_jours'].notna()]['nbr_jours'].mean()
        
        # Grid KPIs
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        
        with kpi_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📋 Réclamations</div>
                <div class="metric-val">{total_claims}</div>
                <div class="metric-desc">Total des dossiers filtrés</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💸 Impact Financier</div>
                <div class="metric-val-vibrant metric-val">{valeur_vente_totale:,.2f} DA</div>
                <div class="metric-desc">Valeur de vente totale</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📉 Coût Interne (Revient)</div>
                <div class="metric-val" style="color: #ef4444;">{cout_revient_total:,.2f} DA</div>
                <div class="metric-desc">Pertes brutes de production</div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_col4:
            res_val = f"{avg_delai_resol:.1f} j" if not pd.isna(avg_delai_resol) else "N/A"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚡ Délai de Clôture</div>
                <div class="metric-val" style="color: #10b981;">{res_val}</div>
                <div class="metric-desc">Temps moyen de résolution</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 🍩 Cartographie Opérationnelle")
        col_g1, col_g2 = st.columns([1, 1])
        
        with col_g1:
            st.markdown("#### Hiérarchie et Origine des Litiges")
            if not df_filtered.empty:
                df_p_plot = df_filtered.copy()
                df_p_plot['motif_plot'] = df_p_plot['motif'].astype(str) + " "
                fig_sun = px.sunburst(df_p_plot, path=['categorie_motif', 'motif_plot'], 
                                     color_discrete_sequence=px.colors.qualitative.Bold,
                                     values='valeur_vente')
                fig_sun.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=420, margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig_sun, use_container_width=True)
            else:
                st.info("Aucune donnée disponible pour tracer le graphique.")
                
        with col_g2:
            st.markdown("#### Pertes par Catégorie de Motif")
            if not df_filtered.empty:
                df_loss_cat = df_filtered.groupby('categorie_motif').agg({'valeur_vente': 'sum', 'reference': 'count'}).reset_index()
                df_loss_cat.columns = ['Motif', 'Valeur', 'Nb']
                fig_bar = px.bar(df_loss_cat, x='Motif', y='Valeur', text='Nb',
                                color='Valeur', color_continuous_scale='Purples',
                                labels={'Valeur': 'Valeur (DA)', 'Nb': 'Nombre'})
                fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=420, margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Aucune donnée.")

        st.markdown("### 🗺️ Répartition Géographique & Zones Logistiques")
        col_g3, col_g4 = st.columns([1, 1])
        
        with col_g3:
            st.markdown("#### Volume Financier des Réclamations par Région")
            if not df_filtered.empty:
                df_reg = df_filtered.groupby('region')['valeur_vente'].sum().reset_index()
                fig_pie = px.pie(df_reg, values='valeur_vente', names='region', hole=0.4,
                                 color_discrete_sequence=px.colors.sequential.Plasma_r)
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380, margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Aucune donnée.")
                
        with col_g4:
            st.markdown("#### Zones Produits Affectées (Localisation Dépôt)")
            if not df_filtered.empty:
                df_zone = df_filtered.groupby('zone_produit').agg({'quantite': 'sum', 'valeur_vente': 'sum'}).reset_index()
                fig_zone = px.bar(df_zone, x='zone_produit', y='valeur_vente', color='quantite',
                                  labels={'zone_produit': 'Zone', 'valeur_vente': 'Valeur de Vente (DA)', 'quantite': 'Unités'},
                                  color_continuous_scale='Reds')
                fig_zone.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380, margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(fig_zone, use_container_width=True)
            else:
                st.info("Aucune donnée.")

        st.markdown("### 📊 Matrice d'Impact : Commerciaux vs Catégorie d'Erreur")
        if not df_filtered.empty and 'commercial' in df_filtered.columns and 'categorie_motif' in df_filtered.columns:
            pivot = df_filtered.groupby(['commercial', 'categorie_motif']).size().unstack(fill_value=0)
            if not pivot.empty:
                fig_heat = px.imshow(pivot, text_auto=True, color_continuous_scale='YlOrRd')
                fig_heat.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450)
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("Matrice vide.")
        else:
            st.info("Données insuffisantes pour la matrice.")

    # ----------------- TAB 2 : AUDIT & ALERTES -----------------
    with tabs[1]:
        st.markdown("### 🚨 Système d'Alerte et d'Audit Qualité")
        st.write("Ce panneau identifie les faiblesses logistiques récurrentes, les anomalies commerciales et les risques de chaîne du froid ou de réglementation.")
        
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("#### 👤 Alerte Tolérance Commerciale (Max 5 Erreurs)")
            err_by_comm = df_raw[df_raw['categorie_motif'] == "Erreur Commerciale"].groupby('commercial').size().reset_index(name='Nb_Erreurs')
            over_limit = err_by_comm[err_by_comm['Nb_Erreurs'] > 5]
            
            if not over_limit.empty:
                for _, row in over_limit.iterrows():
                    st.markdown(f"""
                    <div class="alert-card">
                        ⚠️ <b>{row['commercial']}</b> a dépassé la limite de tolérance !<br>
                        <b>{row['Nb_Erreurs']} erreurs commerciales</b> enregistrées. Un recadrage ou une double vérification est requis lors de la saisie de ses commandes.
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="success-card">
                    ✅ Aucun commercial ne dépasse la limite de tolérance des 5 erreurs.
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("#### 📦 Audit Dépôt (Erreurs Préparateurs / Manques)")
            # Auditer les préparateurs
            df_depot_errors = df_raw[df_raw['categorie_motif'] == "Erreur Dépôt"]
            if not df_depot_errors.empty:
                prep_stats = df_depot_errors.groupby('preparateur').agg({'reference': 'count', 'valeur_vente': 'sum'}).reset_index()
                prep_stats.columns = ['Préparateur', 'Nombre Erreurs', 'Valeur Perdue (DA)']
                prep_stats = prep_stats.sort_values(by='Nombre Erreurs', ascending=False)
                
                st.write("Classement des erreurs de préparation par agent de dépôt :")
                st.dataframe(prep_stats, use_container_width=True, hide_index=True)
                
                critical_prep = prep_stats[prep_stats['Nombre Erreurs'] >= 2]
                if not critical_prep.empty:
                    st.warning(f"⚠️ {len(critical_prep)} préparateur(s) ont commis au moins 2 erreurs de préparation. Une vérification au scan de leurs colis est recommandée.")
            else:
                st.success("✅ Aucune erreur de préparation détectée sur la période.")

        with col_a2:
            st.markdown("#### ❄️ Alerte Qualité Chaîne du Froid")
            df_cold = df_raw[(df_raw['frigo'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)) & (df_raw['statut_bon'].astype(str).str.upper() != "CLOTURER")]
            if not df_cold.empty:
                st.markdown(f"""
                <div class="alert-card" style="background: rgba(59, 130, 246, 0.05); border-left-color: #3b82f6;">
                    ❄️ <b>{len(df_cold)} réclamations frigo en cours !</b><br>
                    Les produits réfrigérés nécessitent une attention immédiate pour éviter la rupture de la chaîne du froid.
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(df_cold[['reference', 'client', 'produit', 'quantite', 'zone_produit', 'preparateur']], use_container_width=True, hide_index=True)
            else:
                st.markdown("""
                <div class="success-card" style="background: rgba(59, 130, 246, 0.05); border-left-color: #3b82f6;">
                    ❄️ Aucun litige frigo actif. Chaîne du froid sous contrôle.
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("#### 💊 Risque Réglementaire (Psychotropes)")
            df_psy = df_raw[(df_raw['psycho'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False))]
            if not df_psy.empty:
                st.markdown(f"""
                <div class="alert-card" style="background: rgba(139, 92, 246, 0.05); border-left-color: #8b5cf6;">
                    ⚠️ <b>{len(df_psy)} litiges sur des produits psychotropes !</b><br>
                    Ces produits sont soumis à des contrôles stricts du ministère de la santé. Chaque réclamation doit faire l'objet d'un rapport écrit du Pharmacien Directeur Technique (DT).
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(df_psy[['reference', 'date', 'client', 'produit', 'quantite', 'statut']], use_container_width=True, hide_index=True)
            else:
                st.success("✅ Aucun litige sur les psychotropes.")
                
            st.markdown("#### 🏷️ Alerte Anomalie Lot (Suspicion Rappel/Qualité)")
            # Identifier si un lot a plus d'une réclamation de type PNC
            df_pnc = df_raw[df_raw['categorie_motif'] == "PNC (Non Conforme)"]
            if not df_pnc.empty:
                lot_stats = df_pnc.groupby('lot').size().reset_index(name='Nb_PNC')
                critical_lots = lot_stats[(lot_stats['lot'] != 'Inconnu') & (lot_stats['Nb_PNC'] >= 2)]
                
                if not critical_lots.empty:
                    for _, row in critical_lots.iterrows():
                        st.markdown(f"""
                        <div class="alert-card">
                            🏷️ <b>Lot suspect : {row['lot']}</b> présente {row['Nb_PNC']} anomalies de non-conformité (PNC) !<br>
                            Il est fortement conseillé de mettre ce lot en quarantaine pour inspection physique.
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.success("✅ Aucun lot ne présente de non-conformités multiples.")
            else:
                st.success("✅ Aucun produit non conforme signalé.")

    # === HELPER : STATUS WORKFLOW ===
    STATUS_PIPELINE = ["VALIDE", "IMPRIME", "EXPEDIE", "CLOTURER"]
    STATUS_ICONS    = {"VALIDE": "✅", "IMPRIME": "🖨️", "EXPEDIE": "🚚", "CLOTURER": "🔒"}
    STATUS_COLORS   = {"VALIDE": "#eab308", "IMPRIME": "#3b82f6", "EXPEDIE": "#f97316", "CLOTURER": "#10b981"}
    STATUS_BADGE    = {"VALIDE": "badge-valide", "IMPRIME": "badge-imprime", "EXPEDIE": "badge-expedie", "CLOTURER": "badge-cloturer"}

    def render_status_pipeline(current_status):
        """Render a visual 4-step status progression bar."""
        cur = str(current_status).upper().strip()
        try:
            cur_idx = STATUS_PIPELINE.index(cur)
        except ValueError:
            cur_idx = -1  # En Cours / Autre

        steps_html = ""
        for i, step in enumerate(STATUS_PIPELINE):
            if i < cur_idx:
                cls = "done"
            elif i == cur_idx:
                cls = "active"
            else:
                cls = "pending"
            icon = STATUS_ICONS[step]
            steps_html += f'<div class="status-step {cls}"><span class="step-icon">{icon}</span><span class="step-label">{step}</span></div>'

        st.markdown(f'<div class="status-pipeline">{steps_html}</div>', unsafe_allow_html=True)

    def advance_status(current_status):
        """Return the next status in the pipeline."""
        cur = str(current_status).upper().strip()
        try:
            idx = STATUS_PIPELINE.index(cur)
            if idx < len(STATUS_PIPELINE) - 1:
                return STATUS_PIPELINE[idx + 1]
        except ValueError:
            pass
        return current_status  # Already at last step or unknown

    def save_status_change(ref, produit_val, new_status):
        """Load DB, update statut_bon for the matching row, save back."""
        df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
        mask = (df_db['reference'] == ref) & (df_db['produit'] == produit_val)
        if mask.any():
            today_str = datetime.now().strftime("%d-%m-%y %H:%M:%S")
            df_db.loc[mask, 'statut_bon'] = new_status
            if new_status == "CLOTURER":
                df_db.loc[mask, 'date_cloture'] = today_str
                df_db.loc[mask, 'cloturer_par'] = st.session_state.current_user['username']
                # Auto-calculate delai if not set
                existing_delai = df_db.loc[mask, 'delai_reclam'].values[0]
                if pd.isna(existing_delai) or str(existing_delai).strip() in ["", "nan"]:
                    claim_date = parse_date_robust(df_db.loc[mask, 'date'].values[0])
                    duration = max(0, (datetime.now() - claim_date).days) if not pd.isna(claim_date) else 0
                    df_db.loc[mask, 'delai_reclam'] = float(duration)
            save_gs_data(df_db, RECLAM_WORKSHEET, RECLAM_FALLBACK)
            st.session_state.df_reclam_analysed = df_db
            return True
        return False

    # ----------------- TAB 3 : CENTRE DE RÉSOLUTION -----------------
    with tabs[2]:
        st.markdown("### ⚙️ Gestion des Résolutions & Clôtures")
        st.write("Sélectionnez une réclamation active pour statuer, rédiger la réponse officielle et clôturer le dossier.")

        # Filtre sur les dossiers non clôturés
        df_active = df_raw[df_raw['statut_bon'].astype(str).str.upper() != "CLOTURER"]

        if df_active.empty:
            st.markdown("""
            <div class="success-card">
                🎉 Félicitations ! Toutes les réclamations clients ont été résolues et clôturées !
            </div>
            """, unsafe_allow_html=True)
        else:
            active_refs = sorted(df_active['reference'].unique().tolist())
            col_sel, col_empty = st.columns([2, 2])
            selected_ref = col_sel.selectbox("Choisir le dossier réclamation à traiter :", active_refs)

            if selected_ref:
                claim_rows = df_active[df_active['reference'] == selected_ref]

                for idx, row in claim_rows.iterrows():
                    st.markdown(f"""
                    <div class="info-card">
                        <h4>📋 Fiche Réclamation : {row['reference']} (Date : {row['date']})</h4>
                        <p><b>Client :</b> {row['client']} (Région : {row['region']}) | <b>Code Client :</b> {row['code_client']}</p>
                        <p><b>Produit :</b> {row['produit']} (Lot : {row['lot']} | Exp : {row['date_exp']})</p>
                        <p><b>Détail financier :</b> Quantité : {row['quantite']} | Prix U : {row['prix_vente']:.2f} DA | Valeur Vente : {row['valeur_vente']:.2f} DA | Coût Revient : {row['cout_revient']:.2f} DA</p>
                        <p><b>Motif déclaré :</b> <span style="color:#ef4444; font-weight:bold;">{row['motif']} ({row['categorie_motif']})</span></p>
                        <p><b>Remarque saisie :</b> <i>{row['remarque_ligne']}</i></p>
                        <p><b>Créé par :</b> {row['cree_par']} le {row['date_creation']} | <b>Facture d'origine :</b> {row['ref_facture']} du {row['date_facture']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # --- STATUS PIPELINE VISUAL ---
                    st.markdown("##### 🔄 Avancement du Dossier")
                    render_status_pipeline(row['statut_bon'])

                    # --- ONE-CLICK STATUS BUTTONS ---
                    cur_stat = str(row['statut_bon']).upper().strip()
                    btn_cols = st.columns(4)
                    for si, s_step in enumerate(STATUS_PIPELINE):
                        btn_label = f"{STATUS_ICONS[s_step]} {s_step}"
                        is_current = (cur_stat == s_step)
                        is_past    = STATUS_PIPELINE.index(s_step) < STATUS_PIPELINE.index(cur_stat) if cur_stat in STATUS_PIPELINE else False
                        btn_type   = "primary" if is_current else "secondary"
                        btn_disabled = is_past  # Can't go back
                        with btn_cols[si]:
                            if st.button(
                                btn_label,
                                key=f"stat_btn_{idx}_{s_step}",
                                type=btn_type,
                                disabled=btn_disabled,
                                use_container_width=True
                            ):
                                if not is_current:
                                    if save_status_change(row['reference'], row['produit'], s_step):
                                        st.success(f"✅ Statut mis à jour → **{s_step}**")
                                        st.rerun()
                                    else:
                                        st.error("Erreur lors de la mise à jour du statut.")

                    st.markdown("---")

                    with st.form(f"resolve_form_{idx}"):
                        st.markdown("##### 📝 Statuer sur le dossier (Résolution complète)")
                        col_form1, col_form2 = st.columns(2)

                        action_type = col_form1.selectbox("Décision / Action Corrective :", [
                            "Avoir Financier (Ajustement)",
                            "Remplacement Produit",
                            "Retour Stock (Produit conforme reconditionné)",
                            "Destruction Lot (Produit déterioré)",
                            "Avertissement Commercial (Forçage de vente)",
                            "Avertissement Dépôt (Erreur préparation)",
                            "Réclamation Rejetée (Litige infondé / Abus)"
                        ])

                        responsible_dept = col_form2.selectbox("Attribuer la responsabilité :", [
                            "Commercial (Saisie/Vente)",
                            "Dépôt (Préparation/Logistique)",
                            "Livreur (Expédition)",
                            "Client (Erreur de commande/commande ferme)"
                        ])

                        avis_dt_text = st.text_area("Avis du Directeur Technique / DT (Obligatoire pour avoir/remboursement) :", value=str(row.get('avis_dt', '')))
                        reponse_text = st.text_area("Réponse officielle transmise au client (Sera visible sur son bon) :", value=str(row.get('reponse', '')))

                        col_form3, col_form4 = st.columns(2)
                        verifier_par_val = col_form3.text_input("Vérifié et validé par :", value=st.session_state.current_user['username'])
                        statut_final = col_form4.selectbox("Statut final de conformité :", ["ACCEPTE", "REFUSE"])

                        if st.form_submit_button("💾 ENREGISTRER LA RÉSOLUTION & CLÔTURER LE LITIGE", type="primary", use_container_width=True):
                            df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
                            mask = (df_db['reference'] == row['reference']) & (df_db['produit'] == row['produit'])

                            if mask.any():
                                today = datetime.now()
                                claim_date = parse_date_robust(row['date'])
                                duration = (today - claim_date).days if not pd.isna(claim_date) else 1
                                if duration < 0:
                                    duration = 0

                                df_db.loc[mask, 'statut_bon'] = "CLOTURER"
                                df_db.loc[mask, 'statut'] = statut_final
                                df_db.loc[mask, 'reponse'] = reponse_text
                                df_db.loc[mask, 'avis_dt'] = avis_dt_text
                                df_db.loc[mask, 'verifier_par'] = verifier_par_val
                                df_db.loc[mask, 'responsable'] = responsible_dept
                                df_db.loc[mask, 'delai_reclam'] = float(duration)
                                df_db.loc[mask, 'date_cloture'] = today.strftime("%d-%m-%y %H:%M:%S")
                                df_db.loc[mask, 'cloturer_par'] = st.session_state.current_user['username']
                                df_db.loc[mask, 'offre'] = action_type

                                save_gs_data(df_db, RECLAM_WORKSHEET, RECLAM_FALLBACK)
                                st.session_state.df_reclam_analysed = df_db

                                st.success("🎉 Réclamation clôturée et synchronisée avec succès !")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Ligne introuvable lors de l'enregistrement.")

    # ----------------- TAB 4 : GESTION DES STATUTS -----------------
    with tabs[3]:
        st.markdown("### 🔄 Tableau de Bord — Gestion des Statuts")
        st.write("Visualisez et mettez à jour le statut de traitement de chaque réclamation : **VALIDE → IMPRIME → EXPEDIE → CLOTURER**.")

        # --- KPIs Statuts ---
        kpi_s1, kpi_s2, kpi_s3, kpi_s4, kpi_s5 = st.columns(5)
        total_r    = len(df_raw)
        nb_valide  = len(df_raw[df_raw['statut_bon'].astype(str).str.upper() == "VALIDE"])
        nb_imprime = len(df_raw[df_raw['statut_bon'].astype(str).str.upper() == "IMPRIME"])
        nb_expedie = len(df_raw[df_raw['statut_bon'].astype(str).str.upper() == "EXPEDIE"])
        nb_clot    = len(df_raw[df_raw['statut_bon'].astype(str).str.upper() == "CLOTURER"])
        nb_other   = total_r - nb_valide - nb_imprime - nb_expedie - nb_clot

        with kpi_s1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">📋 Total</div><div class="metric-val">{total_r}</div><div class="metric-desc">Réclamations</div></div>', unsafe_allow_html=True)
        with kpi_s2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">✅ Validé</div><div class="metric-val" style="color:#eab308">{nb_valide}</div><div class="metric-desc">Bons validés</div></div>', unsafe_allow_html=True)
        with kpi_s3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">🖨️ Imprimé</div><div class="metric-val" style="color:#3b82f6">{nb_imprime}</div><div class="metric-desc">Bons imprimés</div></div>', unsafe_allow_html=True)
        with kpi_s4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">🚚 Expédié</div><div class="metric-val" style="color:#f97316">{nb_expedie}</div><div class="metric-desc">Envoyés client</div></div>', unsafe_allow_html=True)
        with kpi_s5:
            st.markdown(f'<div class="metric-card"><div class="metric-label">🔒 Clôturé</div><div class="metric-val" style="color:#10b981">{nb_clot}</div><div class="metric-desc">Dossiers fermés</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # --- Filtre statut ---
        col_fs1, col_fs2, col_fs3 = st.columns([2, 2, 2])
        filter_stat = col_fs1.selectbox(
            "Filtrer par statut :",
            ["Tous", "En Cours / Autre", "VALIDE", "IMPRIME", "EXPEDIE", "CLOTURER"],
            key="stat_tab_filter"
        )
        search_ref = col_fs2.text_input("Rechercher par référence :", placeholder="26/RC000...", key="stat_search_ref")
        search_cli = col_fs3.text_input("Rechercher par client :", placeholder="Nom client...", key="stat_search_cli")

        df_stat_view = df_raw.copy()
        if filter_stat == "En Cours / Autre":
            df_stat_view = df_stat_view[~df_stat_view['statut_bon'].astype(str).str.upper().isin(STATUS_PIPELINE)]
        elif filter_stat != "Tous":
            df_stat_view = df_stat_view[df_stat_view['statut_bon'].astype(str).str.upper() == filter_stat]
        if search_ref:
            df_stat_view = df_stat_view[df_stat_view['reference'].astype(str).str.contains(search_ref, case=False, na=False)]
        if search_cli:
            df_stat_view = df_stat_view[df_stat_view['client'].astype(str).str.contains(search_cli, case=False, na=False)]

        st.markdown(f"**{len(df_stat_view)} dossier(s) affichés**")

        # --- Tableau interactif avec boutons de statut ---
        if df_stat_view.empty:
            st.info("Aucune réclamation ne correspond aux critères de filtrage.")
        else:
            # Column header
            hdr = st.columns([1.8, 2.5, 1.5, 1.5, 1.3, 1.3, 1.3, 1.3])
            for h, t in zip(hdr, ["📋 Référence", "👤 Client", "💊 Produit (court)", "📅 Date", "✅ VALIDE", "🖨️ IMPRIME", "🚚 EXPEDIE", "🔒 CLOTURER"]):
                h.markdown(f"**{t}**")

            st.markdown("<hr style='margin:4px 0; opacity:0.15;'>", unsafe_allow_html=True)

            for tbl_idx, tbl_row in df_stat_view.iterrows():
                cur_s = str(tbl_row['statut_bon']).upper().strip()
                try:
                    cur_s_idx = STATUS_PIPELINE.index(cur_s)
                except ValueError:
                    cur_s_idx = -1

                row_cols = st.columns([1.8, 2.5, 1.5, 1.5, 1.3, 1.3, 1.3, 1.3])
                row_cols[0].markdown(f"<small><b>{tbl_row['reference']}</b></small>", unsafe_allow_html=True)
                row_cols[1].markdown(f"<small>{tbl_row['client'][:28]}</small>", unsafe_allow_html=True)
                row_cols[2].markdown(f"<small>{str(tbl_row['produit'])[:22]}</small>", unsafe_allow_html=True)
                row_cols[3].markdown(f"<small>{tbl_row['date']}</small>", unsafe_allow_html=True)

                for si, s_step in enumerate(STATUS_PIPELINE):
                    step_idx = STATUS_PIPELINE.index(s_step)
                    is_done    = step_idx < cur_s_idx
                    is_active  = step_idx == cur_s_idx
                    is_past    = step_idx < cur_s_idx

                    if is_done:
                        # Already completed – show green tick, not interactive
                        row_cols[4 + si].markdown(f"<div style='text-align:center; color:#10b981; font-size:1.2rem;'>✔</div>", unsafe_allow_html=True)
                    elif is_active:
                        # Current step – highlight button
                        row_cols[4 + si].markdown(f"<div style='text-align:center; color:{STATUS_COLORS[s_step]}; font-weight:bold; font-size:0.8rem;'>● {s_step}</div>", unsafe_allow_html=True)
                    else:
                        # Upcoming step – clickable button to advance
                        if row_cols[4 + si].button(
                            f"→ {s_step}",
                            key=f"tbl_stat_{tbl_idx}_{s_step}",
                            use_container_width=True
                        ):
                            if save_status_change(tbl_row['reference'], tbl_row['produit'], s_step):
                                st.success(f"✅ **{tbl_row['reference']}** → {s_step}")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la mise à jour.")

                st.markdown("<hr style='margin:3px 0; opacity:0.08;'>", unsafe_allow_html=True)

        # --- Mise à jour groupée ---
        st.markdown("---")
        st.markdown("#### 🔁 Mise à Jour Groupée (Sélection Multiple)")
        st.write("Vous pouvez saisir plusieurs références séparées par des virgules et leur appliquer un statut en masse.")

        col_bulk1, col_bulk2, col_bulk3 = st.columns([3, 2, 1])
        bulk_refs_input = col_bulk1.text_input("Références (ex: 26/RC0000000144, 26/RC0000000146) :", key="bulk_refs")
        bulk_status_sel = col_bulk2.selectbox("Nouveau statut :", STATUS_PIPELINE, key="bulk_status")

        if col_bulk3.button("⚡ Appliquer", type="primary", use_container_width=True, key="bulk_apply_btn"):
            if bulk_refs_input.strip():
                refs_to_update = [r.strip() for r in bulk_refs_input.split(",") if r.strip()]
                df_db_bulk = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
                updated_count = 0
                for ref_bulk in refs_to_update:
                    mask_bulk = df_db_bulk['reference'] == ref_bulk
                    if mask_bulk.any():
                        df_db_bulk.loc[mask_bulk, 'statut_bon'] = bulk_status_sel
                        if bulk_status_sel == "CLOTURER":
                            df_db_bulk.loc[mask_bulk, 'date_cloture'] = datetime.now().strftime("%d-%m-%y %H:%M:%S")
                            df_db_bulk.loc[mask_bulk, 'cloturer_par'] = st.session_state.current_user['username']
                        updated_count += mask_bulk.sum()
                save_gs_data(df_db_bulk, RECLAM_WORKSHEET, RECLAM_FALLBACK)
                st.session_state.df_reclam_analysed = df_db_bulk
                st.success(f"✅ {updated_count} ligne(s) mise(s) à jour avec le statut **{bulk_status_sel}** !")
                st.rerun()
            else:
                st.warning("Veuillez saisir au moins une référence.")

    # ----------------- TAB 5 : PROFILING CLIENT & PRODUIT -----------------
    with tabs[4]:
        st.markdown("### 🔍 Profiling Approfondi des Anomalies")
        
        prof_opt = st.radio("Cible de l'audit :", ["Par Client (CRM)", "Par Produit / Lot"], horizontal=True)
        
        if prof_opt == "Par Client (CRM)":
            clients_list = sorted(df_raw['client'].unique().tolist())
            selected_client = st.selectbox("Choisir le client à auditer :", clients_list)
            
            if selected_client:
                df_client = df_raw[df_raw['client'] == selected_client]
                
                c_val = df_client['valeur_vente'].sum()
                c_nb = len(df_client)
                c_pnc = len(df_client[df_client['categorie_motif'] == "PNC (Non Conforme)"])
                c_comm = len(df_client[df_client['categorie_motif'] == "Erreur Commerciale"])
                c_depot = len(df_client[df_client['categorie_motif'] == "Erreur Dépôt"])
                
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Nombre de Litiges", c_nb)
                col_p2.metric("Valeur Totale Réclamée", f"{c_val:,.2f} DA")
                col_p3.metric("Erreurs Commerciales Subies", c_comm)
                
                col_p4, col_p5 = st.columns(2)
                col_p4.metric("Non-Conformités Reçues (PNC)", c_pnc)
                col_p5.metric("Erreurs Dépôt Subies (Manques)", c_depot)
                
                # Alerte comportement suspect (ex: trop de réclamations PNC ou manque)
                if c_nb >= 3:
                    st.warning("⚠️ **Alerte comportement/Logistique** : Ce client a émis au moins 3 réclamations. Vérifiez l'historique ci-dessous pour voir s'il y a suspicion d'abus ou si la livraison de son secteur a un problème structurel.")
                
                st.markdown("#### Historique complet du client")
                st.dataframe(df_client[['date', 'produit', 'quantite', 'valeur_vente', 'motif', 'statut', 'cree_par', 'preparateur', 'reponse']], use_container_width=True, hide_index=True)
                
        else:
            products_list = sorted(df_raw['produit'].unique().tolist())
            selected_prod = st.selectbox("Choisir le produit à auditer :", products_list)
            
            if selected_prod:
                df_prod = df_raw[df_raw['produit'] == selected_prod]
                
                p_val = df_prod['valeur_vente'].sum()
                p_qty = df_prod['quantite'].sum()
                p_nb = len(df_prod)
                
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Occurrences de Litige", p_nb)
                col_p2.metric("Quantité Totale Réclamée", p_qty)
                col_p3.metric("Impact Financier", f"{p_val:,.2f} DA")
                
                st.markdown("#### Lots et préparateurs concernés par le produit")
                st.dataframe(df_prod[['date', 'lot', 'date_exp', 'quantite', 'valeur_vente', 'preparateur', 'motif', 'statut_bon']], use_container_width=True, hide_index=True)

    # ----------------- TAB 6 : DIAGNOSTIC IA EXPERT -----------------
    with tabs[5]:
        st.subheader("🧠 Diagnostic Stratégique par Intelligence Artificielle (RCA)")
        st.write("L'IA va croiser en profondeur les variables (commerciaux, préparateurs, produits réfrigérés, motifs de retours) pour dégager des solutions logistiques concrètes.")
        
        # Choix de l'angle d'analyse
        ia_angle = st.selectbox("Angle d'analyse prioritaire :", [
            "Performance Logistique (Dépôt & Erreurs de Préparation)",
            "Conformité Commerciale (Retours et Saisies Commerciaux)",
            "Qualité Produit & Stock (PNC, Frigo & Lots suspects)",
            "Diagnostic Global (Synthèse de tous les axes)"
        ])
        
        if is_ia_enabled():
            if st.button("🚀 LANCER L'AUDIT STRATÉGIQUE DE L'IA", use_container_width=True, type="primary"):
                # Préparer le condensé de données
                # Commerciaux
                comm_sum = df_raw.groupby(['commercial', 'categorie_motif']).size().reset_index(name='count').to_dict('records')
                # Préparateurs
                prep_sum = df_raw[df_raw['categorie_motif'] == "Erreur Dépôt"].groupby('preparateur').size().to_dict()
                # Produits
                top_p_claims = df_raw['produit'].value_counts().head(5).to_dict()
                # Motifs
                motifs_sum = df_raw['motif'].value_counts().head(5).to_dict()
                # Frigo
                frigo_claims_count = len(df_raw[df_raw['frigo'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)])
                # Valeur
                total_loss_val = df_raw['valeur_vente'].sum()
                
                prompt = f"""
                Tu es l'auditeur logistique de DarPharm, un grand grossiste de distribution pharmaceutique.
                Voici un rapport consolidé de nos réclamations clients en cours et clôturées :
                - Angle d'analyse demandé : {ia_angle}
                - Pertes financières totales sur les réclamations : {total_loss_val:,.2f} DA
                - Synthèse Commerciaux vs Types d'erreurs : {comm_sum}
                - Erreurs de préparation par préparateur (Dépôt) : {prep_sum}
                - Top 5 produits générant des litiges : {top_p_claims}
                - Top 5 motifs textuels déclarés par les clients : {motifs_sum}
                - Nombre d'anomalies de chaîne du froid (produits Frigo) : {frigo_claims_count}
                
                MISSION :
                1. **Analyse de Cause Racine (Root Cause Analysis)** : En te basant sur l'angle choisi ({ia_angle}), dis-moi clairement quel est le maillon faible. Ne fais pas de langue de bois.
                2. **Indice de Perte Financière** : Commente le coût de ces erreurs pour la société.
                3. **Plan Correctif Immédiat (3 solutions concrètes)** : Donne 3 actions concrètes (SOP - Procédures Opérationnelles Standards) à mettre en place dès demain au dépôt ou au niveau commercial pour éradiquer ces réclamations.
                
                Sois analytique, direct et rédige ta réponse de façon extrêmement structurée avec du Markdown (gras, puces).
                """
                
                with st.spinner("L'IA croise les variables et rédige les procédures opérationnelles..."):
                    report = ask_ai(prompt)
                    st.markdown(f'<div class="ia-report">{report}</div>', unsafe_allow_html=True)
                    st.balloons()
        else:
            st.info("L'intégration IA est désactivée. Veuillez l'activer dans la configuration centrale.")
else:
    st.warning("Aucune donnée de réclamation disponible. Veuillez importer un fichier de réclamations depuis l'Administration Centrale.")
