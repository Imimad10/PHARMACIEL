# --- 1. CSS & STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
    
    .reclam-card {
        background: rgba(124, 58, 237, 0.04);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .ia-report {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(30, 41, 59, 0.05) 100%);
        border-left: 5px solid #7c3aed;
        padding: 30px;
        border-radius: 12px;
        color: #1e293b;
        line-height: 1.6;
        font-family: 'Sora', sans-serif;
        border: 1px solid rgba(124, 58, 237, 0.1);
    }
    
    .stat-box { text-align: center; }
    .stat-val { font-size: 2.2rem; font-weight: 800; color: #1e293b; margin-bottom: 0px; }
    .stat-label { font-size: 0.8rem; color: #475569; text-transform: uppercase; letter-spacing: 1px; }
    
    .severity-high { color: #ef4444; }
    .severity-med { color: #f59e0b; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE TECHNIQUE ---
# ... (Gardons les fonctions clean_reclam_cols et categorize_motif identiques) ...

def clean_reclam_cols(df):
    mapping = {
        'reference': ['ref', 'bon', 'commande', 'document'],
        'client': ['client', 'pharmacie', 'destinataire'],
        'commercial': ['commercial', 'cree par', 'créé par', 'vendeur', 'user'],
        'produit': ['produit', 'designation', 'article'],
        'motif': ['motif', 'cause', 'raison', 'type'],
        'date_creation': ['date de creation', 'date creation', 'cree le', 'date_crea'],
        'date_facture': ['date de facture', 'date facture', 'date_fac']
    }
    new_cols = {}
    found = []
    for target, alts in mapping.items():
        for col in df.columns:
            if any(alt in str(col).lower() for alt in alts):
                new_cols[col] = target
                found.append(target)
                break
    return df.rename(columns=new_cols), found

def categorize_motif(motif_str):
    m = str(motif_str).upper()
    if any(k in m for k in ["COMMERCIAL", "SAISIE", "FORCE", "REVENU", "EXCUSE"]): return "Erreur Commerciale"
    if any(k in m for k in ["PHARMACIEN", "DOSAGE", "FORME", "DCI", "MARQUE"]): return "Erreur Pharmacien"
    if any(k in m for k in ["DEPOT", "PREPARATION", "BOITE", "PLUS", "MOIN", "QUANTITE"]): return "Erreur Dépôt"
    if any(k in m for k in ["PNC", "CONFORME", "VIGNETTE", "ABIMEE", "CASSEE", "DETERIORE"]): return "PNC (Non Conforme)"
    if any(k in m for k in ["SUPERVISEUR", "MODIFICATION", "REFAIRE", "BON DEJA"]): return "Erreur Superviseur"
    return "Autre / Non Classé"

# --- 3. UI ---
st.title("🎯 Audit Stratégique des Réclamations")
st.write("Identifiez les points de friction, recadrez la performance commerciale et optimisez la qualité opérationnelle.")

# Chargement permanent
if "df_reclam_analysed" not in st.session_state:
    df_db = load_gs_data(RECLAM_WORKSHEET, RECLAM_FALLBACK)
    if not df_db.empty:
        st.session_state.df_reclam_analysed = df_db

tabs = st.tabs(["📊 Tableau de Bord", "📥 Import de Données", "🧠 Diagnostic IA Expert"])

with tabs[1]:
    st.markdown('<div class="reclam-card">', unsafe_allow_html=True)
    st.subheader("📥 Source de Données")
    uploaded_file = st.file_uploader("Glissez votre fichier de réclamations (Excel/CSV)", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_clean, found = clean_reclam_cols(df_raw)
            if 'motif' in df_clean.columns: df_clean['categorie_motif'] = df_clean['motif'].apply(categorize_motif)
            st.session_state.df_reclam_analysed = df_clean
            st.success("✅ Données importées et catégorisées !")
            if st.button("💾 Synchroniser avec le Cloud"):
                save_gs_data(df_clean, RECLAM_WORKSHEET, RECLAM_FALLBACK, force_cloud=True)
                st.toast("Cloud Synced!")
        except Exception as e: st.error(f"Erreur : {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[0]:
    if "df_reclam_analysed" in st.session_state:
        df = st.session_state.df_reclam_analysed
        
        # Filtres
        st.sidebar.subheader("🎯 Pilotage")
        comm_list = ["Tous"] + sorted(df['commercial'].unique().tolist()) if 'commercial' in df.columns else ["Tous"]
        selected_comm = st.sidebar.selectbox("Commercial :", comm_list)
        df_p = df[df['commercial'] == selected_comm] if selected_comm != "Tous" else df
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Total Retours</div><div class="stat-val">{len(df_p)}</div></div>', unsafe_allow_html=True)
        with c2: 
            err_c = len(df_p[df_p['categorie_motif'] == "Erreur Commerciale"])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Risque Comm</div><div class="stat-val severity-high">{err_c}</div></div>', unsafe_allow_html=True)
        with c3:
            pnc = len(df_p[df_p['categorie_motif'] == "PNC (Non Conforme)"])
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">Qualité (PNC)</div><div class="stat-val severity-med">{pnc}</div></div>', unsafe_allow_html=True)
        with c4:
            tx = (err_c / len(df_p) * 100) if len(df_p) > 0 else 0
            st.markdown(f'<div class="reclam-card stat-box"><div class="stat-label">% Erreur Saisie</div><div class="stat-val">{tx:.1f}%</div></div>', unsafe_allow_html=True)

        col_g1, col_g2 = st.columns([1, 1])
        
        with col_g1:
            st.markdown("#### 🍩 Hiérarchie des Motifs")
            fig_sun = px.sunburst(df_p, path=['categorie_motif', 'motif'], 
                                 color_discrete_sequence=px.colors.qualitative.Pastel,
                                 template="plotly_dark")
            st.plotly_chart(fig_sun, use_container_width=True)
            
        with col_g2:
            st.markdown("#### 🏆 Top Responsables")
            comm_stats = df_p['commercial'].value_counts().reset_index()
            comm_stats.columns = ['Commercial', 'Nb']
            fig_bar = px.bar(comm_stats.head(8), x='Nb', y='Commercial', orientation='h',
                            color='Nb', color_continuous_scale='Reds', template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.markdown("#### 🕵️ Matrice des Responsabilités (Commercial vs Catégorie)")
        if 'commercial' in df_p.columns and 'categorie_motif' in df_p.columns:
            pivot = df_p.groupby(['commercial', 'categorie_motif']).size().unstack(fill_value=0)
            # Heatmap pour plus de "WOW"
            fig_heat = px.imshow(pivot, text_auto=True, color_continuous_scale='YlOrRd', template="plotly_dark")
            st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.warning("Aucune donnée disponible.")

with tabs[2]:
    if is_ia_enabled() and "df_reclam_analysed" in st.session_state:
        st.subheader("🧠 Intelligence Artificielle - Root Cause Analysis")
        if st.button("🚀 LANCER L'AUDIT DE PERFORMANCE", use_container_width=True, type="primary"):
            df = st.session_state.df_reclam_analysed
            summary = df.groupby(['commercial', 'categorie_motif']).size().reset_index(name='count').to_dict('records')
            
            prompt = f"Tu es un expert en audit logistique. Analyse ces réclamations : {summary}. Identifie les acteurs critiques et propose un plan d'action immédiat. Sois bref et percutant."
            
            with st.spinner("L'IA scanne les comportements..."):
                report = ask_ai(prompt)
                st.markdown(f'<div class="ia-report">{report}</div>', unsafe_allow_html=True)
                st.balloons()
    else:
        st.info("Importez des données pour activer le diagnostic IA.")
