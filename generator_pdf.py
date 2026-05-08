from fpdf import FPDF
from datetime import datetime
import os

class ReclamPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
        self.set_font("Arial", 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'DARPHARM - RECLAMATION LOGISTIQUE', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}} - DarPharm Solutions', 0, 0, 'C')

def generate_reclam_pdf(data, image_path=None):
    """
    data: dict containing keys: date, fournisseur, agent, produit, lot, quantite, motif, commentaire
    image_path: local path to the proof image
    """
    pdf = ReclamPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    
    # Infos générales
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"DETAILS DU LITIGE - {data.get('date', '')}", 1, 1, 'L', fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 11)
    col_width = 95
    
    # Tableau de détails
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(col_width, 8, "Fournisseur:", 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(col_width, 8, str(data.get('fournisseur', '')), 1, 1)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(col_width, 8, "Produit:", 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(col_width, 8, str(data.get('produit', '')), 1, 1)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(col_width, 8, "N Lot / Quantité:", 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(col_width, 8, f"Lot: {data.get('lot', '')} | Qte: {data.get('quantite', '')}", 1, 1)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(col_width, 8, "Motif:", 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(col_width, 8, str(data.get('type', '')), 1, 1)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(col_width, 8, "Agent Saisie:", 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(col_width, 8, str(data.get('agent', '')), 1, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "Commentaire / Observations:", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 8, str(data.get('commentaire', 'N/A')), border=1)
    
    pdf.ln(10)
    
    # Image de preuve
    if image_path and os.path.exists(image_path):
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, "PREUVE VISUELLE (Photo):", 0, 1)
        # Redimensionnement auto pour tenir dans la page (max 180mm large)
        pdf.image(image_path, x=15, w=150)
    else:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "(Aucune photo jointe au dossier)", 0, 1)

    # Output bytes correctly for fpdf2
    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')
