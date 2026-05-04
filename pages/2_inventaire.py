import streamlit as st
import pandas as pd
import os
import unicodedata

# --- CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution - Modes Inventaire", layout="wide")

DATA_DIR = "data_inventaire"
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")
MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
os.makedirs(DATA_DIR, exist_ok=True)

# --- FONCTIONS UTILITAIRES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_columns(df):
    mapping = {'produit': 'designation', 'n°lot': 'lot', 'nlot': 'lot', 'quantite': 'stock_theorique', 'ppa': 'ppa', 'ddp': 'ddp'}
    new_cols = []
    for col in df.columns:
        norm = normalize_text(col)
        found = False
        for k, v in mapping.items():
            if k in norm: 
                new_cols.append(v)
                found = True
                break
        if not found: new_cols.append(norm)
    df.columns = new_cols
    return df

# --- CHARGEMENT ---
df_master = None
if os.path.exists(MASTER_PATH):
    df_master = clean_columns(pd.read_excel(MASTER_PATH))

# --- INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]:
    if df_master is not None:
        st.metric("Total Master", len(df_master))
        if st.checkbox("🔄 Mode Arrivage : Supprimer le Master actuel"):
            if st.button("Confirmer suppression"):
                os.remove(MASTER_PATH)
                st.rerun()

with tabs[1]:
    st.subheader("📝 Mode de Saisie")
    if df_master is not None:
        mode = st.radio("Choisir le mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True)
        
        produit_sel = st.selectbox("Produit", [""] + sorted(df_master['designation'].unique().tolist()))
        
        if produit_sel:
            df_p = df_master[df_master['designation'] == produit_sel]
            lot_orig = st.selectbox("Lot d'origine (Master)", df_p['lot'].unique())
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie"):
                c1, c2 = st.columns(2)
                
                # Mode Rapide : On garde les infos du master
                lot_final = lot_orig
                ddp_final = info_m.get('ddp', '-')
                ppa_final = info_m.get('ppa', 0)
                
                if mode == "🚀 Rapide":
                    qte_saisie = c1.number_input("Quantité", min_value=0.0)
                    st.info(f"Lot : {lot_orig} | DDP : {ddp_final}")
                
                else: # Mode Détaillé : On peut tout modifier
                    lot_final = c1.text_input("Modifier le Lot", value=str(lot_orig))
                    qte_saisie = c2.number_input("Quantité", min_value=0.0)
                    ddp_final = c1.text_input("DDP (Ex: 12/2026)", value=str(info_m.get('ddp', '')))
                    ppa_final = c2.number_input("PPA", value=float(info_m.get('ppa', 0)))

                if st.form_submit_button("Enregistrer"):
                    new_data = {
                        'designation': produit_sel,
                        'lot_master': lot_orig, # Pour la comparaison
                        'lot': lot_final,       # Ce qui est réellement sur la boîte
                        'qte_saisie': qte_saisie,
                        'ddp_saisi': ddp_final,
                        'ppa_saisi': ppa_final,
                        'mode': mode
                    }
                    df_new = pd.DataFrame([new_data])
                    if os.path.exists(SAISIE_PATH):
                        df_old = pd.read_csv(SAISIE_PATH, sep=';')
                        df_new = pd.concat([df_old, df_new], ignore_index=True)
                    df_new.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                    st.success("Saisi !")
                    st.rerun()

with tabs[2]:
    st.subheader("🔍 Analyse & Alertes")
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        saisie = pd.read_csv(SAISIE_PATH, sep=';')
        
        # On groupe les saisies
        s_grouped = saisie.groupby(['designation', 'lot_master', 'lot']).agg({
            'qte_saisie': 'sum',
            'ddp_saisi': 'first',
            'ppa_saisi': 'first'
        }).reset_index()

        # Fusion avec le Master
        df_master['lot'] = df_master['lot'].astype(str)
        s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
        
        comp = pd.merge(df_master, s_grouped, left_on=['designation', 'lot'], right_on=['designation', 'lot_master'], how='left')
        comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
        comp['écart'] = comp['qte_saisie'] - comp.get('stock_theorique', 0)

        # LOGIQUE D'ALERTE : Si le lot saisi est différent du lot master
        def alerte_lot(row):
            if pd.isna(row['lot_y']): return "Pas de saisie"
            return "✅ OK" if str(row['lot_x']) == str(row['lot_y']) else "⚠️ LOT MODIFIÉ"

        comp['Statut Lot'] = comp.apply(alerte_lot, axis=1)

        # Affichage avec style
        st.write("Tableau des écarts :")
        display_cols = ['designation', 'lot_x', 'stock_theorique', 'qte_saisie', 'écart', 'Statut Lot']
        st.dataframe(comp[display_cols].style.applymap(
            lambda x: 'background-color: #ffcccc' if x == "⚠️ LOT MODIFIÉ" else '', subset=['Statut Lot']
        ), use_container_width=True)

with tabs[3]:
    st.header("⚙️ Admin")
    up = st.file_uploader("Nouveau Master Logipharm", type="xlsx")
    if up:
        with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
        st.success("Master mis à jour.")
