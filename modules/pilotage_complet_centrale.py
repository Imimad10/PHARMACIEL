# =============================================================================
# MODULE : Pilotage Rotations & Recouvrement (Fichier Unique Centrale)
# Fichier : modules/pilotage_complet_centrale.py
# Auteur  : PHARMACIEL ERP
# =============================================================================

from datetime import datetime, time, timedelta
import io
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES & SEUILS
# ─────────────────────────────────────────────────────────────────────────────
CUTOFF_ROTATION_2 = time(12, 15, 0)
DEBUT_JOURNEE = time(9, 0, 0)
FIN_JOURNEE = time(19, 0, 0)

DEFAULT_SEUIL_COLIS_ROUGE = 500
DEFAULT_SEUIL_COLIS_ORANGE = 350

# Mappage flexible des colonnes du fichier unique (Centrale)
COLUMN_MAPPING = {
    # --- Volet Commandes / Logistique ---
    "référence": "Référence",
    "reference": "Référence",
    "ref": "Référence",
    "num_bon": "Référence",
    "numero_bon": "Référence",
    "bon": "Référence",
    "client": "Client",
    "nom_client": "Client",
    "wilaya": "Région",
    "region": "Région",
    "région": "Région",
    "colis": "Colis",
    "nb_colis": "Colis",
    "lignes": "Lignes",
    "nb_lignes": "Lignes",
    "nbr ligne": "Lignes",
    "date création": "Date_Creation",
    "date creation": "Date_Creation",
    "date_creation": "Date_Creation",
    "frigo": "Colis_Frigo",
    "frigo_psy": "Colis_Frigo",
    "statut_impression": "Statut_Impression",
    "creer par": "Cree_Par",
    "creer_par": "Cree_Par",
    "créer par": "Cree_Par",
    # --- Volet Recouvrement / Finance ---
    "montant_ttc": "MontantTTC",
    "montant": "MontantTTC",
    "valeur_ttc": "MontantTTC",
    "t.t.c": "MontantTTC",
    "ttc": "MontantTTC",
    "montant réglé": "Montant_Regle",
    "montant regle": "Montant_Regle",
    "montant_encaisse": "Montant_Regle",
    "encaisse": "Montant_Regle",
    "paye": "Montant_Regle",
    "reste à payer": "Reste_A_Payer",
    "reste a payer": "Reste_A_Payer",
    "reste_a_payer": "Reste_A_Payer",
    "solde": "Reste_A_Payer",
    "mode_reglement": "Mode_Reglement",
    "mode_paiement": "Mode_Reglement",
    "statut_paiement": "Statut_Paiement",
}

