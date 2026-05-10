import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Catalogue Produits", layout="wide")

if 'current_user' not in st.session_state:
    st.warning("⚠️ Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

# --- STYLE CSS POUR LES CARTES ---
st.markdown("""
    <style>
    .prod-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        transition: transform 0.2s;
        border-top: 4px solid #1877f2;
    }
    .prod-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    .prod-title {
        color: #1877f2;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 10px;
    }
    .prod-info {
        font-size: 0.9rem;
        color: #444;
        margin-bottom: 5px;
    }
    .prod-img {
        max-height: 150px;
        object-fit: contain;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📚 Catalogue des Produits Pharmaceutiques")
st.write("Ce module vous permet de consulter la liste des médicaments extraits de PharmNet.")

CSV_PATH = "catalogue_pharmnet.csv"

if not os.path.exists(CSV_PATH):
    st.warning("⚠️ La base de données 'catalogue_pharmnet.csv' est introuvable.")
    st.info("💡 Exécutez le script 'scraper_pharmnet.py' sur votre PC pour générer cette base de données avec toutes les images et informations.")
    st.stop()

@st.cache_data(ttl=3600)
def load_catalogue():
    return pd.read_csv(CSV_PATH, encoding='utf-8-sig')

df = load_catalogue()

# --- RECHERCHE ET FILTRES ---
col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
search_q = col_s1.text_input("🔍 Rechercher un produit, DCI, ou Laboratoire...", "")

# Filtres dynamiques selon ce qui existe dans le CSV
if 'Forme' in df.columns:
    formes = ["Toutes"] + sorted(df['Forme'].dropna().unique().tolist())
    f_forme = col_s2.selectbox("Forme", formes)
else:
    f_forme = "Toutes"

if 'Liste' in df.columns:
    listes = ["Toutes"] + sorted(df['Liste'].dropna().unique().tolist())
    f_liste = col_s3.selectbox("Liste", listes)
else:
    f_liste = "Toutes"

# Filtrer
df_filtered = df.copy()
if search_q:
    # Recherche multi-colonnes
    mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)
    df_filtered = df_filtered[mask]
if f_forme != "Toutes":
    df_filtered = df_filtered[df_filtered['Forme'] == f_forme]
if f_liste != "Toutes":
    df_filtered = df_filtered[df_filtered['Liste'] == f_liste]

st.caption(f"{len(df_filtered)} produits trouvés sur {len(df)}")
st.divider()

# --- AFFICHAGE EN GRILLE ---
# On affiche les produits par ligne de 3 ou 4 colonnes
COLS_PER_ROW = 4

# Pagination (pour ne pas crasher si on a 5000 produits)
PAGE_SIZE = 40
if "page_cat" not in st.session_state:
    st.session_state.page_cat = 1

total_pages = (len(df_filtered) // PAGE_SIZE) + 1
page = st.session_state.page_cat

start_idx = (page - 1) * PAGE_SIZE
end_idx = min(start_idx + PAGE_SIZE, len(df_filtered))

display_df = df_filtered.iloc[start_idx:end_idx]

# Boucle d'affichage
rows = [display_df.iloc[i:i+COLS_PER_ROW] for i in range(0, len(display_df), COLS_PER_ROW)]

for row in rows:
    cols = st.columns(COLS_PER_ROW)
    for idx, (_, prod) in enumerate(row.iterrows()):
        with cols[idx]:
            st.markdown(f'<div class="prod-card">', unsafe_allow_html=True)
            
            # Affichage de l'image (si url existe)
            img_url = prod.get('Image', '')
            if pd.notna(img_url) and img_url.startswith("http"):
                st.image(img_url, use_container_width=True)
            else:
                st.image("https://via.placeholder.com/150?text=Pas+d'image", use_container_width=True)
            
            nom = prod.get('Nom Commercial', prod.get('Nom', 'Inconnu'))
            st.markdown(f"<div class='prod-title'>{nom}</div>", unsafe_allow_html=True)
            
            # Détails condensés
            dci = prod.get('Code DCI', '')
            if pd.notna(dci): st.markdown(f"<div class='prod-info'><b>DCI:</b> {dci}</div>", unsafe_allow_html=True)
            
            dosage = prod.get('Dosage', '')
            if pd.notna(dosage): st.markdown(f"<div class='prod-info'><b>Dosage:</b> {dosage}</div>", unsafe_allow_html=True)
            
            ppa = prod.get('PPA', '')
            if pd.notna(ppa): st.markdown(f"<div class='prod-info'><b>PPA:</b> <span style='color:#e74c3c;font-weight:bold;'>{ppa}</span></div>", unsafe_allow_html=True)
            
            with st.expander("Plus de détails"):
                for col_name in ['Forme', 'Conditionnement', 'Type', 'Liste', 'Pays', 'Tarif de référence']:
                    if col_name in prod and pd.notna(prod[col_name]):
                        st.write(f"**{col_name}:** {prod[col_name]}")
            
            st.markdown('</div>', unsafe_allow_html=True)

# Boutons de pagination
st.divider()
c_prev, c_page, c_next = st.columns([1, 2, 1])
if c_prev.button("⬅️ Précédent", disabled=(page == 1)):
    st.session_state.page_cat -= 1
    st.rerun()

c_page.markdown(f"<h4 style='text-align:center;'>Page {page} / {total_pages}</h4>", unsafe_allow_html=True)

if c_next.button("Suivant ➡️", disabled=(page == total_pages)):
    st.session_state.page_cat += 1
    st.rerun()
