import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from utils_gsheets import load_gs_data
from datetime import datetime, timedelta
from utils_ia import ask_ai, is_ia_enabled

user = st.session_state.get('current_user', {'username': 'Utilisateur', 'role': 'Saisie'})
username = user['username']
role = user.get('role', 'Saisie')

st.title(f"📡 Supervision Temps Réel — Darpharm Solution")
st.caption(f"Connecté : **{username}** ({role}) · Actualisé à {datetime.now().strftime('%H:%M:%S')}")

# Choix du template Plotly selon le thème
plotly_template = "plotly_white" if st.session_state.theme == "Clair" else "plotly_dark"
chart_color = "#1a1c21" if st.session_state.theme == "Clair" else "#e0e6ed"

# Bouton de rafraîchissement
col_ref, col_empty = st.columns([1, 5])
with col_ref:
    if st.button("🔄 Actualiser", use_container_width=True, key="btn_refresh"):
        st.cache_data.clear()
        st.rerun()

st.divider()


# ═══════════════════════════════════════════
# 1. COLLECTE DES KPIs DE TOUS LES MODULES
# ═══════════════════════════════════════════
@st.cache_data(ttl=60)  # Rafraîchissement auto toutes les 60 secondes
def collect_all_kpis():
    kpis = {}

    # --- RECOUVREMENT ---
    df_rec = load_gs_data("Recouvrement", "data_recouvrement.csv", ["Reste à payer", "Statut", "Livreur"])
    if not df_rec.empty:
        for col in ["Reste à payer"]:
            if col in df_rec.columns:
                df_rec[col] = pd.to_numeric(df_rec[col].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        kpis['rec_total_du'] = df_rec['Reste à payer'].sum() if 'Reste à payer' in df_rec.columns else 0
        kpis['rec_dossiers'] = len(df_rec)
        kpis['rec_en_attente'] = len(df_rec[df_rec['Statut'] == 'En attente']) if 'Statut' in df_rec.columns else 0
        kpis['rec_regle'] = len(df_rec[df_rec['Statut'] == 'Réglé']) if 'Statut' in df_rec.columns else 0
        kpis['rec_by_status'] = df_rec['Statut'].value_counts().to_dict() if 'Statut' in df_rec.columns else {}
        kpis['rec_by_livreur'] = df_rec.groupby('Livreur')['Reste à payer'].sum().to_dict() if 'Livreur' in df_rec.columns else {}
    else: kpis['rec_total_du'] = kpis['rec_dossiers'] = kpis['rec_en_attente'] = kpis['rec_regle'] = 0

    # --- ARCHIVES RECOUVREMENT ---
    df_arch = load_gs_data("Archives_Recouvrement", "data_archive_recouvrement.csv", ["Montant Initial"])
    if not df_arch.empty:
        kpis['arch_count'] = len(df_arch)
        kpis['arch_recouvre'] = pd.to_numeric(df_arch['Montant Initial'], errors='coerce').fillna(0).sum()
    else: kpis['arch_count'] = kpis['arch_recouvre'] = 0

    # --- INVENTAIRE MASTER ---
    df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", ["designation", "ddp_saisi"])
    if not df_inv.empty:
        kpis['inv_saisies'] = len(df_inv)
        kpis['inv_produits_uniques'] = df_inv['designation'].nunique() if 'designation' in df_inv.columns else 0
    else: kpis['inv_saisies'] = kpis['inv_produits_uniques'] = 0

    # --- INVENTAIRE DÉTAIL ---
    df_det = load_gs_data("Saisie_Inventaire_Zone", "data_inventaire_detail/saisie_detail.csv", ["zone"])
    if not df_det.empty:
        kpis['inv_det_saisies'] = len(df_det)
        kpis['inv_det_zones'] = df_det['zone'].nunique() if 'zone' in df_det.columns else 0
    else: kpis['inv_det_saisies'] = kpis['inv_det_zones'] = 0

    # --- POINTAGES ---
    df_p = load_gs_data("Pointages", "data/db_pointages.csv", ["date_pointage"])
    if not df_p.empty:
        kpis['pointages_total'] = len(df_p)
        today_s = datetime.now().strftime("%d/%m/%Y")
        kpis['pointages_today'] = len(df_p[df_p['date_pointage'].str.contains(today_s, na=False)])
    else: kpis['pointages_total'] = kpis['pointages_today'] = 0

    # --- LITIGES SAV ---
    df_r = load_gs_data("Litiges_SAV", "data/db_reclamations.csv", ["statut"])
    if not df_r.empty:
        kpis['reclams_total'] = len(df_r)
        kpis['reclams_encours'] = len(df_r[df_r['statut'] == 'En cours'])
    else: kpis['reclams_total'] = kpis['reclams_encours'] = 0
    
    # --- INVENTAIRE TRIPLE ---
    df_triple = load_gs_data("Inventaire_Triple", "data/db_inv_triple.csv", ["produit"])
    kpis['inv_triple_count'] = len(df_triple) if not df_triple.empty else 0
    
    # --- PÉREMPTIONS (Basé sur Saisie_Inventaire) ---
    if not df_inv.empty and 'ddp_saisi' in df_inv.columns:
        now = datetime.now()
        critiques = 0
        for d in df_inv['ddp_saisi'].dropna():
            try:
                dt = pd.to_datetime(d, format='%m/%Y')
                if (dt.year - now.year)*12 + dt.month - now.month <= 3:
                    critiques += 1
            except: pass
        kpis['peremptions_critiques'] = critiques
    else: kpis['peremptions_critiques'] = 0

    # --- MISSIONS LIVREURS ---
    df_mis = load_gs_data("Missions", "data_expedition/missions.csv", ["Fin", "Livreur"])
    if not df_mis.empty:
        kpis['missions_total'] = len(df_mis)
        kpis['missions_en_cours'] = len(df_mis[df_mis['Fin'].isna() | (df_mis['Fin'] == '')])
        kpis['missions_by_livreur'] = df_mis['Livreur'].value_counts().to_dict()
    else: kpis['missions_total'] = kpis['missions_en_cours'] = 0

    # --- LOGS ---
    df_logs = load_gs_data("Logs", "data/db_logs.csv", ["timestamp", "user", "action", "module"])
    if not df_logs.empty:
        today_s = datetime.now().strftime("%Y-%m-%d")
        kpis['logs_today'] = len(df_logs[df_logs['timestamp'].str.contains(today_s, na=False)])
        kpis['logs_all'] = df_logs.tail(20).to_dict('records')
    else: kpis['logs_today'] = 0; kpis['logs_all'] = []

    return kpis

kpis = collect_all_kpis()

if is_ia_enabled():
    st.markdown("### 🤖 Briefing Exécutif IA")
    if st.button("✨ Générer la synthèse intelligente du jour", use_container_width=True, type="primary"):
        with st.spinner("L'IA analyse vos performances en temps réel..."):
            prompt = f"Tu es le Directeur des Opérations Virtuel de la pharmacie. Voici les indicateurs actuels : {kpis}. Rédige un briefing très court (3 paragraphes max) et dynamique pour l'équipe dirigeante. Mets en évidence le montant à recouvrer, les risques de péremption, et l'avancement de l'inventaire. Propose 2 actions urgentes à faire aujourd'hui. Utilise des emojis."
            st.info(ask_ai(prompt))
    st.divider()

# ═══════════════════════════════════════════
# 2. KPIs PRINCIPAUX
# ═══════════════════════════════════════════
st.subheader("📊 Indicateurs Clés")
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total à Recouvrer", f"{kpis.get('rec_total_du',0):,.0f} DA",
            delta=f"{kpis.get('rec_en_attente',0)} en attente", delta_color="inverse")
