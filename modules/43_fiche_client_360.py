import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# ==========================================
# 1. GÉNÉRATION DES DONNÉES MOCKÉES
# (A remplacer plus tard par load_gs_data)
# ==========================================
@st.cache_data
def load_mock_data():
    np.random.seed(42)
    random.seed(42)
    
    clients = [f"PHARMACIE {chr(65+i)}{chr(65+j)}" for i in range(5) for j in range(5)]
    dates = [datetime.now() - timedelta(days=x) for x in range(365)]
    
    # 1. MOCK: Suivi Validation
    data_val = []
    for _ in range(500):
        c = random.choice(clients)
        d = random.choice(dates)
        ref = f"CMD-{random.randint(1000, 9999)}"
        statut = random.choice(["Validé", "Rejeté", "En cours", "Anomalie"])
        remarque = random.choice(["", "", "", "RAS", "Retard transporteur", "Colis endommagé", "Client injoignable"])
        data_val.append({
            "validation": "OUI", "impression": "OUI", "expedition": "OUI", 
            "Statut": statut, "Référence": ref, "Date": d.strftime("%Y-%m-%d"), 
            "Client": c, "Région": "ALGER", "Valeur": round(random.uniform(5000, 150000), 2), 
            "Remarque": remarque, "Date clôture": (d + timedelta(days=2)).strftime("%Y-%m-%d")
        })
    df_validation = pd.DataFrame(data_val)
    
    # 2. MOCK: Suivi Livraisons
    data_liv = []
    for row in data_val:
        if row["Statut"] != "Rejeté":
            d = datetime.strptime(row["Date"], "%Y-%m-%d") + timedelta(days=1)
            data_liv.append({
                "N°Bon": f"BL-{random.randint(10000, 99999)}", "Réf.": row["Référence"],
                "Date": d.strftime("%Y-%m-%d"), "Région": row["Région"], "Livreur": "Ahmed",
                "Itinéraire": "ITIN-1", "Vehicule": "Camionnette", "Total TTC": row["Valeur"],
                "Statut": random.choice(["Livré", "Livré", "Livré", "Retour Partiel", "Non Livré"]),
                "Vérification": "OK"
            })
    df_livraisons = pd.DataFrame(data_liv)
    
    # 3. MOCK: Détails Ventes
    data_ventes = []
    for row in data_val:
        if row["Statut"] != "Rejeté":
            ttc = row["Valeur"]
            marge = ttc * random.uniform(0.1, 0.25)
            # 80% des factures sont réglées totalement
            is_regle = random.random() > 0.2
            regle = ttc if is_regle else ttc * random.uniform(0, 0.9)
            reste = ttc - regle
            
            data_ventes.append({
                "Client": row["Client"], "Référence": row["Référence"],
                "Nbr Ligne": random.randint(1, 50), "Colis": random.randint(1, 15),
                "Date Création": row["Date"], "B.L": f"BL-{random.randint(10000, 99999)}",
                "Marge": round(marge, 2), "T.T.C": round(ttc, 2),
                "Montant Réglé": round(regle, 2), "Reste à payer": round(reste, 2),
                "Commercial Attaché": "Younes", "Statut": "Facturé", "Wilaya": "Alger"
            })
    df_ventes = pd.DataFrame(data_ventes)
    # Conversion explicite des dates en datetime
    df_validation['Date'] = pd.to_datetime(df_validation['Date'])
    df_livraisons['Date'] = pd.to_datetime(df_livraisons['Date'])
    df_ventes['Date Création'] = pd.to_datetime(df_ventes['Date Création'])
    
    return df_validation, df_livraisons, df_ventes


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
    
    # 2. Régularité (Max 25) - Approximation : nbr de commandes
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
    else: score -= 10 # Malus !
        
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

