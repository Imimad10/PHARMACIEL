import streamlit as st
import pandas as pd
import os
import unicodedata
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION & CHEMINS ---
if "DATA_DIR_DET" not in st.session_state:
    st.session_state.DATA_DIR_DET = "data_inventaire_detail"
    st.session_state.MASTER_PATH_DET = os.path.join(st.session_state.DATA_DIR_DET, "master_detail.xlsx")
    st.session_state.SAISIE_PATH_DET = os.path.join(st.session_state.DATA_DIR_DET, "saisie_detail.csv")

os.makedirs(st.session_state.DATA_DIR_DET, exist_ok=True)

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_columns_detail(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte']
    new_cols = []
    for col in df.columns:
        norm = normalize_text(col)
        matched = False
        for k, v in mapping.items():
            if k in norm:
                new_cols.append(v)
                matched = True
                break
        if not matched and any(key in norm for key in stock_keywords):
            new_cols.append('stock_theorique')
            matched = True
        if not matched: new_cols.append(norm)
    df.columns = new_cols
    return df

# --- 3. CHARGEMENT DES DONNÉES ---
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

user = st.session_state.current_user

@st.cache_data(ttl=3600)
def load_master_detail(file_path, mtime):
    try:
        df = pd.read_excel(file_path)
        df = clean_columns_detail(df)
        if 'ddp' in df.columns:
            dates = pd.to_datetime(df['ddp'], errors='coerce')
            mask = dates.notna()
            df['ddp'] = df['ddp'].astype(str)
            df.loc[mask, 'ddp'] = dates[mask].dt.strftime('%m/%Y')
        if 'zone' not in df.columns:
            df['zone'] = "A" # Zone par défaut si absente
        df['zone'] = df['zone'].astype(str).str.upper().str.strip()
        return df
    except Exception as e:
        st.error(f"Erreur chargement Master Détail : {e}")
        return None

df_master = None
if os.path.exists(st.session_state.MASTER_PATH_DET):
    mtime = os.path.getmtime(st.session_state.MASTER_PATH_DET)
    df_master = load_master_detail(st.session_state.MASTER_PATH_DET, mtime)

st.title("🔍 Inventaire Détail (Par Zones)")

# Gestion de la Zone Utilisateur
user_assigned_zone = user.get('zone', 'Aucune')
if user_assigned_zone == "Aucune":
    selected_zone = st.sidebar.selectbox("📍 Sélectionner votre Zone :", ["A", "B", "C", "D", "Frigo"])
else:
    selected_zone = user_assigned_zone
    st.sidebar.info(f"📍 Zone attribuée : **{selected_zone}**")

tabs = st.tabs(["📊 Dashboard", "📝 Saisie Zone", "🔍 Confrontation", "⚙️ Admin"])

# --- DASHBOARD ---
with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Total Master", len(df_master))
        zone_count = len(df_master[df_master['zone'] == selected_zone])
        c2.metric(f"Articles Zone {selected_zone}", zone_count)
        
        st.write(f"### Répartition par Zone")
        st.bar_chart(df_master['zone'].value_counts())
    else:
        st.warning("Master manquant.")

# --- SAISIE ---
with tabs[1]:
    if df_master is not None:
        st.subheader(f"📝 Saisie - Zone {selected_zone}")
        # Filtrer le master par zone
        df_zone = df_master[df_master['zone'] == selected_zone]
        
        if df_zone.empty:
            st.error(f"Aucun produit trouvé dans le Master pour la Zone {selected_zone}.")
        else:
            mode = st.radio("Méthode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True)
            produits = sorted([str(p) for p in df_zone['designation'].unique() if pd.notna(p)])
            prod_sel = st.selectbox("🔍 Choisir Produit (Zone {}):".format(selected_zone), [""] + produits)
            
            if prod_sel:
                df_p = df_zone[df_zone['designation'] == prod_sel]
                lot_orig = st.selectbox("Lot Master :", df_p['lot'].unique())
                info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

                with st.form("form_saisie_detail", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    ddp_m = str(info_m.get('ddp', ''))
                    ppa_m = float(info_m.get('ppa', 0)) if 'ppa' in info_m else 0.0
                    
                    if mode == "🚀 Rapide":
                        qte = c1.number_input("Quantité", min_value=0.0, step=1.0)
                        lot_f, ddp_f, ppa_f = lot_orig, ddp_m, ppa_m
                    else:
                        lot_f = c1.text_input("Lot Réel", value=str(lot_orig))
                        qte = c2.number_input("Quantité", min_value=0.0, step=1.0)
                        ddp_f = c1.text_input("DDP (MM/AAAA)", value=ddp_m)
                        ppa_f = c2.number_input("PPA Saisi", value=ppa_m)

                    if st.form_submit_button("💾 Enregistrer"):
                        new_line = pd.DataFrame([{
                            'designation': prod_sel, 'lot_master': str(lot_orig),
                            'lot': str(lot_f), 'qte_saisie': qte, 'ddp_saisi': ddp_f,
                            'ppa_saisi': ppa_f, 'zone': selected_zone, 'agent': user['username']
                        }])
                        if os.path.exists(st.session_state.SAISIE_PATH_DET):
                            old = pd.read_csv(st.session_state.SAISIE_PATH_DET, sep=';')
                            new_line = pd.concat([old, new_line], ignore_index=True)
                        new_line.to_csv(st.session_state.SAISIE_PATH_DET, index=False, sep=';')
                        st.success(f"Validé : {prod_sel}")
    else: st.info("Master requis.")

# --- CONFRONTATION ---
with tabs[2]:
    st.subheader("🔍 Analyse des écarts par Zone")
    if user['role'] == "Admin":
        if os.path.exists(st.session_state.SAISIE_PATH_DET) and df_master is not None:
            try:
                saisie = pd.read_csv(st.session_state.SAISIE_PATH_DET, sep=';')
                
                # Choix de la zone à analyser
                zone_to_analyze = st.selectbox("Zone à analyser :", ["Toutes"] + sorted(df_master['zone'].unique().tolist()))
                
                if zone_to_analyze != "Toutes":
                    df_m_f = df_master[df_master['zone'] == zone_to_analyze]
                    df_s_f = saisie[saisie['zone'] == zone_to_analyze]
                else:
                    df_m_f = df_master
                    df_s_f = saisie

                # Logique de fusion (même que inventaire standard)
                def robust_num(s):
                    if pd.isna(s): return 0.0
                    if isinstance(s, str): s = s.replace('\xa0', '').replace(' ', '').replace(',', '.')
                    return pd.to_numeric(s, errors='coerce')

                df_s_f['qte_saisie'] = df_s_f['qte_saisie'].apply(robust_num).fillna(0)
                # Trouver la colonne de stock
                q_col = None
                for c in df_m_f.columns:
                    if any(k in c.lower() for k in ['quantit', 'stock', 'qte']): q_col = c; break
                
                if q_col:
                    df_m_f[q_col] = df_m_f[q_col].apply(robust_num).fillna(0)
                    
                    # Merge simplifié pour l'exemple (Global)
                    m_g = df_m_f.groupby(['designation', 'zone'])[q_col].sum().reset_index()
                    s_g = df_s_f.groupby(['designation', 'zone'])['qte_saisie'].sum().reset_index()
                    
                    comp = pd.merge(m_g, s_g, on=['designation', 'zone'], how='outer').fillna(0)
                    comp['écart'] = comp['qte_saisie'] - comp[q_col]
                    
                    st.dataframe(comp, use_container_width=True)
                    
                    # Export
                    import io
                    buf = io.BytesIO()
                    comp.to_excel(buf, index=False)
                    st.download_button("📥 Export Zone", buf.getvalue(), f"Inventaire_Zone_{zone_to_analyze}.xlsx")
            except Exception as e: st.error(f"Erreur : {e}")
    else: st.warning("Admin uniquement.")

# --- ADMIN ---
with tabs[3]:
    st.subheader("⚙️ Configuration Détail")
    up = st.file_uploader("Importer Master Détail (Zone requise)", type="xlsx")
    if up:
        with open(st.session_state.MASTER_PATH_DET, "wb") as f:
            f.write(up.getbuffer())
        st.success("Master Détail mis à jour !")
        st.rerun()
    
    if st.button("🗑️ Reset Saisies Détail", type="secondary"):
        if os.path.exists(st.session_state.SAISIE_PATH_DET):
            os.remove(st.session_state.SAISIE_PATH_DET)
            st.rerun()
