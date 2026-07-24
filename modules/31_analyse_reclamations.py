import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_ia import ask_ai, is_ia_enabled
from utils_pdf import generate_inventory_report_pdf

# --- 1. CONFIGURATION ---
RECLAM_WORKSHEET = "Analyse_Reclamations"
RECLAM_FALLBACK = "data/db_reclamations_analyse.csv"

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
        background: var(--bg-card, linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%));
        border: 1px solid rgba(150, 150, 150, 0.2);
        border-radius: 20px;
        padding: 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
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
        color: var(--text-primary, #333);
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

def get_raw_col_name(df, target_internal):
    """Trouver le vrai nom de colonne (brut) depuis un nom interne."""
    for raw_col in df.columns:
        norm = clean_col(raw_col)
        if norm == target_internal or GSHEET_COL_MAP.get(norm, norm) == target_internal:
            return raw_col
    return target_internal

# ─── MAPPING STRICT DES COLONNES GSHEET ────────────────────────────────────
# Dictionnaire de renommage : clé = nom normalisé GSheet, valeur = nom interne
GSHEET_COL_MAP = {
    # Statut & Identifiants
    'statut':                   'statut',
    'reference':                'reference',
    'statut bon':               'statut_bon',
    'statut_bon':               'statut_bon',
    'bon statut':               'statut_bon',
    'etat':                     'statut_bon',
    # Dates
    'date':                     'date',
    'date creation':            'date_creation',
    'cree le':                  'date_creation',
    'date validation':          'date_validation',
    'date cloture':             'date_cloture',
    'ferme le':                 'date_cloture',
    'date facture':             'date_facture',
    # Acteurs
    'client':                   'client',
    'creer par':                'cree_par',
    'cree par':                 'cree_par',
    'valider par':              'valider_par',
    'cloturee par':             'cloturer_par',
    'cloturer par':             'cloturer_par',
    'fermeture utilisateur':    'fermeture_utilisateur',
    'verifier par':             'verifier_par',
    'responsable':              'responsable',
    # Facturation
    'ref facture':              'ref_facture',
    'ref.facture':              'ref_facture',
    # Produit
    'produit':                  'produit',
    'designation':              'produit',
    'produit court':            'produit',
    'lot':                      'lot',
    'n lot':                    'lot',
    'quantite':                 'quantite',
    'qte':                      'quantite',
    'quantite reclamee':        'quantite',
    # Financier
    'code':                     'code_client',
    'code client':              'code_client',
    'categorie':                'motif',
    'categorie de reclamation': 'motif',
    'valeur':                   'valeur_vente',
    'montant':                  'valeur_vente',
    'valeur vente':             'valeur_vente',
    'cout revient':             'cout_revient',
    # Divers
    'commercial':               'commercial',
    'region':                   'region',
    'reponse':                  'reponse',
    'avis dt':                  'avis_dt',
    'avis direction technique': 'avis_dt',
    'offre':                    'offre',
    'delai reclam':             'delai_reclam',
    'delai':                    'delai_reclam',
    'remarque ligne':           'remarque_ligne',
    'remarque':                 'remarque_ligne',
    'region':                   'region',
}


df_db_raw = df_db.copy()
df_db_raw.columns = [clean_col(c) for c in df_db_raw.columns]

# Appliquer le renommage strict
rename_map = {}
for raw_norm, internal in GSHEET_COL_MAP.items():
    if raw_norm in df_db_raw.columns and raw_norm != internal:
        rename_map[raw_norm] = internal
df_db_raw.rename(columns=rename_map, inplace=True)

st.session_state.df_reclam_analysed = df_db_raw

if "df_reclam_analysed" in st.session_state:
    df_raw = st.session_state.df_reclam_analysed.copy()

    # ─── VALEURS PAR DÉFAUT pour toutes les colonnes attendues ────────────────
    _defaults = {
        'motif': 'Non Renseigné', 'commercial': 'Inconnu', 'client': 'Inconnu',
        'produit': 'Inconnu', 'region': 'Inconnu', 'statut_bon': 'En Cours',
        'statut': 'En cours', 'date': '', 'code_client': 'Inconnu',
        'date_exp': '', 'prix_vente': 0.0, 'remarque_ligne': '',
        'cree_par': 'Inconnu', 'date_creation': '', 'date_validation': '',
        'date_cloture': '', 'valider_par': '', 'cloturer_par': '',
        'fermeture_utilisateur': '', 'ref_facture': '', 'date_facture': '',
        'reponse': '', 'reference': 'Inconnu', 'valeur_vente': 0.0,
        'cout_revient': 0.0, 'delai_reclam': 0, 'nbr_jours': 0,
    }
    for col, default_val in _defaults.items():
        if col not in df_raw.columns:
            df_raw[col] = default_val

    # Fallback : si 'cree_par' vide mais 'commercial' renseigné, utiliser commercial
    mask_empty_cree = df_raw['cree_par'].astype(str).str.strip().isin(['', 'nan', 'Inconnu'])
    if mask_empty_cree.any() and 'commercial' in df_raw.columns:
        df_raw.loc[mask_empty_cree, 'cree_par'] = df_raw.loc[mask_empty_cree, 'commercial']

    # ─── NETTOYAGE TYPES ──────────────────────────────────────────────────────
    df_raw['motif'] = df_raw['motif'].fillna("Non Renseigné").astype(str)
    df_raw['categorie_motif'] = df_raw['motif'].apply(categorize_motif)
    df_raw['commercial'] = df_raw['commercial'].fillna("Inconnu").astype(str)
    df_raw['cree_par'] = df_raw['cree_par'].fillna("Inconnu").astype(str).str.strip().str.upper()
    df_raw['valider_par'] = df_raw['valider_par'].fillna("").astype(str)
    df_raw['cloturer_par'] = df_raw['cloturer_par'].fillna("").astype(str)
    df_raw['fermeture_utilisateur'] = df_raw['fermeture_utilisateur'].fillna("").astype(str)
    df_raw['client'] = df_raw['client'].fillna("Inconnu").astype(str)
    df_raw['code_client'] = df_raw['code_client'].fillna("Inconnu").astype(str)
    df_raw['reponse'] = df_raw['reponse'].fillna("").astype(str)
    df_raw['reference'] = df_raw['reference'].fillna("Inconnu").astype(str)
    df_raw['date_exp'] = df_raw['date_exp'].fillna("").astype(str)
    df_raw['remarque_ligne'] = df_raw['remarque_ligne'].fillna("").astype(str)
    df_raw['date_creation'] = df_raw['date_creation'].fillna("").astype(str)
    df_raw['date_validation'] = df_raw['date_validation'].fillna("").astype(str)
    df_raw['date_cloture'] = df_raw['date_cloture'].fillna("").astype(str)
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
    # Normalisation du statut : ramène toutes les variantes vers 2 valeurs canoniques
    def normalize_statut(s):
        s = str(s).strip().lower()
        if any(x in s for x in ['clot', 'ferm', 'terminé', 'close', 'closed']): return 'Clôturer'
        return 'En cours'
    df_raw['statut'] = df_raw['statut'].fillna('En cours').apply(normalize_statut)
    df_raw['datetime_parsed'] = df_raw['date'].apply(parse_date_robust)

    # ─── DATES TYPÉES POUR CALCULS SLA ────────────────────────────────────────
    df_raw['dt_creation']   = df_raw['date_creation'].apply(parse_date_robust)
    df_raw['dt_cloture']    = df_raw['date_cloture'].apply(parse_date_robust)
    df_raw['dt_validation'] = df_raw['date_validation'].apply(parse_date_robust)
    df_raw['dt_facture']    = df_raw['date_facture'].apply(parse_date_robust)

    # Délai de traitement interne : date_cloture - date_creation (en heures)
    df_raw['delai_traitement_h'] = (
        df_raw['dt_cloture'] - df_raw['dt_creation']
    ).dt.total_seconds() / 3600
    df_raw['delai_traitement_h'] = df_raw['delai_traitement_h'].where(
        df_raw['delai_traitement_h'] >= 0, other=pd.NA
    )
    # Délai création après facturation (SLA 48h) : dt_creation - dt_facture
    df_raw['delai_fact_creation_h'] = (
        df_raw['dt_creation'] - df_raw['dt_facture']
    ).dt.total_seconds() / 3600
    df_raw['delai_fact_creation_h'] = df_raw['delai_fact_creation_h'].where(
        df_raw['delai_fact_creation_h'] >= 0, other=pd.NA
    )
    df_raw['sla_breach'] = df_raw['delai_fact_creation_h'].apply(
        lambda x: True if (pd.notna(x) and x > 48) else False
    )
    # Mois/Année pour le suivi quota mensuel
    df_raw['mois_creation'] = df_raw['dt_creation'].dt.to_period('M').astype(str)
    df_raw.loc[df_raw['dt_creation'].isna(), 'mois_creation'] = 'Inconnu'

    # --- FILTRES EN BARRE LATÉRALE ---
    st.sidebar.markdown("### 🎛️ Filtres Globaux")

    # Filtres régionaux
    regions = ["Toutes"] + sorted([r for r in df_raw['region'].unique() if r not in ['Inconnu', 'nan', '']])
    selected_region = st.sidebar.selectbox("Région :", regions)

    # Filtre par commercial créateur ('Créer par') — PRIORITAIRE
    cree_par_vals = sorted([v for v in df_raw['cree_par'].unique() if v not in ['INCONNU', 'Inconnu', 'nan', '']])
    cree_par_opts = ["Tous"] + cree_par_vals
    selected_cree_par = st.sidebar.selectbox("👤 Commercial (Créer par) :", cree_par_opts)

    # Filtre par Statut
    statuts_opts = ["Tous", "En cours", "Clôturer"]
    selected_statut = st.sidebar.selectbox("📌 Statut :", statuts_opts)

    # Filtre par Client
    clients_vals = sorted([v for v in df_raw['client'].unique() if v not in ['Inconnu', 'nan', '']])
    clients_opts = ["Tous"] + clients_vals
    selected_client = st.sidebar.selectbox("🏥 Client :", clients_opts)

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
    if selected_cree_par != "Tous":
        df_filtered = df_filtered[df_filtered['cree_par'] == selected_cree_par]
    if selected_statut != "Tous":
        df_filtered = df_filtered[df_filtered['statut'] == selected_statut]
    if selected_client != "Tous":
        df_filtered = df_filtered[df_filtered['client'] == selected_client]
    if selected_motif != "Tous":
        df_filtered = df_filtered[df_filtered['categorie_motif'] == selected_motif]
    if frigo_filter:
        df_filtered = df_filtered[df_filtered['frigo'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)]
    if psycho_filter:
        df_filtered = df_filtered[df_filtered['psycho'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)]
    if chere_filter:
        df_filtered = df_filtered[df_filtered['chere'].astype(str).str.upper().str.contains("OUI|TRUE|1", na=False)]

    # --- TABS SYSTEM ---
    # tabs[0] = Analyses & KPIs
    # tabs[1] = Performance Commerciaux (NOUVEAU)
    # tabs[2] = Audit & Alertes
    # tabs[3] = Centre de Résolution
    # tabs[4] = Gestion des Statuts
    # tabs[5] = Profiling & Détails
    # tabs[6] = Diagnostic IA Expert
    tabs = st.tabs([
        "📊 Analyses & KPIs",
        "👥 Performance Commerciaux",
        "🚨 Audit & Alertes",
        "⚙️ Centre de Résolution",
        "🔄 Gestion des Statuts",
        "🔍 Profiling & Détails",
        "🧠 Diagnostic IA Expert"
    ])

    # ----------------- TAB 0 : ANALYSES & KPIS -----------------
    with tabs[0]:
        # ── Calculs KPIs ──────────────────────────────────────────────────────
        total_claims   = len(df_filtered)
        nb_en_cours    = len(df_filtered[df_filtered['statut'] == 'En cours'])
        nb_clotures    = len(df_filtered[df_filtered['statut'] == 'Clôturer'])
        valeur_vente_totale = df_filtered['valeur_vente'].sum()
        cout_revient_total  = df_filtered['cout_revient'].sum()

        # Commercial avec le plus haut volume
        comm_counts = df_filtered[df_filtered['cree_par'] != 'INCONNU']['cree_par'].value_counts()
        top_comm     = comm_counts.index[0] if not comm_counts.empty else 'N/A'
        top_comm_nb  = int(comm_counts.iloc[0]) if not comm_counts.empty else 0

        # Temps moyen de clôture (heures → jours)
        delai_h_series = df_filtered['delai_traitement_h'].dropna()
        avg_delai_h  = delai_h_series.mean() if not delai_h_series.empty else float('nan')
        if not pd.isna(avg_delai_h):
            avg_d = int(avg_delai_h // 24)
            avg_hr = int(avg_delai_h % 24)
            avg_closure_str = f"{avg_d}j {avg_hr}h"
        else:
            avg_closure_str = "N/A"

        # Grid 3 KPIs principaux
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

        with kpi_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📋 Total Réclamations</div>
                <div class="metric-val">{total_claims}</div>
                <div class="metric-desc">
                    🟠 En cours : <b>{nb_en_cours}</b> &nbsp;|&nbsp; ✅ Clôturées : <b>{nb_clotures}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">👑 Top Commercial</div>
                <div class="metric-val metric-val-vibrant">{top_comm}</div>
                <div class="metric-desc">{top_comm_nb} réclamation(s) créée(s)</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⏱️ Temps moyen de Clôture</div>
                <div class="metric-val" style="color:#10b981;">{avg_closure_str}</div>
                <div class="metric-desc">Sur les dossiers clôturés filtrés</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📊 Répartition des Réclamations par Commercial et par Statut")
        if not df_filtered.empty and df_filtered['cree_par'].nunique() > 0:
            df_comm_statut = df_filtered.groupby(['cree_par', 'statut']).size().reset_index(name='Nb')
            df_comm_statut = df_comm_statut[df_comm_statut['cree_par'] != 'INCONNU']
            color_map = {'En cours': '#f97316', 'Clôturer': '#10b981'}
            fig_comm_bar = px.bar(
                df_comm_statut, x='cree_par', y='Nb', color='statut', barmode='group',
                text='Nb',
                color_discrete_map=color_map,
                labels={'cree_par': 'Commercial (Créer par)', 'Nb': 'Nombre de Réclamations', 'statut': 'Statut'}
            )
            fig_comm_bar.update_traces(textposition='outside')
            fig_comm_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                height=420, margin=dict(t=30, l=10, r=10, b=10),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                font=dict(family='Plus Jakarta Sans'),
            )
            st.plotly_chart(fig_comm_bar, use_container_width=True)
        else:
            st.info("Aucune donnée disponible pour le graphique.")

        st.markdown("### 🍩 Cartographie Opérationnelle")
        col_g1, col_g2 = st.columns([1, 1])

        with col_g1:
            st.markdown("#### Hiérarchie et Origine des Litiges")
            if not df_filtered.empty:
                df_p_plot = df_filtered.copy()
                df_p_plot['motif_plot'] = df_p_plot['motif'].astype(str) + " "
                val_col = 'valeur_vente' if df_p_plot['valeur_vente'].sum() > 0 else None
                fig_sun = px.sunburst(df_p_plot, path=['categorie_motif', 'motif_plot'],
                                     color_discrete_sequence=px.colors.qualitative.Bold,
                                     values=val_col)
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

        # --- ACTIONS TAB 0 ---
        st.markdown("---")
        col_act0_1, col_act0_2 = st.columns(2)
        with col_act0_1:
            if not df_filtered.empty and df_filtered['cree_par'].nunique() > 0:
                df_export_0 = df_comm_statut.copy()
                df_export_0.columns = ['Commercial', 'Statut', 'Nb_Réclamations']
                pdf_data_0 = generate_inventory_report_pdf(
                    df_export_0,
                    title=f"RAPPORT KPIs RECLAMATIONS - {datetime.now().strftime('%d/%m/%Y')}",
                    cols_to_include=['Commercial', 'Statut', 'Nb_Réclamations'],
                    orientation='P'
                )
                st.download_button(
                    "📥 Télécharger le Rapport KPI en PDF",
                    data=pdf_data_0,
                    file_name=f"Rapport_KPIs_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime='application/pdf',
                    use_container_width=True,
                    type="primary"
                )
        with col_act0_2:
            if is_ia_enabled() and not df_filtered.empty:
                if st.button("🧠 Analyser les KPIs avec l'IA", use_container_width=True):
                    with st.spinner("Analyse IA en cours..."):
                        prompt_kpi = f"""Tu es un analyste expert de données. Analyse ces KPIs de réclamations:
                        - Total Réclamations : {total_claims} (En cours: {nb_en_cours}, Clôturées: {nb_clotures})
                        - Top Commercial : {top_comm} avec {top_comm_nb} réclamations
                        - Temps moyen de clôture : {avg_closure_str}
                        Fais un résumé concis des tendances et donne 2 recommandations stratégiques."""
                        reponse_kpi = ask_ai(prompt_kpi)
                        st.info(reponse_kpi)

    # ----------------- TAB 1 : PERFORMANCE COMMERCIAUX -----------------
    with tabs[1]:
        st.markdown("### 👥 Analyse Performance des Commerciaux")
        st.write("Volume de réclamations créées par commercial, suivi des quotas mensuels et calcul des délais SLA.")

        QUOTA_MAX = 5  # Seuil de réclamations max autorisé par mois et par commercial

        # ── Tableau Volume global par commercial ─────────────────────────────
        df_vol = df_raw[df_raw['cree_par'] != 'INCONNU'].copy()
        if df_vol.empty:
            st.info("Aucune donnée de commercial disponible (colonne 'Créer par' vide ou absente).")
        else:
            vol_stats = df_vol.groupby('cree_par').agg(
                Nb_Reclamations=('reference', 'count'),
                Nb_Cloturees=('statut', lambda x: (x == 'Clôturer').sum()),
                Nb_En_Cours=('statut', lambda x: (x == 'En cours').sum()),
                Delai_Moy_h=('delai_traitement_h', 'mean'),
            ).reset_index()
            vol_stats['% du Total'] = (vol_stats['Nb_Reclamations'] / vol_stats['Nb_Reclamations'].sum() * 100).round(1)
            vol_stats['Délai Moy. (h)'] = vol_stats['Delai_Moy_h'].apply(lambda x: f"{x:.1f}h" if pd.notna(x) else "N/A")
            vol_stats = vol_stats.sort_values('Nb_Reclamations', ascending=False)

            st.markdown("#### 📋 Volume Global de Réclamations par Commercial")
            display_vol = vol_stats[['cree_par', 'Nb_Reclamations', 'Nb_En_Cours', 'Nb_Cloturees', '% du Total', 'Délai Moy. (h)']].copy()
            display_vol.columns = ['Commercial', 'Total', 'En Cours', 'Clôturées', '% du Total', 'Délai Moy.']
            st.dataframe(display_vol, use_container_width=True, hide_index=True)

            # ── QUOTA MENSUEL ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown(f"#### 📅 Suivi du Quota Mensuel (Seuil : {QUOTA_MAX} réclamations/mois)")

            mois_disponibles = sorted(
                [m for m in df_vol['mois_creation'].unique() if m != 'Inconnu'], reverse=True
            )
            mois_disponibles = mois_disponibles if mois_disponibles else ['Inconnu']
            col_mois, col_empty = st.columns([2, 4])
            mois_sel = col_mois.selectbox("Sélectionner le mois :", mois_disponibles, key="quota_mois_sel")

            df_mois = df_vol[df_vol['mois_creation'] == mois_sel]
            quota_stats = df_mois.groupby('cree_par')['reference'].count().reset_index()
            quota_stats.columns = ['Commercial', 'Nb']
            quota_stats = quota_stats.sort_values('Nb', ascending=False)

            if quota_stats.empty:
                st.info(f"Aucune réclamation enregistrée pour {mois_sel}.")
            else:
                # Barres de progression + alertes
                st.markdown(f"**Période : {mois_sel}**")
                for _, qrow in quota_stats.iterrows():
                    comm_name = qrow['Commercial']
                    nb = int(qrow['Nb'])
                    ratio = min(nb / QUOTA_MAX, 1.0)
                    color = "#ef4444" if nb >= QUOTA_MAX else "#f97316" if nb >= QUOTA_MAX * 0.8 else "#10b981"
                    pct = min(int(ratio * 100), 100)
                    badge = f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:700;">{nb}/{QUOTA_MAX}</span>'
                    alert_icon = "🔴" if nb >= QUOTA_MAX else "🟠" if nb >= QUOTA_MAX * 0.8 else "🟢"
                    st.markdown(f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                            <span style="font-weight:700;font-size:0.95rem;">{alert_icon} {comm_name}</span>
                            {badge}
                        </div>
                        <div style="background:rgba(255,255,255,0.07);border-radius:8px;height:10px;overflow:hidden;">
                            <div style="background:{color};width:{pct}%;height:10px;border-radius:8px;transition:width 0.4s;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Graphique Plotly mensuel avec ligne de seuil
                fig_quota = go.Figure()
                fig_quota.add_trace(go.Bar(
                    x=quota_stats['Commercial'], y=quota_stats['Nb'],
                    marker_color=[('#ef4444' if n >= QUOTA_MAX else '#6366f1') for n in quota_stats['Nb']],
                    text=quota_stats['Nb'], textposition='outside',
                    name='Réclamations'
                ))
                fig_quota.add_shape(
                    type='line', x0=-0.5, x1=len(quota_stats) - 0.5,
                    y0=QUOTA_MAX, y1=QUOTA_MAX,
                    line=dict(color='#ef4444', width=2, dash='dash')
                )
                fig_quota.add_annotation(
                    x=len(quota_stats) - 1, y=QUOTA_MAX + 0.3,
                    text=f"Quota Max ({QUOTA_MAX})", showarrow=False,
                    font=dict(color='#ef4444', size=11)
                )
                fig_quota.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    height=380, margin=dict(t=30, l=10, r=10, b=10),
                    xaxis_title='Commercial', yaxis_title='Nb Réclamations',
                    showlegend=False, font=dict(family='Plus Jakarta Sans')
                )
                st.plotly_chart(fig_quota, use_container_width=True)

            # ── SLA 48H ──────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### ⏱️ Analyse SLA 48h (Délai Facturation → Création Réclamation)")
            st.caption("Le SLA de 48h mesure le délai entre la date de facturation et la date de création de la réclamation. Un dépassement indique une réaction tardive.")

            df_sla = df_raw[df_raw['dt_facture'].notna() & df_raw['dt_creation'].notna()].copy()

            if df_sla.empty:
                st.markdown("""
                <div class="info-card">
                    ℹ️ <b>Colonne 'Date Facture' non renseignée</b> dans la base de réclamations.<br>
                    Pour activer l'analyse SLA 48h, assurez-vous que cette colonne est exportée depuis Logipharm.
                </div>
                """, unsafe_allow_html=True)
            else:
                nb_total_sla = len(df_sla)
                nb_breach = df_sla['sla_breach'].sum()
                nb_ok = nb_total_sla - nb_breach
                sla_rate = round((nb_ok / nb_total_sla) * 100, 1) if nb_total_sla > 0 else 0
                avg_delay_h = df_sla['delai_fact_creation_h'].mean()
                avg_d = int(avg_delay_h // 24) if pd.notna(avg_delay_h) else 0
                avg_hr = int(avg_delay_h % 24) if pd.notna(avg_delay_h) else 0

                sla_c1, sla_c2, sla_c3 = st.columns(3)
                with sla_c1:
                    color_sla = "#10b981" if sla_rate >= 80 else "#f97316" if sla_rate >= 50 else "#ef4444"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">✅ Taux de Respect SLA</div>
                        <div class="metric-val" style="color:{color_sla};">{sla_rate}%</div>
                        <div class="metric-desc">{nb_ok} / {nb_total_sla} réclamations dans les délais</div>
                    </div>""", unsafe_allow_html=True)
                with sla_c2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">🔴 Dépassements SLA</div>
                        <div class="metric-val" style="color:#ef4444;">{int(nb_breach)}</div>
                        <div class="metric-desc">Réclamations créées après 48h de facturation</div>
                    </div>""", unsafe_allow_html=True)
                with sla_c3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">⏱ Délai Moy. Fact→Création</div>
                        <div class="metric-val" style="color:#a855f7;">{avg_d}j {avg_hr}h</div>
                        <div class="metric-desc">Délai moyen de déclaration post-facturation</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("##### Détail des réclamations avec dépassement SLA")
                df_breached = df_sla[df_sla['sla_breach'] == True][
                    ['reference', 'client', 'cree_par', 'date_facture', 'date_creation', 'delai_fact_creation_h', 'statut']
                ].copy()
                df_breached['Délai (h)'] = df_breached['delai_fact_creation_h'].apply(
                    lambda x: f"🔴 {x:.1f}h" if pd.notna(x) else "N/A"
                )
                df_breached = df_breached.drop(columns=['delai_fact_creation_h'])
                df_breached.columns = ['Référence', 'Client', 'Commercial', 'Date Facture', 'Date Création', 'Statut', 'Délai (h)']
                if df_breached.empty:
                    st.success("✅ Aucune réclamation ne dépasse le SLA de 48h.")
                else:
                    st.warning(f"⚠️ {len(df_breached)} réclamation(s) ont été déclarées plus de 48h après la facturation.")
                    st.dataframe(df_breached, use_container_width=True, hide_index=True)

            # --- ACTIONS TAB 1 ---
            st.markdown("---")
            col_act1_1, col_act1_2 = st.columns(2)
            with col_act1_1:
                if not df_vol.empty:
                    df_export_1 = display_vol.copy()
                    pdf_data_1 = generate_inventory_report_pdf(
                        df_export_1,
                        title=f"PERFORMANCE COMMERCIAUX - {datetime.now().strftime('%d/%m/%Y')}",
                        cols_to_include=['Commercial', 'Total', 'En Cours', 'Clôturées', 'Délai Moy.'],
                        orientation='P'
                    )
                    st.download_button(
                        "📥 Télécharger le Rapport Performance en PDF",
                        data=pdf_data_1,
                        file_name=f"Rapport_Perf_Commerciaux_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime='application/pdf',
                        use_container_width=True,
                        type="primary"
                    )
            with col_act1_2:
                if is_ia_enabled() and not df_vol.empty:
                    if st.button("🧠 Analyser la Performance Commerciale", use_container_width=True):
                        with st.spinner("Analyse IA en cours..."):
                            vol_dict = display_vol[['Commercial', 'Total']].set_index('Commercial').to_dict()['Total']
                            prompt_perf = f"""Tu es un directeur commercial. Analyse ces performances (Nb de réclamations par commercial):
                            {vol_dict}
                            - Quota autorisé : {QUOTA_MAX} par mois.
                            - Taux global SLA 48h : {sla_rate if 'sla_rate' in locals() else 'N/A'}%
                            Identifie les commerciaux les plus performants (le moins de réclamations) et ceux nécessitant un coaching, et propose 2 actions de coaching."""
                            reponse_perf = ask_ai(prompt_perf)
                            st.info(reponse_perf)

    # ----------------- TAB 2 : AUDIT & ALERTES -----------------
    with tabs[2]:
        st.markdown("### 🚨 Système d'Alerte et d'Audit Qualité")
        st.write("Ce panneau identifie les faiblesses logistiques récurrentes, les anomalies commerciales et les risques de chaîne du froid ou de réglementation.")
        
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("#### 👤 Alerte Tolérance Commerciale (Max 5 Erreurs)")
            err_by_comm = df_raw[df_raw['categorie_motif'] == "Erreur Commerciale"].groupby('cree_par').size().reset_index(name='Nb_Erreurs')
            over_limit = err_by_comm[err_by_comm['Nb_Erreurs'] > 5]
            
            if not over_limit.empty:
                for _, row in over_limit.iterrows():
                    st.markdown(f"""
                    <div class="alert-card">
                        ⚠️ <b>{row['cree_par']}</b> a dépassé la limite de tolérance !<br>
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
            df_depot_errors = df_raw[df_raw['categorie_motif'] == "Erreur Dépôt"]
            if not df_depot_errors.empty:
                prep_stats = df_depot_errors.groupby('preparateur').agg({'reference': 'count', 'valeur_vente': 'sum'}).reset_index()
                prep_stats.columns = ['Préparateur', 'Nombre Erreurs', 'Valeur Perdue (DA)']
                prep_stats = prep_stats.sort_values(by='Nombre Erreurs', ascending=False)
                st.write("Classement des erreurs de préparation par agent de dépôt :")
                st.dataframe(prep_stats, use_container_width=True, hide_index=True)
                critical_prep = prep_stats[prep_stats['Nombre Erreurs'] >= 2]
                if not critical_prep.empty:
                    st.warning(f"⚠️ {len(critical_prep)} préparateur(s) ont commis au moins 2 erreurs de préparation.")
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
                    Ces produits sont soumis à des contrôles stricts du ministère de la santé.
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(df_psy[['reference', 'date', 'client', 'produit', 'quantite', 'statut']], use_container_width=True, hide_index=True)
            else:
                st.success("✅ Aucun litige sur les psychotropes.")
                
            st.markdown("#### 🏷️ Alerte Anomalie Lot (Suspicion Rappel/Qualité)")
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
        raw_ref = get_raw_col_name(df_db, 'reference')
        raw_prod = get_raw_col_name(df_db, 'produit')
        raw_statut_bon = get_raw_col_name(df_db, 'statut_bon')
        raw_date_cloture = get_raw_col_name(df_db, 'date_cloture')
        raw_cloturer_par = get_raw_col_name(df_db, 'cloturer_par')
        raw_delai = get_raw_col_name(df_db, 'delai_reclam')
        raw_date = get_raw_col_name(df_db, 'date')

        mask = (df_db[raw_ref] == ref) & (df_db[raw_prod] == produit_val)
        if mask.any():
            today_str = datetime.now().strftime("%d-%m-%y %H:%M:%S")
            df_db.loc[mask, raw_statut_bon] = new_status
            if new_status == "CLOTURER":
                df_db.loc[mask, raw_date_cloture] = today_str
                df_db.loc[mask, raw_cloturer_par] = st.session_state.current_user['username']
                # Auto-calculate delai if not set
                existing_delai = df_db.loc[mask, raw_delai].values[0] if raw_delai in df_db.columns else None
                if pd.isna(existing_delai) or str(existing_delai).strip() in ["", "nan", "None"]:
                    claim_date = parse_date_robust(df_db.loc[mask, raw_date].values[0]) if raw_date in df_db.columns else pd.NaT
                    duration = max(0, (datetime.now() - claim_date).days) if not pd.isna(claim_date) else 0
                    df_db.loc[mask, raw_delai] = float(duration)
            save_gs_data(df_db, RECLAM_WORKSHEET, RECLAM_FALLBACK)
            # Recharger correctement avec les colonnes normalisées
            df_db_raw_new = df_db.copy()
            df_db_raw_new.columns = [clean_col(c) for c in df_db_raw_new.columns]
            rename_map_new = {}
            for raw_norm, internal in GSHEET_COL_MAP.items():
                if raw_norm in df_db_raw_new.columns and raw_norm != internal:
                    rename_map_new[raw_norm] = internal
            df_db_raw_new.rename(columns=rename_map_new, inplace=True)
            st.session_state.df_reclam_analysed = df_db_raw_new
            return True
        return False

    # ----------------- TAB 3 : CENTRE DE RÉSOLUTION -----------------
    with tabs[3]:
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
                            
                            raw_ref = get_raw_col_name(df_db, 'reference')
                            raw_prod = get_raw_col_name(df_db, 'produit')
                            
                            mask = (df_db[raw_ref] == row['reference']) & (df_db[raw_prod] == row['produit'])

                            if mask.any():
                                today = datetime.now()
                                claim_date = parse_date_robust(row['date'])
                                duration = (today - claim_date).days if not pd.isna(claim_date) else 1
                                if duration < 0:
                                    duration = 0

                                df_db.loc[mask, get_raw_col_name(df_db, 'statut_bon')] = "CLOTURER"
                                df_db.loc[mask, get_raw_col_name(df_db, 'statut')] = statut_final
                                df_db.loc[mask, get_raw_col_name(df_db, 'reponse')] = reponse_text
                                df_db.loc[mask, get_raw_col_name(df_db, 'avis_dt')] = avis_dt_text
                                df_db.loc[mask, get_raw_col_name(df_db, 'verifier_par')] = verifier_par_val
                                df_db.loc[mask, get_raw_col_name(df_db, 'responsable')] = responsible_dept
                                df_db.loc[mask, get_raw_col_name(df_db, 'delai_reclam')] = float(duration)
                                df_db.loc[mask, get_raw_col_name(df_db, 'date_cloture')] = today.strftime("%d-%m-%y %H:%M:%S")
                                df_db.loc[mask, get_raw_col_name(df_db, 'cloturer_par')] = st.session_state.current_user['username']
                                df_db.loc[mask, get_raw_col_name(df_db, 'offre')] = action_type

                                save_gs_data(df_db, RECLAM_WORKSHEET, RECLAM_FALLBACK)
                                
                                df_db_raw_new = df_db.copy()
                                df_db_raw_new.columns = [clean_col(c) for c in df_db_raw_new.columns]
                                rename_map_new = {}
                                for raw_norm, internal in GSHEET_COL_MAP.items():
                                    if raw_norm in df_db_raw_new.columns and raw_norm != internal:
                                        rename_map_new[raw_norm] = internal
                                df_db_raw_new.rename(columns=rename_map_new, inplace=True)
                                st.session_state.df_reclam_analysed = df_db_raw_new

                                st.success("🎉 Réclamation clôturée et synchronisée avec succès !")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Ligne introuvable lors de l'enregistrement.")

    # ----------------- TAB 4 : GESTION DES STATUTS -----------------
    # ----------------- TAB 3 : CENTRE DE RÉSOLUTION -----------------
    with tabs[4]:
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
                
                raw_ref_bulk = get_raw_col_name(df_db_bulk, 'reference')
                raw_statut_bulk = get_raw_col_name(df_db_bulk, 'statut_bon')
                raw_date_cloture_bulk = get_raw_col_name(df_db_bulk, 'date_cloture')
                raw_cloturer_par_bulk = get_raw_col_name(df_db_bulk, 'cloturer_par')
                
                updated_count = 0
                for ref_bulk in refs_to_update:
                    mask_bulk = df_db_bulk[raw_ref_bulk] == ref_bulk
                    if mask_bulk.any():
                        df_db_bulk.loc[mask_bulk, raw_statut_bulk] = bulk_status_sel
                        if bulk_status_sel == "CLOTURER":
                            df_db_bulk.loc[mask_bulk, raw_date_cloture_bulk] = datetime.now().strftime("%d-%m-%y %H:%M:%S")
                            df_db_bulk.loc[mask_bulk, raw_cloturer_par_bulk] = st.session_state.current_user['username']
                        updated_count += mask_bulk.sum()
                save_gs_data(df_db_bulk, RECLAM_WORKSHEET, RECLAM_FALLBACK)
                
                df_db_raw_new = df_db_bulk.copy()
                df_db_raw_new.columns = [clean_col(c) for c in df_db_raw_new.columns]
                rename_map_new = {}
                for raw_norm, internal in GSHEET_COL_MAP.items():
                    if raw_norm in df_db_raw_new.columns and raw_norm != internal:
                        rename_map_new[raw_norm] = internal
                df_db_raw_new.rename(columns=rename_map_new, inplace=True)
                st.session_state.df_reclam_analysed = df_db_raw_new
                st.success(f"✅ {updated_count} ligne(s) mise(s) à jour avec le statut **{bulk_status_sel}** !")
                st.rerun()
            else:
                st.warning("Veuillez saisir au moins une référence.")

    # ----------------- TAB 5 : PROFILING CLIENT & PRODUIT -----------------
    # ----------------- TAB 4 : GESTION DES STATUTS -----------------
    with tabs[5]:
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
    # ----------------- TAB 5 : PROFILING & DÉTAILS -----------------
    with tabs[6]:
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
