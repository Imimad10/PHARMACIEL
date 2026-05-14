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
    st.markdown("### 🤖 Briefing Exécutif IA")
    if st.button("✨ Générer la synthèse intelligente du jour", use_container_width=True, type="primary"):
        with st.spinner("L'IA analyse vos performances en temps réel..."):
            prompt = f"Tu es le Directeur des Opérations Virtuel de la pharmacie. Voici les indicateurs actuels : {kpis}. Rédige un briefing très court (3 paragraphes max) et dynamique pour l'équipe dirigeante. Mets en évidence le montant à recouvrer, les risques de péremption, et l'avancement de l'inventaire. Propose 2 actions urgentes à faire aujourd'hui. Utilise des emojis."
            st.info(ask_ai(prompt))
    st.divider()

# ═══════════════════════════════════════════
# 2. ROUTAGE DES MODÈLES DE VUE
# ═══════════════════════════════════════════

if selected_model == "Standard (Narratif)":
    # 2.1 KPIs PRINCIPAUX
    st.subheader("📊 Indicateurs Clés")
    
    def kpi_card(label, value, delta, icon, color=t["accent"]):
        st.markdown(f"""
            <div class="dash-card" style="border-left: 5px solid {color};">
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                    <div style="font-size: 2.2rem;">{icon}</div>
                    <div>
                        <div style="font-size: 0.8rem; opacity: 0.7; font-weight: 700; text-transform: uppercase;">{label}</div>
                        <div style="font-size: 1.6rem; font-weight: 900;">{value}</div>
                    </div>
                </div>
                <div style="font-size: 0.85rem; opacity: 0.6; font-weight: 600;">{delta}</div>
            </div>
        """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total à Recouvrer", f"{kpis.get('rec_total_du',0):,.0f} DA", f"↑ {kpis.get('rec_en_attente',0)} en attente", "💰", "#f59e0b")
    with c2: kpi_card("Dossiers Archivés", f"{kpis.get('arch_count', 0)}", f"↑ {kpis.get('arch_recouvre',0):,.0f} DA récup.", "✅", "#10b981")
    with c3: kpi_card("Saisies Inventaire", f"{kpis.get('inv_saisies', 0)}", f"↑ {kpis.get('inv_produits_uniques',0)} produits", "📝", t["accent"])
    with c4: kpi_card("Inventaire Triple", f"{kpis.get('inv_triple_count', 0)}", "Lignes modifiées", "📋", "#8b5cf6")

    st.divider()
    
    # Graphiques
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### 💰 Recouvrement par Statut")
        if kpis.get('rec_by_status'):
            df_status = pd.DataFrame(list(kpis['rec_by_status'].items()), columns=['Statut', 'Nb'])
            fig = px.pie(df_status, values='Nb', names='Statut', hole=0.5, template=plotly_template)
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.markdown("#### 🚚 Reste à Payer par Livreur")
        if kpis.get('rec_by_livreur'):
            df_liv = pd.DataFrame(list(kpis['rec_by_livreur'].items()), columns=['Livreur', 'Montant'])
            fig2 = px.bar(df_liv.sort_values('Montant'), x='Montant', y='Livreur', orientation='h', template=plotly_template)
            st.plotly_chart(fig2, use_container_width=True)

elif selected_model == "Centre de Commandement":
    st.subheader("🚀 Command Center - Vision Holistique")
    
    # Barre de progression globale (simulée)
    st.markdown("""
        <div style="background: rgba(255,255,255,0.05); border-radius: 10px; height: 10px; margin-bottom: 30px;">
            <div style="background: linear-gradient(90deg, #5b6cf9, #10b981); width: 85%; height: 100%; border-radius: 10px;"></div>
        </div>
    """, unsafe_allow_html=True)
    
    col_cc1, col_cc2 = st.columns([2, 1])
    
    with col_cc1:
        st.markdown('<div class="dash-card" style="height:600px;">', unsafe_allow_html=True)
        st.write("📈 **Flux d'Activité Logistique**")
        df_perf = pd.DataFrame({"Jour": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"], "Livraisons": [120, 150, 140, 180, 160, 110]})
        fig_cc = px.area(df_perf, x="Jour", y="Livraisons", template=plotly_template, color_discrete_sequence=[t["accent"]])
        fig_cc.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_cc, use_container_width=True)
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
