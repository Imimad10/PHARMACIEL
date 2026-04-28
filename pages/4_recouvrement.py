import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ET CHEMINS ---
DATA_RECOUV = "data_recouvrement.csv"
DATA_CLIENTS = "base_clients.csv"
COLS_RECOUV = ["Client", "Facture", "Mode Paiement", "Région", "Reste à payer", "Livreur", "Date", "Statut"]
COLS_CLIENTS = ["Nom Client", "Région", "Téléphone", "Secteur"]

# --- FONCTIONS DE GESTION DES DONNÉES ---
def load_data(path, columns):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, sep=',', encoding='utf-8-sig')
            # Nettoyage des montants pour éviter les erreurs de calcul
            if "Reste à payer" in df.columns:
                df["Reste à payer"] = pd.to_numeric(
                    df["Reste à payer"].astype(str).str.replace(',', '.').str.replace(r'\s+', '', regex=True), 
                    errors='coerce'
                ).fillna(0.0)
            return df.reindex(columns=columns)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, path):
    # Suppression des lignes vides avant sauvegarde
    df = df.dropna(how='all')
    df.to_csv(path, index=False, sep=',', encoding='utf-8-sig')
    return df

def get_livreur(region_val):
    reg = str(region_val).strip().upper() if pd.notna(region_val) else ""
    mapping = {"ALGER 1": "FETHI", "ALGER 2": "FARES", "ALGER EST": "MAIDI", "TIPAZA": "HAROUN", "BLIDA": "HAROUN"}
    hamid_list = ["MEDEA", "CHLEF", "DJELFA", "AIN-DEFLA", "RELIZANE", "LAGHOUAT", "ORAN"]
    if reg in mapping: return mapping[reg]
    if any(h in reg for h in hamid_list): return "HAMID"
    return "NON ASSIGNÉ"

def generate_pdf(df, livreur_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"FEUILLE DE ROUTE : {livreur_name}", ln=True, align='C')
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    # Entête du tableau PDF
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 10, "Client", 1, 0, 'C', True)
    pdf.cell(35, 10, "Region", 1, 0, 'C', True)
    pdf.cell(35, 10, "Montant", 1, 0, 'C', True)
    pdf.cell(25, 10, "Mode", 1, 0, 'C', True)
    pdf.cell(35, 10, "Pointage", 1, 1, 'C', True) # Colonne vide pour stylo
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(60, 10, str(row['Client'])[:30].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(35, 10, str(row['Région']), 1)
        pdf.cell(35, 10, f"{row['Reste à payer']:,.2f} DA", 1, 0, 'R')
        pdf.cell(25, 10, str(row['Mode Paiement']), 1, 0, 'C')
        pdf.cell(35, 10, "", 1, 1) 
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generate_relance_pdf(client_name, df_client, total_du):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "PHARMACIEL - MISE EN DEMEURE / RELANCE", 0, 1, 'C')
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
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFACE UTILISATEUR ---
st.title("💰 Système de Recouvrement")

tabs = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "📈 Analyse Financière", "⚙️ Administration"])

# ONGLET 1 : SAISIE ET IMPORT
with tabs[0]:
    col1, col2 = st.columns([1, 2])
    df_clients = load_data(DATA_CLIENTS, COLS_CLIENTS)
    
    with col1:
        st.subheader("Saisie Manuelle")
        with st.form("form_rec", clear_on_submit=True):
            if not df_clients.empty:
                noms_valides = sorted([n for n in df_clients["Nom Client"].unique() if str(n).lower() != 'nan'])
                nom_sel = st.selectbox("Client", noms_valides)
                reg_auto = df_clients[df_clients["Nom Client"] == nom_sel]["Région"].values[0]
            else:
                nom_sel = st.text_input("Nom Client")
                reg_auto = st.text_input("Région")
                
            montant = st.number_input("Montant", min_value=0.0)
            mode = st.selectbox("Mode", ["CASH", "CHÈQUE", "VERSEMENT"])
            if st.form_submit_button("Enregistrer"):
                db = load_data(DATA_RECOUV, COLS_RECOUV)
                new_row = pd.DataFrame([{"Client": nom_sel, "Mode Paiement": mode, "Région": reg_auto, "Reste à payer": montant, "Livreur": get_livreur(reg_auto), "Date": str(datetime.now().date()), "Statut": "En attente"}])
                save_data(pd.concat([db, new_row], ignore_index=True), DATA_RECOUV)
                st.success("Enregistré !")
                st.rerun()

    with col2:
        st.subheader("Import Excel")
        f_rec = st.file_uploader("Déposer rec.xlsx", type=["xlsx"])
        if f_rec:
            df_ex = pd.read_excel(f_rec)
            if st.button("🚀 Valider l'importation"):
                df_ex["Livreur"] = df_ex["Région"].apply(get_livreur)
                df_ex["Date"] = str(datetime.now().date())
                df_ex["Statut"] = "En attente"
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
            # BOUTON RÉINITIALISER LE TABLEAU
            if st.button("🗑️ Réinitialiser Tableau", help="Vide toutes les données de recouvrement"):
                save_data(pd.DataFrame(columns=COLS_RECOUV), DATA_RECOUV)
                st.warning("Tableau vidé avec succès.")
                st.rerun()

        edited = st.data_editor(df_display, use_container_width=True, hide_index=True)
        
        if st.button("💾 Sauvegarder Statuts"):
            df_final = pd.concat([df_main[~mask], edited], ignore_index=True)
            save_data(df_final, DATA_RECOUV)
            st.success("Données mises à jour !")
            st.rerun()
    else:
        st.info("Aucune donnée disponible.")

