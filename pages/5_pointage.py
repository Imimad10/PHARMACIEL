import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
from datetime import datetime
import os
from utils import log_action

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
            
            # Correction des colonnes : on s'adapte à votre export (Client, Référence, Région, Date Création)
            cols_attendues = ['Client', 'Référence', 'Région', 'Date Création']
            
            if all(c in df.columns for c in cols_attendues):
                df_clean = df[cols_attendues].copy()
                
                # --- FILTRES ---
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    liste_regions = sorted(df_clean['Région'].dropna().unique())
                    region_sel = st.selectbox("📍 Sélectionner la Région (Secteur)", liste_regions)
                
                with col_b:
                    reg_str = str(region_sel).lower()
                    opts_rotation = ["1ère Rotation (Matin)", "2ème Rotation (Après-midi)"]
                    
                    if "blida" in reg_str:
                        opts_rotation = ["2ème Rotation (Après-midi)"]
                    elif any(r in reg_str for r in ["alger est", "tipaza", "medea", "chlef", "djelfa", "oran", "tizi ouzou", "tissemssilt", "relizane"]):
                        opts_rotation = ["1ère Rotation (Matin)"]
                        
                    rotation_sel = st.selectbox("🔄 Rotation", opts_rotation)
                    
                    # Filtre de date et heure pour la rotation
                    st.write("📅 Période de préparation :")
                    
                    # Date de préparation (par défaut aujourd'hui)
                    default_date = datetime.now().date()
                    d_sel = st.date_input("Date", value=default_date)
                    
                    time_filter_active = False
                    if "1ère Rotation" in rotation_sel:
                        tc1, tc2 = st.columns(2)
                        with tc1:
                            t_start = st.time_input("Début", value=datetime.strptime("00:00", "%H:%M").time(), key="t1")
                        with tc2:
                            t_end = st.time_input("Fin", value=datetime.strptime("23:59", "%H:%M").time(), key="t2")
                        time_filter_active = True
                    else:
                        # Pour la 2ème rotation, on peut aussi mettre un filtre par défaut ou laisser libre
                        t_start, t_end = None, None

                with col_c:
                    liste_livreurs = get_livreurs()
                    if not liste_livreurs:
                        st.error("⚠️ Allez dans 'Administration' pour ajouter des livreurs d'abord.")
                        livreur_sel = None
                    else:
                        # Auto-sélection du livreur
                        idx_livreur = 0
                        if "alger 1" in reg_str:
                            match = [i for i, l in enumerate(liste_livreurs) if "fethi" in l.lower()]
                            if match: idx_livreur = match[0]
                        elif "alger 2" in reg_str:
                            match = [i for i, l in enumerate(liste_livreurs) if "fares" in l.lower()]
                            if match: idx_livreur = match[0]
                            
                        livreur_sel = st.selectbox("🚚 Affecter au Livreur", liste_livreurs, index=idx_livreur)

                if livreur_sel:
                    # --- LOGIQUE DE FILTRAGE ---
                    df_filtre = df_clean[df_clean['Région'] == region_sel].copy()
                    
                    # Conversion en datetime
                    df_filtre['dt_creation'] = pd.to_datetime(df_filtre['Date Création'], dayfirst=True)
                    
                    # Filtre de Date obligatoire
                    df_filtre = df_filtre[df_filtre['dt_creation'].dt.date == d_sel]
                    
                    # Filtre d'Heure (si applicable)
                    if time_filter_active:
                        df_filtre = df_filtre[
                            (df_filtre['dt_creation'].dt.time >= t_start) & 
                            (df_filtre['dt_creation'].dt.time <= t_end)
                        ]

                    # --- AFFICHAGE POUR IMPRESSION ---
                    st.divider()
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;">
                        <h1 style="margin: 0; color: #1f1f1f;">Livreur : <span style="color: #ff4b4b;">{livreur_sel}</span></h1>
                        <h2 style="margin: 5px 0 0 0; color: #555;">Secteur : {region_sel} | {rotation_sel}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    st.subheader(f"📊 Liste des Factures ({len(df_filtre)})")
                    
                    # Ajout de la case OK pour l'impression et de la validation
                    df_view = df_filtre.copy()
                    df_view.insert(0, "OK", "[  ]") # Case pour cocher manuellement après impression
                    df_view.insert(1, "Validé", False) # Case à cocher pour le système
                    
                    # 2. Éditeur de données interactif
                    edited_df = st.data_editor(
                        df_view,
                        column_config={
                            "OK": st.column_config.TextColumn("Pointage Manuel", width="small", disabled=True),
                            "Validé": st.column_config.CheckboxColumn("Système", default=False),
                            "Référence": st.column_config.TextColumn("N° Facture", disabled=True),
                            "Client": st.column_config.TextColumn("Nom du Client", disabled=True),
                            "Date Création": st.column_config.TextColumn("Préparée le", disabled=True),
                            "Région": None # Cacher car déjà en titre
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    # 3. Bouton d'enregistrement
                    if st.button("Confirmer le pointage"):
                        factures_ok = edited_df[edited_df['Validé'] == True]
                        
                        if not factures_ok.empty:
                            new_recouv_rows = []
                            for _, row in factures_ok.iterrows():
                                table_pointage.insert({
                                    'date_pointage': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    'livreur': livreur_sel,
                                    'rotation': rotation_sel,
                                    'reference': row['Référence'],
                                    'client': row['Client'],
                                    'region': row['Région']
                                })
                                
                                # Préparation des données pour le module Recouvrement
                                new_recouv_rows.append({
                                    "Client": row['Client'],
                                    "Facture": row['Référence'],
                                    "Mode Paiement": "À Définir",
                                    "Région": row['Région'],
                                    "Reste à payer": 0.0,
                                    "Livreur": livreur_sel,
                                    "Date": datetime.now().strftime("%d/%m/%Y"),
                                    "Statut": "Non Payé"
                                })
                            
                            # Insertion dans Recouvrement
                            recouv_file = "data_recouvrement.csv"
                            if os.path.exists(recouv_file):
                                df_recouv = pd.read_csv(recouv_file)
                                # S'assurer que la colonne Facture existe
                                if "Facture" not in df_recouv.columns:
                                    df_recouv["Facture"] = ""
                            else:
                                df_recouv = pd.DataFrame(columns=["Client", "Facture", "Mode Paiement", "Région", "Reste à payer", "Livreur", "Date", "Statut"])
                                
                            df_new_recouv = pd.DataFrame(new_recouv_rows)
                            df_recouv = pd.concat([df_recouv, df_new_recouv], ignore_index=True)
                            df_recouv.to_csv(recouv_file, index=False)
                            
                            log_action(st.session_state.current_user['username'], f"Pointage de {len(factures_ok)} factures ({livreur_sel})", "Pointage")
                            st.success(f"✅ {len(factures_ok)} factures pointées avec succès et transférées au Recouvrement !")
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
