import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_pdf import generate_reception_pdf

# --- CONFIGURATION ---
DB_RECEPTIONS = "data/db_receptions.csv"
COLS_RECEPTIONS = ["id", "date", "fournisseur", "facture_num", "statut", "items", "created_by"]

CATALOGUE_PATH = "catalogue_pharmnet.csv"

def load_catalogue():
    if os.path.exists(CATALOGUE_PATH):
        try:
            df = pd.read_csv(CATALOGUE_PATH, encoding='utf-8-sig')
        except:
            try:
                df = pd.read_csv(CATALOGUE_PATH, encoding='latin-1')
            except:
                df = pd.read_csv(CATALOGUE_PATH)
        
        # Nettoyage des noms de colonnes (espaces invisibles)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    return pd.DataFrame(columns=["Nom Commercial", "PPA", "Tarif de référence"])

def save_reception(reception_data):
    df_old = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    
    # Generate ID if new
    if not reception_data.get('id'):
        reception_data['id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Check if update or new
    if reception_data['id'] in df_old['id'].astype(str).values:
        df_old.loc[df_old['id'].astype(str) == str(reception_data['id']), :] = [
            reception_data['id'],
            reception_data['date'],
            reception_data['fournisseur'],
            reception_data['facture_num'],
            reception_data['statut'],
            json.dumps(reception_data['items']),
            reception_data['created_by']
        ]
    else:
        new_row = pd.DataFrame([{
            "id": reception_data['id'],
            "date": reception_data['date'],
            "fournisseur": reception_data['fournisseur'],
            "facture_num": reception_data['facture_num'],
            "statut": reception_data['statut'],
            "items": json.dumps(reception_data['items']),
            "created_by": reception_data['created_by']
        }])
        df_old = pd.concat([df_old, new_row], ignore_index=True)
    
    save_gs_data(df_old, "Receptions", DB_RECEPTIONS)

# --- UI ---
st.title("📦 Pointage de Marchandise & Réception")

if "current_reception" not in st.session_state:
    st.session_state.current_reception = {
        "id": None,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "fournisseur": "",
        "facture_num": "",
        "statut": "En cours",
        "items": [],
        "created_by": st.session_state.current_user['username']
    }

tabs = st.tabs(["⚡ Nouvelle Réception", "📋 Historique & Suivi", "🏛️ Administration"])

# --- ONGLET 1 : NOUVELLE RÉCEPTION ---
with tabs[0]:
    # Entête
    with st.expander("📝 Informations de la Facture", expanded=True):
        col_h1, col_h2, col_h3 = st.columns(3)
        st.session_state.current_reception['date'] = col_h1.date_input("Date Réception", value=datetime.strptime(st.session_state.current_reception['date'], "%Y-%m-%d")).strftime("%Y-%m-%d")
        st.session_state.current_reception['fournisseur'] = col_h2.text_input("Fournisseur", value=st.session_state.current_reception['fournisseur'])
        st.session_state.current_reception['facture_num'] = col_h3.text_input("N° Facture / BL", value=st.session_state.current_reception['facture_num'])

    st.divider()

    # Formulaire d'ajout de produit
    st.subheader("🔍 Ajouter un Produit")
    df_cat = load_catalogue()
    
    # Barre de recherche intelligente
    col_name = "Nom Commercial" if "Nom Commercial" in df_cat.columns else ("Nom" if "Nom" in df_cat.columns else None)
    
    search_list = []
    if col_name and not df_cat.empty:
        search_list = df_cat[col_name].dropna().unique().tolist()
    
    selected_prod_name = st.selectbox("Sélectionner un produit (Tapez pour chercher)", [""] + search_list, index=0)

    if selected_prod_name and col_name:
        prod_info = df_cat[df_cat[col_name] == selected_prod_name].iloc[0]
        
        with st.form("form_add_item", clear_on_submit=True):
            st.info(f"Produit sélectionné : **{selected_prod_name}**")
            c1, c2, c3 = st.columns(3)
            qte = c1.number_input("Quantité reçue", min_value=1, step=1)
            lot = c2.text_input("Numéro de Lot", placeholder="Ex: AX123")
            ddp = c3.text_input("DDP (Péremption)", placeholder="MM/AAAA")
            
            c4, c5, c6 = st.columns(3)
            ppa = c4.number_input("PPA (Public)", value=float(str(prod_info.get('PPA', 0)).replace(',','.') if pd.notna(prod_info.get('PPA')) else 0))
            shp = c5.number_input("SHP (Achat)", value=float(str(prod_info.get('Tarif de référence', 0)).replace(',','.') if pd.notna(prod_info.get('Tarif de référence')) else 0))
            colissage = c6.number_input("Colissage (U/Colis)", min_value=1, value=1)
            
            if st.form_submit_button("➕ Ajouter au pointage", use_container_width=True):
                new_item = {
                    "produit": selected_prod_name,
                    "lot": lot.upper(),
                    "ddp": ddp,
                    "qte": qte,
                    "ppa": ppa,
                    "shp": shp,
                    "colissage": colissage,
                    "total_colis": qte / colissage if colissage > 0 else 0
                }
                st.session_state.current_reception['items'].append(new_item)
                st.success(f"Ajouté : {selected_prod_name}")
                st.rerun()

    # Tableau du pointage en cours
    if st.session_state.current_reception['items']:
        st.divider()
        st.subheader("📋 Liste des produits pointés")
        df_items = pd.DataFrame(st.session_state.current_reception['items'])
        
        # Affichage avec possibilité de supprimer
        for i, item in enumerate(st.session_state.current_reception['items']):
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1, 0.5])
            col1.write(f"**{item['produit']}**")
            col2.write(f"Lot: {item['lot']} | DDP: {item['ddp']}")
            col3.write(f"Qte: {item['qte']} ({item['total_colis']:.1f} Colis)")
            col4.write(f"{item['ppa']} DA")
            if col5.button("🗑️", key=f"del_{i}"):
                st.session_state.current_reception['items'].pop(i)
                st.rerun()
        
        st.divider()
        c_save, c_pdf, c_reset = st.columns(3)
        
        if c_save.button("💾 Clôturer la Réception", type="primary", use_container_width=True):
            st.session_state.current_reception['statut'] = "Terminée"
            save_reception(st.session_state.current_reception)
            st.success("✅ Réception enregistrée et clôturée !")
            # Reset
            st.session_state.current_reception = {
                "id": None,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "fournisseur": "",
                "facture_num": "",
                "statut": "En cours",
                "items": [],
                "created_by": st.session_state.current_user['username']
            }
            st.rerun()

        if c_pdf.button("📄 Exporter PDF", use_container_width=True):
            if st.session_state.current_reception['items']:
                pdf_data = generate_reception_pdf(st.session_state.current_reception)
                st.download_button(
                    label="📥 Télécharger le PDF",
                    data=pdf_data,
                    file_name=f"Reception_{st.session_state.current_reception['fournisseur']}_{st.session_state.current_reception['facture_num']}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("Aucun produit à exporter.")

        if c_reset.button("⚠️ Tout effacer", use_container_width=True):
            st.session_state.current_reception['items'] = []
            st.rerun()

# --- ONGLET 2 : HISTORIQUE & SUIVI ---
with tabs[1]:
    st.subheader("📊 Suivi des Réceptions")
    df_rec = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    
    if not df_rec.empty:
        # Filtres
        col_f1, col_f2 = st.columns(2)
        f_statut = col_f1.multiselect("Statut", ["En cours", "Terminée"], default=["En cours", "Terminée"])
        f_fourn = col_f2.text_input("Filtrer par Fournisseur")
        
        mask = df_rec['statut'].isin(f_statut)
        if f_fourn:
            mask &= df_rec['fournisseur'].str.contains(f_fourn, case=False)
        
        df_disp = df_rec[mask].sort_values("date", ascending=False)
        
        for idx, row in df_disp.iterrows():
            with st.expander(f"📅 {row['date']} | {row['fournisseur']} | Facture: {row['facture_num']} ({row['statut']})"):
                items = json.loads(row['items'])
                st.write(f"Saisie par : **{row['created_by']}**")
                st.dataframe(pd.DataFrame(items), use_container_width=True)
                
                c_edit, c_del = st.columns(2)
                if c_edit.button("✏️ Reprendre / Modifier", key=f"edit_rec_{row['id']}"):
                    st.session_state.current_reception = {
                        "id": row['id'],
                        "date": row['date'],
                        "fournisseur": row['fournisseur'],
                        "facture_num": row['facture_num'],
                        "statut": "En cours",
                        "items": items,
                        "created_by": row['created_by']
                    }
                    st.success("Réception chargée dans l'onglet principal !")
                    st.rerun()
                
                if c_del.button("🗑️ Supprimer l'archive", key=f"del_rec_{row['id']}"):
                    df_rec = df_rec.drop(idx)
                    save_gs_data(df_rec, "Receptions", DB_RECEPTIONS)
                    st.rerun()
    else:
        st.info("Aucune réception enregistrée.")

# --- ONGLET 3 : ADMINISTRATION ---
with tabs[2]:
    st.subheader("🏛️ Gestion des données de réception")
    show_sync_ui("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    
    st.divider()
    st.markdown("### 📥 Mise à jour du catalogue produits")
    st.info("Déposez ici votre fichier 'catalogue_pharmnet.csv' mis à jour ou un Excel pour actualiser la liste des produits disponibles au pointage.")
    
    up_cat = st.file_uploader("Fichier Catalogue (CSV ou Excel)", type=["csv", "xlsx"])
    if up_cat:
        if up_cat.name.endswith('.xlsx'):
            df_new_cat = pd.read_excel(up_cat)
        else:
            df_new_cat = pd.read_csv(up_cat)
        
        st.dataframe(df_new_cat.head())
        if st.button("💾 Remplacer le catalogue actuel"):
            df_new_cat.to_csv(CATALOGUE_PATH, index=False, encoding='utf-8-sig')
            st.success("Catalogue mis à jour !")
            st.rerun()
