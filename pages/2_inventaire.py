import streamlit as st
import pandas as pd
import os
import unicodedata
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION & CHEMINS ---
if "DATA_DIR" not in st.session_state:
    st.session_state.DATA_DIR = "data_inventaire"
    st.session_state.MASTER_PATH = os.path.join(st.session_state.DATA_DIR, "master.xlsx")
    st.session_state.SAISIE_PATH = os.path.join(st.session_state.DATA_DIR, "saisie.csv")

os.makedirs(st.session_state.DATA_DIR, exist_ok=True)

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def find_quantity_col(df_check):
    keywords = ['quantit', 'depot', 'stock', 'qte', 'globale']
    for col in df_check.columns:
        if any(key in col for key in keywords):
            return col
    return None

def format_ddp(val):
    try:
        if pd.isna(val) or val == "" or val == "None": return ""
        dt = pd.to_datetime(val)
        return dt.strftime('%m/%Y')
    except:
        return str(val)

def clean_columns(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp',
        'ppa': 'ppa', 'shp': 'shp'
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

# --- 3. CHARGEMENT DES DONNÉES (OPTIMISÉ AVEC CACHE) ---
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

user = st.session_state.current_user

@st.cache_data(ttl=3600)
def load_and_clean_master(file_path, mtime):
    try:
        df = pd.read_excel(file_path)
        # Nettoyage des colonnes
        df = clean_columns(df)
        
        # Vectorisation du formatage DDP (beaucoup plus rapide que .apply)
        if 'ddp' in df.columns:
            # Conversion en datetime (coerce gère les erreurs en NaT)
            dates = pd.to_datetime(df['ddp'], errors='coerce')
            # Formater uniquement les dates valides
            mask = dates.notna()
            df['ddp'] = df['ddp'].astype(str) # Par défaut on garde le texte
            df.loc[mask, 'ddp'] = dates[mask].dt.strftime('%m/%Y')
            
        return df
    except Exception as e:
        st.error(f"Erreur chargement Master : {e}")
        return None

df_master = None
if os.path.exists(st.session_state.MASTER_PATH):
    mtime = os.path.getmtime(st.session_state.MASTER_PATH)
    df_master = load_and_clean_master(st.session_state.MASTER_PATH, mtime)

# --- 4. INTERFACE (DÉFINITION DES TABS) ---
# CRITIQUE : Cette ligne doit être AVANT l'utilisation de tabs[x]
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

# --- ONGLET 0 : DASHBOARD ---
with tabs[0]:
    st.subheader("📦 État de l'inventaire")
    if df_master is not None:
        st.metric("Articles dans le Master", len(df_master))
    else:
        st.warning("⚠️ Aucun Master détecté. Allez dans l'onglet Admin.")

# --- ONGLET 1 : SAISIE TERRAIN ---
with tabs[1]:
    if df_master is not None:
        st.subheader("📝 Enregistrement")
        mode = st.radio("Mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True)
        produits = sorted(df_master['designation'].unique().tolist())
        prod_sel = st.selectbox("🔍 Choisir Produit :", [""] + produits)
        
        if prod_sel:
            df_p = df_master[df_master['designation'] == prod_sel]
            lot_orig = st.selectbox("Lot Master :", df_p['lot'].unique())
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie_v7", clear_on_submit=True):
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

                if st.form_submit_button("💾 Valider"):
                    new_line = pd.DataFrame([{
                        'designation': prod_sel, 'lot_master': str(lot_orig),
                        'lot': str(lot_f), 'qte_saisie': qte, 'ddp_saisi': ddp_f,
                        'ppa_saisi': ppa_f
                    }])
                    if os.path.exists(st.session_state.SAISIE_PATH):
                        old = pd.read_csv(st.session_state.SAISIE_PATH, sep=';')
                        new_line = pd.concat([old, new_line], ignore_index=True)
                    new_line.to_csv(st.session_state.SAISIE_PATH, index=False, sep=';')
                    st.success(f"Enregistré : {prod_sel}")
    else:
        st.info("En attente du Master...")

# --- ONGLET 2 : CONFRONTATION (CORRIGÉ POUR VALUEERROR ET ALERTES) ---
with tabs[2]:
    st.subheader("🔍 Analyse des écarts (Minitieuse)")
    if user['role'] == "Admin":
        if os.path.exists(st.session_state.SAISIE_PATH) and df_master is not None:
            try:
                saisie = pd.read_csv(st.session_state.SAISIE_PATH, sep=';', encoding='utf-8-sig')
                saisie = clean_columns(saisie)
                q_theo_col = find_quantity_col(df_master)
                
                if q_theo_col and 'designation' in df_master.columns:
                    # Assurer que les colonnes de quantité sont numériques
                    saisie['qte_saisie'] = pd.to_numeric(saisie['qte_saisie'], errors='coerce').fillna(0)
                    df_master[q_theo_col] = pd.to_numeric(df_master[q_theo_col], errors='coerce').fillna(0)
                    
                    # Grouper la saisie par produit pour avoir la quantité totale (tous lots confondus)
                    saisie_grouped = saisie.groupby('designation')['qte_saisie'].sum().reset_index()
                    
                    # Fusionner avec le Master
                    comp = pd.merge(df_master, saisie_grouped, on='designation', how='left')
                    comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
                    comp['écart'] = comp['qte_saisie'] - comp[q_theo_col]
                    
                    st.write("### Tableau Récapitulatif")
                    st.dataframe(comp[['designation', 'laboratoire', q_theo_col, 'qte_saisie', 'écart']], use_container_width=True)
                    
                    # EXPORT EXCEL
                    import io
                    buffer = io.BytesIO()
                    comp.to_excel(buffer, index=False)
                    st.download_button(
                        label="📥 Exporter les écarts en Excel",
                        data=buffer.getvalue(),
                        file_name="Ecarts_Inventaire_Detaille.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    st.divider()
                    st.write("### Détail par Lot (Saisie terrain)")
                    st.dataframe(saisie, use_container_width=True)

                    if st.button("🗑️ Réinitialiser tout l'inventaire"):
                        os.remove(st.session_state.SAISIE_PATH)
                        st.rerun()
                
                # --- ANALYSE IA ---
                if is_ia_enabled():
                    st.divider()
                    with st.expander("🤖 Assistant IA Inventaire"):
                        if st.button("📊 Analyser les écarts", use_container_width=True):
                            with st.spinner("L'IA analyse vos données..."):
                                ecarts = comp[comp['écart'] != 0][['designation', 'écart']].to_dict('records')
                                prompt = f"Voici les écarts d'inventaire détectés : {ecarts}. Donne-moi un résumé des 3 plus gros problèmes et suggère des actions correctives pour un dépôt pharmaceutique."
                                st.write(ask_ai(prompt))
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
        else: st.info("Aucune donnée de saisie trouvée.")
    else: st.warning("Accès restreint à l'administrateur.")

# --- ONGLET 3 : ADMIN ---
with tabs[3]:
    st.subheader("⚙️ Gestion des fichiers")
    up = st.file_uploader("Importer Master (Excel)", type="xlsx")
    if up:
        with open(st.session_state.MASTER_PATH, "wb") as f:
            f.write(up.getbuffer())
        st.success("Master mis à jour !")
        st.rerun()
    
    if st.button("🔴 RESET TOTAL (Vider tout)"):
        if os.path.exists(st.session_state.MASTER_PATH): os.remove(st.session_state.MASTER_PATH)
        if os.path.exists(st.session_state.SAISIE_PATH): os.remove(st.session_state.SAISIE_PATH)
        st.rerun()
