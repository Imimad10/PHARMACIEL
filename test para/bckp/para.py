import streamlit as st
import pandas as pd
import os
import urllib.parse
import base64

# --- CONFIGURATION ---
st.set_page_config(page_title="Pharmaciel - Gestion Para", layout="wide")

# --- FICHIERS ET DOSSIERS ---
DB_PATH = 'database_para.csv'
USERS_PATH = 'users.csv'
IMG_DIR = 'images_stock'
if not os.path.exists(IMG_DIR): 
    os.makedirs(IMG_DIR)

# --- FONCTION UTILITAIRE : IMAGE VERS BASE64 ---
def get_image_base64(path):
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpeg;base64,{encoded_string}"

# --- STYLE CSS (AVEC EFFET ZOOM) ---
st.markdown("""
    <style>
    .product-img {
        width: 100%;
        height: 200px;
        object-fit: contain;
        background-color: #f9f9f9;
        border-radius: 10px;
        transition: transform 0.3s ease;
    }
    .product-img:hover {
        transform: scale(1.05);
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CHARGEMENT ---
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

with tab_cat:
    st.title("🌿 Référentiel Parapharmacie")
    search = st.text_input("🔍 Rechercher un produit...")
    display_df = df_para.copy().fillna("")
    if search:
        display_df = display_df[display_df['nom'].str.contains(search, case=False, na=False)]
    
    if display_df.empty:
        st.info("Aucun produit trouvé.")
    else:
        for i in range(0, len(display_df), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(display_df):
                    row = display_df.iloc[i + j]
                    with cols[j]:
                        raw_path = row['image_path']
                        # Déterminer la source de l'image (Locale ou Web)
                        if os.path.exists(raw_path):
                            img_src = get_image_base64(raw_path)
                        elif raw_path != "":
                            img_src = raw_path
                        else:
                            img_src = "https://via.placeholder.com/200"
                        
                        # Affichage avec classe CSS
                        st.markdown(f'<img src="{img_src}" class="product-img">', unsafe_allow_html=True)
                        st.caption(row['nom'][:50])

with tab_admin:
    st.title("⚙️ Administration")
    sub_user, sub_import, sub_val = st.tabs(["👥 Utilisateurs", "📥 Importation", "🖼️ Validation Images"])

    with sub_user:
        st.subheader("Gestion des accès")
        with st.form("u_form", clear_on_submit=True):
            un = st.text_input("Nom de l'agent")
            ur = st.selectbox("Rôle", ["admin", "preparateur", "commercial"])
            if st.form_submit_button("Ajouter"):
                new_u = pd.DataFrame([[un, ur]], columns=['username', 'role'])
                df_users = pd.concat([df_users, new_u], ignore_index=True)
                save_data(df_users, USERS_PATH)
                st.success("Ajouté."); st.rerun()
        st.dataframe(df_users, use_container_width=True)

    with sub_import:
        st.subheader("Importation Excel / CSV")
        up_file = st.file_uploader("Fichier produits", type=['csv', 'xlsx'])
        if up_file:
            data = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
            if st.button("🚀 Lancer l'intégration"):
                possibilites = ['Produit', 'nom', 'DESIGNATION', 'NOM']
                col_trouvee = next((c for c in possibilites if c in data.columns), None)
                if col_trouvee:
                    data = data.rename(columns={col_trouvee: 'nom'})
                    nouveaux = data[~data['nom'].astype(str).isin(df_para['nom'].tolist())].copy()
                    df_para = pd.concat([df_para, nouveaux[['nom']]], ignore_index=True)
                    save_data(df_para, DB_PATH)
                    st.success(f"✅ {len(nouveaux)} produits ajoutés !"); st.rerun()

    with sub_val:
        st.subheader("🖼️ Ajout d'images")
        df_missing = df_para[df_para['image_path'].isna() | (df_para['image_path'] == "")]
        
        if not df_missing.empty:
            selected_p = st.selectbox("Produit à illustrer :", df_missing['nom'].unique())
            options_source = ["🌐 Lien Google (Web)", "📂 Ma Galerie / Appareil Photo", "📂 Utiliser une image existante"]
            source = st.radio("Source de l'image :", options_source)
            
            if source == "🌐 Lien Google (Web)":
                clean_name = selected_p.split(" C/")[0].split(" BT")[0]
                google_url = f"https://www.google.com/search?q={urllib.parse.quote(clean_name)}&tbm=isch"
                st.markdown(f"### 1. [Chercher sur Google]({google_url})")
                url_input = st.text_input("Coller l'URL de l'image")
                if st.button("💾 Enregistrer le lien"):
                    if url_input:
                        df_para.loc[df_para['nom'] == selected_p, 'image_path'] = url_input
                        save_data(df_para, DB_PATH)
                        st.success("Lien enregistré !"); st.rerun()

            elif source == "📂 Ma Galerie / Appareil Photo":
                uploaded_img = st.file_uploader("Choisir une image de la galerie", type=['png', 'jpg', 'jpeg'])
                if uploaded_img:
                    st.image(uploaded_img, width=150, caption="Aperçu")
                    if st.button("💾 Télécharger l'image dans le stock"):
                        ext = uploaded_img.name.split('.')[-1]
                        safe_name = "".join(x for x in selected_p[:20] if x.isalnum()) + f".{ext}"
                        img_path = os.path.join(IMG_DIR, safe_name)
                        with open(img_path, "wb") as f:
                            f.write(uploaded_img.getbuffer())
                        df_para.loc[df_para['nom'] == selected_p, 'image_path'] = img_path
                        save_data(df_para, DB_PATH)
                        st.success("Image ajoutée au stock local !"); st.rerun()

            elif source == "📂 Utiliser une image existante":
                files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if not files:
                    st.warning("Le dossier images_stock est vide.")
                else:
                    selected_file = st.selectbox("Choisir une image existante :", files)
                    st.image(os.path.join(IMG_DIR, selected_file), width=150, caption="Aperçu sélectionné")
                    if st.button("💾 Associer cette image"):
                        img_path = os.path.join(IMG_DIR, selected_file)
                        df_para.loc[df_para['nom'] == selected_p, 'image_path'] = img_path
                        save_data(df_para, DB_PATH)
                        st.success("Image associée avec succès !"); st.rerun()
        else:
            st.success("Tout est illustré !")
