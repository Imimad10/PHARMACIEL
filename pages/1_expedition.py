import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import qrcode
from utils import log_action

# --- CONFIGURATION ---
# st.set_page_config(page_title="Gestion des Expéditions", layout="wide")
DATA_DIR = "data_expedition"
os.makedirs(DATA_DIR, exist_ok=True)
SECTEURS_PATH = os.path.join(DATA_DIR, "secteurs.csv")
LIVREURS_PATH = os.path.join(DATA_DIR, "livreurs.csv")
MOTIFS_PATH = os.path.join(DATA_DIR, "motifs.csv")

# --- FONCTIONS DE CHARGEMENT ---
def load_clients():
    if not os.path.exists(SECTEURS_PATH) or os.path.getsize(SECTEURS_PATH) == 0:
        return pd.DataFrame(columns=["Client", "Ville", "Tel", "Secteur"])
    try:
        df = pd.read_csv(SECTEURS_PATH)
        mapping = {'nom client': 'Client', 'VILLE': 'Ville', 'tel': 'Tel', 'SECTEUR': 'Secteur'}
        df = df.rename(columns=mapping)
        return df.loc[:, ~df.columns.duplicated()] 
    except:
        return pd.DataFrame(columns=["Client", "Ville", "Tel", "Secteur"])

def save_clients(df):
    df.to_csv(SECTEURS_PATH, index=False)

def load_livreurs():
    if not os.path.exists(LIVREURS_PATH):
        return pd.DataFrame(columns=["Nom", "Prénom", "Téléphone", "Secteur"])
    return pd.read_csv(LIVREURS_PATH)

def save_livreurs(df):
    df.to_csv(LIVREURS_PATH, index=False)

def load_motifs():
    if not os.path.exists(MOTIFS_PATH):
        # Motifs par défaut
        return ["RETOUR", "DEPOSER COLI", "ECHANGE"]
    try:
        return pd.read_csv(MOTIFS_PATH)['Motif'].tolist()
    except:
        return ["RETOUR", "DEPOSER COLI", "ECHANGE"]

def save_motifs(motifs):
    pd.DataFrame({"Motif": motifs}).to_csv(MOTIFS_PATH, index=False)

# --- INITIALISATION ÉTAT ---
if "rows" not in st.session_state:
    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "N° Doc", "Info", "Statut", "Signature"])

# --- INTERFACE ---
st.title("🚛 Gestion des Expéditions")

tab_exp, tab_livreurs, tab_secteurs, tab_admin = st.tabs([
    "📋 Programme d'Expédition", "👤 Gestion des Livreurs", "📍 Gestion des Secteurs", "⚙️ Administration"
])

