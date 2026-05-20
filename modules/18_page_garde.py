import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
import os
import base64
import tempfile
import requests
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
st.set_page_config(page_title="Générateur de Page de Garde", layout="centered", page_icon="📄")

def generate_cover_pdf(fournisseur, date_recep, nb_factures, observation, model="Classique", logo_b64=""):
    # Création du PDF en orientation paysage (L)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # --- STYLES PAR MODÈLE ---
    theme_color = (91, 108, 249) # Bleu par défaut
    if model == "Urgent / Alerte":
        theme_color = (255, 75, 75) # Rouge
    elif model == "Épuré":
        theme_color = (100, 100, 100) # Gris
    elif model == "Moderne / Chic":
        theme_color = (233, 69, 96) # Rose/Rouge Chic
    
    # Bordure décorative (sauf pour épuré)
    if model != "Épuré":
        pdf.set_draw_color(*theme_color)
        pdf.set_line_width(2)
        pdf.rect(10, 10, 277, 190)
        pdf.set_line_width(0.5)
        pdf.rect(12, 12, 273, 186)

    # Entête DarPharm & Logo
    turquoise = (0, 157, 196)
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(*turquoise)
    pdf.set_xy(15, 15)
    
    # Logo Société DarPharm
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=15, y=12, w=25)
        pdf.set_xy(45, 18)
    
    pdf.cell(0, 10, "DARPHARM SOLUTION", ln=True, align='L')
    
    # Affichage du logo fournisseur en haut à droite s'il existe
    if logo_b64 and logo_b64 != "nan":
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(base64.b64decode(logo_b64))
                tmp_path = tmp.name
            pdf.image(tmp_path, x=240, y=15, w=40)
            os.unlink(tmp_path)
        except Exception:
            pass

    pdf.ln(30) # Espace après entête
    
    # Badge Urgent
    if model == "Urgent / Alerte":
        pdf.set_font("Arial", 'B', 45)
        pdf.set_text_color(255, 75, 75)
        pdf.cell(0, 25, "!!! URGENT !!!", ln=True, align='C')
        pdf.ln(10)
    
    # Fournisseur (Dynamique selon longueur)
    name_clean = fournisseur.upper().strip()
    f_size = 70
    if len(name_clean) > 15: f_size = 55
    if len(name_clean) > 25: f_size = 40
    if len(name_clean) > 35: f_size = 30
    
    pdf.set_font("Arial", 'B', f_size)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 50, name_clean, ln=True, align='C')
    
    pdf.ln(10)
    
    # Date (Centrée, sans le mot "Date")
    pdf.set_font("Arial", 'B', 35)
    pdf.set_text_color(*turquoise)
    pdf.cell(0, 25, date_recep, ln=True, align='C')
    
    # Détails Facturation (Si présents)
    if nb_factures:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 15, f"NOMBRE DE FACTURES : {nb_factures}", ln=True, align='C')
        
    # Observation (En bas)
    if observation:
        pdf.ln(5)
        pdf.set_font("Arial", 'I', 18)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 10, f"Observation: {observation}", align='C')

    # Pied de page (Forcé sur la page 1)
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-35) # Plus haut
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, f"Généré par DarPharm Solutions le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", align='C')

    try:
        raw = pdf.output(dest='S')
    except:
        raw = pdf.output()
        
    if isinstance(raw, str):
        return raw.encode('latin-1', 'replace')
    return bytes(raw)


# --- CHARGEMENT DES DONNÉES ---
df_fournisseurs = load_gs_data("DB_Fournisseurs", "data/db_fournisseurs.csv", ["Etablissement", "Wilaya", "Activité", "Logo"])
df_fournisseurs = df_fournisseurs.astype(object) # Forçage du type object pour éviter TypeError lors de l'insertion du logo
fourn_list = sorted(df_fournisseurs['Etablissement'].dropna().unique().tolist()) if not df_fournisseurs.empty else []

# --- INTERFACE ---
st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: #5b6cf9; font-weight: 900;">📄 Générateur de Page de Garde</h1>
        <p style="color: #64748b;">Créez instantanément une couverture avec logo pour vos dossiers de factures.</p>
    </div>
