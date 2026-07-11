import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# Configuration de la page
st.set_page_config(page_title="Performance de la Flotte", layout="wide", page_icon="🚚")

# ==========================================
# 1. INJECTION CSS PREMIUM (Aesthetics & Theme)
# ==========================================
st.markdown("""
<style>
    /* Palette & Variables */
    :root {
        --bg-dark: #1E1E24;
        --accent-blue: #0066FF;
        --accent-cyan: #00B4D8;
        --accent-purple: #7B2CBF;
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
    .kpi-container {
        display: flex;
        gap: 20px;
        margin-bottom: 25px;
    }
    .kpi-card {
        flex: 1;
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 16px;
        padding: 24px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease, border-color 0.3s ease;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        border-color: var(--accent-cyan);
    }
    .kpi-title {
        font-size: 0.85rem;
        color: #A0AEC0;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: white;
        margin: 0;
    }
    .kpi-value.gradient-text {
        background: linear-gradient(90deg, #00B4D8, #7B2CBF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Table Styling & Anomalies Card */
    .anomaly-card {
        background: rgba(220, 38, 38, 0.05);
        border: 1px solid rgba(220, 38, 38, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-top: 25px;
        box-shadow: var(--shadow);
    }
    .anomaly-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #F87171;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Header Styling */
    .header-title {
        font-weight: 900;
        font-size: 2.5rem;
        letter-spacing: -1px;
        margin-bottom: 5px;
        background: linear-gradient(135deg, #FFF, #A0AEC0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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


# ==========================================
# 2. GENERATION DU JEU DE DONNÉES SIMULÉES (MOCK DATA)
# ==========================================
@st.cache_data
def load_mock_fleet_data():
    """
    Simule les données d'expédition et de commandes pour la flotte de livraison.
    A REMPLACER PAR load_gs_data(...) EN PRODUCTION.
    """
    np.random.seed(42)
    random.seed(42)
    
    # Paramètres de simulation
    n_commandes = 600
    date_fin = datetime.now()
    date_debut = date_fin - timedelta(days=60)
    
    # 1. Génération des Commandes Clients
    regions = ["Alger", "Blida", "Tipaza", "Boumerdes", "Oran", "Constantine", "Sétif", "Tizi Ouzou", "Chlef", "Béjaïa"]
    clients = [f"Pharmacie {chr(65+i)}{chr(65+j)}" for i in range(10) for j in range(5)]
    
    commandes_list = []
    for i in range(n_commandes):
        ref = f"CMD-{10000 + i}"
        client = random.choice(clients)
        region = random.choice(regions)
        colis = random.randint(1, 18)
        commandes_list.append({
            "Référence": ref,
            "Client": client,
            "Région/Wilaya": region,
            "Nombre de Colis": colis
        })
    df_commandes = pd.DataFrame(commandes_list)
    
    # 2. Génération des Expéditions de la Flotte
    livreurs = ["Sofiane B.", "Amine K.", "Karim T.", "Reda L.", "Yassine M.", "Brahim H."]
    vehicules = ["00123-118-16 (Partner)", "00542-120-16 (Master)", "00989-115-09 (Jumper)", "00412-122-16 (Kangoo)", "00781-121-31 (Berlingo)"]
    status_options = ["Livré", "Livré", "Livré", "Livré", "Retour Partiel", "Non Livré", "En anomalie"]
    itineraires = [f"IT-EST-{i:02d}" for i in range(1, 6)] + [f"IT-OUEST-{i:02d}" for i in range(1, 6)] + [f"IT-ALGER-{i:02d}" for i in range(1, 8)]

    expeditions_list = []
    for i in range(n_commandes):
        ref = f"CMD-{10000 + i}"
        livreur = random.choice(livreurs)
        # Association stable livreur -> véhicule pour le réalisme
        liv_idx = livreurs.index(livreur)
        vehicule = vehicules[liv_idx % len(vehicules)]
        itineraire = random.choice(itineraires)
        
        # Statut de livraison (avec anomalie plus ou moins rare)
        statut = random.choices(status_options, weights=[60, 20, 10, 5, 2.5, 1.5, 1.0], k=1)[0]
        
        # Attribution d'une date sur les 60 derniers jours
        jours_offset = random.randint(0, 60)
        date_exp = date_debut + timedelta(days=jours_offset, hours=random.randint(8, 18), minutes=random.randint(0, 59))
        
        expeditions_list.append({
            "Référence du bon": ref,
            "Livreur": livreur,
            "Véhicule/Matricule": vehicule,
            "Itinéraire": itineraire,
            "Statut": statut,
            "Date": date_exp
        })
    df_expeditions = pd.DataFrame(expeditions_list)
    
    return df_expeditions, df_commandes


# --- CHARGEMENT DU JEU DE DONNÉES ---
# TODO: Pour intégrer la vraie BDD en production :
# 1. Importer votre fonction Google Sheets : `from utils.data_loader import load_gs_data`
# 2. Remplacer l'appel ci-dessous par :
#    df_expeditions = load_gs_data(spreadsheet_id, "NomFeuilleExpeditions")
#    df_commandes = load_gs_data(spreadsheet_id, "NomFeuilleCommandes")
#    Puis assurez-vous que les types de dates et de jointure concordent.
df_expeditions, df_commandes = load_mock_fleet_data()


# ==========================================
# 3. FILTRES DANS LA SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("### 🚚 Paramètres de la Flotte")
    
    # 1. Filtre Temporel
    periode = st.selectbox(
        "Sélectionner la Période",
        ["Historique global", "Mois en cours", "Semaine en cours", "7 derniers jours"]
    )
    
    # Date pivot fixe (pour que les filtres marchent avec le mock)
    # Dans une vraie app, on utiliserait datetime.now()
    pivot_date = df_expeditions["Date"].max()
    
    if periode == "Mois en cours":
        start_date = pivot_date.replace(day=1, hour=0, minute=0, second=0)
        df_exp_filtered = df_expeditions[df_expeditions["Date"] >= start_date].copy()
    elif periode == "Semaine en cours":
        start_date = pivot_date - timedelta(days=pivot_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0)
        df_exp_filtered = df_expeditions[df_expeditions["Date"] >= start_date].copy()
    elif periode == "7 derniers jours":
        start_date = pivot_date - timedelta(days=7)
        df_exp_filtered = df_expeditions[df_expeditions["Date"] >= start_date].copy()
    else:
        df_exp_filtered = df_expeditions.copy()
        
    # 2. Filtre par Livreur
    liste_livreurs = ["Tous les livreurs"] + sorted(df_exp_filtered["Livreur"].unique().tolist())
    selected_livreur = st.selectbox("Sélectionner un Livreur", liste_livreurs)
    
    if selected_livreur != "Tous les livreurs":
        df_exp_filtered = df_exp_filtered[df_exp_filtered["Livreur"] == selected_livreur]


# ==========================================
# 4. CALCULS ET CROISEMENTS DE DONNÉES
# ==========================================
# Croisement avec les commandes clients pour récupérer les Wilayas et les colis
df_merged = pd.merge(
    df_exp_filtered,
    df_commandes,
    left_on="Référence du bon",
    right_on="Référence",
    how="inner"
)

# A. Volume total de colis acheminés
total_colis = df_merged["Nombre de Colis"].sum()

# B. Nombre de rotations effectuées par véhicule
# Une rotation = un itinéraire unique par véhicule par jour
df_merged["Date_Jour"] = df_merged["Date"].dt.date
rotations_par_vehicule = df_merged.groupby(["Véhicule/Matricule", "Date_Jour", "Itinéraire"]).size().reset_index()
rotations_counts = rotations_par_vehicule.groupby("Véhicule/Matricule").size().reset_index(name="Rotations")

# C. Indice de dispersion géographique
# Nombre de Régions/Wilayas uniques visitées par un même livreur par jour
dispersion_par_jour = df_merged.groupby(["Livreur", "Date_Jour"])["Région/Wilaya"].nunique().reset_index()
dispersion_moyenne = dispersion_par_jour.groupby("Livreur")["Région/Wilaya"].mean().reset_index()
dispersion_moyenne.columns = ["Livreur", "Dispersion Moyenne"]

# D. Métriques pour KPI Cards
# Top Livreur (plus grand nombre de colis)
colis_par_livreur = df_merged.groupby("Livreur")["Nombre de Colis"].sum().reset_index()
if not colis_par_livreur.empty:
    top_livreur_row = colis_par_livreur.sort_values(by="Nombre de Colis", ascending=False).iloc[0]
    top_livreur_name = top_livreur_row["Livreur"]
    top_livreur_colis = top_livreur_row["Nombre de Colis"]
else:
    top_livreur_name = "Aucun"
    top_livreur_colis = 0

# Véhicule le plus sollicité
if not rotations_counts.empty:
    top_vehicule_row = rotations_counts.sort_values(by="Rotations", ascending=False).iloc[0]
    top_vehicule_name = top_vehicule_row["Véhicule/Matricule"].split(" ")[0]
    top_vehicule_rotations = top_vehicule_row["Rotations"]
else:
    top_vehicule_name = "Aucun"
    top_vehicule_rotations = 0


# ==========================================
# 5. RENDER APP HEADER
# ==========================================
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown('<p class="header-subtitle">MODULE SUIVI LOGISTIQUE & FLOTTE</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="header-title">Performance de la Flotte de Livraison</h1>', unsafe_allow_html=True)
with c_head2:
    st.markdown(f"""
    <div style="text-align: right; margin-top: 20px;">
        <span style="color:#A0AEC0; font-size:12px;">Mise à jour</span><br>
        <strong style="color:white; font-size:16px;">{pivot_date.strftime('%d/%m/%Y %H:%M')}</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ==========================================
# 6. RENDER KPI CARDS (CSS PREMIUM)
# ==========================================
st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-title">🥇 Top Livreur (Volume)</div>
        <p class="kpi-value">{top_livreur_name}</p>
        <span style="color:#00B4D8; font-size:13px; font-weight:600;">{top_livreur_colis:,} colis acheminés</span>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">🚛 Véhicule le plus actif</div>
        <p class="kpi-value">{top_vehicule_name}</p>
        <span style="color:#7B2CBF; font-size:13px; font-weight:600;">{top_vehicule_rotations} rotations uniques</span>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">📦 Volume Global Période</div>
        <p class="kpi-value gradient-text">{total_colis:,}</p>
        <span style="color:#A0AEC0; font-size:13px; font-weight:600;">Colis expédiés de l'entrepôt</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 7. ANALYSE GRAPHIQUE COMPLÈTE
# ==========================================
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### 🏆 Classement d'activité des Livreurs")
    # Leaderboard : Colis par livreur
    colis_par_livreur = colis_par_livreur.sort_values(by="Nombre de Colis", ascending=True)
    
    fig_leaderboard = px.bar(
        colis_par_livreur,
        x="Nombre de Colis",
        y="Livreur",
        orientation="h",
        color="Nombre de Colis",
        color_continuous_scale=["#0055D4", "#00B4D8"],
        text="Nombre de Colis"
    )
    
    fig_leaderboard.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(showgrid=False, title="Nombre total de colis"),
        yaxis=dict(showgrid=False, title=""),
        coloraxis_showscale=False,
        height=380,
        margin=dict(l=0, r=20, t=10, b=10)
    )
    fig_leaderboard.update_traces(
        textposition="inside",
        marker_line_color="rgba(0,0,0,0)",
        hovertemplate="Livreur: %{y}<br>Colis: %{x:,}<extra></extra>"
    )
    st.plotly_chart(fig_leaderboard, use_container_width=True)

