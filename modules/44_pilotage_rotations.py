# =============================================================================
# MODULE : Pilotage des Rotations & Charge de Préparation — DONNÉES RÉELLES
# Fichier : modules/44_pilotage_rotations.py
# Auteur  : PHARMACIEL ERP
# Logique : Tri temporel strict sur "Date Création" (colonne clé du fichier bons.xlsx)
#   -> Rotation 2 (Jour-J)   : 09:00 → 12:15:00 (strict)
#   -> Rotation 1 (Lendemain): 12:15:00 → 19:00:00
# Source  : db_commandes_globales.csv (via Admin Centrale) + st.session_state fallback
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, time
import os

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 : CHARGEMENT DES DONNÉES RÉELLES
# ─────────────────────────────────────────────────────────────────────────────
DB_COMMANDES_PATH = "data/db_commandes_globales.csv"

# Toutes les variantes de colonnes du fichier bons.xlsx (Logipharm)
COL_ALIASES = {
    "date": "Date_Creation",
    "date création": "Date_Creation",
    "date creation": "Date_Creation",
    "date_creation": "Date_Creation",
    "date validation": "Date_Creation",
    "heure": "Date_Creation",
    "n°bon": "N°Bon",
    "référence": "N°Bon",
    "reference": "N°Bon",
    "ref": "N°Bon",
    "b.l": "N°Bon",
    "client": "Client",
    "nom client": "Client",
    "raison sociale": "Client",
    "région": "Région",
    "region": "Région",
    "wilaya": "Région",
    "zone": "Région",
    "colis": "Colis",
    "nb colis": "Colis",
    "nb_colis": "Colis",
    "nbr colis": "Colis",
    "lignes": "Lignes",
    "nbr ligne": "Lignes",
    "nb ligne": "Lignes",
    "nb lignes": "Lignes",
    "frigo": "Colis_Frigo_Psy",
    "frigo_psy": "Colis_Frigo_Psy",
    "colis_frigo": "Colis_Frigo_Psy",
    "psy": "Colis_Frigo_Psy",
    "montant": "MontantTTC",
    "montant ttc": "MontantTTC",
    "t.t.c": "MontantTTC",
    "ttc": "MontantTTC",
    "valeur": "MontantTTC",
    "statut": "Statut",
    "nbr impres.": "Statut",       # dans bons.xlsx : col "Nbr Impres." = imprimé quand > 0
    "nbr impres": "Statut",
    "nbr imprès.": "Statut",
    "nbr imprès": "Statut",
}

@st.cache_data(ttl=60, show_spinner=False)
def load_real_data() -> pd.DataFrame:
    """
    Charge les données réelles depuis :
    1. Le CSV persistant db_commandes_globales.csv (écrit par Admin Centrale)
    2. Sinon : un DataFrame vide
    La normalisation des colonnes est faite ici.
    """
    df = pd.DataFrame()

    # Essai de lecture du CSV
    if os.path.exists(DB_COMMANDES_PATH):
        try:
            df = pd.read_csv(DB_COMMANDES_PATH, encoding='utf-8-sig', low_memory=False)
        except Exception:
            try:
                df = pd.read_csv(DB_COMMANDES_PATH, encoding='latin1', low_memory=False)
            except Exception:
                df = pd.DataFrame()

    if df.empty:
        return df

    # Normalisation des colonnes
    renamed = {}
    already_used = set()
    for col in df.columns:
        key = str(col).strip().lower()
        if key in COL_ALIASES:
            target = COL_ALIASES[key]
            if target not in already_used:
                renamed[col] = target
                already_used.add(target)
        else:
            renamed[col] = col
    df = df.rename(columns=renamed)

    # Parsing date — priorité à Date_Creation
    date_col = "Date_Creation"
    if date_col not in df.columns:
        # Chercher une colonne date parmi les colonnes restantes
        for c in df.columns:
            if "date" in str(c).lower() or "heure" in str(c).lower():
                df = df.rename(columns={c: date_col})
                break

    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df["Date"] = df[date_col]
    else:
        return pd.DataFrame()

    # Normalisation numérique
    for num_col in ["Colis", "Lignes", "MontantTTC", "Colis_Frigo_Psy"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors='coerce').fillna(0)
        else:
            df[num_col] = 0

    # N°Bon : assurer existence
    if "N°Bon" not in df.columns:
        for alias in ["Référence", "reference", "ref", "b.l"]:
            if alias in df.columns:
                df["N°Bon"] = df[alias].astype(str)
                break
        if "N°Bon" not in df.columns:
            df["N°Bon"] = df.index.astype(str)

    # Statut impression : Nbr Impres. > 0 → Imprimé
    if "Statut" in df.columns:
        statut_raw = pd.to_numeric(df["Statut"], errors='coerce')
        if statut_raw.notna().any():
            # C'est une colonne numérique (Nbr Impressions)
            df["Statut"] = statut_raw.apply(
                lambda v: "Imprimé" if pd.notna(v) and v > 0 else "Non Imprimé"
            )
        else:
            df["Statut"] = df["Statut"].fillna("Imprimé")
    else:
        df["Statut"] = "Imprimé"

    # Région
    if "Région" not in df.columns:
        df["Région"] = "N/A"
    else:
        df["Région"] = df["Région"].fillna("N/A").astype(str).str.strip().str.upper()

    # Client
    if "Client" not in df.columns:
        df["Client"] = "Client inconnu"
    else:
        df["Client"] = df["Client"].fillna("Client inconnu").astype(str).str.strip()

    return df.sort_values("Date").reset_index(drop=True)


