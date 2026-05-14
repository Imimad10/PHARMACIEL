import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import qrcode
import plotly.express as px
from utils import log_action
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
# st.set_page_config(page_title="Gestion des Expéditions", layout="wide")
DATA_DIR = "data_expedition"
os.makedirs(DATA_DIR, exist_ok=True)
SECTEURS_PATH = os.path.join(DATA_DIR, "secteurs.csv")
LIVREURS_PATH = os.path.join(DATA_DIR, "livreurs.csv")
MOTIFS_PATH = os.path.join(DATA_DIR, "motifs.csv")
COLS_CLIENTS = ["Client", "Ville", "Tel", "Secteur"]
COLS_LIVREURS = ["Nom", "Secteur"]
COLS_SAV = ["client", "ville", "ref", "motif", "date_crea", "statut", "signature", "livreur", "date_reglement"]
SAV_CONFIG_PATH = os.path.join(DATA_DIR, "sav_config.csv")

# --- FONCTIONS DE CHARGEMENT ---
def load_clients():
    df = load_gs_data("Secteurs", SECTEURS_PATH, COLS_CLIENTS)
    mapping = {'nom client': 'Client', 'VILLE': 'Ville', 'tel': 'Tel', 'SECTEUR': 'Secteur'}
    df = df.rename(columns=mapping)
    return df.loc[:, ~df.columns.duplicated()]

def save_clients(df):
    save_gs_data(df, "Secteurs", SECTEURS_PATH)

def load_livreurs():
    return load_gs_data("Livreurs", LIVREURS_PATH, ["Nom", "Prénom", "Téléphone", "Secteur"])

def save_livreurs(df):
    save_gs_data(df, "Livreurs", LIVREURS_PATH)

def load_motifs():
    df = load_gs_data("Motifs_SAV", MOTIFS_PATH, ["Motif"])
    if df.empty:
        return ["RETOUR", "DEPOSER COLI", "ECHANGE"]
    return df['Motif'].tolist()

def save_motifs(motifs):
    df = pd.DataFrame({"Motif": motifs})
    save_gs_data(df, "Motifs_SAV", MOTIFS_PATH)

# --- INITIALISATION ÉTAT ---
if "rows" not in st.session_state:
    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature", "Qte Colis"])

def add_or_merge_row(client, ville, ref, info, statut, signature, mode, secteur="", qte_colis=0):
    """Ajoute une ligne pour chaque réclamation/commande (évite les doublons par référence)."""
    client = str(client).strip()
    ref = str(ref).strip()
    
    # Vérification si la référence existe déjà dans le tableau actuel (session)
    if not st.session_state.rows.empty:
        if ref in st.session_state.rows['N° Doc'].astype(str).values:
            return False 

    # Pour les réclamations, on enregistre en base persistante si pas déjà présent
    if mode == "Réclamation":
        df_sav = load_gs_data("Litiges_SAV", "data/db_sav.csv", COLS_SAV + ["qte_colis"])
        if df_sav.empty or ref not in df_sav['ref'].astype(str).values:
            new_sav = pd.DataFrame([{
                "client": client,
                "ville": ville,
                "ref": ref,
                "motif": info,
                "date_crea": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "statut": "En cours",
                "signature": signature,
                "qte_colis": qte_colis,
                "livreur": "",
                "date_reglement": ""
            }])
            df_sav = pd.concat([df_sav, new_sav], ignore_index=True)
            save_gs_data(df_sav, "Litiges_SAV", "data/db_sav.csv")

    # Ajout à l'état de session
    new_row = pd.DataFrame([{
        "Client": client, 
        "Ville": ville, 
        "Secteur": secteur,
        "N° Doc": ref, 
        "Info": info, 
        "Statut": statut, 
        "Signature": signature,
        "Qte Colis": qte_colis
    }])
    st.session_state.rows = pd.concat([st.session_state.rows, new_row], ignore_index=True)
    return True

# --- INTERFACE ---
st.title("🚛 Gestion des Expéditions")