""", unsafe_allow_html=True)

with st.container(border=True):
    col1, col2 = st.columns(2)
    
    with col1:
        choix_fourn = st.selectbox("🏢 Nom du Fournisseur / Laboratoire", ["-- Nouveau / Saisie Manuelle --"] + fourn_list)
        if choix_fourn == "-- Nouveau / Saisie Manuelle --":
            fourn = st.text_input("Saisissez le nom manuellement")
        else:
            fourn = choix_fourn
            
        # Section de Synchronisation & Importation de Secours
        with st.expander("🔄 Options de Synchronisation & Import"):
            st.markdown("### ☁️ Synchronisation Cloud")
            if st.button("🔄 Synchroniser les Fournisseurs depuis le Cloud", use_container_width=True):
                with st.spinner("Téléchargement de la base fournisseurs..."):
                    try:
                        st.cache_data.clear()
                        df_sync = load_gs_data("DB_Fournisseurs", "data/db_fournisseurs.csv", ["Etablissement", "Wilaya", "Activité", "Logo"], force_cloud=True)
                        if not df_sync.empty:
                            os.makedirs("data", exist_ok=True)
                            df_sync.to_csv("data/db_fournisseurs.csv", index=False, sep=',', encoding='utf-8-sig')
                            st.success(f"✅ {len(df_sync)} fournisseurs synchronisés avec succès !")
                            st.rerun()
                        else:
                            st.error("Aucun fournisseur trouvé sur le Cloud.")
                    except Exception as e_sync:
                        st.error(f"Erreur de synchronisation : {e_sync}")
            
            st.markdown("---")
            st.markdown("### 📦 Extraction depuis la Base des Lots")
            if st.button("⚙️ Extraire les Fournisseurs depuis la Base des Lots", use_container_width=True):
                with st.spinner("Extraction en cours..."):
                    try:
                        # Charger la base des lots
                        df_lots = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", [])
                        if not df_lots.empty:
                            # Trouver la colonne fournisseur (indépendamment de la casse)
                            fourn_col = None
                            for c in df_lots.columns:
                                if str(c).lower().strip() in ["fournisseur", "fourn", "laboratoire", "labo"]:
                                    fourn_col = c
                                    break
                            
                            if fourn_col:
                                extracted = df_lots[fourn_col].dropna().unique().tolist()
                                extracted = [str(f).strip().upper() for f in extracted if str(f).strip() != ""]
                                
                                if extracted:
                                    # Construire les nouvelles lignes
                                    df_new = pd.DataFrame([{"Etablissement": f, "Wilaya": "", "Activité": "", "Logo": ""} for f in extracted])
                                    df_merged = pd.concat([df_fournisseurs, df_new]).drop_duplicates(subset=["Etablissement"], keep='first')
                                    save_gs_data(df_merged, "DB_Fournisseurs", "data/db_fournisseurs.csv")
                                    st.success(f"✅ {len(df_merged) - len(df_fournisseurs)} nouveaux fournisseurs ajoutés à partir de la base des lots (total : {len(df_merged)}) !")
                                    st.rerun()
                                else:
                                    st.warning("Aucun nom de fournisseur non-vide trouvé dans la colonne.")
                            else:
                                st.error("Impossible de trouver une colonne 'Fournisseur' ou 'Laboratoire' dans le fichier des lots.")
                        else:
                            st.error("La base des lots est actuellement vide ou introuvable.")
                    except Exception as e_lots:
                        st.error(f"Erreur lors de l'extraction des lots : {e_lots}")
            
            st.markdown("---")
            st.markdown("### 📤 Importation depuis un Fichier Excel")
            excel_file = st.file_uploader("Déposer un fichier Excel (Lots, Réceptions, etc.)", type=["xlsx", "xls"], key="excel_fourn_uploader")
            if excel_file:
                try:
                    df_excel = pd.read_excel(excel_file)
                    possible_cols = ["fournisseur", "fourn", "laboratoire", "labo", "établissement", "etablissement", "fabricant", "nom"]
                    found_col = None
                    for col in df_excel.columns:
                        if str(col).lower().strip() in possible_cols:
                            found_col = col
                            break
                    if not found_col:
                        # fuzzy check
                        for col in df_excel.columns:
                            if any(p in str(col).lower() for p in ["fourn", "labo", "etab"]):
                                found_col = col
                                break
                    
                    if found_col:
                        extracted = df_excel[found_col].dropna().unique().tolist()
                        extracted = [str(f).strip().upper() for f in extracted if str(f).strip() != ""]
                        if extracted:
                            df_new = pd.DataFrame([{"Etablissement": f, "Wilaya": "", "Activité": "", "Logo": ""} for f in extracted])
                            df_merged = pd.concat([df_fournisseurs, df_new]).drop_duplicates(subset=["Etablissement"], keep='first')
                            save_gs_data(df_merged, "DB_Fournisseurs", "data/db_fournisseurs.csv")
                            st.success(f"✅ {len(df_merged) - len(df_fournisseurs)} nouveaux fournisseurs ajoutés à partir du fichier Excel (total : {len(df_merged)}) !")
                            st.rerun()
                        else:
                            st.warning("Aucun fournisseur valide trouvé dans la colonne.")
                    else:
                        st.error("Aucune colonne de fournisseur reconnue (ex: 'fournisseur', 'labo') dans le fichier.")
                except Exception as e_ex:
                    st.error(f"Erreur lors de la lecture du fichier Excel : {e_ex}")
            
        date_rec = st.date_input("📅 Date de Réception", value=datetime.now())
        
    with col2:
        nb_fac = st.text_input("🔢 Nombre de factures dans le lot (Optionnel)")
        model_sel = st.selectbox("🎨 Modèle Visuel", ["Classique", "Urgent / Alerte", "Épuré", "Moderne / Chic"])
        obs = st.text_area("✍️ Observation particulière", placeholder="Ex: Manque BL, Urgent, etc.")

    st.divider()
    
    # --- GESTION DU LOGO ---
    st.subheader("🖼️ Identité Visuelle (Logo)")
    logo_base64 = ""
    
    if fourn and not df_fournisseurs.empty and fourn in df_fournisseurs['Etablissement'].values:
        row = df_fournisseurs[df_fournisseurs['Etablissement'] == fourn].iloc[0]
        logo_base64 = str(row.get("Logo", ""))
        if logo_base64.lower() == 'nan': logo_base64 = ""

    col_l1, col_l2 = st.columns([1, 2])
    with col_l1:
        if logo_base64:
            st.image(f"data:image/png;base64,{logo_base64}", width=150, caption="Logo enregistré")
        else:
            st.info("Aucun logo pour le moment.")
            
    with col_l2:
        img_up = st.file_uploader("📥 Glissez une image (Drag & Drop)", type=["png", "jpg", "jpeg"])
        img_url = st.text_input("🔗 Ou collez l'URL d'une image (ex: https://...)")
        
        new_logo_b64 = ""
        if img_up:
            new_logo_b64 = base64.b64encode(img_up.read()).decode()
        elif img_url:
            try:
                resp = requests.get(img_url, timeout=5)
                if resp.status_code == 200:
                    new_logo_b64 = base64.b64encode(resp.content).decode()
            except:
                st.error("Impossible de récupérer l'image depuis ce lien.")
                
        if new_logo_b64:
            st.image(f"data:image/png;base64,{new_logo_b64}", width=80, caption="Aperçu du nouveau logo")
            if st.button("💾 Sauvegarder ce Logo en Base de Données", type="primary"):
                if not df_fournisseurs.empty and fourn in df_fournisseurs['Etablissement'].values:
                    df_fournisseurs.loc[df_fournisseurs['Etablissement'] == fourn, 'Logo'] = new_logo_b64
                else:
                    new_row = {"Etablissement": fourn, "Wilaya": "", "Activité": "", "Logo": new_logo_b64}
                    df_fournisseurs = pd.concat([df_fournisseurs, pd.DataFrame([new_row])])
                
                save_gs_data(df_fournisseurs, "DB_Fournisseurs", "data/db_fournisseurs.csv")
                st.success("✅ Logo sauvegardé avec succès ! Il sera réutilisé automatiquement.")
                st.rerun()

    # Le logo final utilisé pour le PDF est soit le nouveau (non sauvegardé encore, mais uploadé), soit celui en base
    final_logo_b64 = new_logo_b64 if new_logo_b64 else logo_base64

    st.divider()
    
    if fourn:
        pdf_bytes = generate_cover_pdf(fourn, date_rec.strftime("%d/%m/%Y"), nb_fac, obs, model=model_sel, logo_b64=final_logo_b64)
        
        st.download_button(
            label=f"📥 Télécharger la Page de Garde",
            data=pdf_bytes,
            file_name=f"PageGarde_{fourn}_{date_rec}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        # Aperçu visuel simplifié dynamique
        preview_border = "2px solid #5b6cf9"
        preview_color = "#5b6cf9"
        urgent_badge = ""
        
        if model_sel == "Urgent / Alerte":
            preview_border = "5px solid #ff4b4b"
            preview_color = "#ff4b4b"
            urgent_badge = '<h1 style="color: #ff4b4b; font-weight: 900; margin-bottom: 0;">!!! URGENT !!!</h1>'
        elif model_sel == "Épuré":
            preview_border = "1px solid #ccc"
            preview_color = "#333"
        elif model_sel == "Moderne / Chic":
            preview_border = "3px solid #e94560"
            preview_color = "#e94560"
            
        logo_html = f'<img src="data:image/png;base64,{final_logo_b64}" style="position:absolute; top:20px; right:20px; width:80px; object-fit:contain;">' if final_logo_b64 else ''

        html_preview = f"""
            <div style="position:relative; border: {preview_border}; border-radius: 10px; padding: 40px; background: white; text-align: center; margin-top: 20px;">
                {logo_html}
                <h3 style="color: #64748b; margin: 0; font-family: sans-serif;">APERÇU DU MODÈLE</h3>
                {urgent_badge}
                <h1 style="font-size: 50px; margin: 20px 0; color: black; font-family: sans-serif;">{fourn.upper()[:25]}</h1>
                <h2 style="color: {preview_color}; font-family: sans-serif;">{date_rec.strftime("%d/%m/%Y")}</h2>
            </div>
        """
        st.markdown(html_preview, unsafe_allow_html=True)
    else:
        st.info("Veuillez saisir le nom du fournisseur pour générer la page.")

st.markdown("""
    <style>
        .stButton button {
            height: 60px;
            font-size: 20px;
            font-weight: 900;
        }
    </style>
""", unsafe_allow_html=True)
