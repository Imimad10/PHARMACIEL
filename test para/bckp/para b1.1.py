import streamlit as st
import pandas as pd
import os
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(page_title="Pharmaciel - Gestion Para", layout="wide")

# --- FICHIERS ---
DB_PATH = 'database_para.csv'
USERS_PATH = 'users.csv'

# --- STYLE CSS POUR UNIFORMISER LES IMAGES ---
st.markdown("""
    <style>
    .product-img {
        width: 100%;
        height: 200px;
        object-fit: contain;
        background-color: #f9f9f9;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CHARGEMENT SÉCURISÉ ---
def load_data(path, cols):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype={c: str for c in cols})
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, path):
    df_to_save = df.copy()
    for col in df_to_save.columns:
        df_to_save[col] = df_to_save[col].astype(str).replace('nan', '')
    df_to_save.to_csv(path, index=False)

# Initialisation
df_para = load_data(DB_PATH, ['nom', 'marque', 'explication', 'image_path'])
df_users = load_data(USERS_PATH, ['username', 'role'])

# --- INTERFACE ---
tab_cat, tab_admin = st.tabs(["📋 Catalogue Produits", "⚙️ Administration"])

# --- CATALOGUE ---
with tab_cat:
    st.title("🌿 Référentiel Parapharmacie")
    search = st.text_input("🔍 Rechercher un produit...", key="main_search")
    
    display_df = df_para.copy().fillna("")
    if search:
        display_df = display_df[display_df['nom'].str.contains(search, case=False, na=False)]
    
    if display_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        # Affichage en grille de 4 colonnes pour un meilleur rendu
        for i in range(0, len(display_df), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(display_df):
                    row = display_df.iloc[i + j]
                    with cols[j]:
                        img_url = row['image_path'] if row['image_path'] != "" else "https://via.placeholder.com/200"
                        # Utilisation de HTML pour forcer la taille
                        st.markdown(f'<img src="{img_url}" class="product-img">', unsafe_allow_html=True)
                        st.caption(row['nom'][:50] + "..." if len(row['nom']) > 50 else row['nom'])

# --- ADMINISTRATION ---
with tab_admin:
    st.title("⚙️ Administration")
    sub_user, sub_import, sub_val = st.tabs(["👥 Utilisateurs", "📥 Importation", "🖼️ Validation Images"])

    with sub_user:
        st.subheader("Gestion des accès")
        with st.form("u_form", clear_on_submit=True):
            un = st.text_input("Nom de l'agent")
            ur = st.selectbox("Rôle", ["admin", "preparateur", "commercial"])
            if st.form_submit_button("Ajouter"):
                if un:
                    new_u = pd.DataFrame([[un, ur]], columns=['username', 'role'])
                    df_users = pd.concat([df_users, new_u], ignore_index=True)
                    save_data(df_users, USERS_PATH)
                    st.success(f"Agent {un} ajouté."); st.rerun()
        st.dataframe(df_users, use_container_width=True, hide_index=True)

    with sub_import:
        st.subheader("Importation Excel / CSV")
        up_file = st.file_uploader("Choisir le fichier", type=['csv', 'xlsx'])
        if up_file:
            data = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
            if st.button("🚀 Lancer l'intégration"):
                possibilites = ['Produit', 'nom', 'DESIGNATION', 'NOM', 'designation']
                col_trouvee = next((c for c in possibilites if c in data.columns), None)
                if col_trouvee:
                    data = data.rename(columns={col_trouvee: 'nom'})
                    nouveaux = data[~data['nom'].astype(str).isin(df_para['nom'].astype(str).tolist())].copy()
                    if not nouveaux.empty:
                        for c in ['marque', 'explication', 'image_path']:
                            if c not in nouveaux.columns: nouveaux[c] = ""
                        df_para = pd.concat([df_para, nouveaux[['nom', 'marque', 'explication', 'image_path']]], ignore_index=True)
                        save_data(df_para, DB_PATH)
                        st.success(f"✅ {len(nouveaux)} produits ajoutés !"); st.rerun()
                else:
                    st.error("Colonne 'Produit' non trouvée.")

    with sub_val:
        st.subheader("🖼️ Validation des images")
        df_missing = df_para[df_para['image_path'].isna() | (df_para['image_path'] == "")]
        
        if not df_missing.empty:
            selected_p = st.selectbox("Choisir le produit :", df_missing['nom'].unique())
            clean_name = selected_p.split(" C/")[0].split(" BT")[0]
            encoded_query = urllib.parse.quote(clean_name)
            google_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch"
            
            st.info(f"Produit : **{selected_p}**")
            st.markdown(f"### 1. [Chercher sur Google]({google_url})")
            url_input = st.text_input("Coller l'adresse de l'image ici")
            
            if st.button("💾 Enregistrer"):
                if url_input:
                    df_para.loc[df_para['nom'] == selected_p, 'image_path'] = str(url_input)
                    save_data(df_para, DB_PATH)
                    st.success("Image enregistrée !"); st.rerun()
        else:
            st.success("Toutes les images sont ok !")
