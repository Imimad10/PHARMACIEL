import streamlit as st
import pandas as pd
import os
import unicodedata

# --- CONFIGURATION ET CHEMINS ---
st.set_page_config(page_title="Darpharm Solution - Inventaire Expert", layout="wide")

DATA_DIR = "data_inventaire"
ARCHIVE_DIR = os.path.join(DATA_DIR, "archives")
MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

for d in [DATA_DIR, ARCHIVE_DIR]:
    os.makedirs(d, exist_ok=True)

# --- FONCTIONS TECHNIQUES ---

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_columns(df):
    """Nettoyage flexible pour Logipharm et Saisie"""
    mapping = {
        'produit': 'designation', 'designation': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot',
        'lot_master': 'lot_master', 'qte_saisie': 'qte_saisie',
        'ppa': 'ppa', 'ddp': 'ddp'
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
        if not matched and any(key in norm for key in stock_keywords) and 'stock_theorique' not in new_cols:
            new_cols.append('stock_theorique')
            matched = True
        if not matched: new_cols.append(norm)
    df.columns = new_cols
    return df

def load_master():
    if not os.path.exists(MASTER_PATH): return None
    try:
        df = pd.read_excel(MASTER_PATH)
        return clean_columns(df)
    except Exception as e:
        st.error(f"Erreur lecture Master : {e}")
        return None

# --- ÉTAT DE LA SESSION ---
if "current_user" not in st.session_state:
    st.warning("Veuillez vous connecter sur la page d'accueil.")
    st.stop()

user = st.session_state.current_user
df_master = load_master()

# --- INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

# 1. DASHBOARD
with tabs[0]:
    st.subheader("État de l'Inventaire & Arrivages")
    if df_master is not None:
        col1, col2 = st.columns(2)
        col1.metric("Références en Stock", len(df_master))
        
        with col2:
            st.write("**🔄 Nouvel Arrivage ?**")
            confirm = st.checkbox("Je veux supprimer le Master actuel pour en charger un nouveau")
            if st.button("🗑️ Réinitialiser le Master", disabled=not confirm):
                os.remove(MASTER_PATH)
                st.rerun()
    else:
        st.info("Aucun Master chargé. Allez dans 'Admin' pour importer votre export Logipharm.")

# 2. SAISIE TERRAIN (MODE RAPIDE & DÉTAILLÉ)
with tabs[1]:
    if df_master is not None:
        st.subheader("📝 Mode de Saisie")
        mode_saisie = st.radio("Sélectionnez le mode :", ["🚀 Rapide (Quantité seule)", "📋 Détaillé (Modif Lot/DDP/PPA)"], horizontal=True)
        
        produits = sorted(df_master['designation'].unique().tolist())
        prod_sel = st.selectbox("Sélectionner le produit :", [""] + produits)
        
        if prod_sel:
            df_p = df_master[df_master['designation'] == prod_sel]
            lot_orig = st.selectbox("Choisir le lot (Logipharm) :", df_p['lot'].unique())
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie", clear_on_submit=True):
                c1, c2 = st.columns(2)
                
                # Valeurs par défaut basées sur le Master
                lot_final = lot_orig
                ddp_final = str(info_m.get('ddp', ''))
                ppa_final = float(info_m.get('ppa', 0))

                if mode_saisie == "🚀 Rapide (Quantité seule)":
                    qte_s = c1.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                    st.info(f"Enregistrement sur le Lot : {lot_orig} | DDP : {ddp_final}")
                else:
                    lot_final = c1.text_input("Modifier le n° de Lot", value=str(lot_orig))
                    qte_s = c2.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                    ddp_final = c1.text_input("DDP (MM/AAAA)", value=ddp_final)
                    ppa_final = c2.number_input("PPA", value=ppa_final)

                if st.form_submit_button("💾 Valider la Saisie"):
                    new_line = {
                        'designation': prod_sel,
                        'lot_master': lot_orig,
                        'lot': lot_final,
                        'qte_saisie': qte_s,
                        'ddp_saisi': ddp_final,
                        'ppa_saisi': ppa_final,
                        'utilisateur': user['username']
                    }
                    df_new = pd.DataFrame([new_line])
                    if os.path.exists(SAISIE_PATH):
                        df_old = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                        df_final = pd.concat([df_old, df_new], ignore_index=True)
                    else:
                        df_final = df_new
                    df_final.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                    st.success(f"Saisie de {prod_sel} enregistrée !")
                    st.rerun()
    else:
        st.warning("Veuillez charger un fichier Master pour commencer la saisie.")

# 3. CONFRONTATION ET ALERTES
with tabs[2]:
    st.subheader("🔍 Analyse des Écarts et Discordances")
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            
            # Sécurité anti-KeyError : Vérification des colonnes du nouveau mode
            if 'lot_master' not in saisie.columns:
                st.error("⚠️ Le fichier de saisie est incompatible avec le nouveau mode.")
                if st.button("Réinitialiser le fichier de saisie"):
                    os.remove(SAISIE_PATH)
                    st.rerun()
                st.stop()

            # Calcul
            s_grouped = saisie.groupby(['designation', 'lot_master', 'lot']).agg({'qte_saisie':'sum', 'ddp_saisi':'first'}).reset_index()
            
            df_master['lot'] = df_master['lot'].astype(str)
            s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
            
            comp = pd.merge(df_master, s_grouped, left_on=['designation', 'lot'], right_on=['designation', 'lot_master'], how='left')
            comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
            comp['écart'] = comp['qte_saisie'] - comp.get('stock_theorique', 0)
            
            # Statut d'alerte
            def check_lot(row):
                if pd.isna(row['lot_y']): return "🚫 Non saisi"
                return "✅ OK" if str(row['lot_x']) == str(row['lot_y']) else "⚠️ LOT CHANGÉ"
            
            comp['Statut'] = comp.apply(check_lot, axis=1)

            # Affichage
            st.dataframe(comp[['designation', 'lot_x', 'stock_theorique', 'qte_saisie', 'écart', 'Statut']], use_container_width=True)

            if st.button("📦 Archiver l'inventaire complet"):
                ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                saisie.to_csv(os.path.join(ARCHIVE_DIR, f"inventaire_{ts}.csv"), index=False, sep=';')
                os.remove(SAISIE_PATH)
                st.success("Archivé !")
                st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info("Aucune donnée à confronter.")

# 4. ADMIN
with tabs[3]:
    st.header("⚙️ Administration Système")
    file = st.file_uploader("Charger le fichier Logipharm (.xlsx)", type="xlsx")
    if file:
        with open(MASTER_PATH, "wb") as f:
            f.write(file.getbuffer())
        st.success("Fichier Master installé avec succès !")
        st.rerun()
