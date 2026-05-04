# VERSION 4 - FIXED ATTRIBUTE ACCESS
import streamlit as st
import pandas as pd
import os
import unicodedata
from datetime import datetime
from utils_ia import ask_ai, is_ia_enabled

st.set_page_config(page_title="Inventaire Détail", layout="wide")

# --- 1. CONFIGURATION ---
DATA_DIR = "data_inventaire_detail"
MASTER_PATH = os.path.join(DATA_DIR, "master_detail.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie_detail.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# --- 2. FONCTIONS ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_cols_v4(df):
    # Mapping très large pour attraper toutes les variations
    mapping = {
        'produit': 'designation', 'designation': 'designation', 'article': 'designation', 'libelle': 'designation', 'nom': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp', 'date': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone', 'sector': 'zone'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte', 'dispo']
    
    new_cols = []
    found_targets = set()
    
    for col in df.columns:
        norm = normalize_text(col)
        target = None
        for k, v in mapping.items():
            if k in norm and v not in found_targets:
                target = v
                found_targets.add(v)
                break
        
        if not target and any(key in norm for key in stock_keywords) and 'stock_theorique' not in found_targets:
            target = 'stock_theorique'
            found_targets.add(target)
            
        new_cols.append(target if target else norm)
        
    df.columns = new_cols
    return df

@st.cache_data(ttl=60) # Très court pour le debug
def load_master_detail_v4(path, mtime):
    try:
        df = pd.read_excel(path, engine='openpyxl')
        df = clean_cols_v4(df)
        
        # Vérification critique
        required = ['designation', 'lot', 'zone']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return f"❌ Colonnes manquantes dans votre Excel : {', '.join(missing)}. Veuillez renommer vos colonnes (Produit, Lot, Zone)."
            
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
            
        if 'zone' not in df.columns: df['zone'] = 'A'
        df['zone'] = df['zone'].astype(str).str.upper().str.strip()
        
        return df
    except Exception as e:
        return f"❌ Erreur lors de la lecture du fichier : {str(e)}"

# --- 3. INTERFACE ---
st.title("🔍 Inventaire Détail (Zones)")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()

user = st.session_state.current_user
user_zone = user.get('zone', 'Aucune')

# Chargement
df_master = None
if os.path.exists(MASTER_PATH):
    with st.spinner("Vérification du Master..."):
        res = load_master_detail_v4(MASTER_PATH, os.path.getmtime(MASTER_PATH))
        if isinstance(res, str):
            st.error(res)
            st.info("💡 Allez dans l'onglet 'Admin' pour importer un fichier correct.")
        else:
            df_master = res

# Zone Sidebar
if user_zone == "Aucune":
    selected_zone = st.sidebar.selectbox("📍 Choisir Zone de travail :", ["A", "B", "C", "D", "Frigo"])
else:
    selected_zone = user_zone
    st.sidebar.success(f"📍 Zone assignée : **{selected_zone}**")

tabs = st.tabs(["📊 État", "📝 Saisie", "🔍 Analyse", "⚙️ Paramètres"])

with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Articles Total", len(df_master))
        count_z = len(df_master[df_master['zone'] == selected_zone])
        c2.metric(f"Articles Zone {selected_zone}", count_z)
        st.write("### Répartition des articles")
        st.bar_chart(df_master['zone'].value_counts())
    else:
        st.info("En attente de l'importation du Master.")

with tabs[1]:
    if df_master is not None:
        df_z = df_master[df_master['zone'] == selected_zone].copy()
        if df_z.empty:
            st.warning(f"La zone **{selected_zone}** ne contient aucun article dans le Master.")
        else:
            # Utilisation de .get() pour une sécurité absolue
            designations = sorted(df_z['designation'].unique())
            
            sel_prod = st.selectbox("Sélectionner le produit :", [""] + designations)
            if sel_prod:
                df_p = df_z[df_z['designation'] == sel_prod]
                lots = sorted(df_p['lot'].unique())
                sel_lot = st.selectbox("Lot (Master) :", lots)
                
                with st.form("form_saisie_v4", clear_on_submit=True):
                    qte = st.number_input("Quantité trouvée", min_value=0.0, step=1.0)
                    if st.form_submit_button("✅ Valider la saisie"):
                        new_data = pd.DataFrame([{
                            'designation': sel_prod, 'lot': sel_lot, 'qte': qte,
                            'zone': selected_zone, 'agent': user['username'],
                            'heure': datetime.now().strftime("%H:%M")
                        }])
                        h = not os.path.exists(SAISIE_PATH)
                        new_data.to_csv(SAISIE_PATH, mode='a', header=h, index=False, sep=';')
                        st.success(f"Saisie validée pour {sel_prod}")
    else:
        st.info("Veuillez d'abord importer le Master dans l'onglet Paramètres.")

with tabs[2]:
    if user['role'] == "Admin" and os.path.exists(SAISIE_PATH):
        saisie_raw = pd.read_csv(SAISIE_PATH, sep=';')
        st.subheader("📋 Historique des saisies")
        st.dataframe(saisie_raw, use_container_width=True)
    else:
        st.info("Aucune donnée de saisie à analyser.")

with tabs[3]:
    st.subheader("⚙️ Importation des données")
    f_up = st.file_uploader("Fichier Master (Excel)", type=["xlsx", "xls"])
    if f_up:
        if st.button("🚀 Lancer l'importation"):
            with open(MASTER_PATH, "wb") as f:
                f.write(f_up.getbuffer())
            st.cache_data.clear()
            st.success("Master importé avec succès ! Rechargement...")
            st.rerun()
            
    st.divider()
    if st.button("🗑️ Réinitialiser tout l'inventaire", type="primary"):
        if os.path.exists(SAISIE_PATH):
            os.remove(SAISIE_PATH)
            st.success("Toutes les saisies ont été supprimées.")
            st.rerun()
