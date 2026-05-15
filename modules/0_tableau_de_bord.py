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

# --- CONFIGURATION DES THÈMES & MODÈLES ---
THEMES_CONFIG = {
    "Clair": {"accent": "#5b6cf9", "bg": "#f8f9fa", "card": "#ffffff", "text": "#1a1c21"},
    "Sombre": {"accent": "#60a5fa", "bg": "#0e1117", "card": "rgba(255,255,255,0.05)", "text": "#e0e6ed"},
    "USMH": {"accent": "#FFD700", "bg": "#000000", "card": "rgba(255, 215, 0, 0.05)", "text": "#ffffff"},
    "CRB": {"accent": "#ff0000", "bg": "#ffffff", "card": "rgba(255, 0, 0, 0.05)", "text": "#1a1c21"},
    "MCA": {"accent": "#00ff00", "bg": "#064e3b", "card": "rgba(0, 255, 0, 0.05)", "text": "#ffffff"}
}

current_theme = st.session_state.get('theme', 'Clair')
t = THEMES_CONFIG.get(current_theme, THEMES_CONFIG["Clair"])

st.title(f"📡 Supervision Temps Réel — Darpharm Solution")

# --- CORTEX PULSE: PROACTIVE AI BAR ---
from utils_cortex import get_strategic_snapshot
snapshot = get_strategic_snapshot()

st.markdown(f"""
<div style="background: linear-gradient(90deg, rgba(124,58,237,0.1) 0%, rgba(59,130,246,0.1) 100%); 
            border: 1px solid rgba(124,58,237,0.3); 
            border-radius: 12px; padding: 15px; margin-bottom: 25px; 
            display: flex; align-items: center; gap: 20px;
            box-shadow: 0 0 20px rgba(124,58,237,0.1);">
    <div style="font-size: 1.5rem; animation: pulse 2s infinite;">🧠</div>
    <div style="flex: 1;">
        <div style="font-size: 0.7rem; color: #7c3aed; font-weight: 800; text-transform: uppercase; letter-spacing: 2px;">Cortex IA Intelligence Pulse</div>
        <div style="font-size: 1rem; color: {t['text']}; font-weight: 600;">
            <b>Analyse :</b> CA {snapshot.get('total_ca', 0):,.0f} DA · 
            <span style="color:#ef4444;">{snapshot.get('total_reclamations', 0)} litiges à résoudre</span> · 
            <span style="color:#10b981;">Pic de charge : {snapshot.get('peak_hour', 'N/A')}h</span>
        </div>
    </div>
    <div style="background: #10b981; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 800;">LIVE</div>
</div>
<style>
@keyframes pulse {{ 0% {{ opacity: 0.5; transform: scale(1); }} 50% {{ opacity: 1; transform: scale(1.1); }} 100% {{ opacity: 0.5; transform: scale(1); }} }}
</style>
""", unsafe_allow_html=True)

st.caption(f"Connecté : **{username}** ({role}) · Actualisé à {datetime.now().strftime('%H:%M:%S')}")

# --- SÉLECTEUR DE MODÈLE (Sidebar) ---
with st.sidebar:
    st.divider()
    st.subheader("📊 Mode de Vue")
    selected_model = st.radio("Mise en page", ["Standard (Narratif)", "Centre de Commandement", "Analyse Comparative"], key="dash_model")

