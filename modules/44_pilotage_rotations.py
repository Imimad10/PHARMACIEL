# =============================================================================
# MODULE : Pilotage des Rotations & Charge de Préparation
# Fichier : modules/44_pilotage_rotations.py
# Auteur  : PHARMACIEL ERP
# Logique : Tri temporel strict sur heure de validation.
#   -> Rotation 2 (Jour-J) : 09:00 -> 12:15:00 (strict)
#   -> Rotation 1 (Lendemain) : 12:15:01 -> 19:00:00
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, time
import random

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 : GÉNÉRATION DES DONNÉES MOCKÉES
# (Remplacer par votre appel load_gs_data une fois en production)
# ─────────────────────────────────────────────────────────────────────────────

REGIONS = ["ALGER", "BLIDA", "BOUMERDÈS", "TIPAZA", "MÉDÉA", "AÏN DEFLA", "TIZI OUZOU", "BOUIRA"]
CLIENTS = [
    "PHARMACIE ATLAS", "PHARMACIE EL BARAKA", "PHARMACIE CENTRALE BLIDA",
    "PHARMACIE BOUKHARI", "PHARMACIE DES PINS", "PHARMACIE AL FATH",
    "PHARMACIE BELLES FEUILLES", "PHARMACIE SOLEIL", "PHARMACIE GHANDI",
    "PHARMACIE IBN SINA", "PHARMACIE ABOUDOU", "PHARMACIE EL BASSIR",
    "PHARMACIE MEZIANE", "PHARMACIE CHERIF", "PHARMACIE DOUNYA",
    "PHARMACIE AMEL", "PHARMACIE DJURDJURA", "PHARMACIE HACENE",
]

@st.cache_data(ttl=300)
def generate_mock_data(nb_jours: int = 14) -> pd.DataFrame:
    """
    Génère un jeu de données fictives réalistes simulant des bons de commande
    avec une répartition temporelle tout au long de la journée de travail.

    ── TODO : INTÉGRATION BDD ─────────────────────────────────────────────────
    Remplacez cette fonction par votre propre appel à load_gs_data :

        from utils_gsheets import load_gs_data
        df = load_gs_data(worksheet_name="Suivi_Commandes", ...)
        # S'assurer que la colonne 'Date' est bien en datetime :
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        return df.dropna(subset=['Date'])
    ──────────────────────────────────────────────────────────────────────────
    """
    random.seed(42)
    np.random.seed(42)
    rows = []
    base_date = datetime.now().date() - timedelta(days=nb_jours - 1)

    for day_offset in range(nb_jours):
        current_date = base_date + timedelta(days=day_offset)
        # Environ 35 à 60 commandes par jour
        nb_cmds = random.randint(35, 60)
        for _ in range(nb_cmds):
            # Distribution réaliste : pic avant cut-off + gros volume l'après-midi
            heure_rand = random.random()
            if heure_rand < 0.45:
                # Bons du matin (Rotation 2 - Jour-J) : 09:00 → 12:15
                h = random.randint(9, 11)
                m = random.randint(0, 59) if h < 11 else random.randint(0, 75)
                if h == 11 and m > 59:
                    h = 12
                    m = random.randint(0, 14)
                s = random.randint(0, 59)
                dt = datetime.combine(current_date, time(h, min(m, 59), s))
                if dt.hour == 12 and dt.minute >= 15:
                    dt = dt.replace(minute=14, second=30)
            else:
                # Bons de l'après-midi (Rotation 1 - Lendemain) : 12:15 → 19:00
                h = random.randint(12, 18)
                m = random.randint(0, 59)
                s = random.randint(0, 59)
                if h == 12 and m < 15:
                    m = random.randint(15, 59)
                dt = datetime.combine(current_date, time(h, m, s))

            rows.append({
                "N°Bon"    : f"BC-{random.randint(10000, 99999)}",
                "Client"   : random.choice(CLIENTS),
                "Région"   : random.choice(REGIONS),
                "Colis"    : random.randint(1, 30),
                "Lignes"   : random.randint(1, 60),
                "Date"     : dt,
            })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 : CONSTANTES & SEUILS MÉTIER
# ─────────────────────────────────────────────────────────────────────────────
CUTOFF_ROTATION_2 = time(12, 15, 0)   # 12h15:00 strict — borne exclusive supérieure
DEBUT_JOURNEE     = time(9, 0, 0)
FIN_JOURNEE       = time(19, 0, 0)

