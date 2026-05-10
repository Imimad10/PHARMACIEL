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

    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_multi_reclam_pdf(items_list):
    """
    items_list: list of dicts, each containing: 
    date, fournisseur, facture, agent, produit, lot, quantite, type, commentaire, Photo_Path
    """
    pdf = ReclamPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    if not items_list:
        return None
        
    first = items_list[0]
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 12, f"RAPPORT DE RECLAMATIONS - {first['fournisseur']}", 1, 1, 'C', fill=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Facture / BL: {first['facture']} | Date: {first['date']}", 0, 1, 'C')
    pdf.ln(5)
    
    for i, item in enumerate(items_list):
        # Vérifier saut de page
        if pdf.get_y() > 220:
            pdf.add_page()
            
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(24, 119, 242)
        pdf.cell(0, 10, f"ARTICLE #{i+1} : {item['produit']}", "T", 1, 'L')
        pdf.set_text_color(0, 0, 0)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(60, 8, f"Lot: {item['lot']}", 0, 0)
        pdf.cell(60, 8, f"Quantite: {item['quantite']}", 0, 0)
        pdf.cell(0, 8, f"Motif: {item['type']}", 0, 1)
        
        pdf.set_font("Arial", 'I', 9)
        pdf.multi_cell(0, 6, f"Observations: {item.get('commentaire', 'N/A')}", 0, 'L')
        
        # Photo si dispo (version réduite pour le rapport groupé)
        photo_path = item.get('Photo_Path', '')
        if photo_path and os.path.exists(photo_path):
            try:
                pdf.image(photo_path, x=140, y=pdf.get_y()-15, w=40)
                pdf.ln(5)
            except: pass
        pdf.ln(5)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 10, f"Rapport genere par {first.get('agent', 'Systeme')} le {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'R')

    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')