# INJECTION CSS PREMIUM
st.markdown("""
<style>
    /* Palette & Variables */
    :root {
        --bg-dark: #1E1E24;
        --accent-blue: #0066FF;
        --accent-cyan: #00B4D8;
        --card-bg: rgba(255, 255, 255, 0.03);
        --card-border: rgba(255, 255, 255, 0.08);
        --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    /* Global App Background */
    .stApp {
        background-color: var(--bg-dark);
        color: white;
    }
    
    /* Custom KPI Cards */
    .kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 16px;
        padding: 20px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease, border-color 0.3s ease;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        border-color: var(--accent-cyan);
    }
    .kpi-title {
        font-size: 0.9rem;
        color: #A0AEC0;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: white;
        margin: 0;
    }
    .kpi-value.gradient-text {
        background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Custom Alerts */
    .alert-premium {
        background: linear-gradient(90deg, rgba(220, 38, 38, 0.15), rgba(220, 38, 38, 0.05));
        border-left: 4px solid #EF4444;
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .alert-icon { font-size: 1.8rem; }
    .alert-content p { margin: 0; color: #FCA5A5; font-weight: 500; }
    .alert-content h4 { margin: 0 0 5px 0; color: white; }
    
    /* Header Styling */
    .header-title {
        font-weight: 900;
        font-size: 2.5rem;
        letter-spacing: -1px;
        margin-bottom: 0;
    }
    .header-subtitle {
        color: var(--accent-cyan);
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# --- CHARGEMENT DES DONNÉES ---
# TODO: Remplacer load_mock_data() par load_gs_data(...) pour la prod
df_validation, df_livraisons, df_ventes = load_mock_data()

# Préparation de la liste des clients (nettoyée des espaces invisibles)
liste_clients = sorted(df_ventes['Client'].dropna().astype(str).str.strip().str.upper().unique().tolist())

# --- SIDEBAR: FILTRES ---
with st.sidebar:
    st.markdown("### ⚙️ Paramètres 360°")
    # Placé tout en haut de la logique UI
    if 'client_selectionne' not in st.session_state:
        st.session_state.client_selectionne = liste_clients[0] if liste_clients else ""
        
    selected_client = st.selectbox(
        "Sélectionner un Client", 
        liste_clients,
        index=liste_clients.index(st.session_state.client_selectionne) if st.session_state.client_selectionne in liste_clients else 0
    )
    st.session_state.client_selectionne = selected_client
    
    time_filter = st.radio("Période d'analyse", ["Historique Global", "Plage Personnalisée"])
    start_date, end_date = None, None
    if time_filter == "Plage Personnalisée":
        dates = st.date_input("Sélectionnez la plage", 
                              [datetime.today() - timedelta(days=30), datetime.today()])
        if len(dates) == 2:
            start_date, end_date = dates

# --- FILTRAGE DES DONNÉES (CORRECTION PANDAS) ---
client_propre = st.session_state.client_selectionne.strip().upper()

# Application du .str.strip().str.upper() pour éviter le bug des espaces invisibles
df_val_c = df_validation[df_validation['Client'].astype(str).str.strip().str.upper() == client_propre].copy()
df_liv_c = df_livraisons[df_livraisons['Réf.'].isin(df_val_c['Référence'])].copy()
df_ven_c = df_ventes[df_ventes['Client'].astype(str).str.strip().str.upper() == client_propre].copy()

# Application du filtre temporel
if time_filter == "Plage Personnalisée" and start_date and end_date:
    sd, ed = pd.to_datetime(start_date), pd.to_datetime(end_date)
    df_ven_c['Date Création'] = pd.to_datetime(df_ven_c['Date Création'])
    df_ven_c = df_ven_c[(df_ven_c['Date Création'] >= sd) & (df_ven_c['Date Création'] <= ed)]
    
    df_val_c['Date'] = pd.to_datetime(df_val_c['Date'])
    df_val_c = df_val_c[(df_val_c['Date'] >= sd) & (df_val_c['Date'] <= ed)]

# --- CALCUL DES MÉTRIQUES ---
metrics = {
    'total_commandes': len(df_ven_c),
    'total_colis': df_ven_c['Colis'].sum(),
    'total_lignes': df_ven_c['Nbr Ligne'].sum(),
    'total_ttc': df_ven_c['T.T.C'].sum(),
    'marge_brute': df_ven_c['Marge'].sum(),
    'reste_a_payer': df_ven_c['Reste à payer'].sum(),
}

# Calcul Réclamations (Statut 'Anomalie' ou Remarque négative)
mots_critiques = ["endommagé", "retard", "injoignable", "cassé", "manquant"]
mask_anomalie = df_val_c['Statut'].str.lower() == 'anomalie'
mask_remarque = df_val_c['Remarque'].str.lower().apply(lambda x: any(m in x for m in mots_critiques))
litiges = df_val_c[mask_anomalie | mask_remarque]

metrics['total_litiges'] = len(litiges)
metrics['taux_reclamation'] = metrics['total_litiges'] / metrics['total_commandes'] if metrics['total_commandes'] > 0 else 0

score = calculate_client_score(metrics)

# --- HEADER APP ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<p class="header-subtitle">MODULE INTELLIGENCE ARTIFICIELLE & DATA</p>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="header-title">{selected_client}</h1>', unsafe_allow_html=True)
with c_head2:
    # Calcul sécurisé de la dernière activité
    if not df_ven_c.empty:
        last_date = pd.to_datetime(df_ven_c['Date Création']).max()
        last_date_str = last_date.strftime('%d/%m/%Y') if pd.notna(last_date) else 'N/A'
    else:
        last_date_str = 'N/A'
    st.markdown(f"""
    <div style="text-align: right; margin-top: 20px;">
        <span style="color:#A0AEC0; font-size:12px;">Dernière Activité</span><br>
        <strong style="color:white; font-size:16px;">{last_date_str}</strong>
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
    <div class="alert-premium" style="border-left-color: #F59E0B; background: linear-gradient(90deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));">
        <div class="alert-icon">🚨</div>
        <div class="alert-content">
            <h4 style="color:#FCD34D;">Vigilance Qualité</h4>
            <p style="color:#FDE68A;">Taux de réclamation critique ({metrics['taux_reclamation']*100:.1f}%). Analyse requise sur les processus de préparation.</p>
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
    cols_reclam = [c for c in ['Date', 'Référence', 'Remarque', 'Statut', 'Valeur'] if c in df_litiges.columns]
    df_show = df_litiges[cols_reclam].copy()
    if 'Date' in df_show.columns:
        df_show['Date'] = pd.to_datetime(df_show['Date']).dt.strftime('%d/%m/%Y')
    if 'Valeur' in df_show.columns:
        df_show['Valeur'] = df_show['Valeur'].apply(lambda x: f"{x:,.0f} DA")
    st.dataframe(df_show.sort_values('Date', ascending=False) if 'Date' in df_show.columns else df_show,
                 use_container_width=True, hide_index=True)


@st.dialog("📄 Détails Factures & Colissage")
def dialog_factures(df_cmds: pd.DataFrame):
    """Popup affichant le listing complet des commandes/factures du client."""
    if df_cmds.empty:
        st.info("Aucune commande trouvée sur la période sélectionnée.")
        return
    st.markdown(f"**{len(df_cmds)} commande(s) / facture(s)**")
    cols_factured = [c for c in ['B.L', 'Date Création', 'Référence', 'Nbr Ligne', 'Colis', 'T.T.C', 'Reste à payer', 'Statut'] if c in df_cmds.columns]
    df_show = df_cmds[cols_factured].copy()
    if 'Date Création' in df_show.columns:
        df_show['Date Création'] = pd.to_datetime(df_show['Date Création']).dt.strftime('%d/%m/%Y')
    for money_col in ['T.T.C', 'Reste à payer']:
        if money_col in df_show.columns:
            df_show[money_col] = df_show[money_col].apply(lambda x: f"{x:,.2f} DA")
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.markdown(f"""
    ---
    📦 **Total Colis :** `{int(df_cmds['Colis'].sum()):,}` &nbsp;| 
    📝 **Total Lignes :** `{int(df_cmds['Nbr Ligne'].sum()):,}` &nbsp;| 
    💰 **CA Total :** `{df_cmds['T.T.C'].sum():,.0f} DA`
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
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Chiffre d'Affaires</div>
            <p class="kpi-value gradient-text">{metrics['total_ttc']/1000000:.1f} M</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Marge Brute</div>
            <p class="kpi-value" style="color: #00B4D8;">{metrics['marge_brute']/1000000:.1f} M</p>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Dette Client</div>
            <p class="kpi-value" style="color: {'#EF4444' if metrics['reste_a_payer'] > 0 else '#10B981'};">
                {metrics['reste_a_payer']/1000:.1f} K
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_gauge, col_trend = st.columns([1, 2])
    with col_gauge:
        # Gauge Chart Plotly
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "SCORE DE FIDÉLITÉ 360°", 'font': {'size': 16, 'color': '#A0AEC0'}},
            gauge = {
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
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=350)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_trend:
        # Graphique Mixte (Barres + Ligne)
        if not df_ven_c.empty:
            df_trend = df_ven_c.copy()
            df_trend['Mois'] = pd.to_datetime(df_trend['Date Création']).dt.to_period('M').astype(str)
            df_group = df_trend.groupby('Mois').agg({'Colis': 'sum', 'T.T.C': 'sum'}).reset_index()
            
            fig_mix = go.Figure()
            # Barres pour le Volume (Colis)
            fig_mix.add_trace(go.Bar(
                x=df_group['Mois'], y=df_group['Colis'],
                name='Volume (Colis)',
                marker_color='rgba(0, 180, 216, 0.6)',
                yaxis='y'
            ))
            # Ligne pour le CA (TTC)
            fig_mix.add_trace(go.Scatter(
                x=df_group['Mois'], y=df_group['T.T.C'],
                name='C.A (TTC)',
                mode='lines+markers',
                line=dict(color='#0066FF', width=3),
                marker=dict(size=8, color='white', line=dict(width=2, color='#0066FF')),
                yaxis='y2'
            ))
            
            fig_mix.update_layout(
                title='Évolution Mensuelle : Volume vs Chiffre d\'Affaires',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                hovermode='x unified',
                yaxis=dict(title='Volume (Colis)', showgrid=False, color='rgba(255,255,255,0.6)'),
                yaxis2=dict(title='C.A (DA)', overlaying='y', side='right', showgrid=True, gridcolor='rgba(255,255,255,0.1)', color='rgba(255,255,255,0.6)'),
                xaxis=dict(showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_mix, use_container_width=True)


with tab2:
    st.markdown("### Détails Financiers & Logistiques")
    c_log1, c_log2 = st.columns(2)
    with c_log1:
        st.markdown("#### Statistiques Logistiques")
        st.write(f"- **Total Colis Expédiés :** {metrics['total_colis']}")
        st.write(f"- **Lignes de Commandes Traitées :** {metrics['total_lignes']}")
        
        # Donut Chart Statut Livraisons
        if not df_liv_c.empty:
            fig_pie = px.pie(df_liv_c, names='Statut', hole=0.6, title="Répartition des Statuts de Livraison",
                             color_discrete_sequence=['#10B981', '#F59E0B', '#EF4444'])
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig_pie, use_container_width=True)

    with c_log2:
        st.markdown("#### Base de Données des Ventes (Filtrée)")
        st.dataframe(df_ven_c[['Date Création', 'Référence', 'B.L', 'T.T.C', 'Reste à payer', 'Statut']].sort_values('Date Création', ascending=False), use_container_width=True)

with tab3:
    st.markdown("### ⚠️ Suivi des Incidents & Réclamations")
    if not litiges.empty:
        st.error(f"{len(litiges)} anomalies / incidents détectés pour ce client.")
        st.dataframe(litiges[['Date', 'Référence', 'Statut', 'Remarque', 'Valeur']].sort_values('Date', ascending=False), use_container_width=True)
    else:
        st.success("✅ Aucune réclamation ou anomalie détectée pour ce client sur la période sélectionnée. Excellence opérationnelle !")


# =============================================================================
# ONGLET 4 : FICHE CLIENT DÉTAILLÉE (Hub Central Interconnecté)
# =============================================================================
with tab4:

    # ─── SECTION 1 : CARTE D’IDENTITÉ CLIENT ─────────────────────────────────
    st.markdown("### 🏥 Identité & Coordonnées")

    # Récupération des données d’identité depuis le premier enregistrement du client
    id_row = df_ven_c.iloc[0] if not df_ven_c.empty else {}
    id_info = {
        "Nom Client"        : client_propre,
        "Wilaya / Région"   : id_row.get("Wilaya", "N/A") if hasattr(id_row, "get") else "N/A",
        "Adresse"           : id_row.get("Adresse", "Non renseignée") if hasattr(id_row, "get") else "Non renseignée",
        "Téléphone"         : id_row.get("Téléphone", "Non renseigné") if hasattr(id_row, "get") else "Non renseigné",
        "Commercial Attaché": id_row.get("Commercial Attaché", "N/A") if hasattr(id_row, "get") else "N/A",
        "Livreur Habituel"  : "Ahmed",
    }

    with st.container(border=True):
        c_id1, c_id2, c_id3 = st.columns(3)
        with c_id1:
            st.markdown(f"""
            <div style='padding:4px 0'>
                <span style='opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:1px;'>Nom Client</span><br>
                <strong style='font-size:1.1rem;'>{id_info['Nom Client']}</strong>
            </div>
            <div style='padding:8px 0'>
                <span style='opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:1px;'>Wilaya / Région</span><br>
                <strong>📍 {id_info['Wilaya / Région']}</strong>
            </div>
            """, unsafe_allow_html=True)
        with c_id2:
            st.markdown(f"""
            <div style='padding:4px 0'>
                <span style='opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:1px;'>Adresse</span><br>
                <strong>{id_info['Adresse']}</strong>
            </div>
            <div style='padding:8px 0'>
                <span style='opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:1px;'>Téléphone</span><br>
                <strong>📞 {id_info['Téléphone']}</strong>
            </div>
            """, unsafe_allow_html=True)
        with c_id3:
            st.markdown(f"""
            <div style='padding:4px 0'>
                <span style='opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:1px;'>Commercial Attaché</span><br>
                <strong>👤 {id_info['Commercial Attaché']}</strong>
            </div>
            <div style='padding:8px 0'>
                <span style='opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:1px;'>Livreur Habituel</span><br>
                <strong>🚚 {id_info['Livreur Habituel']}</strong>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── SECTION 2 : GRILLE DE KPI INTERCONNECTÉS ─────────────────────────────
    st.markdown("### 📊 Métriques Interconnectées (Vue Croisée)")
    st.caption("Données agrégées depuis les modules Ventes, Recouvrement & Validation — filtrées sur la période choisie.")

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric(
            label="⚠️ Réclamations",
            value=metrics['total_litiges'],
            delta=f"{metrics['taux_reclamation']*100:.1f}% du CA",
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

    # ─── SECTION 3 : ACTIONS INTERACTIVES (BOUTONS ➜ POPUPS) ──────────────────
    st.markdown("### 🔍 Actions & Détails Interactifs")

    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        with st.container(border=True):
            st.markdown(f"""
            <div style='text-align:center; padding: 8px 0;'>
                <div style='font-size:2rem;'>⚠️</div>
                <div style='font-weight:800; font-size:1.1rem;'>{metrics['total_litiges']}</div>
                <div style='opacity:.55; font-size:.8rem; margin-bottom:8px;'>Réclamations</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 Plus de détails Réclamations", use_container_width=True, type="secondary", key="btn_dlg_reclam"):
                dialog_reclamations(litiges)

    with btn_col2:
        with st.container(border=True):
            st.markdown(f"""
            <div style='text-align:center; padding: 8px 0;'>
                <div style='font-size:2rem;'>📄</div>
                <div style='font-weight:800; font-size:1.1rem;'>{metrics['total_commandes']}</div>
                <div style='opacity:.55; font-size:.8rem; margin-bottom:8px;'>Factures / BL</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("📄 Détails Factures & Colissage", use_container_width=True, type="secondary", key="btn_dlg_factures"):
                dialog_factures(df_ven_c)

    with btn_col3:
        with st.container(border=True):
            st.markdown(f"""
            <div style='text-align:center; padding: 8px 0;'>
                <div style='font-size:2rem;'>💰</div>
                <div style='font-weight:800; font-size:1.1rem;'>{metrics['total_ttc']/1000:.0f} K</div>
                <div style='opacity:.55; font-size:.8rem; margin-bottom:8px;'>CA Total (DA)</div>
            </div>
            """, unsafe_allow_html=True)
            taux_regl = (1 - metrics['reste_a_payer'] / metrics['total_ttc']) * 100 if metrics['total_ttc'] > 0 else 100
            st.progress(min(int(taux_regl), 100), text=f"Règlement : {taux_regl:.0f}%")

