import streamlit as st
import pandas as pd
import os
import io
import qrcode
from PIL import Image
from datetime import datetime
from fpdf import FPDF
import plotly.express as px
from utils_ia import ask_ai, is_ia_enabled
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ET CHEMINS ---
DATA_RECOUV = "data_recouvrement.csv"
DATA_CLIENTS = "base_clients.csv"
COLS_RECOUV = ["Client", "Facture", "Date", "Montant Initial", "Montant Réglé", "Reste à payer", "Mode Paiement", "Livreur", "Région", "Statut", "Commentaires"]
COLS_CLIENTS = ["Nom Client", "Région", "Téléphone", "Secteur"]
STATUS_OPTIONS = ["En attente", "Partiel", "Réglé", "Clôturé", "Annulé", "Litige"]
GS_CREDS_PATH = "google_creds.json"
GS_CONFIG_PATH = "gs_config.txt"

from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui, get_gs_client, get_gs_url, GS_CREDS_PATH, GS_CONFIG_PATH

st.set_page_config(page_title="Recouvrement Pharmaciel", layout="wide")
show_sync_ui("Recouvrement", DATA_RECOUV, COLS_RECOUV)

# --- FONCTIONS DE GESTION DES DONNÉES (WRAPPERS) ---
def load_data(path, columns):
    worksheet_name = "Recouvrement" if path == DATA_RECOUV else "Base_Clients"
    df = load_gs_data(worksheet_name, path, columns)
    # Nettoyage spécifique aux montants
    for col in ["Montant Initial", "Montant Réglé", "Reste à payer"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    
    # Assurer que les colonnes de texte sont bien de type string (pour éviter les erreurs st.data_editor avec des NaNs)
    text_cols = ["Statut", "Commentaires", "Client", "Facture", "Date", "Mode Paiement", "Livreur", "Région", "Nom Client", "Téléphone", "Secteur"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
            
    return df

def save_data(df, path):
    worksheet_name = "Recouvrement" if path == DATA_RECOUV else "Base_Clients"
    save_gs_data(df, worksheet_name, path)
    return df

def get_livreur(region_val):
    reg = str(region_val).strip().upper() if pd.notna(region_val) else ""
    if not reg: return "NON ASSIGNÉ"
    
    try:
        from utils_gsheets import load_gs_data
        df_livreurs = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Prénom", "Téléphone", "Secteur"])
        if not df_livreurs.empty:
            # Recherche exacte
            match = df_livreurs[df_livreurs["Secteur"].astype(str).str.strip().str.upper() == reg]
            if not match.empty:
                return str(match.iloc[0]["Nom"]).strip().upper()
            
            # Recherche partielle (si la région contient le secteur)
            for _, row in df_livreurs.iterrows():
                secteur = str(row["Secteur"]).strip().upper()
                if secteur and secteur in reg:
                    return str(row["Nom"]).strip().upper()
    except Exception as e:
        pass # Fallback silencieux en cas d'erreur de chargement
    
    return "NON ASSIGNÉ"

def generate_pdf(df, livreur_name):
    mission_id = f"REC-{int(datetime.now().timestamp())}"
    total_du = df["Reste à payer"].sum() if "Reste à payer" in df.columns else 0
    
    # Génération du QR Code
    qr_data = f"ID:{mission_id}|Livreur:{livreur_name}|Date:{datetime.now().strftime('%d/%m/%Y')}|Clients:{len(df)}|Total:{total_du:.2f} DA"
    qr_img = qrcode.make(qr_data)
    qr_path = f"temp_qr_recouv_{mission_id}.png"
    qr_img.save(qr_path)

    pdf = FPDF()
    pdf.add_page()
    
    # En-tête avec QR Code à droite
    pdf.set_font("Arial", "B", 16)
    pdf.cell(150, 10, f"FEUILLE DE ROUTE RECOUVREMENT", ln=False, align='L')
    pdf.image(qr_path, x=165, y=8, w=35)  # QR en haut à droite
    pdf.ln(12)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(190, 8, f"Livreur : {livreur_name}", ln=True, align='L')
    pdf.set_font("Arial", "", 11)
    pdf.cell(190, 8, f"Date : {datetime.now().strftime('%d/%m/%Y')}   |   Ref. Mission : {mission_id}", ln=True)
    pdf.cell(190, 8, f"Nb Clients : {len(df)}   |   Total à recouvrer : {total_du:,.2f} DA", ln=True)
    pdf.ln(8)
    
    # Entête du tableau PDF
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 10, "Client", 1, 0, 'C', True)
    pdf.cell(35, 10, "Region", 1, 0, 'C', True)
    pdf.cell(35, 10, "Montant", 1, 0, 'C', True)
    pdf.cell(25, 10, "Mode", 1, 0, 'C', True)
    pdf.cell(35, 10, "Pointage", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(60, 10, str(row['Client'])[:30].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(35, 10, str(row['Région']), 1)
        pdf.cell(35, 10, f"{row['Reste à payer']:,.2f} DA", 1, 0, 'R')
        pdf.cell(25, 10, str(row['Mode Paiement']), 1, 0, 'C')
        pdf.cell(35, 10, "", 1, 1)
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        result = bytes(raw)
    else:
        result = raw.encode('latin-1', 'replace')
    
    if os.path.exists(qr_path): os.remove(qr_path)
    return result

def generate_relance_pdf(client_name, df_client, total_du):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "DARPHARM SOLUTION - MISE EN DEMEURE / RELANCE", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Date : {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"A l'attention de : {client_name}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 11)
    texte = (
        "Cher client,\n\n"
        "Sauf erreur ou omission de notre part, nous constatons que votre compte client presente "
        f"actuellement un solde debiteur de {total_du:,.2f} DA.\n\n"
        "Voici le detail des factures / montants en attente :\n"
    )
    pdf.multi_cell(0, 8, texte.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 8, "Facture / Ref", 1)
    pdf.cell(40, 8, "Date", 1)
    pdf.cell(40, 8, "Montant Du (DA)", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    for _, row in df_client.iterrows():
        fac = str(row.get('Facture', 'N/A'))
        d = str(row.get('Date', ''))
        mnt = f"{row.get('Reste à payer', 0.0):,.2f}"
        
        pdf.cell(60, 8, fac[:25].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(40, 8, d.encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(40, 8, mnt.encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.ln()
        
    pdf.ln(10)
    footer = "Nous vous remercions de bien vouloir regulariser cette situation dans les plus brefs delais.\n\nCordialement,\nLe Service Recouvrement"
    pdf.multi_cell(0, 8, footer.encode('latin-1', 'replace').decode('latin-1'))
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

# --- INTERFACE UTILISATEUR ---
st.title("💰 Système de Recouvrement")

tabs = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "🗄️ Archives", "📈 Analyse Financière", "⚙️ Administration"])

# ONGLET 1 : SAISIE ET IMPORT
with tabs[0]:
    col1, col2 = st.columns([1, 2])
    df_clients = load_data(DATA_CLIENTS, COLS_CLIENTS)
    
    with col1:
        st.subheader("Saisie Manuelle")
        with st.form("form_rec", clear_on_submit=True):
            if not df_clients.empty:
                noms_valides = sorted([n for n in df_clients["Nom Client"].unique() if str(n).lower() != 'nan'])
                nom_sel = st.selectbox("Client", noms_valides, index=None, placeholder="Rechercher ou sélectionner un client...")
                
                if nom_sel:
                    # Recherche sécurisée de la région
                    match = df_clients[df_clients["Nom Client"] == nom_sel]["Région"]
                    reg_auto = match.values[0] if not match.empty else ""
                else:
                    reg_auto = ""
            else:
                nom_sel = st.text_input("Nom Client")
                reg_auto = st.text_input("Région")
                
            col_m1, col_m2 = st.columns(2)
            montant_ini = col_m1.number_input("Montant Initial", min_value=0.0)
            montant_reg = col_m2.number_input("Montant Réglé", min_value=0.0)
            
            mode = st.selectbox("Mode de Paiement", ["CASH", "CHÈQUE", "VERSEMENT", "TRAITE"])
            statut = st.selectbox("Statut Initial", STATUS_OPTIONS)
            comm = st.text_area("Commentaires / Notes", placeholder="Ex: Promesse de paiement pour lundi...")
            
            if st.form_submit_button("➕ Ajouter à la liste"):
                if not nom_sel:
                    st.error("Veuillez sélectionner un client.")
                else:
                    db = load_data(DATA_RECOUV, COLS_RECOUV)
                    reste = max(0.0, montant_ini - montant_reg)
                    new_row = pd.DataFrame([{
                        "Client": nom_sel, 
                        "Facture": f"MANUEL_{datetime.now().strftime('%d%m%H%M')}",
                        "Date": str(datetime.now().date()),
                        "Montant Initial": montant_ini,
                        "Montant Réglé": montant_reg,
                        "Reste à payer": reste,
                        "Mode Paiement": mode, 
                        "Livreur": get_livreur(reg_auto), 
                        "Région": reg_auto, 
                        "Statut": statut,
                        "Commentaires": comm
                    }])
                    save_data(pd.concat([db, new_row], ignore_index=True), DATA_RECOUV)
                    st.success("Dossier créé !")
                    st.rerun()

    with col2:
        st.subheader("Import Excel")
        f_rec = st.file_uploader("Déposer rec.xlsx", type=["xlsx"])
        if f_rec:
            df_ex = pd.read_excel(f_rec)
            if st.button("🚀 Valider l'importation"):
                # Nettoyage et complétion des colonnes pour le nouveau format
                if "Région" not in df_ex.columns: df_ex["Région"] = "INCONNU"
                if "Montant Initial" not in df_ex.columns and "Reste à payer" in df_ex.columns:
                    df_ex["Montant Initial"] = df_ex["Reste à payer"]
                if "Montant Réglé" not in df_ex.columns:
                    df_ex["Montant Réglé"] = 0.0
                
                df_ex["Livreur"] = df_ex["Région"].apply(get_livreur)
                df_ex["Date"] = str(datetime.now().date())
                df_ex["Statut"] = "En attente"
                df_ex["Reste à payer"] = df_ex["Montant Initial"] - df_ex["Montant Réglé"]
                
                db_old = load_data(DATA_RECOUV, COLS_RECOUV)
                save_data(pd.concat([db_old, df_ex], ignore_index=True), DATA_RECOUV)
                st.success("Import terminé !")
                st.rerun()

# ONGLET 2 : FEUILLES DE ROUTE (AVEC SUPPRESSION DOUBLONS ET RÉINITIALISATION)
with tabs[1]:
    df_main = load_data(DATA_RECOUV, COLS_RECOUV)
    if not df_main.empty:
        livs = sorted([str(l) for l in df_main["Livreur"].unique() if str(l).lower() != 'nan'])
        sel_liv = st.selectbox("Sélectionner Livreur", livs)
        
        # FILTRAGE ET SUPPRESSION AUTOMATIQUE DES DOUBLONS
        mask = df_main["Livreur"] == sel_liv
        df_display = df_main[mask].drop_duplicates(subset=["Client", "Reste à payer"], keep='first').copy()
        
        col_btns = st.columns([1, 1, 2])
        with col_btns[0]:
            st.download_button("📥 Télécharger PDF", generate_pdf(df_display, sel_liv), f"Route_{sel_liv}.pdf")
        
        with col_btns[1]:
            st.write("") # Espace vide à la place du bouton supprimé

        edited = st.data_editor(df_display, use_container_width=True, hide_index=True)
        
        if st.button("💾 Sauvegarder Statuts & Montants"):
            # Recalcul automatique du reste à payer avant sauvegarde
            edited["Reste à payer"] = (edited["Montant Initial"] - edited["Montant Réglé"]).clip(lower=0)
            
            df_final = pd.concat([df_main[~mask], edited], ignore_index=True)
            save_data(df_final, DATA_RECOUV)
            st.success("Données mises à jour et soldes recalculés !")
            st.rerun()
    else:
        st.info("Aucune donnée disponible.")

# ONGLET 3 : SUIVI GLOBAL (FILTRÉ)
with tabs[2]:
    st.subheader("État Global des Recouvrements Actifs")
    df_all = load_data(DATA_RECOUV, COLS_RECOUV)
    
    # Séparation Actifs / Archivés
    status_archived = ["Clôturé", "Annulé", "Réglé"]
    df_global = df_all[~df_all["Statut"].isin(status_archived)].copy()
    
    if not df_global.empty:
        # Filtre par statut
        col_f1, col_f2 = st.columns([1, 2])
        filter_status = col_f1.selectbox("Filtrer par statut", ["Tous les actifs"] + [s for s in STATUS_OPTIONS if s not in status_archived])
        
        if filter_status != "Tous les actifs":
            df_view = df_global[df_global["Statut"] == filter_status]
        else:
            df_view = df_global

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Actif à recouvrer", f"{df_view['Reste à payer'].sum():,.2f} DA")
        c2.metric("Dossiers en vue", len(df_view))
        c3.metric("En attente critique", len(df_view[df_view["Statut"] == "En attente"]))
        
        # Action si "En attente" est sélectionné ou présent
        if "En attente" in df_view["Statut"].values:
            st.info("💡 **Conseil :** Vous avez des dossiers 'En attente'. Pensez à générer une relance ou à envoyer un message WhatsApp ci-dessous.")

        # Tableau éditable avec liste déroulante Statut
        edited_global = st.data_editor(
            df_view.sort_values("Date", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Statut": st.column_config.SelectboxColumn(
                    "Statut",
                    options=STATUS_OPTIONS,
                    required=True,
                    width="medium"
                ),
                "Commentaires": st.column_config.TextColumn("Commentaires", width="large")
            },
            key="editor_suivi_global"
        )

        if st.button("💾 Sauvegarder & Archiver les clôturés", type="primary", use_container_width=True):
            # Recalcul du Reste à payer
            edited_global["Reste à payer"] = (edited_global["Montant Initial"] - edited_global["Montant Réglé"]).clip(lower=0)

            # Séparation : à archiver vs à garder actifs
            to_archive = edited_global[edited_global["Statut"].isin(status_archived)].copy()
            to_keep    = edited_global[~edited_global["Statut"].isin(status_archived)].copy()

            if not to_archive.empty:
                to_archive["Date Archivage"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                # Charger les archives existantes et fusionner
                archive_path = "data_archive_recouvrement.csv"
                archive_cols = COLS_RECOUV + ["Date Archivage"]
                if os.path.exists(archive_path):
                    df_arch_old = pd.read_csv(archive_path, sep=',', encoding='utf-8-sig')
                else:
                    df_arch_old = pd.DataFrame(columns=archive_cols)
                df_arch_new = pd.concat([df_arch_old, to_archive.reindex(columns=archive_cols, fill_value="")], ignore_index=True)
                df_arch_new.to_csv(archive_path, index=False, sep=',', encoding='utf-8-sig')
                st.success(f"✅ {len(to_archive)} dossier(s) archivé(s) avec succès !")

            # Reconstruire la base complète (actifs non touchés + édités actifs)
            df_untouched = df_all[df_all["Statut"].isin(status_archived)]  # archives déjà existantes
            df_final = pd.concat([df_untouched, df_global[~df_global.index.isin(df_view.index)], to_keep], ignore_index=True)
            save_data(df_final, DATA_RECOUV)
            st.rerun()
        
        st.divider()
        st.subheader("✉️ Génération de Lettres de Relance")
        clients_impayes = df_global[df_global['Reste à payer'] > 0]['Client'].dropna().unique().tolist()
        
        if clients_impayes:
            client_relance = st.selectbox("Sélectionner un client pour la relance", clients_impayes, index=None, placeholder="Choisir un client pour la relance...")
            
            if client_relance:
                df_client_impayes = df_global[(df_global['Client'] == client_relance) & (df_global['Reste à payer'] > 0)]
                total_client = df_client_impayes['Reste à payer'].sum()
                
                st.write(f"Total dû par **{client_relance}** : {total_client:,.2f} DA")
                
                pdf_relance_bytes = generate_relance_pdf(client_relance, df_client_impayes, total_client)
                
                st.download_button(
                    label="📥 Télécharger Lettre de Relance (PDF)",
                    data=pdf_relance_bytes,
                    file_name=f"Relance_{client_relance.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            else:
                st.info("Veuillez sélectionner un client pour voir les options de relance.")
            
            # --- PHASE 5: WHATSAPP LINK ---
            st.write("---")
            st.subheader("📲 Relance Rapide via WhatsApp")
            
            # Recherche sécurisée du téléphone
            match_phone = df_clients[df_clients["Nom Client"] == client_relance]["Téléphone"] if not df_clients.empty else pd.Series()
            client_phone = match_phone.values[0] if not match_phone.empty else ""
            
            if pd.notna(client_phone) and str(client_phone) != "":
                # Nettoyage du numéro (garder uniquement les chiffres)
                phone_clean = "".join(filter(str.isdigit, str(client_phone)))
                if not phone_clean.startswith("213"): phone_clean = "213" + phone_clean.lstrip("0")
                
                msg = f"Bonjour {client_relance}, nous vous relançons concernant un solde débiteur de {total_client:,.2f} DA. Merci de régulariser la situation. Cordialement, Service Recouvrement Darpharm Solution."
                wa_link = f"https://wa.me/{phone_clean}?text={msg.replace(' ', '%20')}"
                
                st.link_button(f"💬 Envoyer Relance Standard (WhatsApp)", wa_link)
                
                # --- ASSISTANT IA POUR LA RELANCE ---
                if is_ia_enabled():
                    st.write("---")
                    st.markdown("### 🤖 Assistant IA de Relance")
                    st.info("L'IA va rédiger un message de recouvrement personnalisé en analysant la situation du client.")
                    
                    tone = st.selectbox("Ton du message", ["Professionnel et courtois", "Amical (Bon client)", "Ferme et urgent (Retard important)"])
                    
                    if st.button("✨ Générer un message sur mesure avec l'IA"):
                        with st.spinner("L'IA rédige le message..."):
                            factures_str = "\n".join([f"- Facture {row.get('Facture', 'N/A')} du {row.get('Date', '')}: {row.get('Reste à payer', 0.0)} DA" for _, row in df_client_impayes.iterrows()])
                            
                            prompt = f"""
                            Rédige un message WhatsApp de relance de paiement pour le client {client_relance}.
                            Le ton doit être : {tone}.
                            Le total dû est de {total_client:,.2f} DA.
                            Détail des factures :
                            {factures_str}
                            
                            Le message doit être poli, professionnel, inclure des émojis adaptés et être prêt à être envoyé par le Service Recouvrement de Darpharm Solution. Ne mets pas d'objet de mail, commence directement par Bonjour.
                            """
                            ai_message = ask_ai(prompt)
                            st.session_state[f"ai_msg_{client_relance}"] = ai_message
                    
                    if f"ai_msg_{client_relance}" in st.session_state:
                        ai_text = st.text_area("Message IA (vous pouvez le modifier)", st.session_state[f"ai_msg_{client_relance}"], height=200)
                        wa_link_ai = f"https://wa.me/{phone_clean}?text={ai_text.replace(' ', '%20').replace(chr(10), '%0A')}"
                        st.link_button(f"🚀 Envoyer ce message IA via WhatsApp", wa_link_ai, type="primary")

            else:
                st.warning("Numéro de téléphone manquant pour ce client dans la base.")
        else:
            st.success("Aucun client n'a de reste à payer. Tout est en règle !")
# ONGLET 4 : ARCHIVES
with tabs[3]:
    st.subheader("🗄️ Archives des dossiers terminés")
    df_all_arch = load_data(DATA_RECOUV, COLS_RECOUV)
    status_archived = ["Clôturé", "Annulé", "Réglé"]
    df_arch = df_all_arch[df_all_arch["Statut"].isin(status_archived)].copy()
    
    if not df_arch.empty:
        st.write(f"Il y a **{len(df_arch)}** dossiers archivés.")
        st.dataframe(df_arch.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        
        if st.button("📥 Exporter les archives en Excel"):
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_arch.to_excel(writer, index=False, sheet_name='Archives')
            st.download_button(
                label="📁 Télécharger le fichier Excel",
                data=output.getvalue(),
                file_name=f"Archives_Recouvrement_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("Aucune archive pour le moment.")

# ONGLET 5 : ANALYSE FINANCIÈRE (BALANCE ÂGÉE)
with tabs[4]:
    st.header("📈 Dashboard Financier & Balance Âgée")
    df_global = load_data(DATA_RECOUV, COLS_RECOUV)
    
    if not df_global.empty:
        # Analyse de l'âge de la balance
        df_global['Date_dt'] = pd.to_datetime(df_global['Date'], errors='coerce')
        now = pd.Timestamp(datetime.now().date())
        
        df_global['Ancienneté'] = (now - df_global['Date_dt']).dt.days.fillna(0)
        
        # S'assurer que le reste à payer est numérique
        df_global['Reste à payer'] = pd.to_numeric(df_global['Reste à payer'], errors='coerce').fillna(0)
        
        def age_bucket(days):
            if days <= 15: return "0-15 Jours"
            if days <= 30: return "16-30 Jours"
            if days <= 60: return "31-60 Jours"
            return "+60 Jours"
        
        df_global['Tranche'] = df_global['Ancienneté'].apply(age_bucket)
        
        # Graphiques
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("📁 Balance Âgée")
            df_age = df_global.groupby('Tranche')['Reste à payer'].sum().reindex(["0-15 Jours", "16-30 Jours", "31-60 Jours", "+60 Jours"]).reset_index()
            fig_age = px.bar(df_age, x='Tranche', y='Reste à payer', color='Tranche', 
                             color_discrete_sequence=px.colors.sequential.Reds_r, template="plotly_dark")
            st.plotly_chart(fig_age, use_container_width=True)
            
        with col_g2:
            st.subheader("🚚 Dette par Livreur")
            df_liv_debt = df_global.groupby('Livreur')['Reste à payer'].sum().reset_index()
            fig_pie = px.pie(df_liv_debt, values='Reste à payer', names='Livreur', hole=0.4, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        st.divider()
        st.subheader("🚨 Risques Clients (+60 Jours)")
        df_risques = df_global[df_global['Tranche'] == "+60 Jours"].sort_values('Ancienneté', ascending=False)
        if not df_risques.empty:
            st.warning(f"Il y a {len(df_risques)} factures impayées depuis plus de 60 jours !")
            st.dataframe(df_risques, use_container_width=True)
        else:
            st.success("Aucun client n'a de dettes de plus de 60 jours.")
            
    else:
        st.info("Aucune donnée pour l'analyse financière.")

# ONGLET 6 : ADMINISTRATION
with tabs[5]:
    st.subheader("🌐 Connexion Google Sheets (Cloud)")
    st.info("Cette section permet de synchroniser le module Recouvrement avec un Google Sheet pour un accès collaboratif.")
    
    with st.expander("🛠️ Configuration GSheets"):
        c_gs1, c_gs2 = st.columns(2)
        
        # 1. Upload des credentials
        uploaded_json = c_gs1.file_uploader("1. Upload 'service_account.json'", type="json")
        if uploaded_json:
            with open(GS_CREDS_PATH, "wb") as f:
                f.write(uploaded_json.getbuffer())
            st.success("Fichier credentials enregistré !")
            
        # 2. Saisie de l'URL
        current_url = get_gs_url() or ""
        new_url = c_gs2.text_input("2. URL du Google Sheet", value=current_url)
        if c_gs2.button("Enregistrer l'URL"):
            with open(GS_CONFIG_PATH, "w") as f:
                f.write(new_url)
            st.success("URL enregistrée !")
            st.rerun()

        st.write("---")
        st.markdown("### 🚀 Migration groupée vers le Cloud")
        c_mig1, c_mig2 = st.columns(2)
        
        if c_mig1.button("📊 Migrer Recouvrement", use_container_width=True):
            with st.spinner("Migration..."):
                df = load_data(DATA_RECOUV, COLS_RECOUV)
                save_data(df, DATA_RECOUV)
                st.success("Recouvrement migré !")

        if c_mig2.button("👥 Migrer Base Clients", use_container_width=True):
            with st.spinner("Migration..."):
                df = load_data(DATA_CLIENTS, COLS_CLIENTS)
                save_data(df, DATA_CLIENTS)
                st.success("Base Clients migrée !")

        c_mig3, c_mig4 = st.columns(2)
        if c_mig3.button("🚚 Migrer Livreurs", use_container_width=True):
            import importlib.util
            spec = importlib.util.spec_from_file_location("expedition", "pages/1_expedition.py")
            exp_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exp_mod)
            with st.spinner("Migration..."):
                df = exp_mod.load_livreurs()
                exp_mod.save_livreurs(df)
                st.success("Livreurs migrés !")

        if c_mig4.button("🗺️ Migrer Secteurs/Clients Logistique", use_container_width=True):
            import importlib.util
            spec = importlib.util.spec_from_file_location("expedition", "pages/1_expedition.py")
            exp_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exp_mod)
            with st.spinner("Migration..."):
                df = exp_mod.load_clients()
                exp_mod.save_clients(df)
                st.success("Secteurs migrés !")

    st.divider()
    st.subheader("👥 Synchronisation Centralisée")
    st.info("La gestion des clients et l'affectation régionale des livreurs sont centralisées. Vous pouvez forcer la mise à jour immédiate depuis le Cloud ici.")
    
    col_sync1, col_sync2 = st.columns(2)
    with col_sync1:
        if st.button("🔄 Synchroniser Clients & Livreurs", use_container_width=True, help="Force le rechargement des bases clients et livreurs depuis Google Sheets"):
            with st.spinner("Synchronisation..."):
                st.cache_data.clear() # Vider le cache pour forcer le reload global
                df_sync = load_data(DATA_CLIENTS, COLS_CLIENTS)
                from utils_gsheets import load_gs_data
                df_liv = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Prénom", "Téléphone", "Secteur"])
                st.success(f"✅ Synchronisation réussie : {len(df_sync)} clients et {len(df_liv)} livreurs à jour !")
                st.rerun()
    
    with col_sync2:
        if st.session_state.current_user.get('role') == 'Admin':
            if st.button("🚀 Aller à l'Administration Centrale", use_container_width=True):
                st.switch_page("pages/0_admin_centrale.py")
        else:
            st.warning("Accès Admin Centrale restreint.")

    st.divider()
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("🗑️ Nettoyage des Données (Admin uniquement)")
        st.error("⚠️ Attention : Cette action supprimera définitivement toutes les données de recouvrement enregistrées.")
        
        # Double validation par checkbox pour éviter les erreurs
        confirm = st.checkbox("Je confirme vouloir tout effacer")
        if st.button("🔴 Réinitialiser le système de recouvrement", disabled=not confirm):
            save_data(pd.DataFrame(columns=COLS_RECOUV), DATA_RECOUV)
            st.success("Toutes les données de recouvrement ont été supprimées.")
            st.rerun()
    else:
        st.info("Les fonctions de nettoyage sont réservées à l'administrateur système.")