# ─────────────────────────────────────────────────────────────────────────────
# STYLE CSS PREMIUM DE DARPHARM / PHARMACIEL
# ─────────────────────────────────────────────────────────────────────────────
CSS_PREMIUM = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Page Header ── */
.page-header {
    background: linear-gradient(135deg, rgba(26, 31, 60, 0.4), rgba(0, 102, 255, 0.08));
    border: 1px solid rgba(0, 102, 255, 0.25);
    border-radius: 20px;
    padding: 24px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.page-header h1 {
    font-size: 2rem; font-weight: 900;
    background: linear-gradient(90deg, #00B4D8, #0066FF);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 6px;
}
.page-header p { opacity: 0.75; margin: 0; font-size: 0.95rem; }

/* ── KPI Grid ── */
.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 12px; }
.kpi-card {
    background: rgba(128, 128, 128, 0.06);
    border: 1px solid rgba(128, 128, 128, 0.15);
    border-radius: 16px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.3s, transform 0.3s;
}
.kpi-card:hover { border-color: rgba(0, 102, 255, 0.4); transform: translateY(-2px); }
.kpi-card::after {
    content: ""; position: absolute;
    bottom: 0; left: 0; right: 0; height: 3px;
    border-radius: 0 0 16px 16px;
}
.kpi-card.blue::after { background: linear-gradient(90deg, #0066FF, #00B4D8); }
.kpi-card.green::after { background: linear-gradient(90deg, #10B981, #34D399); }
.kpi-card.orange::after { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.kpi-card.red::after { background: linear-gradient(90deg, #EF4444, #F87171); }
.kpi-card.neutral::after { background: linear-gradient(90deg, rgba(100,116,139,0.5), rgba(71,85,105,0.5)); }

.kpi-icon { font-size: 1.4rem; margin-bottom: 6px; }
.kpi-label { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.8px;
              text-transform: uppercase; opacity: 0.6; margin-bottom: 4px; }
.kpi-value { font-size: 1.6rem; font-weight: 900; margin: 0; line-height: 1.1; }
.kpi-sub   { font-size: 0.75rem; opacity: 0.45; margin-top: 4px; }

/* ── Alerts & Decision Cards ── */
.decision-card {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
}
.alert-box {
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 12px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 0.9rem;
}
.alert-box.danger {
    background: rgba(239, 68, 68, 0.12);
    border-left: 4px solid #EF4444;
    color: #FCA5A5;
}
.alert-box.warning {
    background: rgba(245, 158, 11, 0.12);
    border-left: 4px solid #F59E0B;
    color: #FDE047;
}
.alert-box.success {
    background: rgba(16, 185, 129, 0.12);
    border-left: 4px solid #10B981;
    color: #A7F3D0;
}
.alert-box-title {
    font-weight: 700;
    margin-bottom: 2px;
}
.alert-box-desc {
    opacity: 0.85;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# FONCTION DE LECTURE ET PARSING DU FICHIER UNIQUE
# ─────────────────────────────────────────────────────────────────────────────
def load_and_parse_centrale_file(uploaded_file) -> pd.DataFrame:
    """Lit le fichier unique de la centrale (bons.xlsx) et extrait les données Logistique + Recouvrement sur Date_Creation."""
    try:
        # Lecture robuste du fichier
        if uploaded_file.name.endswith(".csv"):
            content = uploaded_file.read()
            uploaded_file.seek(0)
            df = None
            for encoding in ['utf-8', 'latin1', 'utf-8-sig']:
                try:
                    line = content.decode(encoding).split('\n')[0]
                    sep = ';' if ';' in line else ','
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep=sep, encoding=encoding)
                    break
                except Exception:
                    continue
            if df is None:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Nettoyage des entêtes
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Mappage flexible
        df = df.rename(columns=COLUMN_MAPPING)

        # Vérification des colonnes minimales nécessaires (Date_Creation est obligatoire)
        required_cols = [
            "Référence",
            "Client",
            "Région",
            "Colis",
            "Lignes",
            "Date_Creation",
        ]
        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            st.error(
                f"❌ Colonnes minimales manquantes dans le fichier unique : {', '.join(missing)}"
            )
            return pd.DataFrame()

        # Typage des données logistiques
        df["Date_Creation"] = pd.to_datetime(df["Date_Creation"], errors="coerce")
        df = df.dropna(subset=["Date_Creation"])
        
        df["Colis"] = pd.to_numeric(df["Colis"], errors="coerce").fillna(0).astype(int)
        df["Lignes"] = pd.to_numeric(df["Lignes"], errors="coerce").fillna(0).astype(int)

        # Traitement des colonnes financières (Recouvrement)
        if "MontantTTC" not in df.columns:
            df["MontantTTC"] = 0.0
        else:
            df["MontantTTC"] = pd.to_numeric(df["MontantTTC"], errors="coerce").fillna(0.0)

        if "Montant_Regle" not in df.columns:
            df["Montant_Regle"] = 0.0
        else:
            df["Montant_Regle"] = pd.to_numeric(df["Montant_Regle"], errors="coerce").fillna(0.0)

        if "Reste_A_Payer" not in df.columns:
            df["Reste_A_Payer"] = df["MontantTTC"] - df["Montant_Regle"]
        else:
            df["Reste_A_Payer"] = pd.to_numeric(df["Reste_A_Payer"], errors="coerce").fillna(0.0)

        if "Statut_Paiement" not in df.columns:
            df["Statut_Paiement"] = np.where(
                df["Reste_A_Payer"] <= 0,
                "Réglé",
                np.where(
                    df["Montant_Regle"] > 0,
                    "Partiellement Réglé",
                    "Non Payé",
                ),
            )

        if "Colis_Frigo" not in df.columns:
            df["Colis_Frigo"] = 0
        else:
            df["Colis_Frigo"] = pd.to_numeric(df["Colis_Frigo"], errors="coerce").fillna(0).astype(int)
            
        if "Statut_Impression" not in df.columns:
            df["Statut_Impression"] = "Imprimé"
        else:
            df["Statut_Impression"] = df["Statut_Impression"].fillna("Imprimé")

        if "Mode_Reglement" not in df.columns:
            df["Mode_Reglement"] = "Non défini"
        else:
            df["Mode_Reglement"] = df["Mode_Reglement"].fillna("Non défini")

        # Extraction Date / Heure
        df["Jour_Creation"] = df["Date_Creation"].dt.date
        df["Heure_Creation"] = df["Date_Creation"].dt.time

        return df.sort_values("Date_Creation").reset_index(drop=True)

    except Exception as e:
        st.error(
            f"Erreur lors du traitement du fichier de la centrale : {str(e)}"
        )
        return pd.DataFrame()


def segmenter_rotations(df: pd.DataFrame) -> tuple:
    if df.empty:
        return df.copy(), df.copy()
    h = df["Heure_Creation"]
    mask_r2 = (h >= DEBUT_JOURNEE) & (h < CUTOFF_ROTATION_2)
    mask_r1 = (h >= CUTOFF_ROTATION_2) & (h <= FIN_JOURNEE)
    return df[mask_r2].copy(), df[mask_r1].copy()


# ─────────────────────────────────────────────────────────────────────────────
# INITIALISATION DE LA BASE DE DONNÉES EN SESSION
# ─────────────────────────────────────────────────────────────────────────────
if "db_commandes" not in st.session_state:
    st.session_state["db_commandes"] = pd.DataFrame()

# Page Main Title & Styling
st.markdown(CSS_PREMIUM, unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>⚡ Pilotage Centrale : Commandes, Rotations & Recouvrement (Date Création)</h1>
    <p>Analyse consolidée des flux logistiques et financiers indexée sur la Date de Création • Cut-Off : <strong>12h15 mn 00 sec</strong></p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📥 Import Fichier Unique")
    uploaded_file = st.file_uploader(
        "Déposer le fichier unique (CSV / Excel)", type=["csv", "xlsx", "xls"]
    )

    st.markdown("---")
    st.markdown("#### ⚙️ Paramètres Métier")
    seuil_colis_rouge = st.number_input(
        "🔴 Seuil Surcharge R2 (Colis)", value=DEFAULT_SEUIL_COLIS_ROUGE, step=50
    )
    seuil_colis_orange = st.number_input(
        "🟠 Seuil Alerte R2 (Colis)", value=DEFAULT_SEUIL_COLIS_ORANGE, step=50
    )
    
    st.markdown("---")
    st.markdown("#### ⚙️ Paramètres Financiers")
    seuil_impaye_client = st.number_input(
        "💰 Seuil Impayé Client (DZD)", value=100000, step=10000
    )

# ── Import & Fusion de Fichier ───────────────────────────────────────────────
if uploaded_file is not None:
    df_new = load_and_parse_centrale_file(uploaded_file)
    if not df_new.empty:
        st.success(f"🎯 Fichier analysé : {len(df_new)} lignes détectées avec succès.")
        
        st.subheader("Aperçu des données à fusionner :")
        st.dataframe(
            df_new[
                [
                    "Référence",
                    "Client",
                    "Date_Creation",
                    "Colis",
                    "Lignes",
                    "Région",
                    "MontantTTC",
                    "Reste_A_Payer",
                ]
            ].head(),
            use_container_width=True,
        )
        
        # Bouton de fusion
        if st.button("📥 Fusionner / Mettre à jour la base Commandes & Recouvrement", type="primary", use_container_width=True):
            if st.session_state["db_commandes"].empty:
                st.session_state["db_commandes"] = df_new
            else:
                combined = pd.concat([st.session_state["db_commandes"], df_new], ignore_index=True)
                st.session_state["db_commandes"] = combined.drop_duplicates(subset=["Référence"], keep="last")
            st.success(f"✅ Base mise à jour ! Total enregistrements : {len(st.session_state['db_commandes'])}")
            st.rerun()

# ── Verification que la Base est Alimentée ───────────────────────────────────
if st.session_state["db_commandes"].empty:
    st.info(
        "💡 Veuillez importer le fichier consolidé de la centrale (bons.xlsx) dans la barre latérale et cliquer sur 'Fusionner' pour alimenter le pilotage."
    )

    # Modèle téléchargeable
    modele = pd.DataFrame([
        {
            "Référence": "BC-1001",
            "Client": "PHARMACIE ATLAS",
            "Région": "ALGER",
            "Colis": 15,
            "Lignes": 40,
            "Date_Creation": "2026-07-20 10:30:00",
            "Colis_Frigo": 2,
            "MontantTTC": 200000,
            "Montant_Regle": 200000,
            "Reste_A_Payer": 0,
            "Mode_Reglement": "Chèque",
            "Statut_Paiement": "Réglé",
            "Statut_Impression": "Imprimé"
        },
        {
            "Référence": "BC-1002",
            "Client": "PHARMACIE EL BARAKA",
            "Région": "BLIDA",
            "Colis": 30,
            "Lignes": 80,
            "Date_Creation": "2026-07-20 11:45:00",
            "Colis_Frigo": 0,
            "MontantTTC": 450000,
            "Montant_Regle": 150000,
            "Reste_A_Payer": 300000,
            "Mode_Reglement": "Espèce",
            "Statut_Paiement": "Partiellement Réglé",
            "Statut_Impression": "Non Imprimé"
        },
        {
            "Référence": "BC-1003",
            "Client": "PHARMACIE DES PINS",
            "Région": "TIPAZA",
            "Colis": 12,
            "Lignes": 25,
            "Date_Creation": "2026-07-20 12:05:00",
            "Colis_Frigo": 1,
            "MontantTTC": 120000,
            "Montant_Regle": 0,
            "Reste_A_Payer": 120000,
            "Mode_Reglement": "Virement",
            "Statut_Paiement": "Non Payé",
            "Statut_Impression": "Non Imprimé"
        },
        {
            "Référence": "BC-1004",
            "Client": "PHARMACIE CENTRALE BLIDA",
            "Région": "BLIDA",
            "Colis": 450,
            "Lignes": 310,
            "Date_Creation": "2026-07-20 12:10:00",
            "Colis_Frigo": 5,
            "MontantTTC": 3200000,
            "Montant_Regle": 3200000,
            "Reste_A_Payer": 0,
            "Mode_Reglement": "Chèque",
            "Statut_Paiement": "Réglé",
            "Statut_Impression": "Imprimé"
        },
        {
            "Référence": "BC-1005",
            "Client": "PHARMACIE AL FATH",
            "Région": "ALGER",
            "Colis": 45,
            "Lignes": 90,
            "Date_Creation": "2026-07-20 14:30:00",
            "Colis_Frigo": 0,
            "MontantTTC": 750000,
            "Montant_Regle": 750000,
            "Reste_A_Payer": 0,
            "Mode_Reglement": "Chèque",
            "Statut_Paiement": "Réglé",
            "Statut_Impression": "Imprimé"
        }
    ])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        modele.to_excel(
            writer, index=False, sheet_name="Export_Centrale_Unique"
        )

    st.download_button(
        "📥 Télécharger le Modèle d'Exemple (Fichier Unique)",
        buf.getvalue(),
        file_name="modele_centrale_commande_recouvrement.xlsx",
        mime="application/vnd.ms-excel",
    )
    st.stop()

# ── Base de Données Globale Disponible ───────────────────────────────────────
db = st.session_state["db_commandes"]

# Sélecteur de date basé sur les dates de création
dates_dispo = sorted(db["Jour_Creation"].unique(), reverse=True)
selected_date = st.selectbox("📅 Sélectionner la Date de Création :", dates_dispo)

# Filtrage sur le jour choisi
df_filtered = db[db["Jour_Creation"] == selected_date].copy()

df_r2, df_r1 = segmenter_rotations(df_filtered)

# ── KPIs Globaux (Logistique + Finance) ──────────────────────────────────────
st.markdown("### 📊 Synthèse de la Journée Sélectionnée")

total_bons = len(df_filtered)
total_colis = int(df_filtered['Colis'].sum())
total_ttc = int(df_filtered['MontantTTC'].sum())
total_encaisse = int(df_filtered['Montant_Regle'].sum())
total_reste = int(df_filtered['Reste_A_Payer'].sum())

# Affichage des KPIs Premium avec le style CSS harmonieux
st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card blue">
        <div class="kpi-icon">📋</div>
        <div class="kpi-label">Total Bons</div>
        <p class="kpi-value">{total_bons}</p>
        <div class="kpi-sub">Bons de commande</div>
    </div>
    <div class="kpi-card blue">
        <div class="kpi-icon">📦</div>
        <div class="kpi-label">Total Colis</div>
        <p class="kpi-value">{total_colis:,}</p>
        <div class="kpi-sub">Volume total préparé</div>
    </div>
    <div class="kpi-card green">
        <div class="kpi-icon">💰 Chiffre d'Affaires</div>
        <div class="kpi-label">Chiffre d'Affaires</div>
        <p class="kpi-value" style="font-size:1.1rem; padding-top:6px; color:#10B981; font-weight:bold;">{total_ttc:,} DZD</p>
        <div class="kpi-sub">Montant Total TTC</div>
    </div>
    <div class="kpi-card green">
        <div class="kpi-icon">✅ Encaissé</div>
        <div class="kpi-label">Encaissé</div>
        <p class="kpi-value" style="font-size:1.1rem; padding-top:6px; color:#34D399; font-weight:bold;">{total_encaisse:,} DZD</p>
        <div class="kpi-sub">Cumul règlements</div>
    </div>
    <div class="kpi-card red">
        <div class="kpi-icon">⚠️ Reste à Recouvrer</div>
        <div class="kpi-label">Reste à Recouvrer</div>
        <p class="kpi-value" style="font-size:1.1rem; padding-top:6px; color:#EF4444; font-weight:bold;">{total_reste:,} DZD</p>
        <div class="kpi-sub">Montant restant dû</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# CENTRE DE DÉCISION IA & ALERTES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("### 🚨 Centre de Décision IA & Alertes Critiques")

nb_non_imprimes_r2 = len(df_r2[df_r2["Statut_Impression"] == "Non Imprimé"]) if not df_r2.empty else 0
colis_r2 = int(df_r2['Colis'].sum()) if not df_r2.empty else 0

# Impayés critiques (Reste à payer > seuil paramétrable)
impayes_critiques = df_filtered[df_filtered["Reste_A_Payer"] >= seuil_impaye_client].copy()

# Anomalies de recouvrement
anomalies_paiement = df_filtered[df_filtered["Montant_Regle"] > df_filtered["MontantTTC"]].copy()

with st.container():
    col_dec1, col_dec2 = st.columns([3, 2])
    
    with col_dec1:
        st.markdown('<div class="decision-card">', unsafe_allow_html=True)
        st.markdown("##### 📌 Diagnostic en Temps Réel")
        
        # 1. Alerte Surcharge Logistique R2
        if colis_r2 >= seuil_colis_rouge:
            st.markdown(f"""
            <div class="alert-box danger">
                <span>🚨</span>
                <div>
                    <div class="alert-box-title">SURCHARGE LOGISTIQUE CRITIQUE — Rotation 2</div>
                    <div class="alert-box-desc">
                        La charge pour la Rotation 2 atteint <strong>{colis_r2} colis</strong>, dépassant le seuil critique de <strong>{seuil_colis_rouge} colis</strong>.
                        Risque élevé de rupture du cut-off de 12h15.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif colis_r2 >= seuil_colis_orange:
            st.markdown(f"""
            <div class="alert-box warning">
                <span>⚠️</span>
                <div>
                    <div class="alert-box-title">CHARGE LOGISTIQUE ÉLEVÉE — Rotation 2</div>
                    <div class="alert-box-desc">
                        La charge est de <strong>{colis_r2} colis</strong>. Situation tendue (Seuil d'alerte : {seuil_colis_orange} colis). 
                        Surveillez le rythme de préparation.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-box success">
                <span>✅</span>
                <div>
                    <div class="alert-box-title">FLUX DE PRÉPARATION NOMINAL — Rotation 2</div>
                    <div class="alert-box-desc">
                        La charge en Rotation 2 est de <strong>{colis_r2} colis</strong>. Flux dans les limites opérationnelles.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # 2. Alerte Impayés Importants
        if not impayes_critiques.empty:
            total_impayes_crit = int(impayes_critiques["Reste_A_Payer"].sum())
            st.markdown(f"""
            <div class="alert-box danger">
                <span>💰</span>
                <div>
                    <div class="alert-box-title">RISQUE CRÉDIT IMPORTANT DÉTECTÉ</div>
                    <div class="alert-box-desc">
                        Il y a <strong>{len(impayes_critiques)} commande(s)</strong> avec un reste à recouvrer individuel supérieur ou égal à <strong>{seuil_impaye_client:,} DZD</strong>.
                        Cumul impayé critique : <strong>{total_impayes_crit:,} DZD</strong>.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # 3. Alerte Anomalies
        if not anomalies_paiement.empty:
            st.markdown(f"""
            <div class="alert-box warning">
                <span>⚙️</span>
                <div>
                    <div class="alert-box-title">ANOMALIES DANS LA SAISIE DE PAIEMENT</div>
                    <div class="alert-box-desc">
                        Détecté <strong>{len(anomalies_paiement)} bon(s)</strong> où le montant réglé est supérieur au montant TTC (Erreur d'encaissement ou trop-perçu).
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # 4. Alerte impressions non finalisées en R2
        if nb_non_imprimes_r2 > 0:
            st.markdown(f"""
            <div class="alert-box danger">
                <span>🖨️</span>
                <div>
                    <div class="alert-box-title">BONS NON IMPRIMÉS — Rotation 2</div>
                    <div class="alert-box-desc">
                        ⚠️ Attention, <strong>{nb_non_imprimes_r2} bon(s)</strong> reste(nt) à l'état <strong>Non Imprimé</strong> dans la Rotation 2 alors que le cut-off approche !
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_dec2:
        st.markdown('<div class="decision-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("##### 💡 Recommandations Opérationnelles")
        
        recs = []
        if colis_r2 >= seuil_colis_rouge:
            recs.append("🏃 **Logistique** : Réaffecter immédiatement 2 préparateurs supplémentaires du secteur réception/stockage vers la préparation R2.")
        if nb_non_imprimes_r2 > 0:
            recs.append("🖨️ **Impression** : Lancer immédiatement l'édition physique des bons non imprimés en R2 pour éviter les goulets d'étranglement.")
        if not impayes_critiques.empty:
            recs.append(f"⚠️ **Recouvrement** : Suspendre l'expédition ou demander une validation de la direction financière pour les clients suivants : **{', '.join(impayes_critiques['Client'].unique())}**.")
        if not anomalies_paiement.empty:
            recs.append("🔍 **Finance** : Audit nécessaire sur les encaissements des bons : " + ", ".join(anomalies_paiement["Référence"].tolist()))
        if not recs:
            recs.append("✅ **Tous les indicateurs sont au vert**. Aucune action immédiate requise. Maintenir le rythme actuel.")
            
        for r in recs:
            st.write(r)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Onglets d'Analyse Séparés ────────────────────────────────────────────────
tab_log, tab_fin, tab_raw = st.tabs([
    "📦 Volet Logistique & Rotations",
    "💰 Volet Recouvrement & Paiements",
    "📋 Fichier Brut Traité",
])

# ── ONGLETS LOGISTIQUE ────────────────────────────────────────────────────────
with tab_log:
    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("#### 🔵 Rotation 2 — Livraison Jour-J (départ ≥ 12h30)")
        st.markdown(f"**Tranche :** 09:00 → 12:15 &nbsp;|&nbsp; 📋 **{len(df_r2)} bons** &nbsp;|&nbsp; 📦 **{int(df_r2['Colis'].sum()):,} colis** &nbsp;|&nbsp; ❄️ **{int(df_r2['Colis_Frigo'].sum())} colis sensibles**")
        
        if not df_r2.empty:
            st.dataframe(
                df_r2[["Référence", "Client", "Région", "Colis", "Lignes", "Colis_Frigo", "Statut_Impression", "Date_Creation"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date_Creation": st.column_config.DatetimeColumn("Heure Création", format="HH:mm:ss"),
                    "Colis_Frigo": st.column_config.NumberColumn("❄️ Frigo/Psy")
                }
            )
        else:
            st.info("Aucun bon validé en Rotation 2.")

    with col_l2:
        st.markdown("#### 🟣 Rotation 1 — Livraison Lendemain (départ 05h00)")
        st.markdown(f"**Tranche :** 12:15 → 19:00 &nbsp;|&nbsp; 📋 **{len(df_r1)} bons** &nbsp;|&nbsp; 📦 **{int(df_r1['Colis'].sum()):,} colis** &nbsp;|&nbsp; ❄️ **{int(df_r1['Colis_Frigo'].sum())} colis sensibles**")
        
        if not df_r1.empty:
            st.dataframe(
                df_r1[["Référence", "Client", "Région", "Colis", "Lignes", "Colis_Frigo", "Statut_Impression", "Date_Creation"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date_Creation": st.column_config.DatetimeColumn("Heure Création", format="HH:mm:ss"),
                    "Colis_Frigo": st.column_config.NumberColumn("❄️ Frigo/Psy")
                }
            )
        else:
            st.info("Aucun bon validé en Rotation 1.")

    # Graphique de répartition temporelle empilé par Wilaya
    st.markdown("#### 📈 Distribution Temporelle des Validations (Stacked Bar par Wilaya)")
    
    # Construction de la distribution horaire
    df_chart = df_filtered.copy()
    df_chart["Tranche30m"] = df_chart["Date_Creation"].dt.floor("30min")
    df_group = df_chart.groupby(["Tranche30m", "Région"]).agg(
        Bons=("Référence", "count"),
        Colis=("Colis", "sum")
    ).reset_index().sort_values("Tranche30m")
    
    df_group["Heure_str"] = df_group["Tranche30m"].dt.strftime("%H:%M")
    
    COLORS_REGIONS = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#06B6D4", "#EC4899", "#64748B"]
    
    fig = px.bar(
        df_group,
        x="Heure_str",
        y="Bons",
        color="Région",
        color_discrete_sequence=COLORS_REGIONS,
        custom_data=["Région", "Colis"],
        labels={"Heure_str": "Tranche Horaire (30 min)", "Bons": "Bons Validés", "Région": "Wilaya"},
        barmode="stack"
    )
    
    # Lignes métier
    cutoff_str = "12:15"
    x_labels = []
    for h in df_group["Heure_str"]:
        if h not in x_labels:
            x_labels.append(h)
            
    if x_labels:
        if cutoff_str in x_labels:
            cutoff_idx = x_labels.index(cutoff_str)
        else:
            cutoff_idx = next((i for i, h in enumerate(x_labels) if h >= cutoff_str), len(x_labels) - 1)
            
        fig.add_shape(
            type="line",
            x0=cutoff_idx - 0.5, x1=cutoff_idx - 0.5,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="#EF4444", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=cutoff_idx - 0.5, y=1.05,
            xref="x", yref="paper",
            text="⏱ CUT-OFF 12h15",
            showarrow=False,
            font=dict(color="#EF4444", size=10, weight="bold"),
            xanchor="center", yanchor="bottom",
            bgcolor="rgba(15,17,23,0.85)",
            bordercolor="#EF4444",
            borderwidth=1,
            borderpad=4,
        )
        
    fig.add_hline(
        y=10,
        line_dash="dot",
        line_color="#F59E0B",
        annotation_text="Capacité Max (10)",
        annotation_position="top right",
        annotation_font=dict(color="#F59E0B", size=10, weight="bold"),
    )
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=30, l=30, r=20),
        height=350,
        legend=dict(orientation="h", y=1.15, x=0, bgcolor="rgba(0,0,0,0)")
    )
    st.plotly_chart(fig, use_container_width=True)

# ── ONGLETS FINANCIERS ────────────────────────────────────────────────────────
with tab_fin:
    st.markdown("#### 💳 Analyse Financière & Recouvrement par Client")

    col_f1, col_f2 = st.columns([2, 3])

    with col_f1:
        # Répartition des paiements
        fig_pay = px.pie(
            df_filtered,
            names="Statut_Paiement",
            values="MontantTTC",
            title="Répartition des Montants par Statut de Paiement",
            color_discrete_sequence=["#10B981", "#F59E0B", "#EF4444", "#3B82F6"],
        )
        fig_pay.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig_pay, use_container_width=True)
        
        # Répartition par mode de règlement
        fig_mode = px.bar(
            df_filtered.groupby("Mode_Reglement")["Montant_Regle"].sum().reset_index(),
            x="Mode_Reglement",
            y="Montant_Regle",
            title="Encaissements par Mode de Règlement",
            color_discrete_sequence=["#3B82F6"]
        )
        fig_mode.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title=""),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Encaissé (DZD)")
        )
        st.plotly_chart(fig_mode, use_container_width=True)

    with col_f2:
        st.markdown("##### 🏆 Suivi Détail des En-cours & Recouvrements (Top Clients)")
        
        # Tableau détaillé par client
        recouv_df = (
            df_filtered.groupby("Client")
            .agg(
                Bons_Valides=("Référence", "count"),
                Total_TTC=("MontantTTC", "sum"),
                Encaisse=("Montant_Regle", "sum"),
                Reste_A_Payer=("Reste_A_Payer", "sum"),
            )
            .sort_values("Reste_A_Payer", ascending=False)
            .reset_index()
        )
        
        st.dataframe(
            recouv_df, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total_TTC": st.column_config.NumberColumn("Total TTC", format="%d DZD"),
                "Encaisse": st.column_config.NumberColumn("Encaissé", format="%d DZD"),
                "Reste_A_Payer": st.column_config.NumberColumn("Reste à Recouvrer", format="%d DZD"),
                "Bons_Valides": st.column_config.NumberColumn("Bons")
            }
        )
        
        # Liste des Bons avec impayés
        st.markdown("##### 📑 Liste des Commandes Non Réglées du Jour")
        impayes_df = df_filtered[df_filtered["Reste_A_Payer"] > 0][["Référence", "Client", "MontantTTC", "Montant_Regle", "Reste_A_Payer", "Mode_Reglement", "Statut_Paiement"]].sort_values("Reste_A_Payer", ascending=False)
        st.dataframe(
            impayes_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "MontantTTC": st.column_config.NumberColumn("Montant TTC", format="%d DZD"),
                "Montant_Regle": st.column_config.NumberColumn("Encaissé", format="%d DZD"),
                "Reste_A_Payer": st.column_config.NumberColumn("Reste à Payer", format="%d DZD")
            }
        )

# ── ONGLETS DONNÉES BRUTES ────────────────────────────────────────────────────
with tab_raw:
    st.markdown("#### 📋 Données Consolidées et Mappées")
    st.markdown("Ce tableau affiche le contenu du fichier après nettoyage, renommage des colonnes et enrichissement logistique/financier.")
    st.dataframe(
        df_filtered, 
        use_container_width=True,
        column_config={
            "MontantTTC": st.column_config.NumberColumn("Montant TTC", format="%d DZD"),
            "Montant_Regle": st.column_config.NumberColumn("Montant Réglé", format="%d DZD"),
            "Reste_A_Payer": st.column_config.NumberColumn("Reste à Payer", format="%d DZD"),
            "Date_Creation": st.column_config.DatetimeColumn("Date/Heure Création", format="DD/MM/YYYY HH:mm:ss")
        }
    )
