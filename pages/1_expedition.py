import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import qrcode
import plotly.express as px
from utils import log_action
from tinydb import TinyDB, Query
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
# st.set_page_config(page_title="Gestion des Expéditions", layout="wide")
DATA_DIR = "data_expedition"
os.makedirs(DATA_DIR, exist_ok=True)
SECTEURS_PATH = os.path.join(DATA_DIR, "secteurs.csv")
LIVREURS_PATH = os.path.join(DATA_DIR, "livreurs.csv")
MOTIFS_PATH = os.path.join(DATA_DIR, "motifs.csv")
db_global = TinyDB('db_pharmaciel.json')
table_reclam = db_global.table('reclamations')

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
    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])

def add_or_merge_row(client, ville, ref, info, statut, signature, mode, secteur=""):
    """Ajoute une ligne ou fusionne si le client existe déjà."""
    client = str(client).strip()
    ref = str(ref).strip()
    
    # Pour les réclamations, on enregistre en base persistante
    if mode == "Réclamation":
        table_reclam.insert({
            "client": client,
            "ville": ville,
            "ref": ref,
            "motif": info,
            "date_crea": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "statut": "En cours",
            "signature": signature
        })

    # Mise à jour de la vue session en cours
    mask = st.session_state.rows['Client'] == client
    if mask.any():
        idx = st.session_state.rows[mask].index[0]
        current_ref = str(st.session_state.rows.at[idx, 'N° Doc'])
        if ref not in current_ref and ref != "Réclamation non validée":
            st.session_state.rows.at[idx, 'N° Doc'] = f"{current_ref} | {ref}"
    else:
        new_row = pd.DataFrame([{
            "Client": client, 
            "Ville": ville, 
            "Secteur": secteur,
            "N° Doc": ref, 
            "Info": info, 
            "Statut": statut, 
            "Signature": signature
        }])
        st.session_state.rows = pd.concat([st.session_state.rows, new_row], ignore_index=True)

# --- INTERFACE ---
st.title("🚛 Gestion des Expéditions")

