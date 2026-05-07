import streamlit as st
import pandas as pd
from datetime import datetime
from tinydb import TinyDB, Query
import os
from utils import log_action

# --- CONFIGURATION ---
DB_PATH = 'data/db_reclam_fourn.json'
os.makedirs('data', exist_ok=True)
db = TinyDB(DB_PATH)
Reclam = Query()

st.set_page_config(page_title="Litiges Fournisseurs", layout="wide")

def get_delay(start_date, end_date):
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    d1 = datetime.strptime(start_date, "%Y-%m-%d")
    d2 = datetime.strptime(end_date, "%Y-%m-%d")
    return (d2 - d1).days

st.title("📦 Suivi des Litiges Fournisseurs & Labos")
st.write("Gérez les anomalies de réception (manquants, cassés, erreurs vignettes) et suivez les délais de résolution.")

tab_new, tab_list, tab_stats, tab_admin = st.tabs(["➕ Nouvelle Réclamation", "📋 Liste des Litiges", "📊 Statistiques & Délais", "⚙️ Administration"])

# --- CHARGEMENT DE LA BASE PRODUITS ---
DB_PRODUITS = 'data/db_produits.json'
db_p = TinyDB(DB_PRODUITS)

def load_product_list():
    prods = db_p.all()
    return sorted([p['designation'] for p in prods]) if prods else []

# --- ONGLET 1 : NOUVELLE RÉCLAMATION ---
with tab_new:
    product_list = load_product_list()
    
    with st.form("form_new_reclam", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fournisseur = st.text_input("Nom du Fournisseur / Laboratoire", placeholder="Ex: Sanofi, Biopharm...")
            
            if product_list:
                produit = st.selectbox("Désignation du Produit", product_list, index=None, placeholder="Rechercher un produit...")
            else:
                produit = st.text_input("Désignation du Produit (Base vide, saisie manuelle)")
                
            lot = st.text_input("N° Lot")
            quantite = st.number_input("Quantité concernée", min_value=1, step=1)
            
        with col2:
            type_litige = st.selectbox("Type d'anomalie", [
                "Produit Manquant", 
                "Produit Abîmé / Cassé", 
                "Vignette Abîmée", 
                "Sans Vignette", 
                "Erreur N° Lot", 
                "Erreur PPA / Prix",
                "Date de Péremption Courte",
                "Autre"
            ])
            date_lancement = st.date_input("Date de lancement de la réclamation", value=datetime.now())
            priorite = st.select_slider("Niveau d'Urgence", options=["Normal", "Important", "Critique"])
            commentaire = st.text_area("Détails supplémentaires")

        if st.form_submit_button("🚀 Enregistrer la Réclamation"):
            if fournisseur and produit:
                db.insert({
                    "fournisseur": fournisseur.upper(),
                    "produit": produit.upper(),
                    "lot": lot,
                    "quantite": quantite,
                    "type": type_litige,
                    "date_lancement": str(date_lancement),
                    "date_resolution": None,
                    "priorite": priorite,
                    "statut": "En cours",
                    "commentaire": commentaire,
                    "agent": st.session_state.current_user['username']
                })
                st.success(f"Réclamation enregistrée pour {fournisseur} !")
                log_action(st.session_state.current_user['username'], f"Litige Fournisseur : {fournisseur} - {produit}", "Réclamations")
                st.rerun()
            else:
                st.error("Veuillez remplir au moins le nom du fournisseur et du produit.")

# --- ONGLET 2 : LISTE DES LITIGES ---
with tab_list:
    reclams = db.all()
    if not reclams:
        st.info("Aucune réclamation enregistrée pour le moment.")
    else:
        df = pd.DataFrame(reclams)
        
        # Filtres
        c1, c2 = st.columns(2)
        f_statut = c1.selectbox("Filtrer par statut", ["Tous", "En cours", "Réglée"])
        f_fourn = c2.text_input("Rechercher un fournisseur")
        
        if f_statut != "Tous":
            df = df[df['statut'] == f_statut]
        if f_fourn:
            df = df[df['fournisseur'].str.contains(f_fourn.upper())]
            
        st.write(f"Affichage de **{len(df)}** litiges.")
        
        # Calcul du délai actuel pour l'affichage
        df['Délai (jours)'] = df.apply(lambda row: get_delay(row['date_lancement'], row['date_resolution']), axis=1)
        
        # Édition du statut
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            column_config={
                "statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Réglée"]),
                "date_resolution": st.column_config.DateColumn("Date de Résolution"),
                "date_lancement": st.column_config.DateColumn("Date Lancement", disabled=True),
                "priorite": st.column_config.SelectboxColumn("Urgence", options=["Normal", "Important", "Critique"])
            },
            hide_index=True
        )
        
        if st.button("💾 Mettre à jour les litiges"):
            # On met à jour la base
            for _, row in edited_df.iterrows():
                # Si le statut passe à réglée et que la date n'est pas mise, on met la date du jour
                new_statut = row['statut']
                res_date = row['date_resolution']
                if new_statut == "Réglée" and not res_date:
                    res_date = datetime.now().strftime("%Y-%m-%d")
                
                db.update({
                    "statut": new_statut,
                    "date_resolution": str(res_date) if res_date else None,
                    "priorite": row['priorite'],
                    "commentaire": row['commentaire']
                }, (Reclam.fournisseur == row['fournisseur']) & (Reclam.produit == row['produit']) & (Reclam.date_lancement == row['date_lancement']))
            
            st.success("Mise à jour réussie !")
            st.rerun()

