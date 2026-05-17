import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION ---
SALES_WORKSHEET = "Analyse_Ventes_Perf"
SALES_FALLBACK = "data/db_ventes_performance.csv"

# --- 2. CSS & STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
    
    .perf-card {
        background: rgba(124, 58, 237, 0.04);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .stat-val { font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 0px; }
    .stat-label { font-size: 0.8rem; color: #475569; text-transform: uppercase; letter-spacing: 1px; }
    
    .ia-report {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(30, 41, 59, 0.05) 100%);
        border-left: 5px solid #7c3aed;
        padding: 25px;
        border-radius: 12px;
        color: #1e293b;
        font-family: 'Sora', sans-serif;
        border: 1px solid rgba(124, 58, 237, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIQUE TECHNIQUE ---

def clean_sales_cols(df):
    mapping = {
        'designation': ['designation', 'produit', 'article', 'libelle'],
        'quantite': ['quantite', 'qte', 'volume', 'nombre'],
        'prix_vente': ['prix vente', 'prix_v', 'ca', 'montant', 'total ht'],
        'marge': ['marge', 'profit', 'rentabilite', 'benefice', 'gain'],
        'date': ['date', 'jour', 'facturé le'],
        'heure': ['heure', 'time', 'moment'],
        'colis': ['colis', 'nb colis', 'colissage', 'paquets']
    }
    new_cols = {}
    for target, alts in mapping.items():
        for col in df.columns:
            if any(alt in str(col).lower() for alt in alts):
                new_cols[col] = target
                break
    return df.rename(columns=new_cols)

def process_time_features(df):
    if 'date' in df.columns:
        df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
        df['jour_nom'] = df['date_dt'].dt.day_name()
        df['mois'] = df['date_dt'].dt.month_name()
        df['mois_annee'] = df['date_dt'].dt.strftime('%Y-%m')
    if 'heure' in df.columns:
        df['heure_int'] = pd.to_datetime(df['heure'], format='%H:%M:%S', errors='coerce').dt.hour
        if df['heure_int'].isna().all():
            df['heure_int'] = pd.to_datetime(df['heure'], errors='coerce').dt.hour
    elif 'date_dt' in df.columns:
        df['heure_int'] = df['date_dt'].dt.hour
        
    for col in ['prix_vente', 'marge', 'colis', 'quantite']:
        if col in df.columns:
            if df[col].dtype == 'object':
                try: df[col] = df[col].astype(str).str.replace(' ', '', regex=False).str.replace(',', '.', regex=False)
                except: pass
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

# --- 4. UI ---
st.title("💰 Performance & Rentabilité Ventes")
st.write("Optimisez vos flux logistiques, détectez vos pics de charge et maximisez votre rentabilité.")

# Persistence
if "df_ventes_perf" not in st.session_state:
    df_db = load_gs_data(SALES_WORKSHEET, SALES_FALLBACK)
    if not df_db.empty: st.session_state.df_ventes_perf = process_time_features(df_db)

tabs = st.tabs(["🚀 Dashboard", "📅 Analyse Flux", "📥 Import"])

with tabs[2]:
    st.markdown('<div class="perf-card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Fichier Ventes (Excel/CSV)", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_proc = process_time_features(clean_sales_cols(df_raw))
            st.session_state.df_ventes_perf = df_proc
            st.success(f"✅ {len(df_proc)} lignes analysées.")
            if st.button("💾 Sauvegarder dans le Cloud"):
                save_gs_data(df_proc, SALES_WORKSHEET, SALES_FALLBACK, force_cloud=True)
                st.toast("Saved!")
        except Exception as e: st.error(f"Erreur : {e}")
    st.markdown('</div>', unsafe_allow_html=True)

with tabs[0]:
    if "df_ventes_perf" in st.session_state:
        df = st.session_state.df_ventes_perf
        c1, c2, c3, c4 = st.columns(4)
        
        ca = pd.to_numeric(df['prix_vente'], errors='coerce').sum() if 'prix_vente' in df.columns else 0
        marge = pd.to_numeric(df['marge'], errors='coerce').sum() if 'marge' in df.columns else 0
        lignes = len(df)
        colis = pd.to_numeric(df['colis'], errors='coerce').sum() if 'colis' in df.columns else 0
        
        with c1: st.markdown(f'<div class="perf-card stat-box"><div class="stat-label">Chiffre d\'Affaires</div><div class="stat-val">{ca:,.0f} DA</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="perf-card stat-box"><div class="stat-label">Rentabilité</div><div class="stat-val">{marge:,.0f} DA</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="perf-card stat-box"><div class="stat-label">Volume Lignes</div><div class="stat-val">{lignes}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="perf-card stat-box"><div class="stat-label">Expéditions (Colis)</div><div class="stat-val">{int(colis)}</div></div>', unsafe_allow_html=True)

        if 'mois_annee' in df.columns and 'prix_vente' in df.columns:
            st.markdown("#### 📅 Évolution Mensuelle de la Performance")
            df_monthly = df.groupby('mois_annee')[['prix_vente', 'marge']].sum().reset_index().dropna(subset=['mois_annee'])
            df_monthly = df_monthly.sort_values('mois_annee')
            
            if not df_monthly.empty:
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=df_monthly['mois_annee'], y=df_monthly['prix_vente'], mode='lines+markers', name="Chiffre d'Affaires (DA)", line=dict(color='#3b82f6', width=3, shape='spline')))
                if 'marge' in df.columns:
                    fig_trend.add_trace(go.Bar(x=df_monthly['mois_annee'], y=df_monthly['marge'], name="Rentabilité (Marge DA)", marker_color='#10b981', opacity=0.8))
                
                fig_trend.update_layout(template="plotly_dark", hovermode='x unified', margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_trend, use_container_width=True)

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown("#### 🏆 Top Produits Rentables")
            if 'designation' in df.columns and 'marge' in df.columns:
                top_p = df.groupby('designation')['marge'].sum().sort_values(ascending=False).head(10).reset_index()
                st.plotly_chart(px.bar(top_p, x='marge', y='designation', orientation='h', color='marge', color_continuous_scale='Greens', template="plotly_dark"), use_container_width=True)
        with col_v2:
            st.markdown("#### 📦 Taille des Envois")
            if 'colis' in df.columns:
                st.plotly_chart(px.histogram(df, x='colis', color_discrete_sequence=['#7c3aed'], template="plotly_dark"), use_container_width=True)
    else: st.warning("Importez des données.")

with tabs[1]:
    if "df_ventes_perf" in st.session_state:
        df = st.session_state.df_ventes_perf
        if 'heure_int' in df.columns:
            st.markdown("#### 🔥 Pics de Charge Horaire")
            h_load = df.groupby('heure_int').size().reset_index(name='nb')
            fig = px.line(h_load, x='heure_int', y='nb', markers=True, template="plotly_dark")
            fig.update_traces(line_color='#f43f5e', fill='tozeroy')
            st.plotly_chart(fig, use_container_width=True)
        
        if is_ia_enabled():
            st.markdown("#### 🧠 Audit Prédictif IA")
            if st.button("Lancer l'Analyse IA", use_container_width=True, type="primary"):
                h_sum = df.groupby('heure_int').size().to_dict()
                prompt = f"Analyse ces flux horaires de préparation : {h_sum}. Suggère une organisation d'équipe pour maximiser la rentabilité logistique."
                with st.spinner("Audit en cours..."):
                    res = ask_ai(prompt)
                    st.markdown(f'<div class="ia-report">{res}</div>', unsafe_allow_html=True)