tab_exp, tab_suivi_sav, tab_livreurs, tab_secteurs, tab_admin = st.tabs([
    "📋 Programme d'Expédition", "📊 Suivi des Litiges", "👤 Gestion des Livreurs", "📍 Gestion des Secteurs", "⚙️ Administration"
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
        # Déterminer le secteur du livreur (Recherche robuste)
        secteur_livreur = ""
        if livreur_choisi:
            # On cherche sans tenir compte de la casse pour plus de sécurité
            row_l = df_livreurs[df_livreurs['Nom'].str.upper() == str(livreur_choisi).upper()]
            if not row_l.empty:
                secteur_livreur = str(row_l.iloc[0]['Secteur']).strip().lower()
                if secteur_livreur and secteur_livreur != "nan":
                    st.success(f"📍 Secteur actif : **{secteur_livreur.upper()}**")
                else:
                    st.error("⚠️ Ce livreur n'a **pas de secteur** assigné dans l'onglet Administration.")
            else:
                st.error("⚠️ Livreur non trouvé dans la base.")

    with col_d1:
        date_exp = st.date_input("Date d'expédition")

    # Filtrer les clients selon le secteur du livreur pour l'ajout manuel
    if secteur_livreur and secteur_livreur != "nan":
        df_clients_filtre = df_clients[df_clients['Secteur'].astype(str).str.strip().str.lower() == secteur_livreur]
        client_list = df_clients_filtre["Client"].dropna().astype(str).unique().tolist()
        client_map = dict(zip(df_clients_filtre['Client'].astype(str), df_clients_filtre['Ville']))
    else:
        client_list = []
        client_map = {}

    st.divider()
    
    if mode == "Réclamation":
        with st.expander("📥 Importation groupée des Réclamations (Excel)", expanded=True if not secteur_livreur else False):
            if not secteur_livreur or secteur_livreur == "nan":
                st.warning("🛑 Veuillez d'abord affecter un secteur à ce livreur dans l'onglet 'Gestion des Livreurs' pour pouvoir importer.")
            else:
                st.write(f"Importation pour le secteur : **{secteur_livreur.upper()}**")
                file_complaints = st.file_uploader("Glisser le fichier Excel ici", type=['xlsx', 'xls'], key="uploader_reclamations")
                
                if file_complaints:
                    try:
                        df_reclam = pd.read_excel(file_complaints)
                        
                        import unicodedata
                        def clean_col(c):
                            c = str(c).strip().lower()
                            return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
                        
                        df_reclam.columns = [clean_col(c) for c in df_reclam.columns]
                        
                        required = {'client', 'statut'}
                        if required.issubset(df_reclam.columns):
                            df_reclam['statut_clean'] = df_reclam['statut'].astype(str).str.strip().str.lower()
                            df_to_add = df_reclam[df_reclam['statut_clean'].str.contains("en cours", na=False)].copy()
                            
                            if not df_to_add.empty:
                                df_clients = load_clients()
                                # Dictionnaires de recherche (Normalisés)
                                ville_map = dict(zip(df_clients['Client'].astype(str), df_clients['Ville']))
                                tel_map = dict(zip(df_clients['Client'].astype(str), df_clients['Tel']))
                                secteur_map = dict(zip(df_clients['Client'].astype(str), df_clients['Secteur'].astype(str).str.strip().str.lower()))
                                
                                added_count = 0
                                skipped_count = 0
                                for _, row in df_to_add.iterrows():
                                    client_name = str(row['client']).strip()
                                    
                                    # Vérification du secteur (OBLIGATOIRE ET STRICTE)
                                    client_secteur = secteur_map.get(client_name, "")
                                    if client_secteur != secteur_livreur:
                                        skipped_count += 1
                                        continue
                                    
                                    ref_val = str(row['reference']).strip() if 'reference' in df_reclam.columns and pd.notna(row['reference']) else "Réclamation non validée"
                                    
                                    ville = ville_map.get(client_name, "")
                                    telephone = tel_map.get(client_name, "")
                                    info_str = f"Tel: {telephone}" if telephone else ""
                                    
                                    add_or_merge_row(client_name, ville, ref_val, "RÉCLAMATION IMPORTÉE", "En cours", info_str, mode="Réclamation", secteur=secteur_livreur)
                                    added_count += 1
                                
                                if added_count > 0:
                                    st.success(f"✅ {added_count} réclamations pour {livreur_choisi} ({secteur_livreur.upper()}) ajoutées !")
                                    if skipped_count > 0:
                                        st.info(f"ℹ️ {skipped_count} réclamations ignorées car elles ne sont pas de ce secteur.")
                                    log_action(st.session_state.current_user['username'], f"Importation réclamations {livreur_choisi} ({secteur_livreur})", "Expédition")
                                else:
                                    st.error(f"❌ Aucune réclamation dans ce fichier ne correspond au secteur **{secteur_livreur.upper()}**.")
                            else:
                                st.info("Aucune réclamation 'En cours' trouvée.")
                        else:
                            st.error(f"Colonnes manquantes: client, statut. Trouvé: {list(df_reclam.columns)}")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

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
                val_motif = st.selectbox("Motif", liste_motifs)
                if val_motif == "MANQUE":
                    extra_colis = st.text_input("📦 Colissage (Manque)")
                    val_info = f"MANQUE: {extra_colis}" if extra_colis else "MANQUE"
                else:
                    val_info = val_motif
        with c4:
            st.write("###")
            btn_ajouter = st.button("➕ Ajouter")

    if btn_ajouter:
        if new_client != "Sélectionnez..." and ref_bon:
            annee = datetime.now().strftime('%y')
            prefixe = "RC" if mode == "Réclamation" else "BL"
            full_ref = f"{annee}/{prefixe}/{ref_bon}"
            ville = client_map.get(new_client, "")
            
            add_or_merge_row(new_client, ville, full_ref, val_info, "En cours", "", mode=mode, secteur=secteur_livreur)
            st.rerun()

    # --- OPTIMISATION IA ---
    if is_ia_enabled() and not st.session_state.rows.empty:
        st.divider()
        with st.expander("🤖 Assistant IA Logistique"):
            c_ia1, c_ia2 = st.columns(2)
            with c_ia1:
                if st.button("🗺️ Optimiser l'ordre de livraison", use_container_width=True):
                    with st.spinner("L'IA calcule l'itinéraire optimal..."):
                        villes = st.session_state.rows['Ville'].tolist()
                        prompt = f"Tu es un expert en logistique en Algérie. Voici une liste de villes pour une tournée de livraison : {villes}. Donne l'ordre le plus logique pour minimiser les kilomètres. Réponds par une liste simple."
                        st.info(ask_ai(prompt))
            with c_ia2:
                if mode == "Réclamation" and st.button("🧠 Analyser la gravité des litiges", use_container_width=True):
                    with st.spinner("Analyse IA en cours..."):
                        motifs = st.session_state.rows['Info'].tolist()
                        prompt = f"Voici des motifs de réclamations clients : {motifs}. Lesquels sont les plus critiques pour un grossiste pharma ? Donne une priorité."
                        st.warning(ask_ai(prompt))

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
            "Statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Livré", "Reporté", "Annulé"]),
            "Signature": None, # Cache la signature du tableau UI
            "Secteur": st.column_config.TextColumn("Secteur", disabled=True)
        }
    )
    st.session_state.rows = edited_rows
    
    if st.button("🗑️ Vider le tableau"):
        st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])
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
                
                st.success("✅ PDF prêt ! Une fois téléchargé, cliquez ci-dessous pour archiver et passer au livreur suivant.")
                if st.button("🏁 Valider l'envoi & Vider le tableau", type="secondary"):
                    log_action(st.session_state.current_user['username'], f"Validation finale tournée {livreur_choisi}", "Expédition")
                    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])
                    st.success("Tableau vidé ! Vous pouvez sélectionner un autre livreur.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur PDF : {e}")
        else:
            st.warning("Le tableau est vide.")

