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

# --- 2. LOGIQUE TECHNIQUE ---

def clean_sales_cols(df):
    """Mappe intelligemment les colonnes du fichier de ventes."""
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
    found = []
    for target, alts in mapping.items():
        for col in df.columns:
            if any(alt in str(col).lower() for alt in alts):
                new_cols[col] = target
                found.append(target)
                break
    return df.rename(columns=new_cols), found

def process_time_features(df):
    """Extrait les dimensions temporelles."""
    if 'date' in df.columns:
        df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
        df['jour_nom'] = df['date_dt'].dt.day_name()
        df['mois'] = df['date_dt'].dt.month_name()
        
    if 'heure' in df.columns:
        # Tenter de convertir en heure si c'est du texte ou datetime
        df['heure_int'] = pd.to_datetime(df['heure'], format='%H:%M:%S', errors='coerce').dt.hour
        if df['heure_int'].isna().all():
            df['heure_int'] = pd.to_datetime(df['heure'], errors='coerce').dt.hour
    elif 'date_dt' in df.columns:
        df['heure_int'] = df['date_dt'].dt.hour
        
    return df

# --- 3. UI ---

st.set_page_config(page_title="Performance Ventes", layout="wide")
st.title("💰 Analyse de Performance & Rentabilité Ventes")
st.info("Détectez vos pics d'activité, vos périodes rentables et optimisez votre colissage.")

tabs = st.tabs(["🚀 Dashboard Performance", "📅 Analyse Temporelle", "📥 Import & Données"])

with tabs[2]:
    st.subheader("Chargement des Données de Ventes")
    uploaded_file = st.file_uploader("Importez votre export de ventes (Excel/CSV)", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file)
            else:
                df_raw = pd.read_excel(uploaded_file)
            
            df_clean, found = clean_sales_cols(df_raw)
            df_proc = process_time_features(df_clean)
            
            st.success(f"✅ {len(df_proc)} lignes de ventes analysées.")
            st.session_state.df_ventes_perf = df_proc
            
            with st.expander("Aperçu technique"):
                st.dataframe(df_proc.head(10), use_container_width=True)
                
            if st.button("💾 Synchroniser avec le Cloud DarPharm", use_container_width=True):
                save_gs_data(df_proc, SALES_WORKSHEET, SALES_FALLBACK, force_cloud=True)
                st.success("Données sauvegardées !")
        except Exception as e:
            st.error(f"Erreur : {e}")

# Persistence
if "df_ventes_perf" not in st.session_state:
    df_db = load_gs_data(SALES_WORKSHEET, SALES_FALLBACK)
    if not df_db.empty:
        st.session_state.df_ventes_perf = process_time_features(df_db)

with tabs[0]:
    if "df_ventes_perf" in st.session_state:
        df = st.session_state.df_ventes_perf
        
        # KPIs de haut niveau
        c1, c2, c3, c4 = st.columns(4)
        
        total_ca = df['prix_vente'].sum() if 'prix_vente' in df.columns else 0
        total_marge = df['marge'].sum() if 'marge' in df.columns else 0
        total_lignes = len(df)
        total_colis = df['colis'].sum() if 'colis' in df.columns else 0
        
        c1.metric("Chiffre d'Affaires", f"{total_ca:,.2f} DA")
        c2.metric("Rentabilité Globale", f"{total_marge:,.2f} DA", delta="{:.1f}%".format(total_marge/total_ca*100) if total_ca > 0 else None)
        c3.metric("Volume de Travail", f"{total_lignes} Lignes")
        c4.metric("Colissage Total", f"{int(total_colis)} Colis")
        
        st.divider()
        
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown("#### 🏆 Top Produits par Rentabilité")
            if 'designation' in df.columns and 'marge' in df.columns:
                top_p = df.groupby('designation')['marge'].sum().sort_values(ascending=False).head(10).reset_index()
                fig_top = px.bar(top_p, x='marge', y='designation', orientation='h', 
                                color='marge', color_continuous_scale='Greens', template="plotly_dark")
                st.plotly_chart(fig_top, use_container_width=True)
        
        with col_v2:
            st.markdown("#### 📦 Analyse du Colissage / Poids")
            if 'colis' in df.columns:
                fig_colis = px.histogram(df, x='colis', title="Distribution de la taille des envois", 
                                       color_discrete_sequence=['#7c3aed'], template="plotly_dark")
                st.plotly_chart(fig_colis, use_container_width=True)

with tabs[1]:
    if "df_ventes_perf" in st.session_state:
        df = st.session_state.df_ventes_perf
        
        st.subheader("🕰️ Analyse des Flux & Pics d'Activité")
        
        if 'heure_int' in df.columns:
            st.markdown("#### 🔥 Heures de Pic de Travail (Workload)")
            hourly_load = df.groupby('heure_int').size().reset_index(name='nb_lignes')
            fig_hour = px.line(hourly_load, x='heure_int', y='nb_lignes', markers=True,
                              title="Intensité de préparation par heure", template="plotly_dark")
            fig_hour.update_traces(line_color='#f43f5e', fill='tozeroy')
            st.plotly_chart(fig_hour, use_container_width=True)
            
            peak_hour = hourly_load.loc[hourly_load['nb_lignes'].idxmax(), 'heure_int']
            st.warning(f"💡 **Insight** : Votre pic d'activité maximal se situe à **{int(peak_hour)}h**. Envisagez un renfort équipe à ce moment.")
            
        st.divider()
        
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            if 'jour_nom' in df.columns:
                st.markdown("#### 📅 Rentabilité par Jour de la Semaine")
                order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_perf = df.groupby('jour_nom')['marge'].sum().reindex(order).reset_index()
                fig_day = px.bar(day_perf, x='jour_nom', y='marge', color='marge', 
                                color_continuous_scale='Viridis', template="plotly_dark")
                st.plotly_chart(fig_day, use_container_width=True)
                
        with col_t2:
            if is_ia_enabled():
                st.markdown("#### 🧠 Prévisions IA")
                if st.button("Lancer l'Analyse Prédictive", use_container_width=True):
                    # Résumé pour l'IA
                    h_sum = df.groupby('heure_int').size().to_dict()
                    p_sum = df.groupby('mois')['prix_vente'].sum().to_dict() if 'mois' in df.columns else {}
                    
                    prompt = f"""En tant qu'analyste data DarPharm, analyse ces flux :
                    Heures de pic (Nb lignes) : {h_sum}
                    Saisonnalité : {p_sum}
                    Identifie les goulots d'étranglement logistiques et suggère une réorganisation du planning pour maximiser la rentabilité."""
                    
                    st.write(ask_ai(prompt))
    else:
        st.warning("Aucune donnée disponible.")
