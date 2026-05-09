import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
from PIL import Image
from utils import log_action
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from generator_pdf import generate_reclam_pdf

# --- CONFIGURATION ---
WORKSHEET_NAME = "Litiges"
FALLBACK_PATH = 'data/data_litiges.csv'
PHOTO_DIR = 'data/photos_litiges/'
os.makedirs(PHOTO_DIR, exist_ok=True)

COLUMNS = ["Date", "Heure", "Facture", "Fournisseur", "Agent", "Produit", "Lot", "Quantite", "Type", "Priorite", "Statut", "Commentaire", "Photo_Path", "Date_Resolution"]

st.set_page_config(page_title="Litiges Fournisseurs", layout="wide", page_icon="📦")
show_sync_ui(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

# --- CHARGEMENT DES DONNÉES ---
df_litiges = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

def get_delay(start_date, end_date):
    try:
        if not end_date or end_date == "None":
            end_date = datetime.now().strftime("%Y-%m-%d")
        d1 = datetime.strptime(str(start_date), "%Y-%m-%d")
        d2 = datetime.strptime(str(end_date), "%Y-%m-%d")
        return (d2 - d1).days
    except: return 0

st.title("📦 DARPHARM - Gestion des Litiges & Réclamations")
st.write("Système synchronisé pour le suivi des anomalies de réception et litiges fournisseurs.")

tab_new, tab_list, tab_stats, tab_prods = st.tabs(["➕ Nouveau Rapport", "📋 Suivi des Litiges", "📊 Statistiques", "📦 Base Produits"])

# --- CHARGEMENT DYNAMIQUE DES PRODUITS ---
df_prods = load_gs_data("Base_Produits", "data_produits.csv", ["Désignation"])
liste_prods = sorted([str(p).upper().strip() for p in df_prods["Désignation"].unique() if pd.notna(p) and str(p).strip() != ""])

# --- ONGLET 1 : NOUVELLE RÉCLAMATION ---
with tab_new:
    with st.form("form_new_reclam", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fournisseur = st.text_input("Fournisseur / Laboratoire", placeholder="Ex: Sanofi, Biopharm...")
            num_facture = st.text_input("N° Facture / BL")
            
            # Utilisation de la liste déroulante au lieu du champ texte libre
            if liste_prods:
                produit = st.selectbox("Désignation du Produit", options=liste_prods, index=None, placeholder="Rechercher le produit...")
            else:
                produit = st.text_input("Désignation du Produit (Veuillez importer une base)")
                
            lot = st.text_input("N° Lot")
            quantite = st.number_input("Quantité concernée", min_value=1, step=1)
            
        with col2:
            type_litige = st.selectbox("Motif de réclamation", [
                "Manquant", "Produit Cassé", "Périmé / Date courte", 
                "Erreur Prix", "Vignette Abîmée", "Erreur Livraison", "Autre"
            ])
            priorite = st.select_slider("Urgence", options=["Normal", "Important", "Critique"])
            uploaded_photo = st.file_uploader("📸 Photo de preuve (Optionnel)", type=["jpg", "jpeg", "png"])
            commentaire = st.text_area("Observations détaillées")

        if st.form_submit_button("🚀 Enregistrer & Synchroniser"):
            if fournisseur and produit:
                now = datetime.now()
                photo_path = ""
                
                # Sauvegarde de la photo si présente
                if uploaded_photo:
                    photo_filename = f"reclam_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                    photo_path = os.path.join(PHOTO_DIR, photo_filename)
                    img = Image.open(uploaded_photo)
                    img = img.convert('RGB')
                    img.save(photo_path, quality=80)
                
                new_row = {
                    "Date": now.strftime("%Y-%m-%d"),
                    "Heure": now.strftime("%H:%M"),
                    "Facture": num_facture,
                    "Fournisseur": fournisseur.upper(),
                    "Agent": st.session_state.current_user['username'],
                    "Produit": produit.upper(),
                    "Lot": lot,
                    "Quantite": quantite,
                    "Type": type_litige,
                    "Priorite": priorite,
                    "Statut": "En cours",
                    "Commentaire": commentaire,
                    "Photo_Path": photo_path,
                    "Date_Resolution": ""
                }
                
                df_litiges = pd.concat([df_litiges, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
                
                st.success(f"✅ Réclamation enregistrée et synchronisée !")
                log_action(st.session_state.current_user['username'], f"Nouveau Litige: {fournisseur} - {produit}", "Litiges")
                st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires (Fournisseur & Produit).")

# --- ONGLET 2 : LISTE ET PDF ---
with tab_list:
    if df_litiges.empty:
        st.info("Aucun litige enregistré.")
    else:
        # Filtres rapides
        f_fourn = st.text_input("🔍 Rechercher par Fournisseur ou Produit").upper()
        df_view = df_litiges.copy()
        if f_fourn:
            df_view = df_view[df_view['Fournisseur'].str.contains(f_fourn) | df_view['Produit'].str.contains(f_fourn)]
        
        st.write(f"Affichage de **{len(df_view)}** dossiers.")
        
        for i, row in df_view.iterrows():
            with st.expander(f"📄 {row['Date']} - {row['Fournisseur']} - {row['Produit']} ({row['Statut']})"):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.write(f"**Motif:** {row['Type']}")
                    st.write(f"**Facture:** {row['Facture']}")
                    st.write(f"**Lot/Qte:** {row['Lot']} / {row['Quantite']}")
                with c2:
                    st.write(f"**Agent:** {row['Agent']}")
                    st.write(f"**Priorité:** {row['Priorite']}")
                    if row['Photo_Path'] and os.path.exists(row['Photo_Path']):
                        st.image(row['Photo_Path'], width=150)
                with c3:
                    # Bouton Génération PDF
                    pdf_data = {
                        "date": row['Date'],
                        "fournisseur": row['Fournisseur'],
                        "produit": row['Produit'],
                        "lot": row['Lot'],
                        "quantite": row['Quantite'],
                        "type": row['Type'],
                        "agent": row['Agent'],
                        "commentaire": row['Commentaire']
                    }
                    pdf_bytes = generate_reclam_pdf(pdf_data, row['Photo_Path'])
                    st.download_button(
                        label="📥 Télécharger PDF",
                        data=pdf_bytes,
                        file_name=f"Reclam_{row['Fournisseur']}_{row['Date']}.pdf",
                        mime="application/pdf",
                        key=f"btn_pdf_{i}"
                    )
                    
                    if row['Statut'] == "En cours":
                        if st.button("✅ Régler", key=f"btn_regler_{i}"):
                            df_litiges.at[i, 'Statut'] = "Réglée"
                            df_litiges.at[i, 'Date_Resolution'] = datetime.now().strftime("%Y-%m-%d")
                            save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
                            st.success("Dossier clôturé.")
                            st.rerun()

# --- ONGLET 3 : STATS ---
with tab_stats:
    if not df_litiges.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Litiges", len(df_litiges))
        c2.metric("En cours", len(df_litiges[df_litiges['Statut'] == "En cours"]))
        c3.metric("Résolus", len(df_litiges[df_litiges['Statut'] == "Réglée"]))
        
        st.divider()
        st.subheader("Répartition par Motif")
        df_motif = df_litiges['Type'].value_counts().reset_index()
        st.bar_chart(df_motif, x='Type', y='count')

# --- ONGLET 4 : BASE PRODUITS ---
with tab_prods:
    st.subheader("📦 Base de Données des Produits")
    st.write("Importez une liste Excel ou CSV pour mettre à jour les produits disponibles dans le formulaire de litige. Les doublons seront automatiquement ignorés.")
    
    col_up, col_list = st.columns([1, 1])
    with col_up:
        file_up = st.file_uploader("Importer une nouvelle liste de produits", type=["xlsx", "xls", "csv"])
        if file_up:
            if st.button("🚀 Importer et Mettre à jour la Base", type="primary"):
                with st.spinner("Analyse et nettoyage en cours..."):
                    try:
                        if file_up.name.endswith(".csv"):
                            df_new = pd.read_csv(file_up)
                        else:
                            df_new = pd.read_excel(file_up)
                        
                        # 1. Trouver la bonne colonne de désignation
                        prod_col = None
                        for c in df_new.columns:
                            c_low = str(c).lower()
                            if "produit" in c_low or "designation" in c_low or "nom" in c_low:
                                prod_col = c
                                break
                        if not prod_col: prod_col = df_new.columns[0]
                        
                        # 2. Nettoyer et formater les nouveaux produits
                        new_prods = pd.DataFrame({
                            "Désignation": df_new[prod_col].dropna().astype(str).str.upper().str.strip()
                        })
                        
                        # 3. Fusionner avec l'ancienne base sans créer de doublons
                        df_merged = pd.concat([df_prods, new_prods]).drop_duplicates(subset=["Désignation"]).reset_index(drop=True)
                        
                        # Ne garder que ceux qui ne sont pas vides
                        df_merged = df_merged[df_merged["Désignation"] != ""]
                        
                        # 4. Sauvegarder dans la base centrale
                        save_gs_data(df_merged, "Base_Produits", "data_produits.csv")
                        
                        st.success(f"✅ Import réussi ! Vous avez maintenant {len(df_merged)} produits uniques dans la base.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'importation : {e}")

    with col_list:
        st.metric("Total de produits uniques", len(df_prods))
        if not df_prods.empty:
            st.dataframe(df_prods.sort_values("Désignation"), use_container_width=True, hide_index=True)
        else:
            st.info("La base est actuellement vide.")
