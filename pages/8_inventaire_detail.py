# VERSION 5 - FULL MODES & CONFRONTATION
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

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_cols_v5(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation', 'article': 'designation', 'libelle': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp', 'date': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone', 'sector': 'zone'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte', 'dispo']
    new_cols = []
    found = set()
    for col in df.columns:
        norm = normalize_text(col)
        target = None
        for k, v in mapping.items():
            if k in norm and v not in found:
                target = v; found.add(v); break
        if not target and any(key in norm for key in stock_keywords) and 'stock_theorique' not in found:
            target = 'stock_theorique'; found.add(target)
        new_cols.append(target if target else norm)
    df.columns = new_cols
    return df

@st.cache_data(ttl=60)
def load_master_v5(path, mtime):
    try:
        df = pd.read_excel(path, engine='openpyxl')
        df = clean_cols_v5(df)
        req = ['designation', 'lot', 'zone']
        if not all(c in df.columns for c in req): return f"Colonnes manquantes : {[c for c in req if c not in df.columns]}"
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
        df['zone'] = df['zone'].astype(str).str.upper().str.strip()
        return df
    except Exception as e: return str(e)

# --- 3. UI ---
st.title("🔍 Inventaire Détail (Zones)")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
user_zone = user.get('zone', 'Aucune')

df_master = None
if os.path.exists(MASTER_PATH):
    res = load_master_v5(MASTER_PATH, os.path.getmtime(MASTER_PATH))
    if isinstance(res, str): st.error(res)
    else: df_master = res

if user_zone == "Aucune":
    selected_zone = st.sidebar.selectbox("📍 Zone de travail :", ["A", "B", "C", "D", "Frigo"])
else:
    selected_zone = user_zone
    st.sidebar.success(f"📍 Zone assignée : **{selected_zone}**")

tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Total Articles", len(df_master))
        df_z = df_master[df_master['zone'] == selected_zone]
        c2.metric(f"Zone {selected_zone}", len(df_z))
        st.bar_chart(df_master['zone'].value_counts())
    else: st.info("Importer Master dans Admin.")

