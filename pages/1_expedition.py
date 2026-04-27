import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
# st.set_page_config(page_title="Gestion des Expéditions", layout="wide")
DATA_DIR = "data_expedition"
os.makedirs(DATA_DIR, exist_ok=True)
SECTEURS_PATH = os.path.join(DATA_DIR, "secteurs.csv")
LIVREURS_PATH = os.path.join(DATA_DIR, "livreurs.csv")

# --- FONCTIONS DE CHARGEMENT ---
def load_clients():
    if not os.path.exists(SECTEURS_PATH) or os.path.getsize(SECTEURS_PATH) == 0:
        return pd.DataFrame(columns=["Client", "Ville", "Tel", "Secteur"])
    try:
        df = pd.read_csv(SECTEURS_PATH)
        mapping = {'nom client': 'Client', 'VILLE': 'Ville', 'tel': 'Tel', 'SECTEUR': 'Secteur'}
        df = df.rename(columns=mapping)
        return df.loc[:, ~df.columns.duplicated()] 
    except:
        return pd.DataFrame(columns=["Client", "Ville", "Tel", "Secteur"])

def save_clients(df):
    df.to_csv(SECTEURS_PATH, index=False)

def load_livreurs():
    if not os.path.exists(LIVREURS_PATH):
        return pd.DataFrame(columns=["Nom", "Prénom", "Téléphone", "Secteur"])
    return pd.read_csv(LIVREURS_PATH)

def save_livreurs(df):
    df.to_csv(LIVREURS_PATH, index=False)

# --- INITIALISATION ÉTAT ---
if "rows" not in st.session_state:
    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "N° Doc", "Info", "Signature"])

# --- INTERFACE ---
st.title("🚛 Gestion des Expéditions")

tab_exp, tab_livreurs, tab_secteurs, tab_admin = st.tabs([
    "📋 Programme d'Expédition", "👤 Gestion des Livreurs", "📍 Gestion des Secteurs", "⚙️ Administration"
])

# 1. PROGRAMME D'EXPÉDITION
with tab_exp:
    mode = st.radio("Mode d'expédition", ["Commande", "Réclamation"], horizontal=True)
    
    # Sécurisation des données clients pour le Selectbox
    df_clients = load_clients()
    client_list = df_clients["Client"].dropna().astype(str).unique().tolist() if "Client" in df_clients.columns else []
    client_map = dict(zip(df_clients['Client'].astype(str), df_clients['Ville'])) if "Client" in df_clients.columns else {}

    col_g1, col_d1 = st.columns(2)
    df_livreurs = load_livreurs()
    liste_livreurs = df_livreurs["Nom"].tolist() if not df_livreurs.empty else []
    
    with col_g1:
        livreur_choisi = st.selectbox("Choisir le livreur", liste_livreurs)
    with col_d1:
        date_exp = st.date_input("Date d'expédition")

    st.divider()
    
    # Formulaire d'ajout
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1])
        with c1:
            new_client = st.selectbox("Client", ["Sélectionnez..."] + client_list)
        with c2:
            ref_bon = st.text_input("Réf. Bon")
        with c3:
            if mode == "Commande":
                val_info = st.text_input("Colissage")
            else:
                val_info = st.selectbox("Motif", ["RETOUR", "DEPOSER COLI", "ECHANGE"])
        with c4:
            st.write("###") # Aligne avec le champ texte
            btn_ajouter = st.button("➕ Ajouter")

    if btn_ajouter:
        if new_client != "Sélectionnez..." and ref_bon:
            annee = datetime.now().strftime('%y')
            prefixe = "RC" if mode == "Réclamation" else "BL"
            full_ref = f"{annee}/{prefixe}/{ref_bon}"
            ville = client_map.get(new_client, "")
            
            new_row = pd.DataFrame([{"Client": new_client, "Ville": ville, "N° Doc": full_ref, "Info": val_info, "Signature": ""}])
            st.session_state.rows = pd.concat([st.session_state.rows, new_row], ignore_index=True)
            st.rerun()

    st.subheader(f"Détails des {mode}s")
    
    # Édition et mise à jour du tableau
    col_label = "Colissage" if mode == "Commande" else "Motif"
    edited_rows = st.data_editor(
        st.session_state.rows, 
        num_rows="dynamic", 
        use_container_width=True, 
        column_config={"Info": st.column_config.TextColumn(label=col_label)}
    )
    st.session_state.rows = edited_rows
    
    if st.button("🗑️ Vider le tableau"):
        st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "N° Doc", "Info", "Signature"])
        st.rerun()
        
    if st.button("🖨️ Extraire en PDF"):
        st.info(f"Génération PDF pour {livreur_choisi} le {date_exp}")

# 2. GESTION DES LIVREURS
with tab_livreurs:
    st.header("👤 Gestion des Livreurs")
    with st.form("form_ajout_livreur", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nom = col1.text_input("Nom")
        prenom = col1.text_input("Prénom")
        tel = col2.text_input("Téléphone")
        secteur = col2.text_input("Secteur")
        if st.form_submit_button("Ajouter le livreur"):
            if nom:
                df_l = load_livreurs()
                new_l = pd.DataFrame([{"Nom": nom, "Prénom": prenom, "Téléphone": tel, "Secteur": secteur}])
                save_livreurs(pd.concat([df_l, new_l], ignore_index=True))
                st.rerun()

    df_livreurs = load_livreurs()
    edited_livreurs = st.data_editor(df_livreurs, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder les livreurs"):
        save_livreurs(edited_livreurs)
        st.success("Enregistré !")

# 3. GESTION DES SECTEURS (Clients)
with tab_secteurs:
    st.header("📍 Gestion des Clients")
    with st.expander("➕ Ajouter un nouveau client"):
        with st.form("ajout_client", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_nom = c1.text_input("Nom Client")
            new_ville = c1.text_input("Ville")
            new_tel = c2.text_input("Téléphone")
            new_secteur = c2.text_input("Secteur")
            if st.form_submit_button("Valider l'ajout"):
                df_actuel = load_clients()
                new_data = pd.DataFrame([{"Client": new_nom, "Ville": new_ville, "Tel": new_tel, "Secteur": new_secteur}])
                save_clients(pd.concat([df_actuel, new_data], ignore_index=True))
                st.rerun()

    df_clients_edit = load_clients()
    edited_clients = st.data_editor(df_clients_edit, use_container_width=True, num_rows="dynamic")
