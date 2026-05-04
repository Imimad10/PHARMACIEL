import streamlit as st
import pandas as pd
import os
import unicodedata
from datetime import datetime
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION ---
DATA_DIR = "data_inventaire_detail"
MASTER_PATH = os.path.join(DATA_DIR, "master_detail.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie_detail.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# --- 2. FONCTIONS ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_cols_v3(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation', 'article': 'designation', 'libelle': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp', 'date': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone', 'sector': 'zone'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte', 'dispo']
    new_cols = []
    for col in df.columns:
        norm = normalize_text(col)
        found = False
        for k, v in mapping.items():
            if k in norm:
                new_cols.append(v); found = True; break
        if not found:
            if any(key in norm for key in stock_keywords):
                new_cols.append('stock_theorique'); found = True
        if not found: new_cols.append(norm)
    df.columns = new_cols
    return df

@st.cache_data(ttl=300)
def load_master_detail_v3(path, mtime):
    try:
        # Utilisation de engine='openpyxl' pour plus de stabilité
        df = pd.read_excel(path, engine='openpyxl')
        df = clean_cols_v3(df)
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
        if 'zone' not in df.columns: df['zone'] = 'A'
        df['zone'] = df['zone'].astype(str).str.upper().str.strip()
        # Validation des colonnes essentielles
        for c in ['designation', 'lot', 'zone']:
            if c not in df.columns: return f"Colonne '{c}' manquante."
        return df
    except Exception as e:
        return f"Erreur Excel : {str(e)}"

# --- 3. UI ---
st.title("🔍 Inventaire Détail (Zones)")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
user_zone = user.get('zone', 'Aucune')

# Chargement différé du Master avec spinner
df_master = None
if os.path.exists(MASTER_PATH):
    with st.spinner("Chargement des données..."):
        res = load_master_detail_v3(MASTER_PATH, os.path.getmtime(MASTER_PATH))
        if isinstance(res, str):
            st.error(res)
        else:
            df_master = res

# Sélection Zone
if user_zone == "Aucune":
    selected_zone = st.sidebar.selectbox("📍 Zone :", ["A", "B", "C", "D", "Frigo"])
else:
    selected_zone = user_zone
    st.sidebar.info(f"📍 Zone assignée : **{selected_zone}**")

tabs = st.tabs(["📊 Dashboard", "📝 Saisie", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Total Articles", len(df_master))
        df_z = df_master[df_master['zone'] == selected_zone]
        c2.metric(f"Zone {selected_zone}", len(df_z))
        st.write("### Répartition par Zone")
        st.bar_chart(df_master['zone'].value_counts())
    else: st.info("Importez un fichier Master dans l'onglet Admin.")

with tabs[1]:
    if df_master is not None:
        df_z = df_master[df_master['zone'] == selected_zone]
        if df_z.empty:
            st.warning(f"Aucun produit trouvé pour la zone {selected_zone}.")
        else:
            prods = sorted(df_z['designation'].unique())
            sel_prod = st.selectbox("Produit :", [""] + prods)
            if sel_prod:
                df_p = df_z[df_z['designation'] == sel_prod]
                lot_m = st.selectbox("Lot Master :", df_p['lot'].unique())
                info = df_p[df_p['lot'] == lot_m].iloc[0]
                
                with st.form("form_saisie_det_v3", clear_on_submit=True):
                    q = st.number_input("Quantité réelle", min_value=0.0, step=1.0)
                    if st.form_submit_button("💾 Valider la saisie"):
                        line = pd.DataFrame([{
                            'designation': sel_prod, 'lot': lot_m, 'qte_saisie': q, 
                            'zone': selected_zone, 'agent': user['username'],
                            'date': datetime.now().strftime("%d/%m/%Y %H:%M")
                        }])
                        exists = os.path.exists(SAISIE_PATH)
                        line.to_csv(SAISIE_PATH, mode='a', header=not exists, index=False, sep=';')
                        st.success("Saisie enregistrée !")
    else: st.info("Master requis.")

with tabs[2]:
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';')
            st.write(f"### Journal des saisies - Zone {selected_zone}")
            st.dataframe(saisie[saisie['zone'] == selected_zone], use_container_width=True)
            
            if st.button("📊 Générer Analyse Complète"):
                # Simplifié pour éviter le blocage
                st.info("Traitement en cours...")
                st.dataframe(saisie.groupby('designation')['qte_saisie'].sum(), use_container_width=True)
        else: st.info("Aucune saisie détectée.")
    else: st.warning("Accès Admin requis pour l'analyse.")

with tabs[3]:
    st.subheader("⚙️ Administration du Module")
    up = st.file_uploader("Importer Master Détail (XLSX)", type="xlsx")
    if up:
        if st.button("🚀 Confirmer l'importation"):
            with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
            st.cache_data.clear()
            st.success("Fichier Master mis à jour avec succès !")
            st.rerun()
            
    st.divider()
    if st.button("🗑️ Vider toutes les saisies", type="secondary"):
        if os.path.exists(SAISIE_PATH):
            os.remove(SAISIE_PATH)
            st.success("Saisies effacées.")
            st.rerun()