# ONGLET 3 : SUIVI GLOBAL
with tabs[2]:
    st.subheader("État Global des Recouvrements")
    df_global = load_data(DATA_RECOUV, COLS_RECOUV)
    if not df_global.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total à recouvrer", f"{df_global['Reste à payer'].sum():,.2f} DA")
        c2.metric("Nombre de Clients", len(df_global["Client"].unique()))
        c3.metric("En attente", len(df_global[df_global["Statut"] == "En attente"]))
        st.dataframe(df_global.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("✉️ Génération de Lettres de Relance")
        clients_impayes = df_global[df_global['Reste à payer'] > 0]['Client'].dropna().unique().tolist()
        
        if clients_impayes:
            client_relance = st.selectbox("Sélectionner un client pour la relance", clients_impayes)
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
            
            # --- PHASE 5: WHATSAPP LINK ---
            st.write("---")
            st.subheader("📲 Relance Rapide via WhatsApp")
            client_phone = df_clients[df_clients["Nom Client"] == client_relance]["Téléphone"].values[0] if not df_clients.empty else ""
            
            if pd.notna(client_phone) and str(client_phone) != "":
                # Nettoyage du numéro (garder uniquement les chiffres)
                phone_clean = "".join(filter(str.isdigit, str(client_phone)))
                if not phone_clean.startswith("213"): phone_clean = "213" + phone_clean.lstrip("0")
                
                msg = f"Bonjour {client_relance}, nous vous relançons concernant un solde débiteur de {total_client:,.2f} DA. Merci de régulariser la situation. Cordialement, Service Recouvrement Pharmaciel."
                wa_link = f"https://wa.me/{phone_clean}?text={msg.replace(' ', '%20')}"
                
                st.link_button(f"💬 Envoyer Relance WhatsApp à {client_phone}", wa_link)
            else:
                st.warning("Numéro de téléphone manquant pour ce client dans la base.")
        else:
            st.success("Aucun client n'a de reste à payer. Tout est en règle !")
    else:
        st.info("Base de données vide.")

# ONGLET 4 : ANALYSE FINANCIÈRE (BALANCE ÂGÉE)
with tabs[3]:
    st.header("📈 Dashboard Financier & Balance Âgée")
    df_global = load_data(DATA_RECOUV, COLS_RECOUV)
    
    if not df_global.empty:
        # Conversion date
        df_global['Date_dt'] = pd.to_datetime(df_global['Date'], errors='coerce')
        now = pd.to_datetime(datetime.now().date())
        
        # Calcul de l'ancienneté
        df_global['Ancienneté'] = (now - df_global['Date_dt']).dt.days
        
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
            import plotly.express as px
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

# ONGLET 5 : ADMINISTRATION
with tabs[4]:
    st.subheader("Gestion de la Base Clients")
    f_cli = st.file_uploader("Importer base clients (Excel)", type=["xlsx"])
    if f_cli:
        df_cli_ex = pd.read_excel(f_cli)
        if st.button("📥 Fusionner"):
            old_cli = load_data(DATA_CLIENTS, COLS_CLIENTS)
            # Sécurité colonnes
            cols_ok = [c for c in COLS_CLIENTS if c in df_cli_ex.columns]
            updated_cli = pd.concat([old_cli, df_cli_ex[cols_ok]], ignore_index=True).drop_duplicates(subset=["Nom Client"])
            save_data(updated_cli, DATA_CLIENTS)
            st.success("Base clients mise à jour.")
            st.rerun()
    
    base_actuelle = load_data(DATA_CLIENTS, COLS_CLIENTS)
    edited_base = st.data_editor(base_actuelle, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder Base"):
        save_data(edited_base, DATA_CLIENTS)
        st.rerun()