def get_data() -> pd.DataFrame:
    """
    Retourne les données de pilotage en cherchant dans cet ordre :
    1. st.session_state['db_commandes_recouvrement'] (injecté juste après la fusion Admin Centrale)
    2. Fichier CSV persistant (via cache)
    Affiche un indicateur visuel de la source utilisée.
    """
    # Source 1 : Session state (données fraîches post-import)
    if "db_commandes_recouvrement" in st.session_state and not st.session_state["db_commandes_recouvrement"].empty:
        df_raw = st.session_state["db_commandes_recouvrement"].copy()
        # Normaliser comme dans load_real_data
        renamed = {}
        already_used = set()
        for col in df_raw.columns:
            key = str(col).strip().lower()
            if key in COL_ALIASES:
                target = COL_ALIASES[key]
                if target not in already_used:
                    renamed[col] = target
                    already_used.add(target)
        df_raw = df_raw.rename(columns=renamed)

        date_col = "Date_Creation"
        if date_col not in df_raw.columns:
            for c in df_raw.columns:
                if "date" in str(c).lower():
                    df_raw = df_raw.rename(columns={c: date_col})
                    break

        if date_col in df_raw.columns:
            df_raw[date_col] = pd.to_datetime(df_raw[date_col], errors='coerce')
            df_raw = df_raw.dropna(subset=[date_col])
            df_raw["Date"] = df_raw[date_col]
        else:
            df_raw = pd.DataFrame()

        if not df_raw.empty:
            for num_col in ["Colis", "Lignes", "MontantTTC", "Colis_Frigo_Psy"]:
                if num_col in df_raw.columns:
                    df_raw[num_col] = pd.to_numeric(df_raw[num_col], errors='coerce').fillna(0)
                else:
                    df_raw[num_col] = 0

            if "N°Bon" not in df_raw.columns:
                for alias in ["Référence", "reference", "ref"]:
                    if alias in df_raw.columns:
                        df_raw["N°Bon"] = df_raw[alias].astype(str)
                        break
                if "N°Bon" not in df_raw.columns:
                    df_raw["N°Bon"] = df_raw.index.astype(str)

            if "Statut" in df_raw.columns:
                statut_raw = pd.to_numeric(df_raw["Statut"], errors='coerce')
                if statut_raw.notna().any():
                    df_raw["Statut"] = statut_raw.apply(
                        lambda v: "Imprimé" if pd.notna(v) and v > 0 else "Non Imprimé"
                    )
                else:
                    df_raw["Statut"] = df_raw["Statut"].fillna("Imprimé")
            else:
                df_raw["Statut"] = "Imprimé"

            if "Région" not in df_raw.columns:
                df_raw["Région"] = "N/A"
            else:
                df_raw["Région"] = df_raw["Région"].fillna("N/A").astype(str).str.strip().str.upper()

            if "Client" not in df_raw.columns:
                df_raw["Client"] = "Client inconnu"
            else:
                df_raw["Client"] = df_raw["Client"].fillna("Client inconnu").astype(str).str.strip()

            return df_raw.sort_values("Date").reset_index(drop=True), "🟢 Données fraîches (session après import)"

    # Source 2 : CSV persistant
    df_csv = load_real_data()
    if not df_csv.empty:
        return df_csv, "📂 Données chargées depuis la base persistante (CSV)"

    return pd.DataFrame(), "❌ Aucune donnée"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 : CONSTANTES & SEUILS MÉTIER
# ─────────────────────────────────────────────────────────────────────────────
CUTOFF_ROTATION_2 = time(12, 15, 0)
DEBUT_JOURNEE     = time(9, 0, 0)
FIN_JOURNEE       = time(19, 0, 0)

SEUIL_COLIS_ROUGE   = 500
SEUIL_COLIS_ORANGE  = 350
SEUIL_LIGNES_ROUGE  = 1500
SEUIL_LIGNES_ORANGE = 1000


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 : SEGMENTATION DES ROTATIONS
# ─────────────────────────────────────────────────────────────────────────────
def segmenter_rotations(df: pd.DataFrame) -> tuple:
    h = df["Date"].dt.time
    mask_r2 = (h >= DEBUT_JOURNEE) & (h < CUTOFF_ROTATION_2)
    mask_r1 = (h >= CUTOFF_ROTATION_2) & (h <= FIN_JOURNEE)
    return df[mask_r2].copy(), df[mask_r1].copy()


def get_surcharge_level(colis: int, lignes: int) -> str:
    if colis >= SEUIL_COLIS_ROUGE or lignes >= SEUIL_LIGNES_ROUGE:
        return "CRIT"
    elif colis >= SEUIL_COLIS_ORANGE or lignes >= SEUIL_LIGNES_ORANGE:
        return "WARN"
    return "OK"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 : MOTEUR IA D'ANALYSE APPROFONDIE