SEUIL_COLIS_ROUGE   = 500   # Surcharge critique
SEUIL_COLIS_ORANGE  = 350   # Surcharge modérée
SEUIL_LIGNES_ROUGE  = 1500
SEUIL_LIGNES_ORANGE = 1000


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 : LOGIQUE DE SEGMENTATION DES ROTATIONS
# ─────────────────────────────────────────────────────────────────────────────
def segmenter_rotations(df: pd.DataFrame) -> tuple:
    """
    Segmente les bons en Rotation 2 (Jour-J) et Rotation 1 (Lendemain)
    selon l'heure de validation stricte.
    """
    h = df["Date"].dt.time

    mask_r2 = (h >= DEBUT_JOURNEE) & (h < CUTOFF_ROTATION_2)
    mask_r1 = (h >= CUTOFF_ROTATION_2) & (h <= FIN_JOURNEE)

    return df[mask_r2].copy(), df[mask_r1].copy()


def get_surcharge_level(colis: int, lignes: int) -> str:
    """Retourne le niveau d'alerte : 'OK', 'WARN', 'CRIT'."""
    if colis >= SEUIL_COLIS_ROUGE or lignes >= SEUIL_LIGNES_ROUGE:
        return "CRIT"
    elif colis >= SEUIL_COLIS_ORANGE or lignes >= SEUIL_LIGNES_ORANGE:
        return "WARN"
    return "OK"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 : COMPOSANTS UI (HTML / CSS)
# ─────────────────────────────────────────────────────────────────────────────
CSS_PREMIUM = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