# --- ONGLET 3 : STATISTIQUES ---
with tab_stats:
    if reclams:
        df_stats = pd.DataFrame(reclams)
        df_stats['Délai'] = df_stats.apply(lambda row: get_delay(row['date_lancement'], row['date_resolution']), axis=1)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_delay = df_stats[df_stats['statut'] == 'Réglée']['Délai'].mean()
            st.metric("Délai Moyen de Résolution", f"{avg_delay:.1f} Jours" if pd.notna(avg_delay) else "N/A")
            
        with col2:
            top_fourn = df_stats['fournisseur'].value_counts().idxmax()
            st.metric("Fournisseur le plus litigieux", top_fourn)
            
        with col3:
            en_cours = len(df_stats[df_stats['statut'] == 'En cours'])
            st.metric("Litiges en attente", en_cours)
            
        st.divider()
        st.subheader("📊 Répartition par Type d'Anomalie")
        df_type = df_stats['type'].value_counts().reset_index()
        import plotly.express as px
        fig = px.pie(df_type, values='count', names='type', hole=0.3, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas assez de données pour les statistiques.")

# --- ONGLET 4 : ADMINISTRATION ---
with tab_admin:
    st.header("⚙️ Maintenance & Base de Données")
    st.write("Importez ici votre liste de produits pour faciliter la saisie des réclamations.")
    
    uploaded_file = st.file_uploader("Déposer le fichier Excel des produits (Colonnes : designation)", type=["xlsx"])
    
    if uploaded_file:
        try:
            df_p = pd.read_excel(uploaded_file)
            if 'designation' in df_p.columns:
                if st.button("🚀 Valider l'importation de la base produits"):
                    db_p.truncate() # On remplace l'ancienne base
                    records = df_p[['designation']].dropna().to_dict('records')
                    db_p.insert_multiple(records)
                    st.success(f"Base de données mise à jour : {len(records)} produits importés.")
                    st.rerun()
            else:
                st.error("Le fichier doit contenir une colonne nommée 'designation'.")
                st.write("Colonnes trouvées :", list(df_p.columns))
        except Exception as e:
            st.error(f"Erreur lors de l'import : {e}")

    st.divider()
    if st.button("🗑️ Vider la base produits actuelle"):
        db_p.truncate()
        st.success("Base de produits vidée.")
        st.rerun()