# 1.1 SUIVI DES LITIGES (SAV)
with tab_suivi_sav:
    st.header("📊 Historique et Suivi des Réclamations")
    
    reclams_all = table_reclam.all()
    if not reclams_all:
        st.info("Aucun litige enregistré dans l'historique.")
    else:
        df_sav = pd.DataFrame(reclams_all)
        df_sav['date_crea'] = pd.to_datetime(df_sav['date_crea'])
        
        # Alerte retard (> 48h)
        now = datetime.now()
        df_sav['retard'] = (now - df_sav['date_crea']).dt.total_seconds() / 3600 > 48
        retards_count = df_sav[(df_sav['retard']) & (df_sav['statut'] == 'En cours')].shape[0]
        
        if retards_count > 0:
            st.error(f"🚨 {retards_count} réclamation(s) en attente depuis plus de 48 heures !")
        
        # Filtres
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            filtre_statut = st.selectbox("Filtrer par statut", ["Tous", "En cours", "Livré", "Annulé"])
        
        if filtre_statut != "Tous":
            df_sav = df_sav[df_sav['statut'] == filtre_statut]
            
        # Stats motifs
        st.subheader("📈 Analyse des Motifs")
        df_motif_stats = df_sav['motif'].value_counts().reset_index()
        df_motif_stats.columns = ['Motif', 'Nombre']
        import plotly.express as px
        fig_motifs = px.bar(df_motif_stats, x='Motif', y='Nombre', color='Nombre', template="plotly_dark")
        st.plotly_chart(fig_motifs, use_container_width=True)
        
        # Liste éditable pour clore les litiges
        st.subheader("📝 Liste détaillée")
        edited_sav = st.data_editor(
            df_sav.sort_values('date_crea', ascending=False),
            use_container_width=True,
            column_config={
                "statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Livré", "Annulé"]),
                "retard": None # On cache la colonne technique
            }
        )
        
        if st.button("💾 Mettre à jour l'historique"):
            # Pour chaque ligne modifiée, mettre à jour la TinyDB
            # (Note: une implémentation plus complexe utiliserait l'ID TinyDB, 
            # ici on écrase tout le tableau pour faire simple dans ce contexte)
            table_reclam.truncate()
            # On retire la colonne technique 'retard' avant sauvegarde
            df_to_save = edited_sav.drop(columns=['retard'])
            # Conversion date en string pour JSON
            df_to_save['date_crea'] = df_to_save['date_crea'].dt.strftime("%Y-%m-%d %H:%M")
            table_reclam.insert_multiple(df_to_save.to_dict('records'))
            st.success("Historique mis à jour !")
            st.rerun()

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
