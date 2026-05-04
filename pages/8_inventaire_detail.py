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

# --- 2. UTILS ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_cols_v2(df):
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

@st.cache_data(ttl=600) # Réduit le TTL pour plus de réactivité
def load_master_detail_v2(path, mtime):
    try:
        df = pd.read_excel(path)
        df = clean_cols_v2(df)
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
        if 'zone' not in df.columns: df['zone'] = 'A'
        df['zone'] = df['zone'].astype(str).str.upper().str.strip()
        return df
    except: return None

# --- 3. LOGIQUE ---
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
df_master = None
if os.path.exists(MASTER_PATH):
    df_master = load_master_detail_v2(MASTER_PATH, os.path.getmtime(MASTER_PATH))
    if df_master is not None:
        missing = [c for c in ['designation', 'lot', 'zone'] if c not in df_master.columns]
        if missing:
            st.error(f"Colonnes manquantes : {missing}")
            df_master = None

st.title("🔍 Inventaire Détail (Zones)")

# Zone logic
user_zone = user.get('zone', 'Aucune')
selected_zone = st.sidebar.selectbox("📍 Zone :", ["A", "B", "C", "D", "Frigo"], index=["A", "B", "C", "D", "Frigo"].index(user_zone) if user_zone in ["A", "B", "C", "D", "Frigo"] else 0)
if user_zone != "Aucune":
    st.sidebar.info(f"Assigné à : **{user_zone}**")
    selected_zone = user_zone

tabs = st.tabs(["📊 Dashboard", "📝 Saisie", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Master", len(df_master))
        df_z = df_master[df_master['zone'] == selected_zone]
        c2.metric(f"Zone {selected_zone}", len(df_z))
        st.bar_chart(df_master['zone'].value_counts())
    else: st.warning("Master non chargé.")

with tabs[1]:
    if df_master is not None:
        df_z = df_master[df_master['zone'] == selected_zone]
        if df_z.empty:
            st.error(f"Zone {selected_zone} vide.")
        else:
            prods = sorted(df_z['designation'].unique())
            sel = st.selectbox("Produit :", [""] + prods)
            if sel:
                df_p = df_z[df_z['designation'] == sel]
                lots = df_p['lot'].unique()
                lot_m = st.selectbox("Lot :", lots)
                info = df_p[df_p['lot'] == lot_m].iloc[0]
                
                with st.form("form_det_v2", clear_on_submit=True):
                    q = st.number_input("Quantité", min_value=0.0, step=1.0)
                    if st.form_submit_button("💾 Sauver"):
                        line = pd.DataFrame([{
                            'designation': sel, 'lot': lot_m, 'qte_saisie': q, 
                            'zone': selected_zone, 'agent': user['username'],
                            'timestamp': datetime.now().strftime("%H:%M")
                        }])
                        exists = os.path.exists(SAISIE_PATH)
                        line.to_csv(SAISIE_PATH, mode='a', header=not exists, index=False, sep=';')
                        st.success("Enregistré")
    else: st.info("Master requis.")

with tabs[2]:
    if user['role'] == "Admin" and os.path.exists(SAISIE_PATH) and df_master is not None:
        saisie = pd.read_csv(SAISIE_PATH, sep=';')
        st.write("### Analyse par Zone")
        z_ana = st.selectbox("Filtrer Zone :", ["Toutes"] + sorted(df_master['zone'].unique()))
        
        df_m_f = df_master if z_ana == "Toutes" else df_master[df_master['zone'] == z_ana]
        df_s_f = saisie if z_ana == "Toutes" else saisie[saisie['zone'] == z_ana]
        
        # Merge global
        m_g = df_m_f.groupby(['designation', 'zone'])['stock_theorique' if 'stock_theorique' in df_m_f.columns else df_m_f.columns[0]].count().reset_index() # Fallback safe
        # On va simplifier pour éviter les erreurs de colonnes dynamiques
        st.dataframe(df_s_f, use_container_width=True)
    else: st.info("Données insuffisantes ou accès restreint.")

with tabs[3]:
    st.subheader("⚙️ Admin")
    up = st.file_uploader("Master (XLSX)", type="xlsx")
    if up:
        with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
        st.cache_data.clear()
        st.success("Master OK")
        st.rerun()
    if st.button("🗑️ Vider Saisies"):
        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH); st.rerun()
