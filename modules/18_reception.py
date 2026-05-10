import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_pdf import generate_reception_pdf
from utils_ia import ask_ai_vision, is_ia_enabled
import difflib
import base64
import re

# --- CONFIGURATION ---
DB_RECEPTIONS = "data/db_receptions.csv"
DB_PRODUITS_RECEPTION = "data/db_reception_produits.csv" # Base INDÉPENDANTE
COLS_RECEPTIONS = ["id", "date", "fournisseur", "facture_num", "statut", "items", "created_by"]
COLS_PRODUITS = ["Designation", "PPA", "SHP", "Colissage"] # Colonnes attendues pour cette base

def load_produits_reception():
    if os.path.exists(DB_PRODUITS_RECEPTION):
        try:
            df = pd.read_csv(DB_PRODUITS_RECEPTION, encoding='utf-8-sig')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.read_csv(DB_PRODUITS_RECEPTION)
    return pd.DataFrame(columns=COLS_PRODUITS)

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
    df_prod = load_produits_reception()
    
    # Détection flexible de la colonne de désignation
    col_candidates = ["Designation", "Désignation", "Produit", "Nom", "Nom Commercial"]
    col_name = next((c for c in col_candidates if c in df_prod.columns), None)
    
    search_list = []
    if col_name and not df_prod.empty:
        search_list = sorted(df_prod[col_name].dropna().unique().tolist())
    else:
        # Fallback si rien n'est trouvé : on prend la première colonne
        if not df_prod.empty:
            col_name = df_prod.columns[0]
            search_list = sorted(df_prod[col_name].dropna().unique().tolist())
            
    # --- AI VISION SCANNER ---
    if is_ia_enabled():
        with st.expander("📷 Scanner la marchandise avec l'IA", expanded=False):
            c_img1, c_img2 = st.columns(2)
            img_cam = c_img1.camera_input("Prendre une photo du produit")
            img_file = c_img2.file_uploader("Ou importer une image", type=['jpg', 'jpeg', 'png'], key="file_up_rec")
            img_to_use = img_cam if img_cam else img_file
            
            if img_to_use and st.button("🔍 Identifier et Extraire", use_container_width=True, type="primary"):
                base64_img = base64.b64encode(img_to_use.getvalue()).decode("utf-8")
                prompt = 'Extrais les informations de ce produit ou vignette. Renvoie UNIQUEMENT un objet JSON avec les clés exactes : "designation" (nom du médicament/produit), "lot" (numéro de lot), "ddp" (date péremption MM/AAAA), "ppa" (prix public, juste le nombre), "shp" (tarif hôpital). Si invisible, mets "".'
                with st.spinner("L'IA analyse l'image..."):
                    resp = ask_ai_vision(prompt, base64_img)
                    try:
                        match = re.search(r'```json(.*?)```', resp, re.DOTALL)
                        if match: resp = match.group(1)
                        else:
                            start = resp.find('{')
                            end = resp.rfind('}') + 1
                            if start != -1 and end != 0: resp = resp[start:end]
                        
                        data = json.loads(resp)
                        st.session_state['ai_scan_rec'] = data
                        st.success(f"✅ Détection : {data.get('designation')} (Lot: {data.get('lot')})")
                    except Exception as e:
                        st.error("Lecture échouée. Essayez une image plus nette.")

    ai_data = st.session_state.get('ai_scan_rec', {})
    
    # Auto-sélection intelligente avec prise en compte du dosage
    default_prod_index = 0
    if ai_data.get('designation'):
        target_raw = str(ai_data['designation']).upper()
        
        # Fonction de normalisation des dosages courants (1000mg = 1g)
        def normalize_name(text):
            t = str(text).upper().replace(' ', '')
            t = re.sub(r'1000MG', '1G', t)
            t = re.sub(r'1000UI', '1MUI', t) # au cas où
            return t
            
        target_norm = normalize_name(target_raw)
        nums_target = set(re.findall(r'\d+', target_norm))
        
        best_match = None
        best_score = 0
        
        for s in search_list:
            s_norm = normalize_name(s)
            ratio = difflib.SequenceMatcher(None, target_norm, s_norm).ratio()
            
            nums_candidate = set(re.findall(r'\d+', s_norm))
            
            if nums_target and not nums_target.intersection(nums_candidate):
                ratio -= 0.4
                
            if nums_target and nums_target.intersection(nums_candidate):
                ratio += 0.2
                
            if ratio > best_score:
                best_score = ratio
                best_match = s
                
        if best_match and best_score > 0.4:
            default_prod_index = search_list.index(best_match) + 1
    
    selected_prod_name = st.selectbox("Sélectionner un produit (Tapez pour chercher)", [""] + search_list, index=default_prod_index)

    if selected_prod_name and col_name:
        prod_info = df_prod[df_prod[col_name] == selected_prod_name].iloc[0]
        
        with st.form("form_add_item", clear_on_submit=True):
            st.info(f"Produit sélectionné : **{selected_prod_name}**")
            c1, c2, c3 = st.columns(3)
            qte = c1.number_input("Quantité reçue", min_value=1, step=1)
            
            lot_def = str(ai_data.get('lot', ''))
            ddp_def = str(ai_data.get('ddp', ''))
            
            lot = c2.text_input("Numéro de Lot", value=lot_def, placeholder="Ex: AX123")
            ddp = c3.text_input("DDP (Péremption)", value=ddp_def, placeholder="MM/AAAA")
            
            c4, c5, c6 = st.columns(3)
            # Priorité à l'IA si détecté, sinon données de la base
            def_ppa = float(ai_data['ppa']) if ai_data.get('ppa') else float(str(prod_info.get('PPA', 0)).replace(',','.') if pd.notna(prod_info.get('PPA')) else 0)
            def_shp = float(ai_data['shp']) if ai_data.get('shp') else float(str(prod_info.get('SHP', 0)).replace(',','.') if pd.notna(prod_info.get('SHP')) else 0)
            def_col = int(prod_info.get('Colissage', 1) if pd.notna(prod_info.get('Colissage')) else 1)

            ppa = c4.number_input("PPA (Public)", value=float(def_ppa))
            shp = c5.number_input("SHP (Achat)", value=float(def_shp))
            colissage = c6.number_input("Colissage (U/Colis)", min_value=1, value=def_col)
            
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
                if 'ai_scan_rec' in st.session_state: del st.session_state['ai_scan_rec']
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
    st.markdown("### 📦 Base de données Produits (Réception)")
    st.info("Cette base est **indépendante** du catalogue général. Elle contient les produits spécifiques que vous pointez en réception.")
    
    # Affichage de la base actuelle
    df_prod_current = load_produits_reception()
    if not df_prod_current.empty:
        st.write(f"Nombre de produits enregistrés : **{len(df_prod_current)}**")
        with st.expander("Voir / Modifier la liste actuelle"):
            edited_prod = st.data_editor(df_prod_current, use_container_width=True, num_rows="dynamic", key="editor_prod_rec")
            if st.button("💾 Sauvegarder les modifications manuelles"):
                edited_prod.to_csv(DB_PRODUITS_RECEPTION, index=False, encoding='utf-8-sig')
                st.success("Base de données produits mise à jour !")
                st.rerun()
    
    st.divider()
    st.markdown("### 📥 Importation par Drag & Drop")
    st.write("Importez un fichier Excel ou CSV pour mettre à jour massivement votre liste de produits.")
    
    up_prod = st.file_uploader("Fichier Produits Réception (Excel ou CSV)", type=["csv", "xlsx"])
    if up_prod:
        if up_prod.name.endswith('.xlsx'):
            df_new_prod = pd.read_excel(up_prod)
        else:
            df_new_prod = pd.read_csv(up_prod)
        
        # Nettoyage des colonnes
        df_new_prod.columns = [str(c).strip() for c in df_new_prod.columns]
        
        st.write("Aperçu du fichier importé :")
        st.dataframe(df_new_prod.head())
        
        if st.button("🚀 Remplacer la base de données par ce fichier", type="primary"):
            # On s'assure que les colonnes minimales existent
            df_new_prod.to_csv(DB_PRODUITS_RECEPTION, index=False, encoding='utf-8-sig')
            st.success("La base de données des produits de réception a été remplacée avec succès !")
            st.rerun()
