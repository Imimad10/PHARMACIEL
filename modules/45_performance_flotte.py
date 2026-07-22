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
    /* Palette & Variables (Thème Clair) */
    :root {
        --accent-blue: #0052FF;
        --accent-cyan: #00B4D8;
        --accent-purple: #7B2CBF;
        --card-bg: #FFFFFF;
        --card-border: #E2E8F0;
        --text-main: #1E293B;
        --text-muted: #64748B;
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
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
        transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
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
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .kpi-title {
        font-size: 0.85rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        font-weight: 700;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--text-main);
        margin: 0;
    }
    .kpi-value.gradient-text {
        background: linear-gradient(90deg, #0052FF, #7B2CBF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Table Styling & Anomalies Card */
    .anomaly-card {
        background: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-radius: 16px;
        padding: 20px;
        margin-top: 25px;
        box-shadow: var(--shadow);
    }
    .anomaly-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #B91C1C;
        margin-bottom: 0px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Header Styling */
    .header-title {
        font-weight: 900;
        font-size: 2.5rem;
        letter-spacing: -1px;
        color: var(--text-main);
        margin-bottom: 5px;
    }
    .header-subtitle {
        color: var(--accent-blue);
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. CHARGEMENT DU JEU DE DONNÉES RÉELLES
# ==========================================
from utils_gsheets import load_gs_data

@st.cache_data(ttl=300)
def load_real_fleet_data():
    """
    Charge les données réelles des expéditions depuis la base centrale.
    """
    df_exp = load_gs_data("Expeditions", "data/db_expeditions.csv", None)
    df_cmd = load_gs_data("Commandes", "data/db_commandes.csv", None)
    return df_exp, df_cmd

df_expeditions, df_commandes = load_real_fleet_data()



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
    
    if df_expeditions.empty:
        df_exp_filtered = pd.DataFrame()
        pivot_date = datetime.now()
    else:
        if "Date" in df_expeditions.columns:
            df_expeditions["Date"] = pd.to_datetime(df_expeditions["Date"], errors='coerce')
        
        pivot_date = datetime.now()
        
        if periode == "Mois en cours":
            start_date = pivot_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            df_exp_filtered = df_expeditions[df_expeditions["Date"] >= start_date].copy()
        elif periode == "Semaine en cours":
            start_date = pivot_date - timedelta(days=pivot_date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            df_exp_filtered = df_expeditions[df_expeditions["Date"] >= start_date].copy()
        elif periode == "7 derniers jours":
            start_date = pivot_date - timedelta(days=7)
            df_exp_filtered = df_expeditions[df_expeditions["Date"] >= start_date].copy()
        else:
            df_exp_filtered = df_expeditions.copy()
            
    # 2. Filtre par Livreur
    if not df_exp_filtered.empty and "Livreur" in df_exp_filtered.columns:
        livreurs_dispos = [str(x) for x in df_exp_filtered["Livreur"].dropna().unique().tolist()]
        liste_livreurs = ["Tous les livreurs"] + sorted(livreurs_dispos)
    else:
        liste_livreurs = ["Tous les livreurs"]
        
    selected_livreur = st.selectbox("Sélectionner un Livreur", liste_livreurs)
    
    if selected_livreur != "Tous les livreurs" and not df_exp_filtered.empty:
        df_exp_filtered = df_exp_filtered[df_exp_filtered["Livreur"] == selected_livreur]


# ==========================================
# 4. CALCULS ET CROISEMENTS DE DONNÉES
# ==========================================
if df_exp_filtered.empty:
    st.info("Aucune donnée d'expédition réelle enregistrée pour la période sélectionnée.")
    st.stop()

# Croisement avec les commandes clients pour récupérer les Wilayas et les colis
if not df_commandes.empty and "Référence du bon" in df_exp_filtered.columns and "Référence" in df_commandes.columns:
    df_merged = pd.merge(
        df_exp_filtered,
        df_commandes,
        left_on="Référence du bon",
        right_on="Référence",
        how="inner"
    )
else:
    df_merged = df_exp_filtered.copy()
    if "Nombre de Colis" not in df_merged.columns:
        df_merged["Nombre de Colis"] = 1
    if "Région/Wilaya" not in df_merged.columns:
        df_merged["Région/Wilaya"] = "Inconnue"

# ── TRAÇABILITÉ : Utiliser secteur_fige (figé au moment de l'opération) ──
# Si secteur_fige existe, il prime sur Région/Wilaya actuelle du livreur.
# Cela garantit que les stats passées du livreur refletent les wilayas
# qu'il a réellement desservies à cette époque.
if "secteur_fige" in df_merged.columns:
    df_merged["Secteur_Historique"] = df_merged["secteur_fige"].fillna(
        df_merged.get("Région/Wilaya", "Inconnue")
    )
else:
    df_merged["Secteur_Historique"] = df_merged.get("Région/Wilaya", "Inconnue")

df_merged["Secteur_Historique"] = df_merged["Secteur_Historique"].fillna("Inconnue").astype(str)

# 3. Filtre par Secteur Historique
with st.sidebar:
    secteurs_dispo = ["Tous les secteurs"] + sorted(df_merged["Secteur_Historique"].dropna().unique().tolist())
    selected_secteur = st.selectbox("🗺️ Filtrer par Secteur (historique figé)", secteurs_dispo)
    if selected_secteur != "Tous les secteurs":
        df_merged = df_merged[df_merged["Secteur_Historique"].str.lower() == selected_secteur.lower()]

if df_merged.empty:
    st.info("Aucune donnée d'expédition réelle enregistrée pour la période sélectionnée.")
    st.stop()

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
        <span style="color:#64748B; font-size:12px; font-weight:600;">Mise à jour</span><br>
        <strong style="color:#1E293B; font-size:16px;">{pivot_date.strftime('%d/%m/%Y %H:%M')}</strong>
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
        <span style="color:#64748B; font-size:13px; font-weight:600;">Colis expédiés de l'entrepôt</span>
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
        font=dict(color="#1E293B"),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="Nombre total de colis"),
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
            font=dict(color="#1E293B"),
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
        font=dict(color="#1E293B"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="Wilayas moyennes / jour"),
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