# ─────────────────────────────────────────────────────────────────────────────
def ia_generate_diagnostic(df_all: pd.DataFrame, df_r2: pd.DataFrame, df_r1: pd.DataFrame, selected_day) -> dict:
    """
    Génère un diagnostic IA complet en analysant les données réelles :
    - Surcharge & équilibre des rotations
    - Clients à risque (non imprimés, volume anormal)
    - Régions sous tension
    - Tendances temporelles (pic de charge)
    - Recommandations opérationnelles
    """
    diagnostic = {
        "alertes": [],
        "recommandations": [],
        "insights": [],
        "score_risque": 0,
        "tendances": {}
    }

    if df_all.empty:
        return diagnostic

    colis_r2 = int(df_r2["Colis"].sum()) if not df_r2.empty else 0
    colis_r1 = int(df_r1["Colis"].sum()) if not df_r1.empty else 0
    lignes_r2 = int(df_r2["Lignes"].sum()) if not df_r2.empty else 0
    total_bons = len(df_all)
    total_colis = int(df_all["Colis"].sum())

    score = 0

    # ─── ANALYSE CHARGE LOGISTIQUE ─────────────────────────────────────────
    if colis_r2 >= SEUIL_COLIS_ROUGE:
        diagnostic["alertes"].append({
            "niveau": "CRITIQUE",
            "emoji": "🚨",
            "titre": "Surcharge Logistique Rotation 2",
            "message": f"{colis_r2:,} colis en R2 dépasse le seuil critique de {SEUIL_COLIS_ROUGE:,}. Risque élevé de retard d'expédition J+0."
        })
        diagnostic["recommandations"].append(
            f"🏃 **Action immédiate** : Mobiliser ≥2 préparateurs supplémentaires. Capacité actuelle insuffisante pour {colis_r2:,} colis avant 12h15."
        )
        score += 40
    elif colis_r2 >= SEUIL_COLIS_ORANGE:
        diagnostic["alertes"].append({
            "niveau": "ATTENTION",
            "emoji": "⚠️",
            "titre": "Charge Élevée Rotation 2",
            "message": f"{colis_r2:,} colis détectés. Situation tendue (seuil alerte : {SEUIL_COLIS_ORANGE:,})."
        })
        score += 20

    # ─── ÉQUILIBRE R1 / R2 ─────────────────────────────────────────────────
    if colis_r2 + colis_r1 > 0:
        ratio_r2 = colis_r2 / (colis_r2 + colis_r1) * 100
        diagnostic["tendances"]["ratio_r2_pct"] = round(ratio_r2, 1)
        if ratio_r2 > 70:
            diagnostic["insights"].append(
                f"📊 **Déséquilibre Rotations** : {ratio_r2:.0f}% du volume est en Rotation 2. L'équipe de préparation matinale est sous forte pression."
            )
        elif ratio_r2 < 25:
            diagnostic["insights"].append(
                f"📊 **Rotation 2 sous-utilisée** : Seulement {ratio_r2:.0f}% du volume avant 12h15. Opportunité d'améliorer le cut-off J+0."
            )

    # ─── BONS NON IMPRIMÉS EN R2 ───────────────────────────────────────────
    if not df_r2.empty and "Statut" in df_r2.columns:
        non_imprimes_r2 = df_r2[df_r2["Statut"] == "Non Imprimé"]
        if len(non_imprimes_r2) > 0:
            colis_ni = int(non_imprimes_r2["Colis"].sum())
            clients_ni = non_imprimes_r2["Client"].unique().tolist()[:5]
            diagnostic["alertes"].append({
                "niveau": "CRITIQUE",
                "emoji": "🖨️",
                "titre": f"{len(non_imprimes_r2)} Bon(s) Non Imprimé(s) en Rotation 2",
                "message": f"{colis_ni:,} colis bloqués chez : {', '.join(clients_ni)}{'...' if len(non_imprimes_r2['Client'].unique()) > 5 else ''}. Ces bons ne seront PAS expédiés en J+0 si non traités avant 12h15."
            })
            diagnostic["recommandations"].append(
                f"🖨️ **Impression urgente** : Lancer immédiatement l'édition physique pour les {len(non_imprimes_r2)} bons non imprimés en R2 ({colis_ni:,} colis en attente)."
            )
            score += 30

    # ─── ANALYSE PAR RÉGION ────────────────────────────────────────────────
    if "Région" in df_all.columns:
        region_charge = df_all.groupby("Région").agg(
            Colis=("Colis", "sum"),
            Bons=("N°Bon", "count")
        ).sort_values("Colis", ascending=False)

        if not region_charge.empty:
            top_region = region_charge.index[0]
            top_colis = int(region_charge.iloc[0]["Colis"])
            if len(region_charge) > 1:
                second_colis = int(region_charge.iloc[1]["Colis"])
                if top_colis > second_colis * 2.5:
                    diagnostic["insights"].append(
                        f"🗺️ **Concentration Géographique** : La région **{top_region}** concentre {top_colis:,} colis soit {top_colis/(total_colis)*100:.0f}% du volume total. Risque de congestion sur ce secteur."
                    )
                    diagnostic["recommandations"].append(
                        f"🗺️ **Optimisation Route** : Dédier un véhicule supplémentaire à la région **{top_region}** pour absorber la surconcentration ({top_colis:,} colis)."
                    )
                    score += 10

    # ─── PIC HORAIRE ───────────────────────────────────────────────────────
    if "Date" in df_all.columns and not df_r2.empty:
        df_r2_copy = df_r2.copy()
        df_r2_copy["Tranche30m"] = df_r2_copy["Date"].dt.floor("30min").dt.strftime("%H:%M")
        pic_tranche = df_r2_copy.groupby("Tranche30m")["Colis"].sum()
        if not pic_tranche.empty:
            heure_pic = pic_tranche.idxmax()
            colis_pic = int(pic_tranche.max())
            diagnostic["tendances"]["heure_pic_r2"] = heure_pic
            diagnostic["tendances"]["colis_pic_r2"] = colis_pic
            if colis_pic > 0:
                diagnostic["insights"].append(
                    f"⏱️ **Pic de Charge R2** : La tranche **{heure_pic}** concentre {colis_pic:,} colis. Planifier les ressources de préparation en conséquence."
                )

    # ─── GROS CLIENTS ──────────────────────────────────────────────────────
    if not df_all.empty and "Client" in df_all.columns:
        top_clients = df_all.groupby("Client")["Colis"].sum().nlargest(3)
        if not top_clients.empty:
            tops_list = [f"**{c}** ({int(v):,} colis)" for c, v in top_clients.items()]
            diagnostic["insights"].append(
                f"🏆 **Top 3 Clients du Jour** : {' • '.join(tops_list)}. Ces clients représentent {top_clients.sum() / total_colis * 100:.0f}% du volume."
            )

    # ─── SCORE GLOBAL ──────────────────────────────────────────────────────
    diagnostic["score_risque"] = min(score, 100)

    # Si tout va bien
    if score == 0:
        diagnostic["alertes"].append({
            "niveau": "OK",
            "emoji": "✅",
            "titre": "Tous les indicateurs opérationnels sont au vert",
            "message": f"Flux de préparation nominal : {total_bons} bons, {total_colis:,} colis, répartition R2/R1 équilibrée. Aucune action corrective requise."
        })
        diagnostic["recommandations"].append(
            "✅ **Maintenir le rythme actuel**. Confirmer la disponibilité des véhicules pour l'expédition R2 à 12h30."
        )

    return diagnostic