tab_exp, tab_suivi_sav, tab_admin = st.tabs([
    "📋 Programme d'Expédition", "📊 Suivi des Litiges", "⚙️ Administration"
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
    
    # Liste de tous les secteurs pour le filtrage libre
    all_sectors = sorted([str(s).strip().lower() for s in df_clients['Secteur'].dropna().unique() if str(s).lower() != 'nan'])

    with col_g1:
        # Sélection libre du secteur (Région)
        secteur_affichage = st.selectbox("🌍 Région / Secteur à traiter", ["Tous"] + all_sectors, key="exp_sector_sel")
        
        # --- FIX: TOUJOURS AFFICHER TOUS LES LIVREURS (PAS DE FILTRAGE PAR SECTEUR) ---
        df_all_livreurs = load_livreurs()
        if not df_all_livreurs.empty:
            # On trie pour que les livreurs du secteur soient en haut (optionnel mais utile)
            if secteur_affichage != "Tous":
                mask_secteur = df_all_livreurs['Secteur'].astype(str).str.strip().str.lower() == secteur_affichage.lower()
                livreurs_secteur = df_all_livreurs[mask_secteur]['Nom'].tolist()
                autres_livreurs = df_all_livreurs[~mask_secteur]['Nom'].tolist()
                full_list_display = sorted(livreurs_secteur) + ["--- AUTRES SECTEURS ---"] + sorted(autres_livreurs)
            else:
                full_list_display = sorted(df_all_livreurs['Nom'].tolist())
        else:
            full_list_display = []

        livreur_choisi = st.selectbox("👤 Choisir le livreur pour cette mission", 
                                      full_list_display, 
                                      key="exp_livreur_sel",
                                      help="Tous les livreurs sont affichés ici, peu importe le secteur choisi.")
        
        if secteur_affichage != "Tous":
            st.success(f"📍 Secteur actif : **{secteur_affichage.upper()}**")
        else:
            st.info("🔓 Toutes les régions affichées")
        
        st.caption("✅ Mode Libre : Vous pouvez attribuer n'importe quel livreur à n'importe quel secteur.")

    with col_d1:
        date_exp = st.date_input("Date d'expédition")

    # Préparation de la liste des clients selon le secteur choisi
    if secteur_affichage == "Tous":
        client_list_filtered = df_clients["Client"].dropna().astype(str).unique().tolist()
    else:
        df_c_filtre = df_clients[df_clients['Secteur'].astype(str).str.strip().str.lower() == secteur_affichage]
        client_list_filtered = df_c_filtre["Client"].dropna().astype(str).unique().tolist()

    st.divider()
    
    if mode == "Réclamation":
        with st.expander("📥 Importation groupée des Réclamations (Excel)", expanded=False):
            st.write(f"Importation pour le secteur : **{secteur_affichage.upper()}**")
            file_complaints = st.file_uploader("Glisser le fichier Excel ici", type=['xlsx', 'xls'], key="uploader_reclamations")
            
            if file_complaints:
                try:
                    df_reclam = pd.read_excel(file_complaints)
                    
                    import unicodedata
                    def clean_col(c):
                        c = str(c).strip().lower()
                        return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
                    
                    df_reclam.columns = [clean_col(c) for c in df_reclam.columns]
                    
                    if 'client' in df_reclam.columns:
                        if 'statut' in df_reclam.columns:
                            df_reclam['statut_clean'] = df_reclam['statut'].astype(str).str.strip().str.lower()
                            df_to_add = df_reclam[df_reclam['statut_clean'].str.contains("en cours", na=False)].copy()
                        else:
                            df_to_add = df_reclam.dropna(subset=['client']).copy()
                        
                        if not df_to_add.empty:
                            df_clients_base = load_clients()
                            ville_map = dict(zip(df_clients_base['Client'].astype(str), df_clients_base['Ville']))
                            tel_map = dict(zip(df_clients_base['Client'].astype(str), df_clients_base['Tel']))
                            sect_map = dict(zip(df_clients_base['Client'].astype(str), df_clients_base['Secteur'].astype(str).str.strip().str.lower()))
                            
                            added_count = 0
                            skipped_count = 0
                            for _, row in df_to_add.iterrows():
                                client_name = str(row['client']).strip()
                                
                                # Détermination du secteur : Priorité au fichier Excel, puis à la base locale
                                file_secteur = ""
                                if 'region' in row: file_secteur = str(row['region']).strip().lower()
                                elif 'secteur' in row: file_secteur = str(row['secteur']).strip().lower()
                                
                                client_secteur = file_secteur if file_secteur else sect_map.get(client_name, "")
                                
                                # Filtrage selon le secteur d'affichage (si pas "Tous")
                                if secteur_affichage != "Tous" and client_secteur != secteur_affichage:
                                    skipped_count += 1
                                    continue
                                
                                ref_val = str(row['reference']).strip() if 'reference' in df_reclam.columns and pd.notna(row['reference']) else "Réclamation non validée"
                                ville = str(row['ville']).strip() if 'ville' in row else ville_map.get(client_name, "")
                                telephone = str(row['tel']).strip() if 'tel' in row else tel_map.get(client_name, "")
                                info_str = f"Tel: {telephone}" if telephone else ""
                                
                                add_or_merge_row(client_name, ville, ref_val, "RÉCLAMATION IMPORTÉE", "En cours", info_str, mode="Réclamation", secteur=client_secteur)
                                added_count += 1
                            
                            if added_count > 0:
                                st.success(f"✅ {added_count} réclamations ajoutées !")
                                if skipped_count > 0:
                                    st.info(f"ℹ️ {skipped_count} lignes ignorées (hors secteur {secteur_affichage.upper()}).")
                                log_action(st.session_state.current_user['username'], f"Importation réclamations ({secteur_affichage})", "Expédition")
                            else:
                                st.error(f"❌ Aucune donnée correspondant au secteur **{secteur_affichage.upper()}**.")
                        else:
                            st.info("Aucune réclamation valide trouvée.")
                    else:
                        st.error(f"Colonne 'client' manquante. Trouvé: {list(df_reclam.columns)}")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # Formulaire d'ajout manuel
    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1, 1])
    with c1:
        new_client = st.selectbox("Client", client_list_filtered, index=None, placeholder="Rechercher ou sélectionner un client...")
    with c2:
        ref_bon = st.text_input("Réf. Bon")
    with c3:
        if mode == "Commande":
            val_info = st.text_input("Colissage")
            qte_colis_val = 0
        else:
            liste_motifs = load_motifs()
            val_motif = st.selectbox("Motif", liste_motifs)
            if val_motif == "MANQUE":
                extra_colis = st.text_input("📦 Colissage (Manque)")
                val_info = f"MANQUE: {extra_colis}" if extra_colis else "MANQUE"
                qte_colis_val = 0
            else:
                val_info = val_motif
                qte_colis_val = st.number_input("Nb Colis à déposer", min_value=0, value=0)
    with c4:
        st.write("###")
        btn_ajouter = st.button("➕ Ajouter")

    if btn_ajouter:
        if new_client and ref_bon:
            annee = datetime.now().strftime('%y')
            prefixe = "RC" if mode == "Réclamation" else "BL"
            full_ref = f"{annee}/{prefixe}/{ref_bon}"
            client_data = df_clients[df_clients['Client'] == new_client]
            ville = client_data['Ville'].values[0] if not client_data.empty else ""
            secteur_client = str(client_data['Secteur'].values[0]).strip().lower() if not client_data.empty else ""
            
            add_or_merge_row(new_client, ville, full_ref, val_info, "En cours", "", mode=mode, secteur=secteur_client, qte_colis=qte_colis_val)
            st.rerun()
        elif not new_client:
            st.error("Veuillez sélectionner un client.")
        elif not ref_bon:
            st.error("Veuillez saisir la référence du bon.")

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

    # --- FILTRAGE DYNAMIQUE DU TABLEAU ---
    # On filtre le tableau selon le secteur d'affichage choisi (Région)
    if secteur_affichage == "Tous":
        df_visible = st.session_state.rows
    else:
        df_visible = st.session_state.rows[st.session_state.rows['Secteur'].astype(str).str.strip().str.lower() == secteur_affichage.lower()]

    st.subheader(f"Détails des {mode}s ({secteur_affichage.upper()})")
    
    # Configuration dynamique de la colonne Info selon le mode
    col_label = "Colissage" if mode == "Commande" else "Motif"
    if mode == "Réclamation":
        info_config = st.column_config.SelectboxColumn("Motif", options=load_motifs())
    else:
        info_config = st.column_config.TextColumn("Colissage")

    # --- LOGIQUE DE SUPPRESSION ---
    if "to_delete" not in st.session_state:
        st.session_state.to_delete = None

    if st.session_state.to_delete:
        st.error(f"🗑️ Confirmer la suppression de la ligne : **{st.session_state.to_delete}** ?")
        col_c1, col_c2 = st.columns(2)
        if col_c1.button("✅ Confirmer", type="primary", use_container_width=True):
            st.session_state.rows = st.session_state.rows[st.session_state.rows['N° Doc'] != st.session_state.to_delete]
            st.session_state.to_delete = None
            st.success("Ligne supprimée !")
            st.rerun()
        if col_c2.button("❌ Abandonner", use_container_width=True):
            st.session_state.to_delete = None
            st.rerun()

    # --- AFFICHAGE DU TABLEAU AVEC BOUTONS ---
    if not df_visible.empty:
        # En-têtes du tableau
        h1, h2, h3, h4, h5, h6, h7 = st.columns([2.5, 1, 2, 1, 0.8, 1, 0.5])
        h1.markdown("**Client**")
        h2.markdown("**Ville**")
        h3.markdown("**N° Doc**")
        h4.markdown(f"**{col_label}**")
        h5.markdown("**Nb**")
        h6.markdown("**Statut**")
        h7.markdown("") # Poubelle
        
        # Lignes du tableau
        for i, row in df_visible.iterrows():
            with st.container():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 1, 2, 1, 0.8, 1, 0.5])
                c1.write(row['Client'])
                c2.write(row['Ville'])
                c3.write(f"`{row['N° Doc']}`")
                
                # Info modifiable
                if mode == "Réclamation":
                    motifs_disp = load_motifs()
                    try:
                        idx_m = motifs_disp.index(str(row['Info']))
                    except:
                        idx_m = 0
                    new_info = c4.selectbox("Info", motifs_disp, index=idx_m, key=f"info_{row['N° Doc']}", label_visibility="collapsed")
                    
                    # Bouton Étiquette si DEPOSER ou ECHANGE
                    motif_up = str(row['Info']).upper()
                    if "DEPOSER" in motif_up or "ECHANGE" in motif_up:
                        if c4.button("🏷️ Étiquette", key=f"label_{row['N° Doc']}"):
                            try:
                                # Format A6 paysage (148x105mm) pour une étiquette lisible
                                lpdf = FPDF(orientation='L', unit='mm', format=(148, 105))
                                lpdf.set_margins(8, 8, 8)
                                lpdf.add_page()
                                
                                client_name = str(row['Client']).encode('latin-1', 'replace').decode('latin-1')
                                ref_val = str(row['N° Doc']).encode('latin-1', 'replace').decode('latin-1')
                                qte = int(row.get('Qte Colis', 0))
                                motif_label = str(row['Info']).upper().encode('latin-1', 'replace').decode('latin-1')
                                
                                # ===== BANDEAU ROUGE "RECLAMATION" =====
                                lpdf.set_fill_color(180, 0, 0)
                                lpdf.set_text_color(255, 255, 255)
                                lpdf.set_font("Arial", 'B', 28)
                                lpdf.cell(0, 20, "RECLAMATION", 0, 1, 'C', fill=True)
                                lpdf.ln(3)
                                
                                # ===== NOM DU CLIENT =====
                                lpdf.set_text_color(0, 0, 0)
                                lpdf.set_font("Arial", 'B', 16)
                                lpdf.cell(0, 10, f"CLIENT : {client_name}", 0, 1, 'L')
                                
                                # ===== REFERENCE =====
                                lpdf.set_font("Arial", '', 11)
                                lpdf.cell(0, 7, f"REF : {ref_val}", 0, 1, 'L')
                                lpdf.cell(0, 7, f"MOTIF : {motif_label}", 0, 1, 'L')
                                lpdf.ln(3)
                                
                                # ===== NOMBRE DE COLIS (grand encadré) =====
                                lpdf.set_fill_color(240, 240, 240)
                                lpdf.set_font("Arial", 'B', 32)
                                lpdf.cell(0, 18, f"COLIS : {qte}", 1, 1, 'C', fill=True)
                                
                                raw_out = lpdf.output(dest='S')
                                if isinstance(raw_out, str):
                                    label_bytes = raw_out.encode('latin-1', 'replace')
                                else:
                                    label_bytes = bytes(raw_out)
                                
                                st.download_button("📥 Télécharger Étiquette", data=label_bytes, file_name=f"Etiquette_{row['N° Doc']}.pdf", key=f"dl_label_{row['N° Doc']}")
                            except Exception as le:
                                st.error(f"Erreur Étiquette : {le}")

                else:
                    new_info = c4.text_input("Info", value=str(row['Info']), key=f"info_{row['N° Doc']}", label_visibility="collapsed")
                
                if new_info != str(row['Info']):
                    st.session_state.rows.loc[st.session_state.rows['N° Doc'] == row['N° Doc'], 'Info'] = new_info
                    st.rerun()

                # Nb Colis (modifiable)
                new_qte = c5.number_input("Nb", min_value=0, value=int(row.get('Qte Colis', 0)), key=f"qte_{row['N° Doc']}", label_visibility="collapsed")
                if new_qte != int(row.get('Qte Colis', 0)):
                    st.session_state.rows.loc[st.session_state.rows['N° Doc'] == row['N° Doc'], 'Qte Colis'] = new_qte
                    st.rerun()

                # Statut modifiable
                new_statut = c6.selectbox(
                    "Statut", 
                    ["En cours", "Livré", "Reporté", "Annulé"], 
                    index=["En cours", "Livré", "Reporté", "Annulé"].index(row['Statut']),
                    key=f"statut_{row['N° Doc']}",
                    label_visibility="collapsed"
                )
                if new_statut != row['Statut']:
                    st.session_state.rows.loc[st.session_state.rows['N° Doc'] == row['N° Doc'], 'Statut'] = new_statut
                    st.rerun()

                # Bouton Poubelle
                if c7.button("🗑️", key=f"del_{row['N° Doc']}", help="Supprimer cette ligne"):
                    st.session_state.to_delete = row['N° Doc']
                    st.rerun()
                st.divider()
    else:
        st.info("Aucune donnée à afficher pour ce secteur.")
    
    if st.button("🗑️ Vider le secteur/filtre actuel"):
        if secteur_affichage == "Tous":
            st.session_state.rows = pd.DataFrame(columns=st.session_state.rows.columns)
        else:
            st.session_state.rows = st.session_state.rows[st.session_state.rows['Secteur'].astype(str).str.strip().str.lower() != secteur_affichage.lower()]
        st.rerun()
        
    if st.button("🖨️ Générer la Feuille de Route (PDF)"):
        if not df_visible.empty:
            try:
                # Génération du QR Code
                mission_id = f"M-{int(datetime.now().timestamp())}"
                qr_data = f"ID:{mission_id}|Livreur:{livreur_choisi}|Secteur:{secteur_affichage}|Date:{datetime.now().strftime('%d/%m/%Y')}|Nb:{len(df_visible)}"
                qr = qrcode.make(qr_data)
                qr_path = "temp_qr.png"
                qr.save(qr_path)
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"FEUILLE DE ROUTE - {livreur_choisi}", 0, 1, 'C')
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, f"SECTEUR : {secteur_affichage.upper()}", 0, 1, 'C')
                pdf.set_font("Arial", '', 11)
                pdf.cell(0, 10, f"Date: {date_exp}   |   Total Clients: {len(df_visible)}", 0, 1, 'C')
                
                pdf.image(qr_path, x=170, y=10, w=30)
                pdf.ln(10)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(45, 8, "Client", 1)
                pdf.cell(30, 8, "Ville", 1)
                pdf.cell(40, 8, "N Doc", 1)
                pdf.cell(25, 8, col_label, 1)
                pdf.cell(20, 8, "Statut", 1)
                pdf.cell(30, 8, "Signature", 1)
                pdf.ln()
                
                pdf.set_font("Arial", '', 9)
                for _, row in df_visible.iterrows():
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
                    
                raw = pdf.output(dest='S')
                if isinstance(raw, (bytes, bytearray)):
                    pdf_bytes = bytes(raw)
                else:
                    pdf_bytes = raw.encode('latin-1', 'replace')
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
                    if mode == "Réclamation":
                        # Affecter le livreur aux réclamations dans la base centrale
                        df_sav_all = load_gs_data("Litiges_SAV", "data/db_sav.csv", COLS_SAV)
                        refs_to_update = df_visible['N° Doc'].tolist()
                        df_sav_all.loc[df_sav_all['ref'].isin(refs_to_update), 'livreur'] = livreur_choisi
                        save_gs_data(df_sav_all, "Litiges_SAV", "data/db_sav.csv")
                        st.success(f"Affectation de {livreur_choisi} enregistrée.")

                    log_action(st.session_state.current_user['username'], f"Validation finale tournée {livreur_choisi}", "Expédition")
                    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur PDF : {e}")
        else:
            st.warning("Le tableau est vide.")

