import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Pharmaciel - Gestion Para", layout="wide")

# CSS pour améliorer l'esthétique
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ET FICHIERS ---
DB_PATH = 'database_para.csv'
USERS_PATH = 'users.csv'
IMG_DIR = 'images'

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# --- FONCTIONS DE DONNÉES ---
def load_data(path, columns):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, path):
    df.to_csv(path, index=False)

# Chargement des bases
df_para = load_data(DB_PATH, ['id', 'nom', 'marque', 'explication', 'image_path'])
df_users = load_data(USERS_PATH, ['username', 'role'])

# --- NAVIGATION ---
tab_catalogue, tab_admin = st.tabs(["📋 Catalogue Produits", "⚙️ Administration"])

# --- ONGLET 1 : CATALOGUE (VUE UTILISATEUR) ---
with tab_catalogue:
    st.title("🌿 Référentiel Parapharmacie")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Rechercher un produit...", placeholder="Saisissez un nom, une marque ou un mot-clé...")
    with col2:
        marques_dispos = df_para['marque'].dropna().unique().tolist()
        filter_marque = st.multiselect("Filtrer par marque", options=marques_dispos)

    # Logique de filtrage
    results = df_para.copy()
    if search:
        # Recherche dans le nom ET l'explication
        mask = results['nom'].str.contains(search, case=False, na=False) | \
               results['explication'].str.contains(search, case=False, na=False)
        results = results[mask]
    if filter_marque:
        results = results[results['marque'].isin(filter_marque)]

    if results.empty:
        st.info("Aucun produit trouvé dans la base. Utilisez l'onglet Administration pour importer des données.")
    else:
        # Affichage en grille de 3 colonnes
        for i in range(0, len(results), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(results):
                    row = results.iloc[i + j]
                    with cols[j]:
                        with st.container(border=True):
                            # Image par défaut si vide
                            img_path = row['image_path']
                            if pd.isna(img_path) or not os.path.exists(str(img_path)):
                                img_display = "https://via.placeholder.com/300x200?text=Image+Indisponible"
                            else:
                                img_display = img_path
                            
                            st.image(img_display, use_container_width=True)
                            st.subheader(row['nom'])
                            st.caption(f"🔖 Marque: {row['marque'] if pd.notna(row['marque']) else 'Non précisée'}")
                            
                            with st.expander("ℹ️ Détails & Explications"):
                                text = row['explication'] if pd.notna(row['explication']) else "Aucune consigne spécifique pour ce produit."
                                st.write(text)

# --- ONGLET 2 : ADMINISTRATION ---
with tab_admin:
    st.title("⚙️ Panneau de Contrôle")
    
    admin_sub1, admin_sub2, admin_sub3 = st.tabs(["👥 Utilisateurs", "📥 Importation Data", "🖼️ Gestion Images"])

    # 1. GESTION DES UTILISATEURS
    with admin_sub1:
        st.subheader("Ajouter un accès")
        with st.form("user_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            u_name = c1.text_input("Nom d'utilisateur / Agent")
            u_role = c2.selectbox("Rôle attribué", ["admin", "preparateur", "commercial"])
            if st.form_submit_button("Enregistrer"):
                if u_name:
                    new_u = pd.DataFrame([[u_name, u_role]], columns=['username', 'role'])
                    df_users = pd.concat([df_users, new_u], ignore_index=True)
                    save_data(df_users, USERS_PATH)
                    st.success(f"Utilisateur {u_name} ajouté.")
                    st.rerun()

        st.write("### Liste des accès actuels")
        st.dataframe(df_users, use_container_width=True, hide_index=True)

    # 2. IMPORTATION ET DOUBLONS
    with admin_sub2:
        st.subheader("Importation massive de produits")
        st.info("Le script cherche automatiquement les colonnes 'nom' ou 'Produit'.")
        up_file = st.file_uploader("Déposez votre Excel ou CSV", type=['csv', 'xlsx'])

        if up_file:
            if up_file.name.endswith('.csv'):
                new_data = pd.read_csv(up_file)
            else:
                new_data = pd.read_excel(up_file)
            
            st.write("Aperçu du fichier :")
            st.dataframe(new_data, hide_index=True)

            if st.button("🚀 Lancer l'intégration"):
                # Liste de synonymes pour la colonne nom
                synonymes = ['nom', 'Produit', 'PRODUIT', 'designation', 'DESIGNATION', 'Produits']
                col_nom = next((c for c in synonymes if c in new_data.columns), None)

                if col_nom:
                    # Uniformisation
                    new_data = new_data.rename(columns={col_nom: 'nom'})
                    
                    # Détection doublons
                    exist_list = df_para['nom'].tolist()
                    to_add = new_data[~new_data['nom'].isin(exist_list)].copy()
                    doublons = len(new_data) - len(to_add)
                    
                    if not to_add.empty:
                        # Colonnes manquantes
                        for c in ['id', 'marque', 'explication', 'image_path']:
                            if c not in to_add.columns:
                                to_add[c] = None
                        
                        df_para = pd.concat([df_para, to_add[['id', 'nom', 'marque', 'explication', 'image_path']]], ignore_index=True)
                        save_data(df_para, DB_PATH)
                        st.success(f"✅ {len(to_add)} produits ajoutés !")
                    
                    if doublons > 0:
                        st.warning(f"⚠️ {doublons} doublons ignorés.")
                    st.rerun()
                else:
                    st.error(f"Erreur : Impossible de trouver une colonne 'Produit' ou 'nom'. Colonnes présentes : {list(new_data.columns)}")

    # 3. ASSOCIATION D'IMAGES
    with admin_sub3:
        st.subheader("Lier une image à un produit")
        if df_para.empty:
            st.warning("La base est vide. Importez des produits d'abord.")
        else:
            selected_prod = st.selectbox("Sélectionnez le produit à illustrer", options=df_para['nom'].unique())
            up_img = st.file_uploader("Choisir une photo", type=['jpg', 'jpeg', 'png'])
            
            if st.button("💾 Enregistrer l'image"):
                if up_img:
                    # On crée un nom de fichier propre basé sur le nom du produit
                    clean_name = "".join([c if c.isalnum() else "_" for c in selected_prod])
                    file_ext = up_img.name.split('.')[-1]
                    final_path = os.path.join(IMG_DIR, f"{clean_name}.{file_ext}")
                    
                    with open(final_path, "wb") as f:
                        f.write(up_img.getbuffer())
                    
                    # Mise à jour CSV
                    df_para.loc[df_para['nom'] == selected_prod, 'image_path'] = final_path
                    save_data(df_para, DB_PATH)
                    st.success(f"Image liée à : {selected_prod}")
                    st.rerun()
                else:
                    st.error("Veuillez sélectionner un fichier image.")
            
            st.divider()
            st.write("### Aperçu des images déjà liées")
            st.dataframe(df_para[df_para['image_path'].notna()][['nom', 'image_path']], hide_index=True)