def render_ia_panel(diagnostic: dict):
    """Affiche le panneau IA avec les alertes, scores et recommandations."""
    score = diagnostic["score_risque"]

    # Couleur du score
    if score >= 60:
        score_color = "#EF4444"
        score_label = "RISQUE ÉLEVÉ"
    elif score >= 25:
        score_color = "#F59E0B"
        score_label = "ATTENTION"
    else:
        score_color = "#10B981"
        score_label = "NOMINAL"

    st.markdown(f"""
    <div style="background: rgba(128,128,128,0.06); border: 1px solid rgba(128,128,128,0.2); border-radius: 20px; padding: 24px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
                <h3 style="margin: 0; font-size: 1.1rem; font-weight: 900;">🤖 Diagnostic IA Opérationnel — Données Réelles</h3>
                <p style="margin: 4px 0 0; opacity: 0.6; font-size: 0.85rem;">Analyse automatique basée sur les flux de bons.xlsx importés</p>
            </div>
            <div style="text-align: center; background: rgba(128,128,128,0.1); border: 2px solid {score_color}; border-radius: 16px; padding: 10px 22px;">
                <div style="font-size: 0.7rem; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; color: {score_color};">Score Risque</div>
                <div style="font-size: 2.2rem; font-weight: 900; color: {score_color}; line-height: 1.1;">{score}</div>
                <div style="font-size: 0.7rem; color: {score_color}; font-weight: 700;">{score_label}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Alertes
    for alerte in diagnostic["alertes"]:
        niv = alerte["niveau"]
        if niv == "CRITIQUE":
            bg, border = "rgba(239,68,68,0.1)", "#EF4444"
            txt_color = "#FCA5A5"
        elif niv == "ATTENTION":
            bg, border = "rgba(245,158,11,0.1)", "#F59E0B"
            txt_color = "#FDE68A"
        else:
            bg, border = "rgba(16,185,129,0.1)", "#10B981"
            txt_color = "#A7F3D0"

        st.markdown(f"""
        <div style="background: {bg}; border-left: 4px solid {border}; border-radius: 0 12px 12px 0; padding: 14px 18px; margin-bottom: 10px;">
            <div style="font-weight: 800; font-size: 0.95rem; color: {txt_color};">{alerte['emoji']} {alerte['titre']}</div>
            <div style="font-size: 0.87rem; opacity: 0.85; margin-top: 4px;">{alerte['message']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Recommandations & Insights
    col_rec, col_ins = st.columns(2)

    with col_rec:
        st.markdown("#### 💡 Recommandations Opérationnelles")
        for rec in diagnostic["recommandations"]:
            st.markdown(f"- {rec}")

    with col_ins:
        st.markdown("#### 📊 Insights & Tendances")
        if diagnostic["insights"]:
            for insight in diagnostic["insights"]:
                st.markdown(f"- {insight}")
        else:
            st.markdown("- ✅ Aucune anomalie de tendance détectée.")

        # Mini stats tendances
        tend = diagnostic["tendances"]
        if tend:
            st.markdown("---")
            if "ratio_r2_pct" in tend:
                st.metric("Part Volume R2", f"{tend['ratio_r2_pct']}%", help="% colis expédiés en J+0 vs J+1")
            if "heure_pic_r2" in tend:
                st.metric("Pic de charge R2", tend["heure_pic_r2"], delta=f"{tend.get('colis_pic_r2', 0):,} colis")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 : STYLES CSS
# ─────────────────────────────────────────────────────────────────────────────
CSS_PREMIUM = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.page-header {
    background: linear-gradient(135deg, rgba(0, 102, 255, 0.1), rgba(0, 180, 216, 0.08));
    border: 1px solid rgba(0, 102, 255, 0.3);
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
    background: radial-gradient(circle, rgba(0,102,255,0.15), transparent 70%);
    border-radius: 50%;
}
.page-header h1 {
    font-size: 2rem; font-weight: 900;
    background: linear-gradient(90deg, #00B4D8, #0066FF);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 6px;
}
.page-header p { opacity: 0.75; margin: 0; font-size: 0.95rem; }

.section-title { display: flex; align-items: center; gap: 12px; margin: 24px 0 16px; }
.section-badge { font-size: 0.7rem; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; padding: 4px 12px; border-radius: 30px; border: 1px solid; }
.badge-r2 { color: #3B82F6; border-color: rgba(59,130,246,0.4); background: rgba(59,130,246,0.08); }
.badge-r1 { color: #8B5CF6; border-color: rgba(139,92,246,0.4); background: rgba(139,92,246,0.08); }
.section-title h2 { font-size: 1.25rem; font-weight: 800; margin: 0; }

.kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 12px; }
.kpi-card {
    background: rgba(128, 128, 128, 0.08);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 16px;
    padding: 20px 22px;
    position: relative; overflow: hidden;
    transition: border-color 0.3s, transform 0.3s;
}
.kpi-card:hover { border-color: rgba(0, 102, 255, 0.5); transform: translateY(-3px); }
.kpi-card::after {
    content: ""; position: absolute;
    bottom: 0; left: 0; right: 0; height: 3px;
    border-radius: 0 0 16px 16px;
}
.kpi-card.r2::after { background: linear-gradient(90deg, #0066FF, #00B4D8); }
.kpi-card.r1::after { background: linear-gradient(90deg, #7C3AED, #A78BFA); }
.kpi-card.neutral::after { background: linear-gradient(90deg, rgba(100,116,139,0.5), rgba(71,85,105,0.5)); }
.kpi-icon { font-size: 1.6rem; margin-bottom: 10px; }
.kpi-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; opacity: 0.55; margin-bottom: 6px; }
.kpi-value { font-size: 2rem; font-weight: 900; margin: 0; line-height: 1; }
.kpi-sub   { font-size: 0.8rem; opacity: 0.45; margin-top: 6px; }

.alert-crit { background: rgba(239, 68, 68, 0.12); border-left: 5px solid #EF4444; border-radius: 0 14px 14px 0; padding: 18px 22px; margin: 10px 0 16px; display: flex; align-items: flex-start; gap: 16px; }
.alert-warn { background: rgba(245, 158, 11, 0.12); border-left: 5px solid #F59E0B; border-radius: 0 14px 14px 0; padding: 18px 22px; margin: 10px 0 16px; display: flex; align-items: flex-start; gap: 16px; }
.alert-ok   { background: rgba(16, 185, 129, 0.12); border-left: 5px solid #10B981; border-radius: 0 14px 14px 0; padding: 14px 20px; margin: 10px 0 16px; display: flex; align-items: center; gap: 14px; }
.alert-icon { font-size: 2rem; flex-shrink: 0; }
.alert-title { font-size: 1rem; font-weight: 800; margin: 0 0 4px; }
.alert-msg   { font-size: 0.85rem; margin: 0; opacity: 0.8; }

.cutoff-banner { background: rgba(99, 102, 241, 0.1); border: 1px dashed rgba(99, 102, 241, 0.35); border-radius: 12px; padding: 10px 18px; text-align: center; color: #818CF8; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.5px; margin: 4px 0 20px; }
[data-testid="stTabs"] [role="tab"] { font-weight: 700 !important; font-size: 0.9rem !important; }
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
                <p class="alert-msg">{nb_colis} colis / {nb_lignes} lignes détectés. Seuils dépassés : ≥ {SEUIL_COLIS_ROUGE} colis ou ≥ {SEUIL_LIGNES_ROUGE} lignes. Risque de retard de livraison élevé !</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif level == "WARN":
        st.markdown(f"""
        <div class="alert-warn">
            <div class="alert-icon">⚠️</div>
            <div>
                <p class="alert-title">CHARGE ÉLEVÉE — {rotation_label}</p>
                <p class="alert-msg">{nb_colis} colis / {nb_lignes} lignes. Charge modérée mais à surveiller. Prévoyez une équipe de préparation renforcée.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-ok">
            <div class="alert-icon">✅</div>
            <p style="margin:0; font-weight:700;">{rotation_label} — Charge nominale ({nb_colis} colis / {nb_lignes} lignes). Tout est sous contrôle.</p>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 : GRAPHIQUES
# ─────────────────────────────────────────────────────────────────────────────
def build_timeline_chart(df_day: pd.DataFrame) -> go.Figure:
    if df_day.empty:
        fig = go.Figure()
        fig.update_layout(title="Aucune donnée disponible.", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    df_tmp = df_day.copy()
    df_tmp["Tranche30m"] = df_tmp["Date"].dt.floor("30min")
    df_group = df_tmp.groupby(["Tranche30m", "Région"]).agg(
        Bons=("N°Bon", "count"),
        Colis=("Colis", "sum")
    ).reset_index().sort_values("Tranche30m")
    df_group["Heure_str"] = df_group["Tranche30m"].dt.strftime("%H:%M")

    COLORS_REGIONS = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#06B6D4", "#EC4899", "#64748B", "#84CC16", "#F97316"]
    fig = px.bar(
        df_group,
        x="Heure_str", y="Bons", color="Région",
        color_discrete_sequence=COLORS_REGIONS,
        custom_data=["Région", "Colis"],
        labels={"Heure_str": "Tranche Horaire (30 min)", "Bons": "Nombre de Bons Validés", "Région": "Wilaya/Région"},
        barmode="stack"
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>%{y} bons — %{customdata[1]} colis<extra></extra>"
    )

    # Ligne cut-off 12:15
    cutoff_str = "12:15"
    x_labels = list(dict.fromkeys(df_group["Heure_str"].tolist()))
    if x_labels:
        cutoff_idx = next((i for i, h in enumerate(x_labels) if h >= cutoff_str), len(x_labels) - 1)
        fig.add_shape(
            type="line", x0=cutoff_idx - 0.5, x1=cutoff_idx - 0.5, y0=0, y1=1,
            xref="x", yref="paper", line=dict(color="#EF4444", width=2, dash="dash")
        )
        fig.add_annotation(
            x=cutoff_idx - 0.5, y=1.05, xref="x", yref="paper",
            text="⏱ CUT-OFF 12h15", showarrow=False,
            font=dict(color="#EF4444", size=10, family="Inter", weight="bold"),
            xanchor="center", yanchor="bottom",
            bgcolor="rgba(15,17,23,0.85)", bordercolor="#EF4444", borderwidth=1, borderpad=4,
        )

    fig.add_hline(
        y=10, line_dash="dot", line_color="#F59E0B",
        annotation_text="Capacité Max (10 bons/30min)",
        annotation_position="top right",
        annotation_font=dict(color="#F59E0B", size=10)
    )

    fig.update_layout(
        title=dict(text="Distribution Temporelle des Validations (Wilaya · tranches 30 min)", font=dict(size=15), x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=None),
        xaxis=dict(title="Heure de Création", showgrid=False, tickangle=-35, color="#64748B"),
        yaxis=dict(title="Bons Validés", showgrid=True, gridcolor="#21262D", color="#64748B"),
        legend=dict(orientation="h", y=1.18, x=0, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=100, b=40, l=40, r=20),
        bargap=0.25, height=420,
    )
    return fig


def build_region_chart(df_rot: pd.DataFrame, color: str, title: str) -> go.Figure:
    if df_rot.empty:
        return go.Figure()
    grp = df_rot.groupby("Région").agg(Colis=("Colis", "sum"), Bons=("N°Bon", "count")).reset_index()
    grp = grp.sort_values("Colis", ascending=True)
    fig = go.Figure(go.Bar(
        x=grp["Colis"], y=grp["Région"], orientation="h",
        marker=dict(color=color, line_width=0),
        text=grp["Colis"].apply(lambda v: f"{int(v):,}"),
        textposition="inside",
        hovertemplate="<b>%{y}</b><br>%{x} colis — %{customdata} bons<extra></extra>",
        customdata=grp["Bons"],
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13), x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=None),
        xaxis=dict(showgrid=True, gridcolor="#21262D"),
        yaxis=dict(showgrid=False),
        margin=dict(t=50, b=20, l=10, r=20), height=300,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 : PAGE PRINCIPALE STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(CSS_PREMIUM, unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>⚡ Pilotage des Rotations & Charge</h1>
    <p>Suivi en temps réel des flux de préparation sur <strong>données réelles (bons.xlsx)</strong> • Cut-off Rotation 2 : <strong>12h15 mn 00 sec</strong> • Rotation 1 : après 12h15</p>
</div>
""", unsafe_allow_html=True)

# ── Chargement données réelles ─────────────────────────────────────────────────
result = get_data()
if isinstance(result, tuple):
    df_all, source_label = result
else:
    df_all, source_label = result, "❓ Source inconnue"

# Bandeau source données
if df_all.empty:
    st.error("❌ **Aucune donnée disponible.** Veuillez importer votre fichier `bons.xlsx` depuis **Admin Centrale (Data)** et cliquer sur **Fusionner avec la base Commandes & Recouvrement**.")
    st.info("💡 **Comment ça marche :** 1️⃣ Allez dans 'Admin Centrale (Data)' → 2️⃣ Importez votre fichier bons.xlsx → 3️⃣ Cliquez 'Fusionner' → 4️⃣ Revenez ici, les données s'affichent automatiquement.")
    st.stop()
else:
    st.success(f"{source_label} — **{len(df_all):,} bons** chargés (période : {df_all['Date'].dt.date.min()} → {df_all['Date'].dt.date.max()})")
    if st.button("🔄 Rafraîchir les données", key="btn_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Sidebar : Filtres ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Paramètres Rotations")
    st.markdown("---")

    mode_date = st.radio("Mode de filtrage", ["Jour précis", "Plage de dates"], index=0)
    dates_dispo = sorted(df_all["Date"].dt.date.unique(), reverse=True)

    if mode_date == "Jour précis":
        selected_day = st.selectbox(
            "📅 Choisir le Jour", dates_dispo,
            format_func=lambda d: d.strftime("%A %d/%m/%Y").capitalize()
        )
        df_filtered = df_all[df_all["Date"].dt.date == selected_day].copy()
        periode_label = selected_day.strftime("%A %d %B %Y").capitalize()
    else:
        date_range = st.date_input(
            "📆 Plage de dates",
            value=[dates_dispo[-1], dates_dispo[0]],
            min_value=dates_dispo[-1], max_value=dates_dispo[0]
        )
        if len(date_range) == 2:
            sd = pd.Timestamp(date_range[0])
            ed = pd.Timestamp(date_range[1]) + timedelta(hours=23, minutes=59)
            df_filtered = df_all[(df_all["Date"] >= sd) & (df_all["Date"] <= ed)].copy()
            periode_label = f"{date_range[0].strftime('%d/%m/%Y')} → {date_range[1].strftime('%d/%m/%Y')}"
        else:
            df_filtered = df_all.copy()
            periode_label = "Sélection en cours..."

    st.markdown("---")
    st.markdown("#### ⚙️ Seuils d'Alerte")
    seuil_colis_rouge  = st.number_input("🔴 Colis critique", value=SEUIL_COLIS_ROUGE, step=50)
    seuil_colis_orange = st.number_input("🟠 Colis alerte",   value=SEUIL_COLIS_ORANGE, step=50)
    SEUIL_COLIS_ROUGE  = seuil_colis_rouge
    SEUIL_COLIS_ORANGE = seuil_colis_orange

    st.markdown("---")
    st.markdown("#### ℹ️ Base de données")
    st.caption(f"Lignes totales : **{len(df_all):,}**")
    st.caption(f"Lignes filtrées : **{len(df_filtered):,}**")
    if st.button("🗑️ Vider la session", key="btn_clear_session", help="Efface les données de session pour forcer un rechargement depuis le CSV"):
        if "db_commandes_recouvrement" in st.session_state:
            del st.session_state["db_commandes_recouvrement"]
        st.cache_data.clear()
        st.rerun()

# ── Segmentation ─────────────────────────────────────────────────────────────
df_r2, df_r1 = segmenter_rotations(df_filtered)

# ── KPIs Globaux ──────────────────────────────────────────────────────────────
col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
total_bons     = len(df_filtered)
total_colis    = int(df_filtered["Colis"].sum()) if not df_filtered.empty else 0
total_frigo    = int(df_filtered["Colis_Frigo_Psy"].sum()) if not df_filtered.empty else 0
total_montant  = int(df_filtered["MontantTTC"].sum()) if not df_filtered.empty else 0

with col_s1:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">📅 Période Analysée</div>
        <p class="kpi-value" style="font-size:0.9rem; font-weight:700; margin-top:10px; white-space:normal;">{periode_label}</p>
    </div>""", unsafe_allow_html=True)
with col_s2:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">📋 Total Bons</div>
        <p class="kpi-value">{total_bons}</p>
        <div class="kpi-sub">Bons de commande</div>
    </div>""", unsafe_allow_html=True)
with col_s3:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">📦 Total Colis</div>
        <p class="kpi-value">{total_colis:,}</p>
        <div class="kpi-sub">Colis à préparer</div>
    </div>""", unsafe_allow_html=True)
with col_s4:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">❄️ Frigo / 🔒 Psy</div>
        <p class="kpi-value" style="font-size:1.6rem; color:#00B4D8;">{total_frigo}</p>
        <div class="kpi-sub">Chaîne du froid</div>
    </div>""", unsafe_allow_html=True)
with col_s5:
    st.markdown(f"""<div class="kpi-card neutral" style="text-align:center;">
        <div class="kpi-label">💰 Montant Total TTC</div>
        <p class="kpi-value" style="font-size:1.2rem; color:#10B981;">{total_montant:,} DZD</p>
        <div class="kpi-sub">Valeur totale des BL</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Graphique Temporel ─────────────────────────────────────────────────────────
st.plotly_chart(build_timeline_chart(df_filtered), use_container_width=True)

# ── Section Alerte Cut-Off & Récap Wilaya ─────────────────────────────────────
col_warn, col_recap = st.columns([1, 1])
with col_warn:
    st.markdown("#### ⏳ Statut Impressions Rotation 2")
    nb_non_imprimes = len(df_r2[df_r2["Statut"] == "Non Imprimé"]) if not df_r2.empty else 0
    if nb_non_imprimes > 0:
        st.error(f"⚠️ **Attention :** {nb_non_imprimes} bon(s) reste(nt) **Non Imprimé(s)** pour la Rotation 2 avant le cut-off de 12h15 !")
        if not df_r2.empty:
            ni_df = df_r2[df_r2["Statut"] == "Non Imprimé"][["N°Bon", "Client", "Région", "Colis"]].head(10)
            st.dataframe(ni_df, hide_index=True, use_container_width=True)
    else:
        st.success("✅ Tous les bons de la Rotation 2 ont été imprimés avec succès.")

with col_recap:
    st.markdown("#### 📊 Charge & Volume par Wilaya")
    if not df_filtered.empty:
        recap_wilaya = df_filtered.groupby("Région").agg(
            Bons=("N°Bon", "count"),
            Colis=("Colis", "sum"),
            Lignes=("Lignes", "sum"),
        ).reset_index().rename(columns={"Région": "Wilaya"}).sort_values("Colis", ascending=False)
        st.dataframe(recap_wilaya, hide_index=True, use_container_width=True,
                     column_config={"Colis": st.column_config.NumberColumn(format="%d"), "Lignes": st.column_config.NumberColumn(format="%d")})

st.markdown("""
<div class="cutoff-banner">
    🔵 Avant 12h15 mn 00 sec = <strong>ROTATION 2</strong> (Expédition Jour-J à partir de 12h30) &nbsp;|&nbsp; 
    🟣 Après 12h15 mn 00 sec = <strong>ROTATION 1</strong> (Expédition le lendemain à 05h00)
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 : ONGLETS
# ─────────────────────────────────────────────────────────────────────────────
tab_r2, tab_r1, tab_ia, tab_detail = st.tabs([
    f"🔵 ROTATION 2 — Jour-J  ({len(df_r2)} bons)",
    f"🟣 ROTATION 1 — Lendemain  ({len(df_r1)} bons)",
    "🤖 ANALYSE IA APPROFONDIE",
    "📋 Détail Complet",
])

# ─── ROTATION 2 ──────────────────────────────────────────────────────────────
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
            st.plotly_chart(build_region_chart(df_r2, "#3B82F6", "Volume Colis par Région (Rotation 2)"), use_container_width=True)
        with c_top:
            st.markdown("##### 🏆 Top Clients – Rotation 2")
            top_clients_r2 = df_r2.groupby("Client").agg(Colis=("Colis","sum"), Bons=("N°Bon","count")).sort_values("Colis", ascending=False).head(10).reset_index()
            st.dataframe(top_clients_r2, use_container_width=True, hide_index=True,
                         column_config={"Colis": st.column_config.NumberColumn(format="%d colis")})
    else:
        st.info("Aucun bon créé avant 12h15 sur cette période.")

# ─── ROTATION 1 ──────────────────────────────────────────────────────────────
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
            st.plotly_chart(build_region_chart(df_r1, "#8B5CF6", "Volume Colis par Région (Rotation 1)"), use_container_width=True)
        with c_top2:
            st.markdown("##### 🏆 Top Clients – Rotation 1")
            top_clients_r1 = df_r1.groupby("Client").agg(Colis=("Colis","sum"), Bons=("N°Bon","count")).sort_values("Colis", ascending=False).head(10).reset_index()
            st.dataframe(top_clients_r1, use_container_width=True, hide_index=True,
                         column_config={"Colis": st.column_config.NumberColumn(format="%d colis")})
    else:
        st.info("Aucun bon créé après 12h15 sur cette période.")

# ─── ANALYSE IA ───────────────────────────────────────────────────────────────
with tab_ia:
    st.markdown("### 🤖 Diagnostic IA Approfondi — Pilotage Logistique")
    st.caption("Ce moteur analyse les données réelles importées depuis bons.xlsx pour générer des alertes contextuelles et des recommandations opérationnelles.")

    selected_day_ia = selected_day if mode_date == "Jour précis" else None
    diagnostic = ia_generate_diagnostic(df_filtered, df_r2, df_r1, selected_day_ia)
    render_ia_panel(diagnostic)

    st.markdown("---")
    st.markdown("#### 📈 Analyse Comparative : Rotation 2 vs Rotation 1")
    col_ia1, col_ia2, col_ia3 = st.columns(3)

    colis_r2_ia = int(df_r2["Colis"].sum()) if not df_r2.empty else 0
    colis_r1_ia = int(df_r1["Colis"].sum()) if not df_r1.empty else 0

    with col_ia1:
        fig_compare = go.Figure(go.Bar(
            x=["Rotation 2 (J+0)", "Rotation 1 (J+1)"],
            y=[colis_r2_ia, colis_r1_ia],
            marker_color=["#3B82F6", "#8B5CF6"],
            text=[f"{colis_r2_ia:,}", f"{colis_r1_ia:,}"],
            textposition="outside",
        ))
        fig_compare.update_layout(
            title="Volume Colis par Rotation",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=280, margin=dict(t=40, b=20, l=20, r=20),
            yaxis=dict(gridcolor="#21262D")
        )
        st.plotly_chart(fig_compare, use_container_width=True)

    with col_ia2:
        if not df_filtered.empty and "Statut" in df_filtered.columns:
            statut_counts = df_filtered["Statut"].value_counts().reset_index()
            statut_counts.columns = ["Statut", "Bons"]
            fig_statut = px.pie(
                statut_counts, names="Statut", values="Bons",
                color_discrete_sequence=["#10B981", "#EF4444"],
                title="Répartition Statut Impression"
            )
            fig_statut.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=280, margin=dict(t=40, b=20, l=10, r=10))
            st.plotly_chart(fig_statut, use_container_width=True)

    with col_ia3:
        if not df_filtered.empty:
            top_reg = df_filtered.groupby("Région")["Colis"].sum().nlargest(8).reset_index()
            fig_top_reg = px.bar(
                top_reg, x="Colis", y="Région", orientation="h",
                color="Colis", color_continuous_scale="Blues",
                title="Top Régions (Total Jour)"
            )
            fig_top_reg.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=280, margin=dict(t=40, b=20, l=10, r=10),
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_top_reg, use_container_width=True)

    # Tableau IA : Clients à surveiller
    st.markdown("#### 🎯 Clients à Surveiller (Volume Élevé + Non Imprimés)")
    if not df_filtered.empty:
        client_analysis = df_filtered.groupby("Client").agg(
            Bons=("N°Bon", "count"),
            Colis_Total=("Colis", "sum"),
            Lignes_Total=("Lignes", "sum"),
            Non_Imprimes=("Statut", lambda x: (x == "Non Imprimé").sum()),
        ).reset_index().sort_values("Colis_Total", ascending=False)

        client_analysis["% Non Imprimés"] = (
            client_analysis["Non_Imprimes"] / client_analysis["Bons"] * 100
        ).round(1)
        client_analysis["🔴 Priorité"] = client_analysis.apply(
            lambda r: "🚨 CRITIQUE" if r["Non_Imprimes"] > 0 and r["Colis_Total"] > 50
                      else ("⚠️ ATTENTION" if r["Non_Imprimes"] > 0 else "✅ OK"),
            axis=1
        )

        st.dataframe(
            client_analysis.head(20),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Colis_Total": st.column_config.NumberColumn("Colis", format="%d"),
                "Lignes_Total": st.column_config.NumberColumn("Lignes", format="%d"),
                "Non_Imprimes": st.column_config.NumberColumn("Non Imprimés"),
                "% Non Imprimés": st.column_config.NumberColumn(format="%.1f %%"),
            }
        )

# ─── DÉTAIL COMPLET ───────────────────────────────────────────────────────────
with tab_detail:
    st.markdown("##### 📋 Liste complète des bons – Période sélectionnée")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        rot_filter = st.selectbox("Filtrer par Rotation", ["Toutes", "🔵 Rotation 2 (Jour-J)", "🟣 Rotation 1 (Lendemain)"])
    with col_f2:
        statut_filter = st.selectbox("Filtrer par Statut", ["Tous", "Non Imprimé", "Imprimé"])
    with col_f3:
        search = st.text_input("🔍 Rechercher un client, N°Bon ou Région", placeholder="ex: ALGER, PHARMACIE ATLAS...")

    df_show = df_filtered.copy()
    df_show["Rotation"] = df_show["Date"].apply(
        lambda x: "🔵 Rotation 2" if x.time() < CUTOFF_ROTATION_2 else "🟣 Rotation 1"
    )
    df_show["Heure"] = df_show["Date"].dt.strftime("%H:%M:%S")
    df_show["Date_seule"] = df_show["Date"].dt.strftime("%d/%m/%Y")

    if rot_filter != "Toutes":
        target_rot = "🔵 Rotation 2" if "2" in rot_filter else "🟣 Rotation 1"
        df_show = df_show[df_show["Rotation"] == target_rot]

    if statut_filter != "Tous":
        df_show = df_show[df_show["Statut"] == statut_filter]

    if search:
        mask = (
            df_show["Client"].str.contains(search, case=False, na=False)
            | df_show["N°Bon"].str.contains(search, case=False, na=False)
            | df_show["Région"].str.contains(search, case=False, na=False)
        )
        df_show = df_show[mask]

    cols_display = [c for c in ["Rotation", "Date_seule", "Heure", "N°Bon", "Client", "Région", "Colis", "Lignes", "Colis_Frigo_Psy", "MontantTTC", "Statut"] if c in df_show.columns]
    st.dataframe(
        df_show[cols_display].sort_values(["Date_seule", "Heure"], ascending=[False, True]),
        use_container_width=True, hide_index=True, height=500,
        column_config={
            "MontantTTC": st.column_config.NumberColumn("Montant (TTC)", format="%d DZD"),
            "Colis_Frigo_Psy": st.column_config.NumberColumn("❄️ Frigo/Psy"),
            "Colis": st.column_config.NumberColumn(format="%d"),
            "Lignes": st.column_config.NumberColumn(format="%d"),
        }
    )
    st.markdown(f"**{len(df_show)} bons affichés** | Colis : **{int(df_show['Colis'].sum()):,}** | Lignes : **{int(df_show['Lignes'].sum()):,}**")
