import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils_gsheets import load_gs_data

# ==========================================
# 1. CHARGEMENT DES VRAIS DONNÉES (ADMIN CENTRALE)
# ==========================================

# --- Colonnes de la base Recouvrement ---
COLS_RECOUV = [
    "Client", "Facture", "Date", "Montant Initial", "Montant Réglé",
    "Reste à payer", "Mode Paiement", "Livreur", "Région", "Statut",
    "Commentaires", "Société"
]


def parse_numeric_series(series):
    """Nettoie et convertit une série en valeurs numériques."""
    if series.empty:
        return series

    def clean_val(val):
        if pd.isna(val):
            return "0.0"
        s = str(val).strip()
        for space_char in [" ", "\xa0", "\u202f", "\u205f", "\u2007", "\t", "\n", "\r"]:
            s = s.replace(space_char, "")
        s = s.replace(",", ".")
        return s

    cleaned = series.apply(clean_val)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0.0)


@st.cache_data(ttl=300)
def load_real_data():
    """
    Charge les vrais DataFrames depuis l'Admin Centrale :
    - df_ventes      : Commandes & Ventes globales (colonnes _logi_*)
    - df_validation  : Suivi des Réclamations (colonnes nettoyées)
    - df_recouvrement: Recouvrement financier (colonnes standard)
    - df_clients_base: Base Clients (identité, coordonnées)
    """
    # 1. VENTES / COMMANDES GLOBALES (avec colonnes _logi_*)
    df_ventes = load_gs_data(
        "Commandes_Recouvrement",
        "data/db_commandes_globales.csv",
        None  # Accepter toutes les colonnes
    )

    # 2. RÉCLAMATIONS
    df_validation = load_gs_data(
        "Analyse_Reclamations",
        "data/db_reclamations_analyse.csv",
        None
    )

    # 3. RECOUVREMENT
    df_recouvrement = load_gs_data(
        "Recouvrement",
        "data_recouvrement.csv",
        COLS_RECOUV
    )
    # Nettoyage des montants
    for col in ["Montant Initial", "Montant Réglé", "Reste à payer"]:
        if col in df_recouvrement.columns:
            df_recouvrement[col] = parse_numeric_series(df_recouvrement[col])

    # 4. BASE CLIENTS (identité & coordonnées)
    df_clients_base = load_gs_data(
        "Base_Clients",
        "base_clients.csv",
        None
    )

    # --- Conversion des dates ---
    if 'Date' in df_ventes.columns:
        df_ventes['Date'] = pd.to_datetime(df_ventes['Date'], errors='coerce')
    if 'date' in df_validation.columns:
        df_validation['date'] = pd.to_datetime(df_validation['date'], errors='coerce')
    if 'Date' in df_recouvrement.columns:
        df_recouvrement['Date'] = pd.to_datetime(df_recouvrement['Date'], errors='coerce')

    return df_ventes, df_validation, df_recouvrement, df_clients_base


# ==========================================
# 2. LOGIQUE D'AGRÉGATION & SCORING
# ==========================================
def calculate_client_score(metrics):
    """
    Calcule le score de fidélité sur 100.
    Pondération:
    - Volume (CA TTC) : 35 points
    - Régularité (Commandes/Mois) : 25 points
    - Santé financière (Absence de dette) : 25 points
    - Qualité (Faible taux de réclamation) : 15 points
    """
    score = 0

    # 1. Volume CA (Max 35)
    ca = metrics['total_ttc']
    if ca > 5000000: score += 35
    elif ca > 2000000: score += 25
    elif ca > 500000: score += 15
    else: score += 5

    # 2. Régularité (Max 25) - nbr de commandes
    cmds = metrics['total_commandes']
    if cmds > 50: score += 25
    elif cmds > 20: score += 18
    elif cmds > 5: score += 10
    else: score += 5

    # 3. Santé Financière (Max 25)
    dette = metrics['reste_a_payer']
    taux_dette = dette / ca if ca > 0 else 0
    if taux_dette == 0: score += 25
    elif taux_dette < 0.05: score += 20
    elif taux_dette < 0.15: score += 10
    elif taux_dette < 0.30: score += 0
    else: score -= 10  # Malus !

    # 4. Qualité / Réclamations (Max 15)
    taux_rec = metrics['taux_reclamation']
    if taux_rec < 0.01: score += 15
    elif taux_rec < 0.05: score += 10
    elif taux_rec < 0.10: score += 5
    else: score -= 5

    return max(0, min(100, score))