# Injection CSS Dynamique
st.markdown(f"""
    <style>
        .stApp {{
            background: {t['bg']} !important;
            color: {t['text']} !important;
        }}
        [data-testid="stMetric"] {{
            background: {t['card']} !important;
            border-left: 5px solid {t['accent']} !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        }}
        .dash-card {{
            background: {t['card']};
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 20px;
        }}
    </style>
""", unsafe_allow_html=True)

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
    now = datetime.now()

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

    # --- INVENTAIRE MASTER (Saisies récentes) ---
    df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", ["designation", "ddp_saisi"])
    kpis['inv_saisies'] = len(df_inv) if not df_inv.empty else 0
    kpis['inv_produits_uniques'] = df_inv['designation'].nunique() if not df_inv.empty and 'designation' in df_inv.columns else 0

    # --- INVENTAIRE TRIPLE ---
    df_triple = load_gs_data("Inventaire_Triple", "data/db_inv_triple.csv", ["produit"])
    kpis['inv_triple_count'] = len(df_triple) if not df_triple.empty else 0

    # --- POINTAGES EXPEDITEURS (Historique Dispatch) ---
    df_p_exp = load_gs_data("Historique_Pointage", "data/db_pointage_hist.csv", ["date_dispatch"])
    if not df_p_exp.empty:
        kpis['pointages_total'] = len(df_p_exp)
        today_s = now.strftime("%d/%m/%Y")
        kpis['pointages_today'] = len(df_p_exp[df_p_exp['date_dispatch'].astype(str).str.contains(today_s, na=False)])
    else: kpis['pointages_total'] = kpis['pointages_today'] = 0

    # --- LITIGES SAV (Expédition) ---
    df_sav = load_gs_data("Litiges_SAV", "data/db_sav.csv", ["statut"])
    if not df_sav.empty:
        kpis['reclams_total'] = len(df_sav)
        kpis['reclams_encours'] = len(df_sav[df_sav['statut'] == 'En cours'])
    else: kpis['reclams_total'] = kpis['reclams_encours'] = 0
    
    # --- PÉREMPTIONS (Basé sur la Liste Officielle des Lots) ---
    df_lots = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", ["ddp"])
    if not df_lots.empty:
        critiques = 0
        for d in df_lots['ddp'].dropna():
            try:
                # On supporte MM/AA, YYYY-MM-DD, etc. via parse_ddp_local style
                from utils_notifications import parse_ddp_local
                dt = parse_ddp_local(d)
                if dt and (dt.year - now.year)*12 + dt.month - now.month <= 3:
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
        today_s = now.strftime("%Y-%m-%d")
        kpis['logs_today'] = len(df_logs[df_logs['timestamp'].astype(str).str.contains(today_s, na=False)])
        kpis['logs_all'] = df_logs.tail(20).to_dict('records')
    else: kpis['logs_today'] = 0; kpis['logs_all'] = []

    return kpis

kpis = collect_all_kpis()

if is_ia_enabled():
    st.markdown("""
    <div style="background: rgba(124,58,237,0.03); border-radius: 20px; padding: 25px; border: 1px solid rgba(124,58,237,0.1); margin-bottom: 30px;">
        <h3 style="margin-top: 0; color: #7c3aed;">🤖 Briefing Exécutif du Cortex</h3>
    """, unsafe_allow_html=True)
    
    with st.spinner("L'IA affine votre stratégie..."):
        # On génère un résumé plus compact et percutant
        try:
            from utils_cortex import ask_cortex
            synthesis = ask_cortex("Rédige une synthèse TRÈS COURTE (2 phrases) de la situation actuelle et donne l'ordre du jour prioritaire.")
            st.markdown(f'<div style="font-size: 1.1rem; line-height: 1.6; color: {t["text"]}; font-weight: 500;">{synthesis}</div>', unsafe_allow_html=True)
        except:
            st.info("Synthèse IA temporairement indisponible.")
            
    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()

# ═══════════════════════════════════════════
# 2. FILTRES & FONCTIONS GLOBALES
# ═══════════════════════════════════════════

def kpi_card(label, value, delta, icon, color=t["accent"]):
    st.markdown(f"""
        <div class="dash-card" style="border-left: 5px solid {color}; height: 160px; display: flex; flex-direction: column; justify-content: center;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 2rem;">{icon}</div>
                <div>
                    <div style="font-size: 0.75rem; opacity: 0.7; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">{label}</div>
                    <div style="font-size: 1.5rem; font-weight: 900; color: {color};">{value}</div>
                </div>
            </div>
            <div style="font-size: 0.8rem; opacity: 0.6; font-weight: 600; margin-top: 8px;">{delta}</div>
        </div>
    """, unsafe_allow_html=True)

## --- FILTRES INTERACTIFS (Global) ---
st.markdown('<div class="dash-card">', unsafe_allow_html=True)
f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
with f_col1:
    search_query = st.text_input("🔍 Recherche globale (Produit, Livreur, Client...)", placeholder="Tapez pour filtrer...")
with f_col2:
    date_range = st.date_input("📅 Période", [datetime.now() - timedelta(days=30), datetime.now()])
with f_col3:
    status_filter = st.multiselect("🏷️ Statuts", ["En attente", "Réglé", "Litige", "Partiel"], default=[])
st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# 3. ROUTAGE DES MODÈLES DE VUE
# ═══════════════════════════════════════════

