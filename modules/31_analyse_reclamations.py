import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
RECLAM_WORKSHEET = "Analyse_Reclamations"
RECLAM_FALLBACK = "data/db_reclamations_analyse.csv"

# --- STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    * { font-family: 'Outfit', sans-serif; }

    .reclam-header {
        background: linear-gradient(135deg, #4338ca 0%, #7c3aed 100%);
        padding: 32px; border-radius: 22px; color: white;
        margin-bottom: 28px; box-shadow: 0 10px 30px rgba(124, 58, 237, 0.25);
    }
    .reclam-header h1 { margin:0; font-size:2.2rem; font-weight:800; }
    .reclam-header p  { margin:6px 0 0; opacity:.85; font-size:1rem; }

    .kpi-card {
        background: white; border-radius: 16px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        border: 1px solid #f1f5f9; text-align: center;
    }
    .kpi-num  { font-size: 2rem; font-weight: 800; margin-top: 5px; }
    .kpi-lbl  { font-size: 0.72rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .badge    { display:inline-block; padding: 3px 10px; border-radius: 20px; font-size:.75rem; font-weight:700; }
    .badge-green  { background:#d1fae5; color:#065f46; }
    .badge-yellow { background:#fef3c7; color:#92400e; }
    .badge-red    { background:#fee2e2; color:#991b1b; }
    .badge-blue   { background:#dbeafe; color:#1e40af; }

    .ia-report {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.05), rgba(30,41,59,0.02));
        border-left: 5px solid #7c3aed; padding: 28px; border-radius: 16px;
        color: #1e293b; line-height: 1.7; border: 1px solid rgba(124,58,237,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="reclam-header">
    <h1>🎯 Suivi des Réclamations (Export Logipharm)</h1>
    <p>Tableau de bord opérationnel : Workflow complet (Validé → Imprimé → Expédié → Clôturé) — Données issues de l'export Logipharm via l'Importateur Universel.</p>
</div>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNEES ---
if "df_reclam_analysed" not in st.session_state:
    df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
    if not df_db.empty:
        st.session_state.df_reclam_analysed = df_db

if "df_reclam_analysed" not in st.session_state or st.session_state.df_reclam_analysed.empty:
    st.warning("⚠️ Aucune donnée disponible. Importez un fichier de réclamations via **Administration Centrale → Importateur Universel**.")
    st.info("Le système détectera automatiquement le type 'Réclamations' si votre colonne **Référence** contient des valeurs commençant par **RC** (ex: 26/RC0000000144).")
    st.stop()

df_raw = st.session_state.df_reclam_analysed.copy()

# --- NORMALISATION DES COLONNES LOGIPHARM ---
# Mapping flexible pour le fichier Logipharm (colonnes A=Valide, B=Imprime, C=Expedie, D=Cloture)
col_map_display = {
    "Valide":           "✅ Validé",
    "Imprime":          "🖨️ Imprimé",
    "Expedie":          "🚚 Expédié",
    "Cloture":          "📦 Clôturé",
    "reference":        "Référence RC",
    "date":             "Date",
    "client":           "Client / Pharmacie",
    "region":           "Région",
    "Valeur":           "Valeur (DA)",
    "Date_Creation":    "Date Création",
    "Créer par":        "Créé par",
    "Valider par":      "Validé par",
    "Date validation":  "Date Validation",
    "Remarque":         "Remarque",
    "Date Clôture":     "Date Clôture",
    "Clôturé par":      "Clôturé par",
    "Formation":        "Formation Hors Date",
    "Stat":             "Statut Secondaire",
    "Verif. primaire":  "Vérifié par",
    "à Reçu par":       "Reçu par",
    "Date verif":       "Date Vérif.",
    "Date envoi":       "Date Envoi",
    "date réception":   "Date Réception",
}

# Nettoyage: remplir les colonnes de workflow si absentes
for col_wf in ["Valide", "Imprime", "Expedie", "Cloture"]:
    if col_wf not in df_raw.columns:
        df_raw[col_wf] = ""

# Normaliser les valeurs booléennes de workflow
def norm_bool(val):
    s = str(val).strip().upper()
    if any(k in s for k in ["VALID", "IMPRIM", "EXPEDI", "CLÔTUR", "CLOTUR", "OUI", "TRUE", "1", "X"]): return True
    return False

df_raw["_est_valide"]  = df_raw["Valide"].apply(norm_bool)
df_raw["_est_imprime"] = df_raw["Imprime"].apply(norm_bool)
df_raw["_est_expedie"] = df_raw["Expedie"].apply(norm_bool)
df_raw["_est_cloture"] = df_raw["Cloture"].apply(norm_bool)

# Colonne Valeur numérique
valeur_col = next((c for c in df_raw.columns if str(c).strip().lower() in ["valeur", "montant", "h.t", "ht"]), None)
if valeur_col:
    df_raw["_valeur_num"] = pd.to_numeric(
        df_raw[valeur_col].astype(str).str.replace(r'[\s\xa0,]', '', regex=True).str.replace(',', '.'),
        errors="coerce"
    ).fillna(0.0)
else:
    df_raw["_valeur_num"] = 0.0

# Extraire agent créateur (créer par / cree_par)
agent_col = next((c for c in df_raw.columns if str(c).strip().lower() in ["créer par", "creer par", "cree_par", "créé par"]), None)
region_col = next((c for c in df_raw.columns if str(c).strip().lower() in ["region", "région"]), None)
client_col = next((c for c in df_raw.columns if str(c).strip().lower() in ["client", "nom_pharmacie", "pharmacie"]), None)
date_col   = next((c for c in df_raw.columns if str(c).strip().lower() in ["date", "date création", "date creation"]), None)
ref_col    = next((c for c in df_raw.columns if str(c).strip().lower() in ["référence", "reference", "ref"]), None)
remarque_col = next((c for c in df_raw.columns if str(c).strip().lower() in ["remarque", "observation", "commentaire"]), None)

# --- FILTRES SIDEBAR ---
st.sidebar.markdown("### 🎯 Filtres Réclamations")

# Filtre Statut workflow
wf_filter = st.sidebar.multiselect("Statut Workflow", ["Validé ✅", "Imprimé 🖨️", "Expédié 🚚", "Clôturé 📦"], default=[])

# Filtre par agent/créateur
if agent_col and agent_col in df_raw.columns:
    agents = ["Tous"] + sorted(df_raw[agent_col].dropna().astype(str).unique().tolist())
    sel_agent = st.sidebar.selectbox("Agent Créateur", agents)
else:
    sel_agent = "Tous"

# Filtre par région
if region_col and region_col in df_raw.columns:
    regions = ["Toutes"] + sorted(df_raw[region_col].dropna().astype(str).unique().tolist())
    sel_region = st.sidebar.selectbox("Région", regions)
else:
    sel_region = "Toutes"

# Application des filtres
df_f = df_raw.copy()
if "Validé ✅" in wf_filter:   df_f = df_f[df_f["_est_valide"]]
if "Imprimé 🖨️" in wf_filter:  df_f = df_f[df_f["_est_imprime"]]
if "Expédié 🚚" in wf_filter:  df_f = df_f[df_f["_est_expedie"]]
if "Clôturé 📦" in wf_filter:  df_f = df_f[df_f["_est_cloture"]]
if sel_agent != "Tous" and agent_col and agent_col in df_f.columns:
    df_f = df_f[df_f[agent_col].astype(str) == sel_agent]
if sel_region != "Toutes" and region_col and region_col in df_f.columns:
    df_f = df_f[df_f[region_col].astype(str) == sel_region]

# --- TABS ---
tabs = st.tabs([
    "📊 Tableau de Bord",
    "🔁 Suivi Workflow",
    "📋 Base de Données",
    "💡 Suggestions & Alertes",
    "🧠 Diagnostic IA"
])

# ════════════════════════════════════════════════
# TAB 1 — TABLEAU DE BORD
# ════════════════════════════════════════════════
with tabs[0]:
    total   = len(df_f)
    valides = df_f["_est_valide"].sum()
    expires = (~df_f["_est_cloture"]).sum()
    ca_total = df_f["_valeur_num"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">📋 Total RC</div><div class="kpi-num" style="color:#4338ca;">{total}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">✅ Validées</div><div class="kpi-num" style="color:#059669;">{valides}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">⏳ Non Clôturées</div><div class="kpi-num" style="color:#d97706;">{expires}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-lbl">💰 Valeur Totale (DA)</div><div class="kpi-num" style="color:#7c3aed;">{ca_total:,.0f}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)

    # Graphe 1 : Funnel workflow
    with col_g1:
        st.markdown("#### 🔽 Entonnoir Workflow")
        funnel_data = {
            "Étape": ["Total RC", "Validées", "Imprimées", "Expédiées", "Clôturées"],
            "Quantité": [
                total,
                int(df_f["_est_valide"].sum()),
                int(df_f["_est_imprime"].sum()),
                int(df_f["_est_expedie"].sum()),
                int(df_f["_est_cloture"].sum()),
            ]
        }
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_data["Étape"],
            x=funnel_data["Quantité"],
            textinfo="value+percent initial",
            marker={"color": ["#4338ca", "#7c3aed", "#0ea5e9", "#059669", "#6b7280"]}
        ))
        fig_funnel.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(t=10, l=10, r=10, b=10))
        st.plotly_chart(fig_funnel, use_container_width=True)

    # Graphe 2 : Répartition par région
    with col_g2:
        st.markdown("#### 🗺️ Volume par Région")
        if region_col and region_col in df_f.columns:
            reg_stats = df_f[region_col].value_counts().reset_index()
            reg_stats.columns = ["Région", "Nb RC"]
            fig_reg = px.bar(reg_stats.head(10), x="Région", y="Nb RC",
                             color="Nb RC", color_continuous_scale="Purples")
            fig_reg.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(t=10, l=10, r=10, b=10), showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("Colonne région non trouvée dans les données.")

    # Graphe 3 : Volume par agent créateur
    st.markdown("#### 👤 Réclamations par Agent Créateur")
    if agent_col and agent_col in df_f.columns:
        agent_stats = df_f[agent_col].value_counts().reset_index()
        agent_stats.columns = ["Agent", "Nb RC"]
        fig_ag = px.bar(agent_stats, x="Agent", y="Nb RC", color="Nb RC", color_continuous_scale="Blues")
        fig_ag.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(t=10, l=0, r=0, b=40), coloraxis_showscale=False)
        st.plotly_chart(fig_ag, use_container_width=True)

    # Graphe 4 : Valeur par région
    if valeur_col and region_col and region_col in df_f.columns:
        st.markdown("#### 💰 Valeur Financière par Région")
        val_reg = df_f.groupby(region_col)["_valeur_num"].sum().reset_index()
        val_reg.columns = ["Région", "Montant (DA)"]
        val_reg = val_reg.sort_values("Montant (DA)", ascending=False)
        fig_val = px.bar(val_reg, x="Région", y="Montant (DA)", color="Montant (DA)", color_continuous_scale="Reds")
        fig_val.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(t=10, l=0, r=0, b=40), coloraxis_showscale=False)
        st.plotly_chart(fig_val, use_container_width=True)

# ════════════════════════════════════════════════
# TAB 2 — SUIVI WORKFLOW
# ════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🔁 Suivi de l'état de traitement des Réclamations")
    st.markdown("Chaque réclamation passe par 4 étapes : **Validé → Imprimé → Expédié → Clôturé**")

    # Construire un df d'affichage du workflow
    wf_cols = []
    if ref_col: wf_cols.append(ref_col)
    if client_col: wf_cols.append(client_col)
    if date_col: wf_cols.append(date_col)
    if region_col: wf_cols.append(region_col)
    if agent_col: wf_cols.append(agent_col)
    if valeur_col: wf_cols.append(valeur_col)
    wf_cols += ["Valide", "Imprime", "Expedie", "Cloture"]

    wf_cols_present = [c for c in wf_cols if c in df_f.columns]
    df_wf = df_f[wf_cols_present].copy()

    # Formater les colonnes de statut avec des icônes
    def fmt_wf(val):
        if norm_bool(val):
            return "✅"
        return "⏳ En cours"

    for wf_c in ["Valide", "Imprime", "Expedie", "Cloture"]:
        if wf_c in df_wf.columns:
            df_wf[wf_c] = df_wf[wf_c].apply(fmt_wf)

    # Filtres rapides workflow
    col_wf_f1, col_wf_f2 = st.columns(2)
    show_non_cloture = col_wf_f1.checkbox("Afficher uniquement les RC non clôturées", value=False)
    show_non_valide  = col_wf_f2.checkbox("Afficher uniquement les RC non validées", value=False)

    df_wf_view = df_f.copy()
    if show_non_cloture:
        df_wf_view = df_wf_view[~df_wf_view["_est_cloture"]]
    if show_non_valide:
        df_wf_view = df_wf_view[~df_wf_view["_est_valide"]]

    wf_cols_view = [c for c in wf_cols_present if c in df_wf_view.columns]
    df_final_wf = df_wf_view[wf_cols_view].copy()
    for wf_c in ["Valide", "Imprime", "Expedie", "Cloture"]:
        if wf_c in df_final_wf.columns:
            df_final_wf[wf_c] = df_final_wf[wf_c].apply(fmt_wf)

    st.dataframe(df_final_wf, use_container_width=True, hide_index=True)

    # Métriques workflow détaillées
    st.divider()
    st.markdown("#### 📊 Taux de progression par étape")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    total_rc = len(df_f) if len(df_f) > 0 else 1

    def pct_bar(val, total, label, color):
        pct = (val / total) * 100
        return f'<div class="kpi-card"><div class="kpi-lbl">{label}</div><div class="kpi-num" style="color:{color};">{pct:.0f}%</div><div style="background:#f1f5f9;border-radius:8px;height:8px;margin-top:8px;"><div style="width:{pct:.0f}%;background:{color};height:8px;border-radius:8px;"></div></div><div style="font-size:.7rem;color:#94a3b8;margin-top:4px;">{val} / {total}</div></div>'

    col_p1.markdown(pct_bar(int(df_f["_est_valide"].sum()), total_rc, "✅ Validées", "#4338ca"), unsafe_allow_html=True)
    col_p2.markdown(pct_bar(int(df_f["_est_imprime"].sum()), total_rc, "🖨️ Imprimées", "#0ea5e9"), unsafe_allow_html=True)
    col_p3.markdown(pct_bar(int(df_f["_est_expedie"].sum()), total_rc, "🚚 Expédiées", "#059669"), unsafe_allow_html=True)
    col_p4.markdown(pct_bar(int(df_f["_est_cloture"].sum()), total_rc, "📦 Clôturées", "#7c3aed"), unsafe_allow_html=True)

# ════════════════════════════════════════════════
# TAB 3 — BASE DE DONNÉES
# ════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📋 Base de données complète des réclamations")

    # Recherche par référence RC
    search_ref = st.text_input("🔍 Rechercher par Référence RC ou Pharmacie", placeholder="Ex: RC0000000144 ou Pharmacie Centrale")

    df_view = df_f.copy()
    # Exclure les colonnes internes
    cols_excl = [c for c in df_view.columns if str(c).startswith("_")]
    df_view = df_view.drop(columns=cols_excl, errors="ignore")

    if search_ref:
        mask = pd.Series([False] * len(df_view), index=df_view.index)
        for c in df_view.columns:
            mask = mask | df_view[c].astype(str).str.contains(search_ref, case=False, na=False)
        df_view = df_view[mask]

    st.dataframe(df_view, use_container_width=True, hide_index=True)
    st.caption(f"📊 {len(df_view)} réclamation(s) affichée(s) sur {len(df_f)} au total")

    # Export CSV
    csv_data = df_view.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📥 Exporter en CSV", data=csv_data, file_name=f"reclamations_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

# ════════════════════════════════════════════════
# TAB 4 — SUGGESTIONS & ALERTES
# ════════════════════════════════════════════════
with tabs[3]:
    st.subheader("💡 Suggestions Opérationnelles & Alertes")

    non_valide_count  = (~df_raw["_est_valide"]).sum()
    non_imprime_count = (df_raw["_est_valide"] & ~df_raw["_est_imprime"]).sum()
    non_expedie_count = (df_raw["_est_imprime"] & ~df_raw["_est_expedie"]).sum()
    non_cloture_count = (df_raw["_est_expedie"] & ~df_raw["_est_cloture"]).sum()

    st.markdown("### 🚨 Points de blocage détectés dans le workflow")

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        if non_valide_count > 0:
            st.error(f"🔴 **{non_valide_count} RC non validées** — Ces réclamations sont bloquées dès l'entrée. Action requise : Superviseur doit valider.")
        else:
            st.success("✅ Toutes les réclamations sont validées.")

        if non_imprime_count > 0:
            st.warning(f"🟡 **{non_imprime_count} RC validées mais non imprimées** — Le bon de réclamation n'a pas encore été généré.")
        else:
            st.success("✅ Tous les bons ont été imprimés.")

    with col_a2:
        if non_expedie_count > 0:
            st.warning(f"🟡 **{non_expedie_count} RC imprimées mais non expédiées** — Des colis attendent encore d'être remis au transporteur.")
        else:
            st.success("✅ Toutes les RC imprimées ont été expédiées.")

        if non_cloture_count > 0:
            st.error(f"🔴 **{non_cloture_count} RC expédiées mais non clôturées** — La confirmation de réception ou la validation finale manque.")
        else:
            st.success("✅ Toutes les RC expédiées ont été clôturées.")

    st.divider()
    st.markdown("### 📌 Propositions d'Amélioration")

    suggestions = [
        ("⚡ Automatiser la validation", "Paramétrer un délai maximum de 24h pour la validation des RC après création. Au-delà, alerter le superviseur."),
        ("🖨️ Impression en lot", "Regrouper les impressions des bons de RC validés en une seule session quotidienne pour économiser du temps."),
        ("📦 Suivi livraison transporteur", "Intégrer un numéro de suivi transporteur dès la validation de l'expédition pour clôturer automatiquement les RC à réception."),
        ("📊 Rapport hebdomadaire", "Générer automatiquement chaque lundi un rapport PDF des RC en cours, segmenté par agent et par région."),
        ("📱 Notification par SMS/WhatsApp", "Notifier automatiquement le client pharmacien lors de l'expédition de sa réclamation pour améliorer l'expérience client."),
    ]

    for titre, desc in suggestions:
        with st.expander(titre):
            st.write(desc)

    # Analyse Pareto par région
    st.markdown("### 📈 Analyse Pareto : Top Régions (Concentration des RC)")
    if region_col and region_col in df_raw.columns:
        reg_cnt = df_raw[region_col].value_counts().reset_index()
        reg_cnt.columns = ["Région", "Nb"]
        reg_cnt["Cumul %"] = (reg_cnt["Nb"].cumsum() / reg_cnt["Nb"].sum() * 100).round(1)

        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(name="Nb RC", x=reg_cnt["Région"], y=reg_cnt["Nb"], marker_color="#7c3aed"))
        fig_pareto.add_trace(go.Scatter(name="Cumul %", x=reg_cnt["Région"], y=reg_cnt["Cumul %"],
                                        mode="lines+markers", line=dict(color="#ef4444", width=2), yaxis="y2"))
        fig_pareto.update_layout(
            yaxis2=dict(overlaying="y", side="right", range=[0, 110], ticksuffix="%"),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            height=350, margin=dict(t=10, l=0, r=0, b=40), legend=dict(orientation="h", y=-0.2)
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

# ════════════════════════════════════════════════
# TAB 5 — DIAGNOSTIC IA
# ════════════════════════════════════════════════
with tabs[4]:
    if is_ia_enabled():
        st.subheader("🧠 Intelligence Artificielle — Root Cause Analysis")
        st.write("L'IA va analyser les données de réclamations et identifier les causes profondes et les axes d'amélioration.")

        if st.button("🚀 LANCER L'AUDIT IA COMPLET", use_container_width=True, type="primary"):
            df_ia = df_raw.copy()

            wf_summary = {
                "Total RC":      len(df_ia),
                "Validées":      int(df_ia["_est_valide"].sum()),
                "Imprimées":     int(df_ia["_est_imprime"].sum()),
                "Expédiées":     int(df_ia["_est_expedie"].sum()),
                "Clôturées":     int(df_ia["_est_cloture"].sum()),
                "Non validées":  int((~df_ia["_est_valide"]).sum()),
                "Non clôturées": int((~df_ia["_est_cloture"]).sum()),
                "Valeur totale": f"{df_ia['_valeur_num'].sum():,.0f} DA",
            }

            top_regions = df_ia[region_col].value_counts().head(5).to_dict() if region_col and region_col in df_ia.columns else {}
            top_agents  = df_ia[agent_col].value_counts().head(5).to_dict() if agent_col and agent_col in df_ia.columns else {}
            top_clients = df_ia[client_col].value_counts().head(5).to_dict() if client_col and client_col in df_ia.columns else {}

            prompt = f"""
            Tu es un expert en logistique pharmaceutique et en gestion de la qualité pour un grossiste répartiteur algérien.
            Voici les données complètes de suivi des réclamations (fichier Logipharm) :

            **Résumé Workflow :**
            {wf_summary}

            **Top 5 Régions les plus touchées :**
            {top_regions}

            **Top 5 Agents créateurs de RC :**
            {top_agents}

            **Top 5 Clients avec le plus de réclamations :**
            {top_clients}

            TA MISSION :
            1. **Diagnostic Workflow** : Identifie où se situent les goulots d'étranglement (entre quelle étape les RC s'accumulent le plus).
            2. **Analyse Régionale** : Explique pourquoi certaines régions génèrent plus de réclamations (distance, type de produits, agent commercial...).
            3. **Profil des Agents** : Évalue si la concentration de RC par agent est normale ou révèle un problème de formation/qualité.
            4. **Plan d'Action Prioritaire** : Donne 5 actions concrètes et immédiatement applicables pour réduire les RC de 30% en 30 jours.

            Utilise le Markdown (titres, gras, puces) pour structurer ta réponse. Sois précis et orienté action.
            """

            with st.spinner("L'IA analyse les données... "):
                report = ask_ai(prompt)
                st.markdown(f'<div class="ia-report">{report}</div>', unsafe_allow_html=True)
                st.balloons()
    else:
        st.info("Activez l'IA dans les paramètres pour accéder au diagnostic automatique.")