# 1.1 SUIVI DES LITIGES (SAV)
with tab_suivi_sav:
    st.header("📊 Suivi Stratégique des Réclamations (SLA)")
    
    # Chargement Config Secteurs Proches
    df_near_config = load_gs_data("SAV_Config", SAV_CONFIG_PATH, ["Secteur"])
    near_sectors = [str(s).strip().lower() for s in df_near_config['Secteur'].tolist()] if not df_near_config.empty else ["alger 1", "alger 2", "blida", "tipaza", "medea", "alger est"]

    df_sav = load_gs_data("Litiges_SAV", "data/db_sav.csv", COLS_SAV + ["secteur"])
    if df_sav.empty:
        st.info("Aucun litige enregistré dans l'historique.")
    else:
        # Nettoyage et typage
        df_sav['date_crea'] = pd.to_datetime(df_sav['date_crea'], errors='coerce')
        df_sav = df_sav.dropna(subset=['date_crea'])
        
        now = datetime.now()
        
        def calculate_sla_status(row):
            secteur = str(row.get('secteur', '')).strip().lower()
            date_c = row['date_crea']
            diff_h = (now - date_c).total_seconds() / 3600
            
            # 1. Déterminer le délai max (SLA)
            if secteur in near_sectors:
                limit_h = 48
                label_sla = "PROCHE (48h)"
            else:
                limit_h = 24 * 14 # 2 semaines
                label_sla = "LOINTAIN (2sem)"
            
            # 2. Calculer l'état
            if row['statut'] != 'En cours':
                return "✅ Réglé", "green", label_sla
            
            remaining = limit_h - diff_h
            if remaining < 0:
                return "🚨 RETARD", "red", label_sla
            elif remaining < 24:
                return "⚠️ URGENT", "orange", label_sla
            else:
                return "⏳ DANS LES DÉLAIS", "blue", label_sla

        # Application de la logique SLA
        df_sav[['SLA_Statut', 'SLA_Color', 'Type_Region']] = df_sav.apply(
            lambda r: pd.Series(calculate_sla_status(r)), axis=1
        )

        # Affichage des KPIs
        c_k1, c_k2, c_k3 = st.columns(3)
        retards = df_sav[df_sav['SLA_Statut'] == "🚨 RETARD"].shape[0]
        urgents = df_sav[df_sav['SLA_Statut'] == "⚠️ URGENT"].shape[0]
        total_encours = df_sav[df_sav['statut'] == 'En cours'].shape[0]
        
        c_k1.metric("Total En Cours", total_encours)
        c_k2.metric("Urgents (<24h)", urgents, delta_color="inverse")
        c_k3.metric("En Retard 💀", retards, delta="-Hors SLA-", delta_color="inverse")

        # Filtres
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            filtre_statut = st.selectbox("Statut", ["Tous", "En cours", "Livré", "Annulé"])
        with col_s2:
            filtre_sla = st.selectbox("SLA / Priorité", ["Tous", "Retard", "Urgent", "Dans les délais"])
        
        df_disp = df_sav.copy()
        if filtre_statut != "Tous":
            df_disp = df_disp[df_disp['statut'] == filtre_statut]
        if filtre_sla != "Tous":
            df_disp = df_disp[df_disp['SLA_Statut'].str.contains(filtre_sla.upper())]

        # Table avec coloration
        st.subheader("📋 Liste des Litiges par Priorité")
        
        # Formattage pour l'affichage
        df_disp['Date'] = df_disp['date_crea'].dt.strftime("%d/%m %H:%M")
        
        edited_df = st.data_editor(
            df_disp.sort_values(['SLA_Statut', 'date_crea'], ascending=[True, True]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "SLA_Statut": st.column_config.TextColumn("État SLA", disabled=True),
                "SLA_Color": None, 
                "statut": st.column_config.SelectboxColumn("Statut Opérationnel", options=["En cours", "Livré", "Annulé"]),
                "Type_Region": st.column_config.TextColumn("Type Secteur", disabled=True),
                "date_crea": None,
                "secteur": st.column_config.TextColumn("Région", disabled=True),
                "client": st.column_config.TextColumn("Client", disabled=True),
                "ville": st.column_config.TextColumn("Ville", disabled=True),
                "ref": st.column_config.TextColumn("Ref", disabled=True),
                "motif": st.column_config.TextColumn("Motif", disabled=True),
                "Date": st.column_config.TextColumn("Date", disabled=True)
            }
        )

        if st.button("💾 Enregistrer les changements de statut"):
            # On récupère les colonnes originales
            # Si le statut passe à "Livré", on met la date de règlement
            edited_df.loc[(edited_df['statut'] == 'Livré') & (edited_df['date_reglement'] == ""), 'date_reglement'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            df_to_save = edited_df[COLS_SAV + ["secteur"]]
            # S'assurer que date_crea est bien formatée en string
            df_to_save['date_crea'] = pd.to_datetime(edited_df['date_crea']).dt.strftime("%Y-%m-%d %H:%M")
            
            save_gs_data(df_to_save, "Litiges_SAV", "data/db_sav.csv")
            st.success("Modifications enregistrées !")
            st.rerun()

        # --- NOUVELLE SECTION : PERFORMANCE LIVREURS ---
        st.divider()
        st.subheader("🏎️ Performance des Livreurs (Résolution SAV)")
        
        df_perf = df_sav[df_sav['statut'] == 'Livré'].copy()
        if not df_perf.empty:
            df_perf['date_reglement'] = pd.to_datetime(df_perf['date_reglement'], errors='coerce')
            df_perf['lead_time_h'] = (df_perf['date_reglement'] - df_perf['date_crea']).dt.total_seconds() / 3600
            
            # Agrégation par livreur
            perf_stats = df_perf.groupby('livreur').agg({
                'ref': 'count',
                'lead_time_h': 'mean'
            }).reset_index()
            perf_stats.columns = ['Livreur', 'Réclamations Réglées', 'Délai Moyen (Heures)']
            
            c_p1, c_p2 = st.columns([2, 3])
            with c_p1:
                st.dataframe(perf_stats.sort_values('Réclamations Réglées', ascending=False), hide_index=True)
            with c_p2:
                fig_perf = px.bar(perf_stats, x='Livreur', y='Délai Moyen (Heures)', 
                                 title="Délai Moyen de Règlement par Livreur",
                                 color='Délai Moyen (Heures)',
                                 color_continuous_scale='RdYlGn_r')
                st.plotly_chart(fig_perf, use_container_width=True)
        else:
            st.info("Pas encore assez de données réglées pour afficher les performances.")

# --- LES AUTRES ONGLETS SONT SUPPRIMÉS POUR CENTRALISATION ---

# 4. ADMINISTRATION
with tab_admin:
    # Gestion des Livreurs
    st.divider()
    st.subheader("👥 Gestion des Livreurs & Secteurs")
    df_liv_admin = load_livreurs()
    
    with st.expander("➕ Ajouter / Modifier un Livreur"):
        c_l1, c_l2, c_l3 = st.columns(3)
        l_nom = c_l1.text_input("Nom du Livreur")
        l_sect = c_l2.selectbox("Secteur Assigné (Par défaut)", [""] + all_sectors)
        l_tel = c_l3.text_input("Téléphone")
        
        if st.button("💾 Enregistrer Livreur"):
            if l_nom:
                new_l = pd.DataFrame([{"Nom": l_nom, "Secteur": l_sect, "Téléphone": l_tel, "Prénom": ""}])
                if not df_liv_admin.empty and l_nom in df_liv_admin['Nom'].values:
                    df_liv_admin.loc[df_liv_admin['Nom'] == l_nom, ['Secteur', 'Téléphone']] = [l_sect, l_tel]
                else:
                    df_liv_admin = pd.concat([df_liv_admin, new_l], ignore_index=True)
                save_livreurs(df_liv_admin)
                st.success(f"Livreur {l_nom} mis à jour !")
                st.rerun()

    if not df_liv_admin.empty:
        st.write("Liste des livreurs actifs :")
        for i, row in df_liv_admin.iterrows():
            cl1, cl2, cl3, cl4 = st.columns([2, 2, 2, 0.5])
            cl1.text(f"👤 {row['Nom']}")
            cl2.text(f"📍 {row['Secteur']}")
            cl3.text(f"📞 {row.get('Téléphone', '')}")
            if cl4.button("🗑️", key=f"del_liv_{i}"):
                df_liv_admin = df_liv_admin.drop(i)
                save_livreurs(df_liv_admin)
                st.rerun()

    st.divider()
    st.subheader("🎯 Configuration SLA Réclamations")
    df_near_config = load_gs_data("SAV_Config", SAV_CONFIG_PATH, ["Secteur"])
    
    with st.expander("⚙️ Gérer les Secteurs 'Proches' (SLA 48h)", expanded=False):
        st.write("Les secteurs non listés ici seront considérés comme 'Lointains' (SLA 2 semaines).")
        
        new_near = st.multiselect("Ajouter des secteurs proches :", all_sectors, 
                                 default=[str(s).strip().lower() for s in df_near_config['Secteur'].tolist()] if not df_near_config.empty else ["alger 1", "alger 2", "blida", "tipaza", "medea", "alger est"])
        
        if st.button("💾 Enregistrer la Config SLA"):
            df_save_near = pd.DataFrame({"Secteur": new_near})
            save_gs_data(df_save_near, "SAV_Config", SAV_CONFIG_PATH)
            st.success("Configuration SLA mise à jour !")
            st.rerun()

    st.divider()
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("🗑️ Nettoyage des Données (Admin)")
        st.error("⚠️ Cette action videra toutes les expéditions en cours pour tous les secteurs.")
        confirm_route = st.checkbox("Confirmer la réinitialisation des feuilles de route")
        if st.button("🔴 Réinitialiser toutes les Feuilles de Route", use_container_width=True, disabled=not confirm_route):
            st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])
            st.success("Toutes les feuilles de route ont été réinitialisées.")
            st.rerun()
    else:
        st.info("Les fonctions de nettoyage sont réservées à l'administrateur.")
