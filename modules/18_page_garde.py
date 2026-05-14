import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Générateur de Page de Garde", layout="centered", page_icon="📄")

def generate_cover_pdf(fournisseur, date_recep, nb_factures, observation):
    # Création du PDF en orientation paysage (L)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Bordure décorative
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(12, 12, 273, 186)

    # Logo / Nom Entreprise (En haut à gauche)
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(91, 108, 249)
    pdf.cell(0, 15, "DARPHARM SOLUTION", ln=True, align='L')
    
    pdf.ln(20)
    
    # Titre Central
    pdf.set_font("Arial", 'B', 45)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 30, "PAGE DE GARDE RÉCEPTION", ln=True, align='C')
    
    pdf.ln(10)
    
    # Fournisseur (Très Gros)
    pdf.set_font("Arial", 'B', 60)
    pdf.cell(0, 40, fournisseur.upper(), ln=True, align='C')
    
    pdf.ln(10)
    
    # Date et Détails
    pdf.set_font("Arial", 'B', 30)
    pdf.cell(135, 20, f"DATE: {date_recep}", ln=False, align='L')
    if nb_factures:
        pdf.cell(135, 20, f"NB FACTURES: {nb_factures}", ln=True, align='R')
    else:
        pdf.ln(20)
        
    # Observation (En bas)
    if observation:
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 18)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 10, f"Observation: {observation}", align='C')

    # Pied de page
    pdf.set_y(-25)
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, f"Généré par Pharmaciel Pro le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", align='C')

    # On gère les différentes versions de FPDF (dest='S' ou retour direct)
    try:
        raw = pdf.output(dest='S')
    except:
        raw = pdf.output()
        
    if isinstance(raw, str):
        return raw.encode('latin-1', 'replace')
    return bytes(raw)

# --- INTERFACE ---
st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: #5b6cf9; font-weight: 900;">📄 Générateur de Page de Garde</h1>
        <p style="color: #64748b;">Créez instantanément une couverture pour vos dossiers de factures physiques.</p>
    </div>
""", unsafe_allow_html=True)

with st.container(border=True):
    col1, col2 = st.columns(2)
    
    with col1:
        fourn = st.text_input("🏢 Nom du Fournisseur / Laboratoire", placeholder="Ex: SANOFI, BIOPHARM...")
        date_rec = st.date_input("📅 Date de Réception", value=datetime.now())
        
    with col2:
        nb_fac = st.text_input("🔢 Nombre de factures dans le lot (Optionnel)")
        obs = st.text_area("✍️ Observation particulière", placeholder="Ex: Manque BL, Urgent, etc.")

    st.divider()
    
    if fourn:
        pdf_bytes = generate_cover_pdf(fourn, date_rec.strftime("%d/%m/%Y"), nb_fac, obs)
        
        st.success("✅ Page de garde prête !")
        st.download_button(
            label="📥 Télécharger & Imprimer (Paysage)",
            data=pdf_bytes,
            file_name=f"PageGarde_{fourn}_{date_rec}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        # Aperçu visuel simplifié
        st.markdown(f"""
            <div style="border: 2px solid #5b6cf9; border-radius: 10px; padding: 40px; background: white; text-align: center; margin-top: 20px;">
                <h3 style="color: #64748b; margin: 0;">APERÇU</h3>
                <h1 style="font-size: 50px; margin: 20px 0;">{fourn.upper()}</h1>
                <h2 style="color: #5b6cf9;">{date_rec.strftime("%d/%m/%Y")}</h2>
            </div>
        """, unsafe_allow_html=True)
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