# 1. PROGRAMME D'EXPÉDITION
with tab_exp:
    mode = st.radio("Mode d'expédition", ["Commande", "Réclamation"], horizontal=True)
    
    # Sécurisation des données clients pour le Selectbox
    df_clients = load_clients()
    client_list = df_clients["Client"].dropna().astype(str).unique().tolist() if "Client" in df_clients.columns else []
    client_map = dict(zip(df_clients['Client'].astype(str), df_clients['Ville'])) if "Client" in df_clients.columns else {}

    col_g1, col_d1 = st.columns(2)
    df_livreurs = load_livreurs()
    liste_livreurs = df_livreurs["Nom"].tolist() if not df_livreurs.empty else []
    
    with col_g1:
        livreur_choisi = st.selectbox("Choisir le livreur", liste_livreurs)
        # Déterminer le secteur du livreur
        secteur_livreur = ""
        if livreur_choisi:
            row_l = df_livreurs[df_livreurs['Nom'] == livreur_choisi]
            if not row_l.empty:
                secteur_livreur = str(row_l.iloc[0]['Secteur']).strip().lower()

    with col_d1:
        date_exp = st.date_input("Date d'expédition")

    # Filtrer les clients selon le secteur du livreur
    if secteur_livreur:
        df_clients_filtre = df_clients[df_clients['Secteur'].astype(str).str.strip().str.lower() == secteur_livreur]
        client_list = df_clients_filtre["Client"].dropna().astype(str).unique().tolist()
        client_map = dict(zip(df_clients_filtre['Client'].astype(str), df_clients_filtre['Ville']))
    else:
        # Si pas de secteur défini pour le livreur, on montre tout ou rien ?
        # On montre tout par défaut mais on prévient
        if livreur_choisi: st.warning(f"Le livreur {livreur_choisi} n'a pas de secteur assigné.")

    st.divider()
    
    if mode == "Réclamation":
        with st.expander("📥 Importation groupée des Réclamations (Excel)", expanded=False):
            st.write("Le fichier doit contenir les colonnes : **client, reference, statut**")
            file_complaints = st.file_uploader("Glisser le fichier Excel ici", type=['xlsx', 'xls'], key="uploader_reclamations")
            
            if file_complaints:
                try:
                    df_reclam = pd.read_excel(file_complaints)
                    
                    # Normalisation des colonnes
                    import unicodedata
                    def clean_col(c):
                        c = str(c).strip().lower()
                        return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
                    
                    df_reclam.columns = [clean_col(c) for c in df_reclam.columns]
                    
                    required = {'client', 'statut'} # Reference est optionnelle selon la règle
                    if required.issubset(df_reclam.columns):
                        # Filtrage statut "en cours"
                        df_reclam['statut_clean'] = df_reclam['statut'].astype(str).str.strip().str.lower()
                        df_to_add = df_reclam[df_reclam['statut_clean'].str.contains("en cours", na=False)].copy()
                        
                        if not df_to_add.empty:
                            df_clients = load_clients()
                            # Dictionnaires de recherche
                            ville_map = dict(zip(df_clients['Client'].astype(str), df_clients['Ville']))
                            tel_map = dict(zip(df_clients['Client'].astype(str), df_clients['Tel']))
                            secteur_map = dict(zip(df_clients['Client'].astype(str), df_clients['Secteur'].astype(str).str.strip().str.lower()))
                            
                            added_count = 0
                            skipped_count = 0
                            for _, row in df_to_add.iterrows():
                                client_name = str(row['client']).strip()
                                
                                # Vérification du secteur (STRICTE)
                                if secteur_livreur:
                                    client_secteur = secteur_map.get(client_name, "")
                                    if client_secteur != secteur_livreur:
                                        skipped_count += 1
                                        continue
                                
                                ref_val = str(row['reference']).strip() if 'reference' in df_reclam.columns and pd.notna(row['reference']) else "Réclamation non validée"
                                
                                ville = ville_map.get(client_name, "")
                                telephone = tel_map.get(client_name, "")
                                info_str = f"Tel: {telephone}" if telephone else ""
                                
                                new_entry = pd.DataFrame([{
                                    "Client": client_name, 
                                    "Ville": ville, 
                                    "N° Doc": ref_val, 
                                    "Info": "RÉCLAMATION IMPORTÉE", 
                                    "Statut": "En cours", 
                                    "Signature": info_str
                                }])
                                
                                st.session_state.rows = pd.concat([st.session_state.rows, new_entry], ignore_index=True)
                                added_count += 1
                            
                            if added_count > 0:
                                st.success(f"✅ {added_count} réclamations pour {livreur_choisi} ({secteur_livreur}) importées !")
                                if skipped_count > 0:
                                    st.warning(f"ℹ️ {skipped_count} réclamations ignorées (autres secteurs).")
                                log_action(st.session_state.current_user['username'], f"Importation {added_count} réclamations pour {livreur_choisi}", "Expédition")
                            else:
                                st.warning(f"⚠️ Aucune réclamation dans le fichier ne correspond au secteur de {livreur_choisi} ({secteur_livreur}).")
                        else:
                            st.info("Aucune réclamation avec le statut 'En cours' trouvée dans le fichier.")
                    else:
                        st.error(f"Colonnes manquantes. Attendu: client, statut. Trouvé: {list(df_reclam.columns)}")
                except Exception as e:
                    st.error(f"Erreur lors de la lecture : {e}")

    # Formulaire d'ajout manuel
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1])
        with c1:
            new_client = st.selectbox("Client", ["Sélectionnez..."] + client_list)
        with c2:
            ref_bon = st.text_input("Réf. Bon")
        with c3:
            if mode == "Commande":
                val_info = st.text_input("Colissage")
            else:
                liste_motifs = load_motifs()
                val_info = st.selectbox("Motif", liste_motifs)
        with c4:
            st.write("###") # Aligne avec le champ texte
            btn_ajouter = st.button("➕ Ajouter")

    if btn_ajouter:
        if new_client != "Sélectionnez..." and ref_bon:
            annee = datetime.now().strftime('%y')
            prefixe = "RC" if mode == "Réclamation" else "BL"
            full_ref = f"{annee}/{prefixe}/{ref_bon}"
            ville = client_map.get(new_client, "")
            
            new_row = pd.DataFrame([{"Client": new_client, "Ville": ville, "N° Doc": full_ref, "Info": val_info, "Statut": "En cours", "Signature": ""}])
            st.session_state.rows = pd.concat([st.session_state.rows, new_row], ignore_index=True)
            st.rerun()

    st.subheader(f"Détails des {mode}s")
    
    # Édition et mise à jour du tableau
    col_label = "Colissage" if mode == "Commande" else "Motif"
    
    # Configuration dynamique de la colonne Info selon le mode
    if mode == "Réclamation":
        info_config = st.column_config.SelectboxColumn("Motif", options=load_motifs())
    else:
        info_config = st.column_config.TextColumn("Colissage")

    edited_rows = st.data_editor(
        st.session_state.rows, 
        num_rows="dynamic", 
        use_container_width=True, 
        column_config={
            "Info": info_config,
            "Statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Livré", "Reporté", "Annulé"])
        }
    )
    st.session_state.rows = edited_rows
    
    if st.button("🗑️ Vider le tableau"):
        st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "N° Doc", "Info", "Statut", "Signature"])
        st.rerun()
        
    if st.button("🖨️ Générer la Feuille de Route (PDF)"):
        if not st.session_state.rows.empty:
            try:
                # Génération du QR Code
                qr = qrcode.QRCode(box_size=4, border=2)
                qr_data = f"Livreur: {livreur_choisi}\nDate: {date_exp}\nDoc: {len(st.session_state.rows)}"
                qr.add_data(qr_data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                qr_path = "temp_qr.png"
                img.save(qr_path)
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"FEUILLE DE ROUTE - {livreur_choisi}", 0, 1, 'C')
                pdf.set_font("Arial", '', 12)
                pdf.cell(0, 10, f"Date d'expedition: {date_exp}   |   Total: {len(st.session_state.rows)}", 0, 1, 'C')
                
                pdf.image(qr_path, x=170, y=10, w=30)
                pdf.ln(15)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(45, 8, "Client", 1)
                pdf.cell(30, 8, "Ville", 1)
                pdf.cell(40, 8, "N Doc", 1)
                pdf.cell(25, 8, col_label, 1)
                pdf.cell(20, 8, "Statut", 1)
                pdf.cell(30, 8, "Signature", 1)
                pdf.ln()
                
                pdf.set_font("Arial", '', 9)
                for _, row in st.session_state.rows.iterrows():
                    c = str(row.get('Client', '')).encode('latin-1', 'replace').decode('latin-1')
                    v = str(row.get('Ville', '')).encode('latin-1', 'replace').decode('latin-1')
                    d = str(row.get('N° Doc', '')).encode('latin-1', 'replace').decode('latin-1')
                    i = str(row.get('Info', '')).encode('latin-1', 'replace').decode('latin-1')
                    s = str(row.get('Statut', '')).encode('latin-1', 'replace').decode('latin-1')
                    
                    pdf.cell(45, 8, c[:22], 1)
                    pdf.cell(30, 8, v[:13], 1)
                    pdf.cell(40, 8, d[:20], 1)
                    pdf.cell(25, 8, i[:12], 1)
                    pdf.cell(20, 8, s[:10], 1)
                    pdf.cell(30, 8, "", 1)
                    pdf.ln()
                    
                pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                if os.path.exists(qr_path):
                    os.remove(qr_path)
                    
                log_action(st.session_state.current_user['username'], f"Génération PDF Expédition pour {livreur_choisi}", "Expédition")
                
                st.download_button(
                    label="📥 Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"Feuille_Route_{livreur_choisi}_{date_exp}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Erreur PDF : {e}")
        else:
            st.warning("Le tableau est vide.")

# 2. GESTION DES LIVREURS
with tab_livreurs:
    st.header("👤 Gestion des Livreurs")
    
    # Récupérer les secteurs existants dans la base clients pour l'attribution
    df_clients_all = load_clients()
    liste_secteurs_dispo = sorted(df_clients_all["Secteur"].dropna().unique().tolist()) if "Secteur" in df_clients_all.columns else []
    
    with st.form("form_ajout_livreur", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nom = col1.text_input("Nom")
        prenom = col1.text_input("Prénom")
        tel = col2.text_input("Téléphone")
        secteur = col2.selectbox("Attribuer un Secteur", ["Aucun"] + liste_secteurs_dispo)
        
        if st.form_submit_button("Ajouter le livreur"):
            if nom:
                df_l = load_livreurs()
                sect_val = secteur if secteur != "Aucun" else ""
                new_l = pd.DataFrame([{"Nom": nom, "Prénom": prenom, "Téléphone": tel, "Secteur": sect_val}])
                save_livreurs(pd.concat([df_l, new_l], ignore_index=True))
                st.success(f"Livreur {nom} ajouté au secteur {sect_val}")
                st.rerun()

    st.subheader("📋 Liste des Livreurs et Affectations")
    df_livreurs_actuel = load_livreurs()
    edited_livreurs = st.data_editor(
        df_livreurs_actuel, 
        use_container_width=True, 
        num_rows="dynamic",
        column_config={
            "Secteur": st.column_config.SelectboxColumn("Secteur Affecté", options=liste_secteurs_dispo)
        }
    )
    if st.button("💾 Sauvegarder les modifications"):
        save_livreurs(edited_livreurs)
        st.success("Affectations mises à jour !")

# 3. GESTION DES SECTEURS (Clients)
with tab_secteurs:
    st.header("📍 Gestion des Clients")
    with st.expander("➕ Ajouter un nouveau client"):
        with st.form("ajout_client", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_nom = c1.text_input("Nom Client")
            new_ville = c1.text_input("Ville")
            new_tel = c2.text_input("Téléphone")
            new_secteur = c2.text_input("Secteur")
            if st.form_submit_button("Valider l'ajout"):
                df_actuel = load_clients()
                new_data = pd.DataFrame([{"Client": new_nom, "Ville": new_ville, "Tel": new_tel, "Secteur": new_secteur}])
                save_clients(pd.concat([df_actuel, new_data], ignore_index=True))
                st.rerun()

    df_clients_edit = load_clients()
    edited_clients = st.data_editor(df_clients_edit, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder les clients"):
        save_clients(edited_clients)
        st.success("Clients sauvegardés !")

# 4. ADMINISTRATION
with tab_admin:
    st.header("⚙️ Paramètres du module")
    
    st.subheader("📋 Gestion des Motifs (Réclamations)")
    current_motifs = load_motifs()
    
    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        new_motif = st.text_input("Nouveau motif")
    with col_m2:
        st.write("###")
        if st.button("➕ Ajouter Motif"):
            if new_motif and new_motif not in current_motifs:
                current_motifs.append(new_motif)
                save_motifs(current_motifs)
                st.rerun()
    
    # Liste des motifs avec bouton supprimer
    st.write("Motifs actuels :")
    for i, m in enumerate(current_motifs):
        c_m1, c_m2 = st.columns([3, 1])
        c_m1.text(f"• {m}")
        if c_m2.button("🗑️", key=f"del_m_{i}"):
            current_motifs.pop(i)
            save_motifs(current_motifs)
            st.rerun()
