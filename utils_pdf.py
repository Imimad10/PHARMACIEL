from fpdf import FPDF
import pandas as pd
from datetime import datetime
import io

class InventoryPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, self.title_text, 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f"Date d'édition : {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_blank_inventory_pdf(df, module_name, columns_to_print):
    """
    df: DataFrame contenant les produits (Master)
    module_name: Nom du module pour le titre
    columns_to_print: Liste de tuples (Nom Colonne Master, Label Affichage, Largeur)
    """
    pdf = InventoryPDF()
    pdf.title_text = f"FICHE D'INVENTAIRE VIERGE - {module_name.upper()}"
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Header du tableau
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font('Arial', 'B', 9)
    
    for col_name, label, width in columns_to_print:
        pdf.cell(width, 8, label, 1, 0, 'C', 1)
    
    # Colonnes vides à ajouter à la fin (Qte, DDP, etc.)
    # On définit les colonnes de saisie manuelle selon le module
    extra_cols = []
    if "Triple" in module_name:
        extra_cols = [("DDP", 20), ("PPA", 15), ("Vrac P.", 18), ("Colis P.", 18), ("Vrac M.", 18), ("Colis M.", 18)]
    else:
        extra_cols = [("DDP", 25), ("QTE RÉELLE", 30), ("OBSERVATIONS", 35)]
        
    for label, width in extra_cols:
        pdf.cell(width, 8, label, 1, 0, 'C', 1)
    pdf.ln()

    # Contenu du tableau
    pdf.set_font('Arial', '', 8)
    for index, row in df.iterrows():
        # Pour éviter que les lignes soient coupées bizarrement
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_fill_color(200, 220, 255)
            pdf.set_font('Arial', 'B', 9)
            for col_name, label, width in columns_to_print:
                pdf.cell(width, 8, label, 1, 0, 'C', 1)
            for label, width in extra_cols:
                pdf.cell(width, 8, label, 1, 0, 'C', 1)
            pdf.ln()
            pdf.set_font('Arial', '', 8)

        for col_name, label, width in columns_to_print:
            val = str(row.get(col_name, ""))[:30] # Tronquer si trop long
            pdf.cell(width, 7, val.encode('latin-1', 'replace').decode('latin-1'), 1)
        
        for label, width in extra_cols:
            pdf.cell(width, 7, "", 1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1', 'replace')