col2.metric("✅ Dossiers Archivés", kpis.get('arch_count', 0),
            delta=f"{kpis.get('arch_recouvre',0):,.0f} DA récupérés")
col3.metric("📝 Saisies Inventaire", kpis.get('inv_saisies', 0),
            delta=f"{kpis.get('inv_produits_uniques',0)} produits uniques")
col4.metric("📋 Inventaire Triple", kpis.get('inv_triple_count', 0),
            delta="Lignes modifiées")

st.markdown("<br>", unsafe_allow_html=True)
col5, col6, col7, col8 = st.columns(4)
col5.metric("🚚 Pointages Exp.", kpis.get('pointages_total', 0),
            delta=f"{kpis.get('pointages_today',0)} aujourd'hui")
col6.metric("⚠️ Litiges SAV", kpis.get('reclams_total', 0),
            delta=f"{kpis.get('reclams_encours',0)} en cours", delta_color="inverse")
col7.metric("⏳ Périmés / Critiques", kpis.get('peremptions_critiques', 0),
            delta="Moins de 3 mois", delta_color="inverse")
col8.metric("🚚 Missions Liv.", kpis.get('missions_total', 0),
            delta=f"{kpis.get('missions_en_cours',0)} en cours")

st.divider()

# ═══════════════════════════════════════════
# 3. GRAPHIQUES ANALYTIQUES
# ═══════════════════════════════════════════
g1, g2 = st.columns(2)