if selected_model == "Standard (Narratif)":
    # 2.1 KPIs PRINCIPAUX (RESTORED ALL 8)
    st.subheader("📊 Indicateurs de Performance")
    
    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
    with r1_c1: kpi_card("Total à Recouvrer", f"{kpis.get('rec_total_du',0):,.0f} DA", f"↑ {kpis.get('rec_en_attente',0)} en attente", "💰", "#f59e0b")
    with r1_c2: kpi_card("Dossiers Archivés", f"{kpis.get('arch_count', 0)}", f"↑ {kpis.get('arch_recouvre',0):,.0f} DA récup.", "✅", "#10b981")
    with r1_c3: kpi_card("Saisies Inventaire", f"{kpis.get('inv_saisies', 0)}", f"↑ {kpis.get('inv_produits_uniques',0)} produits", "📝", t["accent"])
    with r1_c4: kpi_card("Inventaire Triple", f"{kpis.get('inv_triple_count', 0)}", "Lignes modifiées", "📋", "#8b5cf6")

    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
    with r2_c1: kpi_card("Pointages Exp.", f"{kpis.get('pointages_total', 0)}", f"↑ {kpis.get('pointages_today',0)} aujourd'hui", "🚚", "#3b82f6")
    with r2_c2: kpi_card("Litiges SAV", f"{kpis.get('reclams_total', 0)}", f"↑ {kpis.get('reclams_encours',0)} en cours", "⚠️", "#ef4444")
    with r2_c3: kpi_card("Périmés Critiques", f"{kpis.get('peremptions_critiques', 0)}", "Moins de 3 mois", "⏳", "#f06585")
    with r2_c4: kpi_card("Missions Liv.", f"{kpis.get('missions_total', 0)}", f"↑ {kpis.get('missions_en_cours',0)} en cours", "🚛", "#10b981")

    st.divider()
    
    # INTERACTIVITÉ : Détails au clic
    st.markdown("#### 🔍 Analyse Interactive")
    tab_rec, tab_log, tab_inv = st.tabs(["💰 Finance", "🚚 Logistique", "📦 Stocks"])
    
    with tab_rec:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("##### Répartition par Statut")
            if kpis.get('rec_by_status'):
                df_status = pd.DataFrame(list(kpis['rec_by_status'].items()), columns=['Statut', 'Nb'])
                fig = px.pie(df_status, values='Nb', names='Statut', hole=0.5, template=plotly_template)
                st.plotly_chart(fig, use_container_width=True)
                
                selected_status = st.selectbox("Voir le détail pour :", ["Tous"] + list(kpis['rec_by_status'].keys()))
                if selected_status != "Tous":
                    st.info(f"Affichage des dossiers avec le statut : **{selected_status}**")
                    # Ici on pourrait charger le CSV complet et filtrer
            else: st.info("Aucune donnée.")
        with g2:
            st.markdown("##### Créances par Livreur")
            if kpis.get('rec_by_livreur'):
                df_liv = pd.DataFrame(list(kpis['rec_by_livreur'].items()), columns=['Livreur', 'Montant'])
                fig2 = px.bar(df_liv.sort_values('Montant'), x='Montant', y='Livreur', orientation='h', template=plotly_template, color='Montant', color_continuous_scale='Reds')
                st.plotly_chart(fig2, use_container_width=True)
            else: st.info("Aucune donnée.")

    with tab_log:
        st.markdown("##### 🗺️ Suivi des Missions")
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            st.metric("Total Missions", kpis.get('missions_total', 0))
            st.metric("🟢 En Cours", kpis.get('missions_en_cours', 0))
        with m_col2:
            if kpis.get('missions_by_livreur'):
                df_mis_liv = pd.DataFrame(list(kpis['missions_by_livreur'].items()), columns=['Livreur', 'Missions'])
                fig3 = px.bar(df_mis_liv, x='Livreur', y='Missions', color='Missions', template=plotly_template)
                st.plotly_chart(fig3, use_container_width=True)

    with tab_inv:
        st.markdown("##### 📦 Précision par Zone")
        try:
            df_det_full = load_gs_data("Saisie_Inventaire_Zone", "data_inventaire_detail/saisie_detail.csv", ["zone"])
            if not df_det_full.empty:
                df_zone = df_det_full.groupby('zone').size().reset_index(name='Saisies')
                fig4 = px.bar(df_zone, x='zone', y='Saisies', color='Saisies', template=plotly_template)
                st.plotly_chart(fig4, use_container_width=True)
        except: st.info("En attente de données...")