/* ── Global ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0F1117; color: #E2E8F0; }
[data-testid="stSidebar"] { background: #161B22 !important; }

/* ── Page Header ── */
.page-header {
    background: linear-gradient(135deg, #0066FF22, #00B4D822);
    border: 1px solid #0066FF44;
    border-radius: 20px;
    padding: 28px 36px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.page-header::before {
    content: "";
    position: absolute; top: -40px; right: -40px;
    width: 180px; height: 180px;
    background: radial-gradient(circle, #0066FF33, transparent 70%);
    border-radius: 50%;
}
.page-header h1 {
    font-size: 2rem; font-weight: 900;
    background: linear-gradient(90deg, #FFFFFF, #00B4D8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 6px;
}
.page-header p { color: #94A3B8; margin: 0; font-size: 0.95rem; }

/* ── Section Title ── */
.section-title {
    display: flex; align-items: center; gap: 12px;
    margin: 24px 0 16px;
}
.section-badge {
    font-size: 0.7rem; font-weight: 800; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 4px 12px;
    border-radius: 30px; border: 1px solid;
}
.badge-r2 { color: #60A5FA; border-color: #60A5FA44; background: #60A5FA11; }
.badge-r1 { color: #A78BFA; border-color: #A78BFA44; background: #A78BFA11; }
.section-title h2 { font-size: 1.25rem; font-weight: 800; margin: 0; }

/* ── KPI Card ── */
.kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 12px; }
.kpi-card {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 16px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s, transform 0.3s;
}
.kpi-card:hover { border-color: #0066FF88; transform: translateY(-3px); }
.kpi-card::after {
    content: ""; position: absolute;
    bottom: 0; left: 0; right: 0; height: 3px;
    border-radius: 0 0 16px 16px;
}
.kpi-card.r2::after { background: linear-gradient(90deg, #0066FF, #00B4D8); }
.kpi-card.r1::after { background: linear-gradient(90deg, #7C3AED, #A78BFA); }
.kpi-card.neutral::after { background: linear-gradient(90deg, #374151, #4B5563); }
.kpi-icon { font-size: 1.6rem; margin-bottom: 10px; }
.kpi-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 1px;
              text-transform: uppercase; color: #64748B; margin-bottom: 6px; }
.kpi-value { font-size: 2rem; font-weight: 900; color: #F8FAFC; margin: 0; line-height: 1; }
.kpi-sub   { font-size: 0.8rem; color: #475569; margin-top: 6px; }

/* ── Alert Banners ── */
.alert-crit {
    background: linear-gradient(90deg, #7F1D1D, #1E0000);
    border-left: 5px solid #EF4444;
    border-radius: 0 14px 14px 0;
    padding: 18px 22px; margin: 10px 0 16px;
    display: flex; align-items: flex-start; gap: 16px;
}
.alert-warn {
    background: linear-gradient(90deg, #78350F, #1C0E00);
    border-left: 5px solid #F59E0B;
    border-radius: 0 14px 14px 0;
    padding: 18px 22px; margin: 10px 0 16px;
    display: flex; align-items: flex-start; gap: 16px;
}
.alert-ok {
    background: linear-gradient(90deg, #064E3B, #011F15);
    border-left: 5px solid #10B981;
    border-radius: 0 14px 14px 0;
    padding: 14px 20px; margin: 10px 0 16px;
    display: flex; align-items: center; gap: 14px;
}
.alert-icon { font-size: 2rem; flex-shrink: 0; }
.alert-title { font-size: 1rem; font-weight: 800; margin: 0 0 4px; color: white; }
.alert-msg   { font-size: 0.85rem; margin: 0; color: rgba(255,255,255,0.75); }

/* ── Cut-off Banner ── */
.cutoff-banner {
    background: linear-gradient(90deg, #1E1B4B, #0F172A);
    border: 1px dashed #6366F144;
    border-radius: 12px;
    padding: 10px 18px; text-align: center;
    color: #818CF8; font-size: 0.82rem; font-weight: 700;
    letter-spacing: 0.5px; margin: 4px 0 20px;
}

/* ── Tabs overrides ── */
[data-testid="stTabs"] [role="tab"] {
    font-weight: 700 !important; font-size: 0.9rem !important;
}

/* ── DataFrame ── */
.stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
</style>
"""


def render_kpi_row(df_rot: pd.DataFrame, color_cls: str):
    nb_bons  = len(df_rot)
    nb_colis = int(df_rot["Colis"].sum()) if not df_rot.empty else 0
    nb_lig   = int(df_rot["Lignes"].sum()) if not df_rot.empty else 0

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card {color_cls}">
            <div class="kpi-icon">📋</div>
            <div class="kpi-label">Bons à Préparer</div>
            <p class="kpi-value">{nb_bons}</p>
            <div class="kpi-sub">Nombre total de BL</div>
        </div>
        <div class="kpi-card {color_cls}">
            <div class="kpi-icon">📦</div>
            <div class="kpi-label">Volume Colis</div>
            <p class="kpi-value">{nb_colis:,}</p>
            <div class="kpi-sub">Colis à expédier</div>
        </div>
        <div class="kpi-card {color_cls}">
            <div class="kpi-icon">🔢</div>
            <div class="kpi-label">Lignes Commandes</div>
            <p class="kpi-value">{nb_lig:,}</p>
            <div class="kpi-sub">Lignes à scanner</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    return nb_bons, nb_colis, nb_lig


def render_alert(nb_colis: int, nb_lignes: int, rotation_label: str):
    level = get_surcharge_level(nb_colis, nb_lignes)
    if level == "CRIT":
        st.markdown(f"""
        <div class="alert-crit">
            <div class="alert-icon">🚨</div>
            <div>
                <p class="alert-title">SURCHARGE CRITIQUE — {rotation_label}</p>
                <p class="alert-msg">
                    {nb_colis} colis / {nb_lignes} lignes détectés.
                    Seuils dépassés : ≥ {SEUIL_COLIS_ROUGE} colis ou ≥ {SEUIL_LIGNES_ROUGE} lignes.
                    Risque de retard de livraison élevé — Mobiliser des renforts immédiatement !
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif level == "WARN":
        st.markdown(f"""
        <div class="alert-warn">
            <div class="alert-icon">⚠️</div>
            <div>
                <p class="alert-title">CHARGE ÉLEVÉE — {rotation_label}</p>
                <p class="alert-msg">
                    {nb_colis} colis / {nb_lignes} lignes. Charge modérée mais à surveiller.
                    Prévoyez une équipe de préparation renforcée.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-ok">
            <div class="alert-icon">✅</div>
            <p style="margin:0; color:white; font-weight:700;">
                {rotation_label} — Charge nominale ({nb_colis} colis / {nb_lignes} lignes). Tout est sous contrôle.
            </p>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 : GRAPHIQUE TEMPOREL
# ─────────────────────────────────────────────────────────────────────────────
def build_timeline_chart(df_day: pd.DataFrame) -> go.Figure:
    """
    Graphique en barres : nombre de bons validés par tranche de 30 minutes.
    Colorisé selon la rotation (Rotation 2 = bleu, Rotation 1 = violet).
    """
    if df_day.empty:
        fig = go.Figure()
        fig.update_layout(title="Aucune donnée disponible pour cette journée.",
                          paper_bgcolor="#0F1117", plot_bgcolor="#0F1117",
                          font=dict(color="white"))
        return fig

    df_tmp = df_day.copy()
    df_tmp["Tranche30m"] = df_tmp["Date"].dt.floor("30min")
    df_group = df_tmp.groupby("Tranche30m").agg(
        Bons=("N°Bon", "count"),
        Colis=("Colis", "sum")
    ).reset_index()
    df_group["Heure_str"] = df_group["Tranche30m"].dt.strftime("%H:%M")
    df_group["Rotation"] = df_group["Tranche30m"].apply(
        lambda x: "🔵 Rotation 2 (Jour-J)" if x.time() < CUTOFF_ROTATION_2
                  else "🟣 Rotation 1 (Lendemain)"
    )

    color_map = {
        "🔵 Rotation 2 (Jour-J)": "#3B82F6",
        "🟣 Rotation 1 (Lendemain)": "#8B5CF6"
    }

    fig = px.bar(
        df_group, x="Heure_str", y="Bons",
        color="Rotation",
        color_discrete_map=color_map,
        custom_data=["Colis", "Rotation"],
        labels={"Heure_str": "Tranche Horaire (30 min)", "Bons": "Nombre de Bons Validés"},
    )

    # Ligne verticale cut-off 12:15
    # (add_shape utilisé car add_vline est instable sur axe catégoriel Plotly)
    cutoff_str = "12:15"
    x_labels = df_group["Heure_str"].tolist()
    if cutoff_str in x_labels:
        cutoff_idx = x_labels.index(cutoff_str)
    else:
        # Trouver la tranche la plus proche >= 12:15
        cutoff_idx = next(
            (i for i, h in enumerate(x_labels) if h >= cutoff_str),
            len(x_labels) - 1
        )

    fig.add_shape(
        type="line",
        x0=cutoff_idx - 0.5, x1=cutoff_idx - 0.5,
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#F87171", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=cutoff_idx - 0.5, y=1,
        xref="x", yref="paper",
        text="⏱ CUT-OFF 12h15",
        showarrow=False,
        font=dict(color="#F87171", size=11),
        xanchor="left", yanchor="bottom",
        bgcolor="rgba(15,17,23,0.7)",
        borderpad=4,
    )

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Bons : %{y}<br>Colis : %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        marker_line_width=0,
        opacity=0.9,
    )

    fig.update_layout(
        title=dict(
            text="Distribution Temporelle des Validations (par tranches de 30 min)",
            font=dict(size=15, color="#E2E8F0"), x=0
        ),
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font=dict(color="#94A3B8"),
        xaxis=dict(
            title="Heure de Validation",
            showgrid=False,
            tickangle=-35,
            color="#64748B",
        ),
        yaxis=dict(
            title="Bons Validés",
            showgrid=True, gridcolor="#21262D",
            color="#64748B",
        ),
        legend=dict(
            orientation="h", y=1.12, x=0,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(t=60, b=40, l=40, r=20),
        bargap=0.25,
        height=380,
    )
    return fig


def build_region_chart(df_rot: pd.DataFrame, color: str, title: str) -> go.Figure:
    """Barres horizontales : Volume colis par région pour une rotation."""
    if df_rot.empty:
        return go.Figure()
    grp = df_rot.groupby("Région").agg(Colis=("Colis","sum"), Bons=("N°Bon","count")).reset_index()
    grp = grp.sort_values("Colis", ascending=True)

    fig = go.Figure(go.Bar(
        x=grp["Colis"], y=grp["Région"],
        orientation="h",
        marker=dict(
            color=color,
            line_width=0,
        ),
        text=grp["Colis"],
        textposition="inside",
        hovertemplate="<b>%{y}</b><br>%{x} colis — %{customdata} bons<extra></extra>",
        customdata=grp["Bons"],
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#E2E8F0"), x=0),
        paper_bgcolor="#161B22", plot_bgcolor="#161B22",
        font=dict(color="#94A3B8"),
        xaxis=dict(showgrid=True, gridcolor="#21262D"),
        yaxis=dict(showgrid=False),
        margin=dict(t=50, b=20, l=10, r=20),
        height=300,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 : PAGE PRINCIPALE STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(CSS_PREMIUM, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>⚡ Pilotage des Rotations & Charge</h1>
    <p>Suivi en temps réel des flux de préparation • Cut-off Rotation 2 : <strong>12h15 mn 00 sec</strong> (Livraison Jour-J) • Rotation 1 : après 12h15 (Livraison Lendemain)</p>
</div>
""", unsafe_allow_html=True)

# ── Chargement données ─────────────────────────────────────────────────────────
# ── TODO: Remplacer par load_gs_data() en production ─────────────────────────
df_all = generate_mock_data(nb_jours=14)

# ── Sidebar : Filtres ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Paramètres Rotations")
    st.markdown("---")

    mode_date = st.radio("Mode de filtrage", ["Jour précis", "Plage de dates"], index=0)

    dates_dispo = sorted(df_all["Date"].dt.date.unique(), reverse=True)

    if mode_date == "Jour précis":
        selected_day = st.selectbox("📅 Choisir le Jour", dates_dispo,
                                    format_func=lambda d: d.strftime("%A %d/%m/%Y").capitalize())
        df_filtered = df_all[df_all["Date"].dt.date == selected_day].copy()
        periode_label = selected_day.strftime("%A %d %B %Y").capitalize()
    else:
        date_range = st.date_input(
            "📆 Plage de dates",
            value=[dates_dispo[-1], dates_dispo[0]],
            min_value=dates_dispo[-1], max_value=dates_dispo[0]
        )
        if len(date_range) == 2:
            sd, ed = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + timedelta(hours=23, minutes=59)
            df_filtered = df_all[(df_all["Date"] >= sd) & (df_all["Date"] <= ed)].copy()
            periode_label = f"{date_range[0].strftime('%d/%m/%Y')} → {date_range[1].strftime('%d/%m/%Y')}"
        else:
            df_filtered = df_all.copy()
            periode_label = "Plage en cours de sélection"

    st.markdown("---")
    st.markdown("#### ⚙️ Seuils d'Alerte")
    seuil_colis_rouge  = st.number_input("🔴 Colis critique", value=SEUIL_COLIS_ROUGE, step=50)
    seuil_colis_orange = st.number_input("🟠 Colis alerte", value=SEUIL_COLIS_ORANGE, step=50)
    SEUIL_COLIS_ROUGE  = seuil_colis_rouge
    SEUIL_COLIS_ORANGE = seuil_colis_orange

# ── Segmentation ───────────────────────────────────────────────────────────────
df_r2, df_r1 = segmenter_rotations(df_filtered)

# ── Résumé période ─────────────────────────────────────────────────────────────
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">Période Analysée</div>
        <p class="kpi-value" style="font-size:1.1rem; margin-top:6px;">{periode_label}</p>
    </div>""", unsafe_allow_html=True)
with col_s2:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">Total Bons sur la Période</div>
        <p class="kpi-value">{len(df_filtered)}</p>
    </div>""", unsafe_allow_html=True)
with col_s3:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">Total Colis sur la Période</div>
        <p class="kpi-value">{int(df_filtered['Colis'].sum()):,}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Graphique Temporel ─────────────────────────────────────────────────────────
# En mode "Jour précis" → graphique du jour
# En mode "Plage" → graphique agrégé sur tous les jours
if mode_date == "Jour précis":
    fig_timeline = build_timeline_chart(df_filtered)
else:
    # Sur plage multi-jours on moyenne par heure (agrégé par jour puis par tranche)
    df_tmp2 = df_filtered.copy()
    df_tmp2["Tranche30m_str"] = df_tmp2["Date"].apply(
        lambda x: x.replace(minute=30 if x.minute >= 30 else 0, second=0, microsecond=0).strftime("%H:%M")
    )
    df_grp2 = df_tmp2.groupby("Tranche30m_str").agg(
        Bons=("N°Bon", "count"), Colis=("Colis", "sum")
    ).reset_index().sort_values("Tranche30m_str")

    # Recréer un DataFrame pour build_timeline_chart en reformatant
    df_tmp3 = df_filtered.copy()
    fig_timeline = build_timeline_chart(df_tmp3)

st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("""
<div class="cutoff-banner">
    🔵 Avant 12h15 mn 00 sec = <strong>ROTATION 2</strong> (Expédition Jour-J à partir de 12h30) &nbsp;|&nbsp; 
    🟣 Après 12h15 mn 00 sec = <strong>ROTATION 1</strong> (Expédition le lendemain à 05h00)
</div>
""", unsafe_allow_html=True)

# ── Tabs Rotations ──────────────────────────────────────────────────────────────
tab_r2, tab_r1, tab_detail = st.tabs([
    f"🔵 ROTATION 2 — Jour-J  ({len(df_r2)} bons)",
    f"🟣 ROTATION 1 — Lendemain  ({len(df_r1)} bons)",
    "📋 Détail Complet"
])

# ─── ROTATION 2 ────────────────────────────────────────────────────────────────
with tab_r2:
    st.markdown("""
    <div class="section-title">
        <span class="section-badge badge-r2">09:00 → 12:14:59</span>
        <h2>🔵 Rotation 2 — Livraison Jour-J (départ ≥ 12h30)</h2>
    </div>
    """, unsafe_allow_html=True)

    nb_bons_r2, nb_colis_r2, nb_lig_r2 = render_kpi_row(df_r2, "r2")
    render_alert(nb_colis_r2, nb_lig_r2, "Rotation 2 – Jour-J")

    if not df_r2.empty:
        c_map, c_top = st.columns([1, 1])
        with c_map:
            st.plotly_chart(
                build_region_chart(df_r2, "#3B82F6", "Volume Colis par Région (Rotation 2)"),
                use_container_width=True
            )
        with c_top:
            st.markdown("##### 🏆 Top Clients – Rotation 2")
            top_clients_r2 = (df_r2.groupby("Client")
                              .agg(Colis=("Colis","sum"), Bons=("N°Bon","count"))
                              .sort_values("Colis", ascending=False)
                              .head(8).reset_index())
            st.dataframe(top_clients_r2, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun bon validé avant 12h15 sur cette période.")

# ─── ROTATION 1 ────────────────────────────────────────────────────────────────
with tab_r1:
    st.markdown("""
    <div class="section-title">
        <span class="section-badge badge-r1">12:15:00 → 19:00</span>
        <h2>🟣 Rotation 1 — Livraison Lendemain (départ 05h00)</h2>
    </div>
    """, unsafe_allow_html=True)

    nb_bons_r1, nb_colis_r1, nb_lig_r1 = render_kpi_row(df_r1, "r1")
    render_alert(nb_colis_r1, nb_lig_r1, "Rotation 1 – Lendemain")

    if not df_r1.empty:
        c_map2, c_top2 = st.columns([1, 1])
        with c_map2:
            st.plotly_chart(
                build_region_chart(df_r1, "#8B5CF6", "Volume Colis par Région (Rotation 1)"),
                use_container_width=True
            )
        with c_top2:
            st.markdown("##### 🏆 Top Clients – Rotation 1")
            top_clients_r1 = (df_r1.groupby("Client")
                              .agg(Colis=("Colis","sum"), Bons=("N°Bon","count"))
                              .sort_values("Colis", ascending=False)
                              .head(8).reset_index())
            st.dataframe(top_clients_r1, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun bon validé après 12h15 sur cette période.")

# ─── DÉTAIL COMPLET ────────────────────────────────────────────────────────────
with tab_detail:
    st.markdown("##### 📋 Liste complète des bons – Période sélectionnée")

    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        rot_filter = st.selectbox("Filtrer par Rotation",
                                  ["Toutes", "🔵 Rotation 2 (Jour-J)", "🟣 Rotation 1 (Lendemain)"])
    with col_f2:
        search = st.text_input("🔍 Rechercher un client ou un bon", placeholder="ex: PHARMACIE ATLAS")

    df_show = df_filtered.copy()
    df_show["Rotation"] = df_show["Date"].apply(
        lambda x: "🔵 Rotation 2" if x.time() < CUTOFF_ROTATION_2 else "🟣 Rotation 1"
    )
    df_show["Heure"] = df_show["Date"].dt.strftime("%H:%M:%S")
    df_show["Date_seule"] = df_show["Date"].dt.strftime("%d/%m/%Y")

    if rot_filter != "Toutes":
        target = "🔵 Rotation 2" if "2" in rot_filter else "🟣 Rotation 1"
        df_show = df_show[df_show["Rotation"] == target]

    if search:
        mask = (df_show["Client"].str.contains(search, case=False, na=False) |
                df_show["N°Bon"].str.contains(search, case=False, na=False))
        df_show = df_show[mask]

    cols_display = ["Rotation", "Date_seule", "Heure", "N°Bon", "Client", "Région", "Colis", "Lignes"]
    st.dataframe(df_show[cols_display].sort_values(["Date_seule", "Heure"], ascending=[False, True]),
                 use_container_width=True, hide_index=True, height=450)

    st.markdown(f"**{len(df_show)} bons affichés** | Colis : {int(df_show['Colis'].sum()):,} | Lignes : {int(df_show['Lignes'].sum()):,}")