with col_right:
    st.markdown("### 📈 Utilisation de la Flotte (Rotations)")
    # Donut Chart : Répartition des rotations par Matricule
    if not rotations_counts.empty:
        fig_donut = px.pie(
            rotations_counts,
            names="Véhicule/Matricule",
            values="Rotations",
            hole=0.6,
            color_discrete_sequence=px.colors.sequential.Sunsetdark
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            height=380,
            margin=dict(l=0, r=0, t=10, b=50)
        )
        fig_donut.update_traces(
            hovertemplate="Véhicule: %{label}<br>Rotations: %{value}<br>Part: %{percent}<extra></extra>"
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.warning("Aucune rotation enregistrée sur cette période.")


# ==========================================
# 8. DEUXIÈME BLOC : DISPERSION GÉOGRAPHIQUE
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
col_disp, col_details = st.columns([1, 1])

with col_disp:
    st.markdown("### 🗺️ Indice de Dispersion Géographique")
    st.markdown(
        "*Indice évaluant la charge mentale et physique des livreurs. Représente le nombre moyen "
        "de Wilayas distinctes desservies par jour.*"
    )
    
    # Jointure avec dispersion moyenne
    disp_sorted = dispersion_moyenne.sort_values(by="Dispersion Moyenne", ascending=False)
    
    fig_disp = go.Figure()
    fig_disp.add_trace(go.Bar(
        x=disp_sorted["Livreur"],
        y=disp_sorted["Dispersion Moyenne"],
        marker=dict(
            color=disp_sorted["Dispersion Moyenne"],
            colorscale="Viridis",
            line=dict(color="rgba(0,0,0,0)")
        ),
        text=disp_sorted["Dispersion Moyenne"].round(2),
        textposition="outside"
    ))
    
    fig_disp.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Wilayas moyennes / jour"),
        height=300,
        margin=dict(l=0, r=0, t=10, b=10)
    )
    st.plotly_chart(fig_disp, use_container_width=True)