elif selected_model == "Centre de Commandement":
    st.info("💡 Utilisez les onglets ci-dessous pour explorer les données en détail.")
    
    # 2.1 KPIs PRINCIPAUX (RESTORED ALL 8)
    r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
    with r1_c1: kpi_card("Total à Recouvrer", f"{kpis.get('rec_total_du',0):,.0f} DA", f"↑ {kpis.get('rec_en_attente',0)} en attente", "💰", "#f59e0b")
    with r1_c2: kpi_card("Dossiers Archivés", f"{kpis.get('arch_count', 0)}", f"↑ {kpis.get('arch_recouvre',0):,.0f} DA récup.", "✅", "#10b981")
    with r1_c3: kpi_card("Saisies Inventaire", f"{kpis.get('inv_saisies', 0)}", f"↑ {kpis.get('inv_produits_uniques',0)} produits", "📝", t["accent"])
    with r1_c4: kpi_card("Inventaire Triple", f"{kpis.get('inv_triple_count', 0)}", "Lignes modifiées", "📋", "#8b5cf6")

    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
    with r2_c1: kpi_card("Pointages Exp.", f"{kpis.get('pointages_total', 0)}", f"↑ {kpis.get('pointages_today',0)} aujourd'hui", "🚚", "#3b82f6")
    with r2_c2: kpi_card("Litiges SAV", f"{kpis.get('reclams_total', 0)}", f"↑ {kpis.get('reclams_encours',0)} en cours", "⚠️", "#ef4444")
    with r2_c3: kpi_card("Périmés Critiques", f"{kpis.get('peremptions_critiques', 0)}", "Moins de 3 mois", "⏳", "#f06585")
    with r2_c4: kpi_card("Missions Liv.", f"{kpis.get('missions_total', 0)}", f"↑ {kpis.get('missions_en_cours',0)} en cours", "🚛", "#10b981")

    col_cc1, col_cc2 = st.columns([2, 1])
    
    with col_cc1:
        st.markdown('<div class="dash-card" style="height:600px;">', unsafe_allow_html=True)
        st.write("📈 **Flux d'Activité Logistique**")
        df_perf = pd.DataFrame({"Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], "Livraisons": [120, 150, 140, 180, 160, 110]})
        fig_cc = px.area(df_perf, x="Jour", y="Livraisons", template=plotly_template, color_discrete_sequence=[t["accent"]])
        fig_cc.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        # Interaction Drill-down (Simulation)
        event = st.plotly_chart(fig_cc, use_container_width=True, on_select="rerun")
        if event and 'selection' in event:
            st.write("Détails du jour sélectionné...")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_cc2:
        # Mini KPIs
        st.markdown(f'<div class="dash-card"><h4>💰 Finance</h4><h3>{kpis.get("rec_total_du",0)/1e6:.1f}M DA</h3><p style="color:#ef4444;">{kpis.get("rec_en_attente",0)} à relancer</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dash-card"><h4>📦 Stocks</h4><h3>{kpis.get("inv_saisies",0)}</h3><p style="color:#10b981;">{kpis.get("inv_produits_uniques",0)} catalogués</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="dash-card"><h4>⏳ Alertes</h4><h3>{kpis.get("peremptions_critiques",0)}</h3><p style="color:#f59e0b;">Périls < 3 mois</p></div>', unsafe_allow_html=True)

elif selected_model == "Analyse Comparative":
    st.subheader("🔄 Comparatif & Benchmarking")
    
    c_sel1, c_sel2 = st.columns(2)
    depot_a = c_sel1.selectbox("Dépôt / Zone A", ["Principal", "Vrac", "Chambre Froide"])
    depot_b = c_sel2.selectbox("Dépôt / Zone B", ["Vrac", "Principal", "Chambre Froide"])
    
    comp1, comp2 = st.columns(2)
    with comp1:
        st.markdown(f'<div class="dash-card"><h3>{depot_a}</h3><h1 style="color:{t["accent"]};">94%</h1><p>Précision inventaire</p></div>', unsafe_allow_html=True)
    with comp2:
        st.markdown(f'<div class="dash-card"><h3>{depot_b}</h3><h1 style="color:{t["accent"]};">88%</h1><p>Précision inventaire</p></div>', unsafe_allow_html=True)
    
    st.info("💡 L'Analyse Comparative permet de détecter les écarts de performance entre les différentes zones de l'entrepôt.")

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
