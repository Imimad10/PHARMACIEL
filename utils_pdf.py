from fpdf import FPDF
import pandas as pd
from datetime import datetime
import io

class InventoryPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, self.title_text, 0, 1, 'C')
        if hasattr(self, 'subtitle_text') and self.subtitle_text:
            self.set_font('Arial', 'B', 11)
            self.cell(0, 8, self.subtitle_text, 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f"Date d'édition : {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def generate_blank_inventory_pdf(df, module_name, columns_to_print, subtitle=""):
    """
    df: DataFrame contenant les produits (Master)
    module_name: Nom du module pour le titre
    columns_to_print: Liste de tuples (Nom Colonne Master, Label Affichage, Largeur)
    subtitle: Sous-titre optionnel (ex: agents affectés)
    """
    pdf = InventoryPDF()
    pdf.title_text = f"FICHE D'INVENTAIRE VIERGE - {module_name.upper()}"
    pdf.subtitle_text = subtitle
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
        # Correspondance avec 16_inventaire_triple.py : Terrain (Vrac), Terrain (Colis), Mini (Colis)
        extra_cols = [("DDP", 20), ("PPA", 15), ("Vrac T.", 18), ("Colis T.", 18), ("Colis M.", 18), ("OBS", 18)]
    else:
        extra_cols = [("DDP", 22), ("VRAC", 15), ("MINISTOCK", 20), ("TOTAL", 15), ("OBSERVATIONS", 28)]
        
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

    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_inventory_report_pdf(df_diff, title="RAPPORT D'INVENTAIRE"):
    """
    df_diff: DataFrame contenant les écarts (doit avoir 'produit', 'lot', 'qte_logi', 'Total', 'Ecart')
    """
    pdf = InventoryPDF()
    pdf.title_text = title.upper()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Statistiques
    total_items = len(df_diff)
    manquants = len(df_diff[df_diff['Ecart'] < 0])
    excedents = len(df_diff[df_diff['Ecart'] > 0])
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. RESUME DES ECARTS", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f"- Nombre total de produits avec ecart : {total_items}", 0, 1)
    pdf.cell(0, 8, f"- Nombre de produits manquants : {manquants}", 0, 1)
    pdf.cell(0, 8, f"- Nombre de produits en excedent : {excedents}", 0, 1)
    pdf.ln(5)
    
    # Tableau des écarts
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    cols = [('produit', 'Produit', 70), ('lot', 'Lot', 30), ('qte_logi', 'Logi', 20), ('Total', 'Reel', 20), ('Ecart', 'Ecart', 20)]
    
    for _, label, w in cols:
        pdf.cell(w, 8, label, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for _, row in df_diff.iterrows():
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 9)
            for _, label, w in cols: pdf.cell(w, 8, label, 1, 0, 'C', 1)
            pdf.ln()
            pdf.set_font('Arial', '', 8)
            
        for key, _, w in cols:
            val = str(row.get(key, ""))[:40]
            align = 'L' if key == 'produit' else 'C'
            pdf.cell(w, 7, val.encode('latin-1', 'replace').decode('latin-1'), 1, 0, align)
        pdf.ln()
        
    # Conclusion
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. CONCLUSION ET VALIDATION", 0, 1)
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(0, 8, "L'inventaire a ete realise et confronte au systeme Logipharm. Les ecarts listes ci-dessus doivent faire l'objet d'une regularisation en stock ou d'une recherche approfondie dans les factures.")
    pdf.ln(15)
    
    # Signatures
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 10, "L'Agent Saisie", 0, 0, 'C')
    pdf.cell(95, 10, "Le Superviseur / Admin", 0, 1, 'C')
    pdf.ln(20)
    pdf.cell(95, 0, "__________________", 0, 0, 'C')
    pdf.cell(95, 0, "__________________", 0, 1, 'C')

    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_reception_pdf(reception_data):
    """
    reception_data: dict with id, date, fournisseur, facture_num, items (list)
    """
    pdf = InventoryPDF()
    pdf.title_text = "FICHE DE RECEPTION & POINTAGE"
    pdf.subtitle_text = f"Fournisseur: {reception_data['fournisseur']} | Facture: {reception_data['facture_num']}"
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Tableau
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    cols = [('produit', 'Désignation', 70), ('lot', 'Lot', 30), ('ddp', 'DDP', 25), ('qte', 'Qte', 20), ('ppa', 'PPA', 20), ('shp', 'SHP', 20)]
    
    for _, label, w in cols:
        pdf.cell(w, 8, label, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for item in reception_data['items']:
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 9)
            for _, label, w in cols: pdf.cell(w, 8, label, 1, 0, 'C', 1)
            pdf.ln()
            pdf.set_font('Arial', '', 8)
            
        for key, _, w in cols:
            val = str(item.get(key, ""))[:40]
            align = 'L' if key == 'produit' else 'C'
            pdf.cell(w, 7, val.encode('latin-1', 'replace').decode('latin-1'), 1, 0, align)
        pdf.ln()
    
    # Pied de page
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    pdf.write(5, f"Reception terminee le {reception_data['date']} par {reception_data.get('created_by', 'Equipe Reception')}")
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')
