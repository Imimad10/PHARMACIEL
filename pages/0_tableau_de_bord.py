import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from tinydb import TinyDB
from datetime import datetime, timedelta

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
    try:
        df_rec = pd.read_csv("data_recouvrement.csv", sep=',', encoding='utf-8-sig')
        for col in ["Montant Initial", "Montant Réglé", "Reste à payer"]:
            if col in df_rec.columns:
                df_rec[col] = pd.to_numeric(df_rec[col].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        kpis['rec_total_du'] = df_rec['Reste à payer'].sum() if 'Reste à payer' in df_rec.columns else 0
        kpis['rec_dossiers'] = len(df_rec)
        kpis['rec_en_attente'] = len(df_rec[df_rec['Statut'] == 'En attente']) if 'Statut' in df_rec.columns else 0
        kpis['rec_regle'] = len(df_rec[df_rec['Statut'] == 'Réglé']) if 'Statut' in df_rec.columns else 0
        kpis['rec_by_status'] = df_rec['Statut'].value_counts().to_dict() if 'Statut' in df_rec.columns else {}
        kpis['rec_by_livreur'] = df_rec.groupby('Livreur')['Reste à payer'].sum().to_dict() if 'Livreur' in df_rec.columns else {}
    except: kpis['rec_total_du'] = kpis['rec_dossiers'] = kpis['rec_en_attente'] = kpis['rec_regle'] = 0

    # --- ARCHIVES RECOUVREMENT ---
    try:
        df_arch = pd.read_csv("data_archive_recouvrement.csv", sep=',', encoding='utf-8-sig')
        kpis['arch_count'] = len(df_arch)
        kpis['arch_recouvre'] = pd.to_numeric(df_arch.get('Montant Initial', pd.Series()), errors='coerce').fillna(0).sum()
    except: kpis['arch_count'] = kpis['arch_recouvre'] = 0

    # --- INVENTAIRE MASTER ---
    try:
        import unicodedata
        df_inv = pd.read_csv("data_inventaire/saisie.csv", sep=';', encoding='utf-8-sig')
        kpis['inv_saisies'] = len(df_inv)
        kpis['inv_produits_uniques'] = df_inv['designation'].nunique() if 'designation' in df_inv.columns else 0
    except: kpis['inv_saisies'] = kpis['inv_produits_uniques'] = 0

    # --- INVENTAIRE DÉTAIL ---
    try:
        df_det = pd.read_csv("data_inventaire_detail/saisie_detail.csv", sep=';', encoding='utf-8-sig')
        kpis['inv_det_saisies'] = len(df_det)
        kpis['inv_det_zones'] = df_det['zone'].nunique() if 'zone' in df_det.columns else 0
    except: kpis['inv_det_saisies'] = kpis['inv_det_zones'] = 0

    # --- LOGISTIQUE (TinyDB) ---
    try:
        db = TinyDB("db_pharmaciel.json")
        pointages = db.table('pointages').all()
        kpis['pointages_total'] = len(pointages)
        kpis['pointages_today'] = len([p for p in pointages if str(datetime.now().date()) in str(p.get('date_pointage',''))])
        reclams = db.table('reclamations').all()
        kpis['reclams_total'] = len(reclams)
        kpis['reclams_encours'] = len([r for r in reclams if r.get('statut') == 'En cours'])
    except: kpis['pointages_total'] = kpis['pointages_today'] = kpis['reclams_total'] = kpis['reclams_encours'] = 0

    # --- MISSIONS LIVREURS ---
    try:
        df_mis = pd.read_csv("data_expedition/missions.csv", sep=',', encoding='utf-8-sig')
        kpis['missions_total'] = len(df_mis)
        kpis['missions_en_cours'] = len(df_mis[df_mis['Fin'] == '']) if 'Fin' in df_mis.columns else 0
        kpis['missions_by_livreur'] = df_mis['Livreur'].value_counts().to_dict() if 'Livreur' in df_mis.columns else {}
    except: kpis['missions_total'] = kpis['missions_en_cours'] = 0

    # --- LOGS ---
    try:
        db_logs = TinyDB('data/db_logs.json')
        logs = db_logs.all()
        kpis['logs_today'] = len([l for l in logs if str(datetime.now().date()) in str(l.get('timestamp',''))])
        kpis['logs_all'] = logs[-20:]  # 20 dernières actions
    except: kpis['logs_today'] = 0; kpis['logs_all'] = []

    return kpis

kpis = collect_all_kpis()

# ═══════════════════════════════════════════
# 2. KPIs PRINCIPAUX
# ═══════════════════════════════════════════
st.subheader("📊 Indicateurs Clés")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Total à Recouvrer", f"{kpis.get('rec_total_du',0):,.0f} DA",
            delta=f"{kpis.get('rec_en_attente',0)} en attente", delta_color="inverse")
col2.metric("✅ Dossiers Archivés", kpis.get('arch_count', 0),
            delta=f"{kpis.get('arch_recouvre',0):,.0f} DA récupérés")
col3.metric("📝 Saisies Inventaire", kpis.get('inv_saisies', 0),
            delta=f"{kpis.get('inv_produits_uniques',0)} produits uniques")
col4.metric("🚚 Pointages", kpis.get('pointages_total', 0),
            delta=f"{kpis.get('pointages_today',0)} aujourd'hui")
col5.metric("⚠️ Litiges SAV", kpis.get('reclams_total', 0),
            delta=f"{kpis.get('reclams_encours',0)} en cours", delta_color="inverse")

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
        df_det_full = pd.read_csv("data_inventaire_detail/saisie_detail.csv", sep=';', encoding='utf-8-sig')
        if 'zone' in df_det_full.columns:
            df_zone = df_det_full.groupby('zone').size().reset_index(name='Saisies')
            fig4 = px.bar(df_zone, x='zone', y='Saisies', color='Saisies',
                          color_continuous_scale='Greens', text_auto=True,
                          template=plotly_template)
            fig4.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)
    except: st.info("Aucune saisie d'inventaire détail.")

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