# ==========================================
# 3. INTERFACE UTILISATEUR (UI/UX)
# ==========================================
st.set_page_config(page_title="Fiche Client 360°", layout="wide", page_icon="🏆")

# INJECTION CSS PREMIUM (Adapté au thème clair/par défaut)
st.markdown("""
<style>
    /* Palette & Variables */
    :root {
        --accent-blue: #0052FF;
        --accent-cyan: #00B4D8;
        --card-bg: #FFFFFF;
        --card-border: #E2E8F0;
        --text-main: #1E293B;
        --text-muted: #64748B;
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }

    /* Custom KPI Cards */
    .kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 20px;
        box-shadow: var(--shadow);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: var(--accent-blue);
    }
    .kpi-title {
        font-size: 0.85rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: var(--text-main);
        margin: 0;
    }
    .kpi-value.gradient-text {
        background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Custom Alerts */
    .alert-premium {
        background: #FEF2F2;
        border-left: 4px solid #EF4444;
        border-radius: 4px 12px 12px 4px;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .alert-icon { font-size: 1.8rem; }
    .alert-content p { margin: 0; color: #991B1B; font-weight: 500; font-size: 0.95rem; }
    .alert-content h4 { margin: 0 0 5px 0; color: #7F1D1D; font-weight: 700; }

    /* Header Styling */
    .header-title {
        font-weight: 900;
        font-size: 2.2rem;
        color: var(--text-main);
        letter-spacing: -0.5px;
        margin-bottom: 0;
    }
    .header-subtitle {
        color: var(--accent-blue);
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# --- CHARGEMENT DES VRAIES DONNÉES ---
df_ventes, df_validation, df_recouvrement, df_clients_base = load_real_data()

# =====================================================================
# DÉTECTION DYNAMIQUE DES COLONNES (compatibilité _logi_ et standard)
# =====================================================================
# Le fichier "Commandes & Recouvrement" importé via l'Admin Centrale
# a ses colonnes non mappées préfixées par "_logi_".
# On détecte dynamiquement le bon nom de colonne.

def _detect_col(df, candidates):
    """Retourne le premier nom de colonne trouvé dans le DataFrame."""
    for c in candidates:
        if c in df.columns:
            return c
    return None

COL_CLIENT   = _detect_col(df_ventes, ["_logi_Client", "Client", "client"])
COL_COLIS    = _detect_col(df_ventes, ["_logi_Colis", "Colis", "colis"])
COL_REF      = _detect_col(df_ventes, ["_logi_Référence", "Référence", "reference", "référence", "B.L"])
COL_LIGNES   = _detect_col(df_ventes, ["_logi_Nbr Ligne", "Nbr Ligne", "nbr_ligne", "Lignes"])
COL_DATE     = _detect_col(df_ventes, ["Date", "date", "_logi_Date"])
COL_REGION   = _detect_col(df_ventes, ["Région", "_logi_Région", "region", "Secteur"])
COL_TTC      = _detect_col(df_ventes, ["_logi_T.T.C", "T.T.C", "_logi_H.T", "H.T", "Montant Initial", "prix_vente"])
COL_MARGE    = _detect_col(df_ventes, ["_logi_Marge", "Marge", "marge"])

# Colonnes Réclamations (nettoyées par clean_reclam_cols)
COL_REC_CLIENT = _detect_col(df_validation, ["client", "Client"])
COL_REC_STATUT = _detect_col(df_validation, ["statut", "Statut"])
COL_REC_MOTIF  = _detect_col(df_validation, ["motif", "Motif", "reponse"])
COL_REC_DATE   = _detect_col(df_validation, ["date", "Date"])
COL_REC_REF    = _detect_col(df_validation, ["reference", "Référence"])

# --- VÉRIFICATION : données disponibles ? ---
if df_ventes.empty and df_recouvrement.empty:
    st.warning("⚠️ Aucune donnée n'a été importée. Veuillez charger vos fichiers de ventes/commandes via l'**Admin Centrale** (Importateur Universel).")
    st.info("💡 L'Admin Centrale détectera automatiquement le type de fichier Excel Logipharm et alimentera ce module.")
    st.stop()

# --- Construction de la liste des vrais clients ---
# On fusionne les clients des ventes et du recouvrement pour avoir une liste exhaustive
clients_from_ventes = []
clients_from_recouvrement = []

if not df_ventes.empty and COL_CLIENT:
    clients_from_ventes = df_ventes[COL_CLIENT].dropna().astype(str).str.strip().unique().tolist()

if not df_recouvrement.empty and 'Client' in df_recouvrement.columns:
    clients_from_recouvrement = df_recouvrement['Client'].dropna().astype(str).str.strip().unique().tolist()

all_clients = sorted(set(clients_from_ventes + clients_from_recouvrement))

if not all_clients:
    st.warning("⚠️ Aucun client détecté dans les données importées. Vérifiez vos fichiers dans l'Admin Centrale.")
    st.stop()

# --- SIDEBAR: FILTRES ---
with st.sidebar:
    st.markdown("### ⚙️ Paramètres 360°")

    client_selectionne = st.selectbox(
        "Sélectionner un Client",
        options=all_clients,
        index=0
    )

    time_filter = st.radio("Période d'analyse", ["Historique Global", "Plage Personnalisée"])
    start_date, end_date = None, None
    if time_filter == "Plage Personnalisée":
        dates = st.date_input("Sélectionnez la plage",
                              [datetime.today() - timedelta(days=30), datetime.today()])
        if len(dates) == 2:
            start_date, end_date = dates

# --- FILTRAGE DES DONNÉES SUR LE CLIENT SÉLECTIONNÉ ---
client_propre = client_selectionne.strip()

# 1. Filtrage des VENTES / COMMANDES
if not df_ventes.empty and COL_CLIENT:
    df_ven_c = df_ventes[df_ventes[COL_CLIENT].astype(str).str.strip() == client_propre].copy()
else:
    df_ven_c = pd.DataFrame()

# 2. Filtrage des RÉCLAMATIONS
if not df_validation.empty and COL_REC_CLIENT:
    df_val_c = df_validation[df_validation[COL_REC_CLIENT].astype(str).str.strip() == client_propre].copy()
else:
    df_val_c = pd.DataFrame()

# 3. Filtrage du RECOUVREMENT
if not df_recouvrement.empty and 'Client' in df_recouvrement.columns:
    df_rec_c = df_recouvrement[df_recouvrement['Client'].astype(str).str.strip() == client_propre].copy()
else:
    df_rec_c = pd.DataFrame()

# Application du filtre temporel
if time_filter == "Plage Personnalisée" and start_date and end_date:
    sd, ed = pd.to_datetime(start_date), pd.to_datetime(end_date)

    if not df_ven_c.empty and COL_DATE and COL_DATE in df_ven_c.columns:
        df_ven_c[COL_DATE] = pd.to_datetime(df_ven_c[COL_DATE], errors='coerce')
        df_ven_c = df_ven_c[(df_ven_c[COL_DATE] >= sd) & (df_ven_c[COL_DATE] <= ed)]

    if not df_val_c.empty and COL_REC_DATE and COL_REC_DATE in df_val_c.columns:
        df_val_c[COL_REC_DATE] = pd.to_datetime(df_val_c[COL_REC_DATE], errors='coerce')
        df_val_c = df_val_c[(df_val_c[COL_REC_DATE] >= sd) & (df_val_c[COL_REC_DATE] <= ed)]

    if not df_rec_c.empty and 'Date' in df_rec_c.columns:
        df_rec_c['Date'] = pd.to_datetime(df_rec_c['Date'], errors='coerce')
        df_rec_c = df_rec_c[(df_rec_c['Date'] >= sd) & (df_rec_c['Date'] <= ed)]


# --- CALCUL DES MÉTRIQUES RÉELLES ---
def safe_sum(df, col):
    """Somme sécurisée d'une colonne, avec conversion numérique."""
    if df.empty or col is None or col not in df.columns:
        return 0
    return parse_numeric_series(df[col]).sum()

def safe_nunique(df, col):
    """Compte unique sécurisé."""
    if df.empty or col is None or col not in df.columns:
        return 0
    return df[col].nunique()

# KPIs depuis les Ventes/Commandes (_logi_*)
total_commandes = len(df_ven_c)
total_colis = int(safe_sum(df_ven_c, COL_COLIS))
total_lignes = int(safe_sum(df_ven_c, COL_LIGNES))
total_refs = safe_nunique(df_ven_c, COL_REF)
total_ttc = safe_sum(df_ven_c, COL_TTC)
marge_brute = safe_sum(df_ven_c, COL_MARGE)

# KPIs depuis le Recouvrement (dette réelle)
reste_a_payer_recouvrement = 0
if not df_rec_c.empty and 'Reste à payer' in df_rec_c.columns:
    reste_a_payer_recouvrement = df_rec_c['Reste à payer'].sum()

# Réclamations
total_litiges = len(df_val_c) if not df_val_c.empty else 0
taux_reclamation = total_litiges / total_commandes if total_commandes > 0 else 0

metrics = {
    'total_commandes': total_commandes,
    'total_colis': total_colis,
    'total_lignes': total_lignes,
    'total_refs': total_refs,
    'total_ttc': total_ttc,
    'marge_brute': marge_brute,
    'reste_a_payer': reste_a_payer_recouvrement,
    'total_litiges': total_litiges,
    'taux_reclamation': taux_reclamation,
}

score = calculate_client_score(metrics)

# --- HEADER APP ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<p class="header-subtitle">MODULE INTELLIGENCE ARTIFICIELLE & DATA</p>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="header-title">📋 Fiche Technique : {client_selectionne}</h1>', unsafe_allow_html=True)
with c_head2:
    # Calcul sécurisé de la dernière activité
    last_date_str = 'N/A'
    if not df_ven_c.empty and COL_DATE and COL_DATE in df_ven_c.columns:
        last_date = pd.to_datetime(df_ven_c[COL_DATE], errors='coerce').max()
        if pd.notna(last_date):
            last_date_str = last_date.strftime('%d/%m/%Y')

    st.markdown(f"""
    <div style="text-align: right; margin-top: 20px;">
        <span style="color:var(--text-muted); font-size:12px; font-weight:600; text-transform:uppercase;">Dernière Activité</span><br>
        <strong style="color:var(--text-main); font-size:18px;">{last_date_str}</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- ALERTES CRITIQUES ---
if metrics['reste_a_payer'] > 0:
    st.markdown(f"""
    <div class="alert-premium">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
            <h4>Attention : Dette Active Détectée</h4>
            <p>Ce client a un reste à payer cumulé de {metrics['reste_a_payer']:,.2f} DA.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

if metrics['taux_reclamation'] >= 0.10:
    st.markdown(f"""
    <div class="alert-premium" style="border-left-color: #F59E0B; background: #FFFBEB;">
        <div class="alert-icon">🚨</div>
        <div class="alert-content">
            <h4 style="color:#92400E;">Vigilance Qualité</h4>
            <p style="color:#B45309;">Taux de réclamation critique ({metrics['taux_reclamation']*100:.1f}%). Analyse requise sur les processus de préparation.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- DIALOGS @st.dialog (Fenêtres Modales Interactives) ---
@st.dialog("🚨 Historique Complet des Réclamations")
def dialog_reclamations(df_litiges: pd.DataFrame):
    """Popup affichant le détail des réclamations du client."""
    if df_litiges.empty:
        st.success("✅ Aucune réclamation trouvée pour ce client sur la période.")
        return
    st.markdown(f"**{len(df_litiges)} incident(s) détecté(s)**")
    # Afficher les colonnes disponibles
    cols_show = [c for c in df_litiges.columns if c in ['date', 'reference', 'motif', 'statut', 'type', 'produit', 'qte_reclam']]
    if cols_show:
        st.dataframe(df_litiges[cols_show].sort_values('date', ascending=False) if 'date' in cols_show else df_litiges[cols_show],
                     use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_litiges, use_container_width=True, hide_index=True)


@st.dialog("📄 Détails Factures & Colissage")
def dialog_factures(df_cmds: pd.DataFrame):
    """Popup affichant le listing complet des commandes/factures du client."""
    if df_cmds.empty:
        st.info("Aucune commande trouvée sur la période sélectionnée.")
        return
    st.markdown(f"**{len(df_cmds)} commande(s) / facture(s)**")
    # Afficher les colonnes pertinentes disponibles
    cols_display = [c for c in [COL_DATE, COL_REF, COL_LIGNES, COL_COLIS, COL_TTC, COL_REGION] if c and c in df_cmds.columns]
    if cols_display:
        st.dataframe(df_cmds[cols_display], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_cmds, use_container_width=True, hide_index=True)
    st.markdown(f"""
    ---
    📦 **Total Colis :** `{total_colis:,}` &nbsp;|
    📝 **Total Lignes :** `{total_lignes:,}` &nbsp;|
    💰 **CA Total :** `{total_ttc:,.0f} DA`
    """)


# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🥇 Vue d'ensemble & Score",
    "💰 Analyse Financière & Logistique",
    "⚠️ Suivi des Incidents",
    "📋 Fiche Client Détaillée"
])

with tab1:
    st.markdown("### Synthèse des Performances")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Commandes</div>
            <p class="kpi-value">{metrics['total_commandes']}</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        ca_display = f"{metrics['total_ttc']/1000000:.1f} M" if metrics['total_ttc'] >= 1000000 else f"{metrics['total_ttc']/1000:.0f} K"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Chiffre d'Affaires</div>
            <p class="kpi-value gradient-text">{ca_display}</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        marge_display = f"{metrics['marge_brute']/1000000:.1f} M" if metrics['marge_brute'] >= 1000000 else f"{metrics['marge_brute']/1000:.0f} K"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Marge Brute</div>
            <p class="kpi-value" style="color: #00B4D8;">{marge_display}</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        dette_display = f"{metrics['reste_a_payer']/1000:.1f} K" if metrics['reste_a_payer'] >= 1000 else f"{metrics['reste_a_payer']:,.0f}"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Dette Client</div>
            <p class="kpi-value" style="color: {'#DC2626' if metrics['reste_a_payer'] > 0 else '#059669'};">
                {dette_display} DA
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_gauge, col_trend = st.columns([1, 2])
    with col_gauge:
        # Gauge Chart Plotly
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "SCORE DE FIDÉLITÉ 360°", 'font': {'size': 16, 'color': '#A0AEC0'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#0066FF"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "rgba(255,255,255,0.1)",
                'steps': [
                    {'range': [0, 40], 'color': "rgba(239, 68, 68, 0.4)"},
                    {'range': [40, 70], 'color': "rgba(245, 158, 11, 0.4)"},
                    {'range': [70, 100], 'color': "rgba(16, 185, 129, 0.4)"}],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#1E293B"}, height=350)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_trend:
        # Graphique Mixte (Barres + Ligne) — évolution mensuelle
        if not df_ven_c.empty and COL_DATE and COL_DATE in df_ven_c.columns:
            df_trend = df_ven_c.copy()
            df_trend[COL_DATE] = pd.to_datetime(df_trend[COL_DATE], errors='coerce')
            df_trend = df_trend.dropna(subset=[COL_DATE])

            if not df_trend.empty:
                df_trend['Mois'] = df_trend[COL_DATE].dt.to_period('M').astype(str)

                agg_dict = {}
                if COL_COLIS and COL_COLIS in df_trend.columns:
                    df_trend[COL_COLIS] = parse_numeric_series(df_trend[COL_COLIS])
                    agg_dict[COL_COLIS] = 'sum'
                if COL_TTC and COL_TTC in df_trend.columns:
                    df_trend[COL_TTC] = parse_numeric_series(df_trend[COL_TTC])
                    agg_dict[COL_TTC] = 'sum'

                if agg_dict:
                    df_group = df_trend.groupby('Mois').agg(agg_dict).reset_index()

                    fig_mix = go.Figure()

                    # Barres pour le Volume (Colis)
                    if COL_COLIS and COL_COLIS in df_group.columns:
                        fig_mix.add_trace(go.Bar(
                            x=df_group['Mois'], y=df_group[COL_COLIS],
                            name='Volume (Colis)',
                            marker_color='rgba(0, 180, 216, 0.6)',
                            yaxis='y'
                        ))

                    # Ligne pour le CA (TTC)
                    if COL_TTC and COL_TTC in df_group.columns:
                        fig_mix.add_trace(go.Scatter(
                            x=df_group['Mois'], y=df_group[COL_TTC],
                            name='C.A (TTC)',
                            mode='lines+markers',
                            line=dict(color='#0066FF', width=3),
                            marker=dict(size=8, color='white', line=dict(width=2, color='#0066FF')),
                            yaxis='y2'
                        ))

                    fig_mix.update_layout(
                        title="Évolution Mensuelle : Volume vs Chiffre d'Affaires",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#1E293B'),
                        hovermode='x unified',
                        yaxis=dict(title='Volume (Colis)', showgrid=False, color='#64748B'),
                        yaxis2=dict(title='C.A (DA)', overlaying='y', side='right', showgrid=True,
                                    gridcolor='rgba(0,0,0,0.05)', color='#64748B'),
                        xaxis=dict(showgrid=False),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_mix, use_container_width=True)
        else:
            st.info("📊 Les données de ventes ne sont pas encore importées pour visualiser l'évolution mensuelle.")


with tab2:
    st.markdown("### Détails Financiers & Logistiques")
    c_log1, c_log2 = st.columns(2)
    with c_log1:
        st.markdown("#### Statistiques Logistiques")
        st.write(f"- **Total Colis Expédiés :** {metrics['total_colis']:,}")
        st.write(f"- **Lignes de Commandes Traitées :** {metrics['total_lignes']:,}")
        st.write(f"- **Références / Bons Uniques :** {metrics['total_refs']:,}")

        # Donut Chart Statut Recouvrement (depuis vraies données recouvrement)
        if not df_rec_c.empty and 'Statut' in df_rec_c.columns:
            fig_pie = px.pie(df_rec_c, names='Statut', hole=0.6, title="Répartition des Statuts de Recouvrement",
                             color_discrete_sequence=['#10B981', '#F59E0B', '#EF4444', '#6366F1', '#8B5CF6'])
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#1E293B"))
            st.plotly_chart(fig_pie, use_container_width=True)

    with c_log2:
        st.markdown("#### Base de Données des Ventes (Filtrée)")
        if not df_ven_c.empty:
            cols_display = [c for c in [COL_DATE, COL_REF, COL_COLIS, COL_LIGNES, COL_TTC, COL_REGION] if c and c in df_ven_c.columns]
            if cols_display:
                df_show = df_ven_c[cols_display].copy()
                if COL_DATE and COL_DATE in df_show.columns:
                    df_show = df_show.sort_values(COL_DATE, ascending=False)
                st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_ven_c, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune vente trouvée pour ce client sur la période sélectionnée.")

with tab3:
    st.markdown("### ⚠️ Suivi des Incidents & Réclamations")
    if not df_val_c.empty:
        st.error(f"{len(df_val_c)} anomalies / incidents détectés pour ce client.")
        cols_reclam = [c for c in df_val_c.columns if c in ['date', 'reference', 'statut', 'motif', 'type', 'produit', 'qte_reclam', 'reponse']]
        if cols_reclam:
            df_display_reclam = df_val_c[cols_reclam].copy()
            if 'date' in df_display_reclam.columns:
                df_display_reclam = df_display_reclam.sort_values('date', ascending=False)
            st.dataframe(df_display_reclam, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_val_c, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Aucune réclamation ou anomalie détectée pour ce client sur la période sélectionnée. Excellence opérationnelle !")


# =============================================================================
# ONGLET 4 : FICHE CLIENT DÉTAILLÉE (Hub Central Interconnecté)
# =============================================================================
with tab4:

    # ─── SECTION 1 : CARTE D'IDENTITÉ CLIENT ─────────────────────────────────
    st.markdown("### 🏥 Identité & Coordonnées")

    # Récupération des infos d'identité depuis la Base Clients (Admin Centrale)
    id_info = {
        "Nom Client": client_selectionne,
        "Wilaya / Région": "N/A",
        "Adresse": "Non renseignée",
        "Téléphone": "Non renseigné",
        "Commercial Attaché": "N/A",
        "Livreur Habituel": "N/A",
    }

    if not df_clients_base.empty:
        # Recherche du client dans la base clients (multi-colonnes possibles)
        col_nom = _detect_col(df_clients_base, ["Nom_Pharmacie", "Nom Client", "Nom", "client"])
        if col_nom:
            match_client = df_clients_base[df_clients_base[col_nom].astype(str).str.strip() == client_propre]
            if match_client.empty:
                # Tentative avec upper()
                match_client = df_clients_base[df_clients_base[col_nom].astype(str).str.strip().str.upper() == client_propre.upper()]
            if not match_client.empty:
                row = match_client.iloc[0]
                id_info["Wilaya / Région"] = str(row.get("Wilaya", row.get("Region", row.get("Région", "N/A")))).strip()
                if id_info["Wilaya / Région"].lower() in ("nan", ""): id_info["Wilaya / Région"] = "N/A"

                id_info["Adresse"] = str(row.get("Adresse", "Non renseignée")).strip()
                if id_info["Adresse"].lower() in ("nan", ""): id_info["Adresse"] = "Non renseignée"

                tel = str(row.get("Telephone", row.get("Téléphone", row.get("Mobile", "Non renseigné")))).strip()
                id_info["Téléphone"] = tel if tel.lower() not in ("nan", "") else "Non renseigné"

                com = str(row.get("Commercial_Reserve", row.get("Commercial", row.get("Delegue", "N/A")))).strip()
                id_info["Commercial Attaché"] = com if com.lower() not in ("nan", "") else "N/A"

    # Livreur habituel depuis le Recouvrement
    if not df_rec_c.empty and 'Livreur' in df_rec_c.columns:
        livreurs = df_rec_c['Livreur'].dropna().astype(str).str.strip()
        livreurs = livreurs[livreurs != ""]
        if not livreurs.empty:
            id_info["Livreur Habituel"] = livreurs.mode().iloc[0] if not livreurs.mode().empty else livreurs.iloc[0]

    with st.container(border=True):
        c_id1, c_id2, c_id3 = st.columns(3)
        with c_id1:
            st.markdown(f"""
            <div style='padding:4px 0'>
                <span style='color:var(--text-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Nom Client</span><br>
                <strong style='font-size:1.1rem;color:var(--text-main);'>{id_info['Nom Client']}</strong>
            </div>
            <div style='padding:8px 0'>
                <span style='color:var(--text-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Wilaya / Région</span><br>
                <strong style='color:var(--text-main);'>📍 {id_info['Wilaya / Région']}</strong>
            </div>
            """, unsafe_allow_html=True)
        with c_id2:
            st.markdown(f"""
            <div style='padding:4px 0'>
                <span style='color:var(--text-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Adresse</span><br>
                <strong style='color:var(--text-main);'>{id_info['Adresse']}</strong>
            </div>
            <div style='padding:8px 0'>
                <span style='color:var(--text-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Téléphone</span><br>
                <strong style='color:var(--text-main);'>📞 {id_info['Téléphone']}</strong>
            </div>
            """, unsafe_allow_html=True)
        with c_id3:
            st.markdown(f"""
            <div style='padding:4px 0'>
                <span style='color:var(--text-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Commercial Attaché</span><br>
                <strong style='color:var(--text-main);'>👤 {id_info['Commercial Attaché']}</strong>
            </div>
            <div style='padding:8px 0'>
                <span style='color:var(--text-muted);font-size:.75rem;text-transform:uppercase;letter-spacing:1px;font-weight:600;'>Livreur Habituel</span><br>
                <strong style='color:var(--text-main);'>🚚 {id_info['Livreur Habituel']}</strong>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── SECTION 2 : GRILLE DE KPI INTERCONNECTÉS ─────────────────────────────
    st.markdown("### 📊 Métriques Interconnectées (Vue Croisée)")
    st.caption("Données agrégées depuis les modules Ventes, Recouvrement & Réclamations — filtrées sur la période choisie.")

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric(
            label="⚠️ Réclamations",
            value=metrics['total_litiges'],
            delta=f"{metrics['taux_reclamation']*100:.1f}% du total",
            delta_color="inverse"
        )
    with k2:
        st.metric(
            label="📝 Lignes Commandées",
            value=f"{metrics['total_lignes']:,}"
        )
    with k3:
        st.metric(
            label="📄 Commandes Totales",
            value=metrics['total_commandes']
        )
    with k4:
        st.metric(
            label="📦 Volume Colis Reçus",
            value=f"{metrics['total_colis']:,}"
        )
    with k5:
        st.metric(
            label="💸 Encours / Dette",
            value=f"{metrics['reste_a_payer']:,.0f} DA",
            delta="Dette active" if metrics['reste_a_payer'] > 0 else "Solde OK",
            delta_color="inverse" if metrics['reste_a_payer'] > 0 else "normal"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── SECTION 3 : ACTIONS INTERACTIVES (BOUTONS → POPUPS) ──────────────────
    st.markdown("### 🔍 Actions & Détails Interactifs")

    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        with st.container(border=True):
            st.markdown(f"""
            <div style='text-align:center; padding: 8px 0;'>
                <div style='font-size:2rem;'>⚠️</div>
                <div style='font-weight:800; font-size:1.1rem; color:var(--text-main);'>{metrics['total_litiges']}</div>
                <div style='color:var(--text-muted); font-size:.8rem; margin-bottom:8px; font-weight:600;'>Réclamations</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 Plus de détails Réclamations", use_container_width=True, type="secondary", key="btn_dlg_reclam"):
                dialog_reclamations(df_val_c)

    with btn_col2:
        with st.container(border=True):
            st.markdown(f"""
            <div style='text-align:center; padding: 8px 0;'>
                <div style='font-size:2rem;'>📄</div>
                <div style='font-weight:800; font-size:1.1rem; color:var(--text-main);'>{metrics['total_commandes']}</div>
                <div style='color:var(--text-muted); font-size:.8rem; margin-bottom:8px; font-weight:600;'>Factures / BL</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("📄 Détails Factures & Colissage", use_container_width=True, type="secondary", key="btn_dlg_factures"):
                dialog_factures(df_ven_c)

    with btn_col3:
        with st.container(border=True):
            ca_k = f"{metrics['total_ttc']/1000:.0f} K" if metrics['total_ttc'] < 1000000 else f"{metrics['total_ttc']/1000000:.1f} M"
            st.markdown(f"""
            <div style='text-align:center; padding: 8px 0;'>
                <div style='font-size:2rem;'>💰</div>
                <div style='font-weight:800; font-size:1.1rem; color:var(--text-main);'>{ca_k}</div>
                <div style='color:var(--text-muted); font-size:.8rem; margin-bottom:8px; font-weight:600;'>CA Total (DA)</div>
            </div>
            """, unsafe_allow_html=True)
            taux_regl = (1 - metrics['reste_a_payer'] / metrics['total_ttc']) * 100 if metrics['total_ttc'] > 0 else 100
            st.progress(min(int(taux_regl), 100), text=f"Règlement : {taux_regl:.0f}%")