with tabs[1]:
    if df_master is not None:
        df_z = df_master[df_master['zone'] == selected_zone].copy()
        if df_z.empty: st.warning(f"Zone {selected_zone} vide.")
        else:
            mode = st.radio("Méthode de saisie :", ["🚀 Rapide", "📋 Détaillée"], horizontal=True)
            prods = sorted(df_z['designation'].unique())
            sel_prod = st.selectbox("Produit :", [""] + prods)
            
            if sel_prod:
                df_p = df_z[df_z['designation'] == sel_prod]
                lots = sorted(df_p['lot'].unique())
                sel_lot = st.selectbox("Lot Master :", lots)
                info = df_p[df_p['lot'] == sel_lot].iloc[0]
                
                with st.form("form_saisie_det_v5", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    ddp_m = str(info.get('ddp', ''))
                    ppa_m = float(info.get('ppa', 0)) if 'ppa' in info else 0.0
                    
                    if mode == "🚀 Rapide":
                        qte = c1.number_input("Quantité", min_value=0.0, step=1.0)
                        lot_r, ddp_r, ppa_r = sel_lot, ddp_m, ppa_m
                    else:
                        lot_r = c1.text_input("Lot Réel", value=str(sel_lot))
                        qte = c2.number_input("Quantité", min_value=0.0, step=1.0)
                        ddp_r = c1.text_input("DDP (MM/AAAA)", value=ddp_m)
                        ppa_r = c2.number_input("PPA Saisi", value=ppa_m)
                    
                    if st.form_submit_button("💾 Enregistrer"):
                        new_line = pd.DataFrame([{
                            'designation': sel_prod, 'lot_master': sel_lot, 'lot': lot_r,
                            'qte_saisie': qte, 'ddp_saisi': ddp_r, 'ppa_saisi': ppa_r,
                            'zone': selected_zone, 'agent': user['username']
                        }])
                        h = not os.path.exists(SAISIE_PATH)
                        new_line.to_csv(SAISIE_PATH, mode='a', header=h, index=False, sep=';')
                        st.success(f"Saisie OK : {sel_prod}")
    else: st.info("Master requis.")

with tabs[2]:
    st.subheader("🔍 Analyse des écarts")
    if user['role'] in ["Admin", "Superviseur"] and os.path.exists(SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', on_bad_lines='skip')
            
            st.write(f"📊 **Statut :** {len(saisie)} saisies totales détectées dans le journal.")
            
            if 'qte_saisie' not in saisie.columns:
                st.warning("⚠️ Le format du fichier de saisie est obsolète. Veuillez le vider dans l'onglet Admin pour repartir à neuf.")
                st.dataframe(saisie.head())
            else:
                mode_conf = st.radio("Type d'Analyse :", ["⚡ Rapide (Global)", "🔬 Détaillée (Par Lot)"], horizontal=True)
                
                # Filtrage par zone pour l'analyse
                unique_zones = [str(z) for z in df_master['zone'].unique() if pd.notna(z)]
                z_ana = st.selectbox("Filtrer par Zone :", ["Toutes"] + sorted(unique_zones))
                
                df_m_f = df_master if z_ana == "Toutes" else df_master[df_master['zone'] == z_ana]
                df_s_f = saisie if z_ana == "Toutes" else saisie[saisie['zone'] == z_ana]
                
                if df_s_f.empty:
                    st.warning(f"Aucune saisie trouvée pour la zone {z_ana}.")
                else:
                    def robust_num(s):
                        if pd.isna(s): return 0.0
                        if isinstance(s, (int, float)): return float(s)
                        if isinstance(s, str):
                            s = s.replace('\xa0', '').replace(' ', '').replace(',', '.')
                        try:
                            val = pd.to_numeric(s, errors='coerce')
                            return float(val) if pd.notna(val) else 0.0
                        except: return 0.0

                    q_col = 'stock_theorique' if 'stock_theorique' in df_m_f.columns else None
                    
                    if q_col:
                        df_m_f[q_col] = df_m_f[q_col].apply(robust_num).fillna(0)
                        df_s_f['qte_saisie'] = df_s_f['qte_saisie'].apply(robust_num).fillna(0)
                    
                    if "Rapide" in mode_conf:
                        m_g = df_m_f.groupby('designation')[q_col].sum().reset_index()
                        s_g = df_s_f.groupby('designation')['qte_saisie'].sum().reset_index()
                        comp = pd.merge(m_g, s_g, on='designation', how='outer').fillna(0)
                        comp['écart'] = comp['qte_saisie'] - comp[q_col]
                        
                        def style_ecart(row):
                            return ['background-color: #9e1a1a; color: white' if row['écart'] != 0 else '' for _ in row]
                        
                        st.write("### 📊 Écarts de Quantités Globales")
                        st.dataframe(comp.style.apply(style_ecart, axis=1), use_container_width=True, hide_index=True)
                    else:
                        # Analyse détaillée par Lot
                        m_sub = df_m_f[['designation', 'lot', q_col, 'ddp', 'ppa', 'shp'] if 'shp' in df_m_f.columns else ['designation', 'lot', q_col, 'ddp', 'ppa']].copy()
                        m_sub.columns = [c + '_master' if c != 'designation' and c != 'lot' else ('lot_master' if c == 'lot' else c) for c in m_sub.columns]
                        
                        comp_d = pd.merge(m_sub, df_s_f, on=['designation', 'lot_master'], how='outer').fillna(0)
                        
                        def highlight_diffs_detail(row):
                            styles = ['' for _ in row.index]
                            red = 'background-color: #9e1a1a; color: white'
                            
                            # Qte
                            q_m = robust_num(row.get(f'{q_col}_master' if q_col else 'stock_theorique_master', 0))
                            q_s = robust_num(row.get('qte_saisie', 0))
                            if q_s != q_m:
                                styles[row.index.get_loc('qte_saisie')] = red
                            
                            # Lot
                            if str(row.get('lot')) != str(row.get('lot_master')) and pd.notna(row.get('lot')):
                                styles[row.index.get_loc('lot')] = red
                            
                            # DDP
                            if str(row.get('ddp_saisi')) != str(row.get('ddp_master')) and pd.notna(row.get('ddp_saisi')):
                                styles[row.index.get_loc('ddp_saisi')] = red
                            
                            # PPA
                            p_m = robust_num(row.get('ppa_master', 0))
                            p_s = robust_num(row.get('ppa_saisi', 0))
                            if p_s != p_m and p_s != 0:
                                styles[row.index.get_loc('ppa_saisi')] = red
                            return styles

                        st.write("### 🔬 Confrontation Minutieuse (Lots & Métadonnées)")
                        st.dataframe(comp_d.style.apply(highlight_diffs_detail, axis=1), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")
    else: st.warning("Accès réservé aux Administrateurs et Superviseurs.")

with tabs[3]:
    if user['role'] == "Admin":
        st.subheader("⚙️ Gestion des fichiers")
    up = st.file_uploader("Importer Master Détail (XLSX)", type="xlsx")
    if up:
        if st.button("🚀 Confirmer l'importation"):
            with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
            st.cache_data.clear()
            st.success("Master Détail importé avec succès !")
            st.rerun()
            
    st.divider()
    c1, c2 = st.columns(2)
    
    if c1.button("🗑️ Vider Inventaire (Saisie)", use_container_width=True):
        if os.path.exists(SAISIE_PATH):
            os.remove(SAISIE_PATH)
            st.success("Toutes les saisies terrain ont été effacées.")
            st.rerun()
        else:
            st.info("Le fichier de saisie est déjà vide.")
            
    if c2.button("🔴 Supprimer Master", use_container_width=True):
        if os.path.exists(MASTER_PATH):
            os.remove(MASTER_PATH)
            st.cache_data.clear()
            st.success("Fichier Master supprimé.")
            st.rerun()
        else:
            st.info("Aucun Master à supprimer.")
    else:
        st.warning("L'onglet Admin est réservé aux administrateurs système.")
