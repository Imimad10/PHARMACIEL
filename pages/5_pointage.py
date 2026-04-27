import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
from datetime import datetime

# --- CONFIGURATION ET BASE DE DONNÉES ---
# st.set_page_config(page_title="Pharmaciel Pro - Pointage", layout="wide", page_icon="🚚")

# Initialisation de la base de données locale
db = TinyDB('db_pharmaciel.json')
table_livreurs = db.table('livreurs')
table_pointage = db.table('pointages')

# --- FONCTIONS DE GESTION ---
def ajouter_livreur(nom):
    if not table_livreurs.search(Query().nom == nom):
        table_livreurs.insert({'nom': nom})
        return True
    return False

def get_livreurs():
    return [item['nom'] for item in table_livreurs.all()]

# --- INTERFACE SIDEBAR ---
st.sidebar.title("📦 Pharmaciel Pro")
menu = st.sidebar.radio("Navigation", ["Pointage Factures", "Administration"])

# --- ONGLET ADMINISTRATION ---
if menu == "Administration":
    st.header("⚙️ Gestion des Livreurs")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ajouter un agent")
        nouveau_nom = st.text_input("Nom du livreur (ex: Fares, Ayoub...)")
        if st.button("Enregistrer le livreur"):
            if nouveau_nom:
                if ajouter_livreur(nouveau_nom.strip().upper()):
                    st.success(f"Livreur {nouveau_nom} ajouté !")
                    st.rerun()
                else:
                    st.warning("Ce livreur existe déjà.")
    
    with col2:
        st.subheader("Équipe actuelle")
        livreurs = get_livreurs()
        if livreurs:
            for l in livreurs:
                st.text(f"• {l}")
        else:
            st.info("Aucun livreur enregistré.")

# --- ONGLET POINTAGE ---
elif menu == "Pointage Factures":
    st.header("📝 Pointage des Factures")

    # 1. Importation du fichier Excel
    uploaded_file = st.file_uploader("Importer l'export LogiPharm (Excel)", type=['xlsx'])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Correction des colonnes : on s'adapte à votre export (Client, Référence, Région)
            cols_attendues = ['Client', 'Référence', 'Région']
            
            if all(c in df.columns for c in cols_attendues):
                df_clean = df[cols_attendues].copy()
                
                # --- FILTRES ---
                col_a, col_b = st.columns(2)
                
                with col_a:
                    liste_regions = sorted(df_clean['Région'].dropna().unique())
                    region_sel = st.selectbox("📍 Sélectionner la Région", liste_regions)
                
                with col_b:
                    liste_livreurs = get_livreurs()
                    if not liste_livreurs:
                        st.error("⚠️ Allez dans 'Administration' pour ajouter des livreurs d'abord.")
                        livreur_sel = None
                    else:
                        livreur_sel = st.selectbox("🚚 Affecter au Livreur", liste_livreurs)

                if livreur_sel:
                    # Filtrage des données selon la région choisie
                    df_filtre = df_clean[df_clean['Région'] == region_sel].copy()
                    df_filtre.insert(0, "Reçu", False) # Ajout de la case à cocher au début

                    st.divider()
                    st.subheader(f"Factures à pointer pour : {region_sel}")
                    
                    # 2. Éditeur de données interactif
                    edited_df = st.data_editor(
                        df_filtre,
                        column_config={
                            "Reçu": st.column_config.CheckboxColumn("Validé", default=False),
                            "Référence": st.column_config.TextColumn("N° Facture", disabled=True),
                            "Client": st.column_config.TextColumn("Nom du Client", disabled=True),
                            "Région": st.column_config.TextColumn("Zone", disabled=True)
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    # 3. Bouton d'enregistrement
                    if st.button("Confirmer le pointage"):
                        factures_ok = edited_df[edited_df['Reçu'] == True]
                        
                        if not factures_ok.empty:
                            for _, row in factures_ok.iterrows():
                                table_pointage.insert({
                                    'date_pointage': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    'livreur': livreur_sel,
                                    'reference': row['Référence'],
                                    'client': row['Client'],
                                    'region': row['Région']
                                })
                            st.success(f"✅ {len(factures_ok)} factures pointées avec succès pour {livreur_sel} !")
                        else:
                            st.warning("Veuillez cocher au moins une facture avant de valider.")
            else:
                st.error(f"Erreur de colonnes. Votre fichier contient : {list(df.columns)}")
                st.info("Le fichier doit contenir exactement : Client, Référence, Région")
                
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

# --- HISTORIQUE (EN BAS DE PAGE) ---
if st.sidebar.checkbox("Afficher l'historique"):
    st.divider()
    st.subheader("📊 Historique des derniers pointages")
    data_hist = table_pointage.all()
    if data_hist:
        df_hist = pd.DataFrame(data_hist)
        st.dataframe(df_hist.tail(20), use_container_width=True)
    else:
        st.write("Aucun historique pour le moment.")