with g1:
    st.markdown("#### 💰 Recouvrement par Statut")
    if kpis.get('rec_by_status'):
        df_status = pd.DataFrame(list(kpis['rec_by_status'].items()), columns=['Statut', 'Nb'])
        colors = {'En attente': '#f59e0b', 'Partiel': '#3b82f6', 'Réglé': '#10b981',
                  'Clôturé': '#6b7280', 'Annulé': '#ef4444', 'Litige': '#8b5cf6'}
        fig = px.pie(df_status, values='Nb', names='Statut', hole=0.5,
                     color='Statut', color_discrete_map=colors,
                     template=plotly_template)
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée de recouvrement.")

with g2:
    st.markdown("#### 🚚 Reste à Payer par Livreur")
    if kpis.get('rec_by_livreur'):
        df_liv = pd.DataFrame(list(kpis['rec_by_livreur'].items()), columns=['Livreur', 'Montant'])
        df_liv = df_liv.sort_values('Montant', ascending=True)
        fig2 = px.bar(df_liv, x='Montant', y='Livreur', orientation='h',
                      color='Montant', color_continuous_scale='Reds',
                      text_auto='.2s', template=plotly_template)
        fig2.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Aucune donnée par livreur.")

st.divider()

# ═══════════════════════════════════════════
# 4. ÉTAT DES MISSIONS EN COURS
# ═══════════════════════════════════════════
g3, g4 = st.columns(2)

with g3:
    st.markdown("#### 🗺️ Missions Livreurs")
    m1, m2 = st.columns(2)
    m1.metric("Total Missions", kpis.get('missions_total', 0))
    m2.metric("🟢 En Cours", kpis.get('missions_en_cours', 0))
    if kpis.get('missions_by_livreur'):
        df_mis_liv = pd.DataFrame(list(kpis['missions_by_livreur'].items()), columns=['Livreur', 'Missions'])
        fig3 = px.bar(df_mis_liv, x='Livreur', y='Missions', color='Missions',
                      color_continuous_scale='Blues', text_auto=True,
                      template=plotly_template)
        fig3.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

with g4:
    st.markdown("#### 📦 Inventaire Détail")
    i1, i2 = st.columns(2)
    i1.metric("Lignes Saisies", kpis.get('inv_det_saisies', 0))
    i2.metric("Zones Actives", kpis.get('inv_det_zones', 0))

    try:
        df_det_full = load_gs_data("Saisie_Inventaire_Zone", "data_inventaire_detail/saisie_detail.csv", ["zone"])
        if not df_det_full.empty and 'zone' in df_det_full.columns:
            df_zone = df_det_full.groupby('zone').size().reset_index(name='Saisies')
            fig4 = px.bar(df_zone, x='zone', y='Saisies', color='Saisies',
                          color_continuous_scale='Greens', text_auto=True,
                          template=plotly_template)
            fig4.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)
    except: st.info("Aucune saisie d'inventaire détail sur GSheets.")

st.divider()

# ═══════════════════════════════════════════
# 5. JOURNAL D'ACTIVITÉ EN TEMPS RÉEL
# ═══════════════════════════════════════════
st.markdown("#### 📋 Journal d'Activité (20 dernières actions)")
logs_data = kpis.get('logs_all', [])
if logs_data:
    df_logs = pd.DataFrame(logs_data[::-1])  # Plus récent en premier
    cols_to_show = [c for c in ['timestamp', 'user', 'action', 'module'] if c in df_logs.columns]
    st.dataframe(df_logs[cols_to_show] if cols_to_show else df_logs,
                 use_container_width=True, hide_index=True)
else:
    st.info("Aucune activité enregistrée.")

st.caption(f"⏱️ Cache actualisé automatiquement toutes les 60 secondes. Cliquez sur 🔄 Actualiser pour forcer la mise à jour.")