with col_details:
    st.markdown("### 📋 Synthèse Opérationnelle par Livreur")
    
    # Agrégation finale pour affichage du tableau synthétique
    df_synth = df_merged.groupby("Livreur").agg(
        colis=("Nombre de Colis", "sum"),
        commandes=("Référence du bon", "count"),
        wilayas_visitees=("Région/Wilaya", "nunique"),
        taux_livre=("Statut", lambda x: (x == "Livré").sum() / len(x) * 100)
    ).reset_index()
    
    df_synth.columns = ["Livreur", "Colis Transportés", "Bons Livrés", "Wilayas Clés", "Taux de Réussite (%)"]
    df_synth["Taux de Réussite (%)"] = df_synth["Taux de Réussite (%)"].round(1)
    
    st.dataframe(
        df_synth.sort_values(by="Colis Transportés", ascending=False),
        use_container_width=True,
        hide_index=True
    )


# ==========================================
# 9. SECTION ANOMALIES & INCIDENTS (TABLEAU DE BORD)
# ==========================================
df_anomalies = df_merged[df_merged["Statut"] == "En anomalie"].copy()

st.markdown(f"""
<div class="anomaly-card">
    <div class="anomaly-title">
        <span>⚠️ Tableau de Bord des Anomalies Logistiques</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not df_anomalies.empty:
    st.markdown(f"**{len(df_anomalies)} livraisons en cours de traitement de litige ou d'anomalie.**")
    st.dataframe(
        df_anomalies[["Date", "Référence du bon", "Client", "Région/Wilaya", "Livreur", "Véhicule/Matricule", "Itinéraire", "Nombre de Colis"]]
        .sort_values(by="Date", ascending=False),
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("✅ Aucune anomalie détectée sur le réseau de livraison sur cette période.")
