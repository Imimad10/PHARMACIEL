import os

pdf_code = '''
def generate_factures_report_pdf(df, livreur_nom='Non specifie', region='Non specifiee'):
    """
    Genere un rapport PDF pour le pointage des factures.
    """
    from fpdf import FPDF
    from datetime import datetime

    pdf = FPDF()
    pdf.add_page()
    
    # En-tete
    pdf.set_font('Arial', 'B', 15)
    pdf.cell(0, 10, 'POINTAGE DE FACTURES', 0, 1, 'C')
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 6, f'Date : {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f'Livreur : {livreur_nom.encode("latin-1", "replace").decode("latin-1")}', 0, 1, 'L')
    pdf.cell(0, 8, f'Region : {region.encode("latin-1", "replace").decode("latin-1")}', 0, 1, 'L')
    pdf.ln(5)
    
    # Tableau
    cols_config = [
        ("Client", "Client", 90),
        ("Reference", "Reference", 40),
        ("Date_Creation", "Date", 40),
        ("Statut", "Statut", 20),
    ]
    
    # Header tableau
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    for _, label, width in cols_config:
        pdf.cell(width, 8, label, 1, 0, 'C', 1)
    pdf.ln()
    
    # Lignes tableau
    pdf.set_font('Arial', '', 9)
    for _, row in df.iterrows():
        for key, _, width in cols_config:
            val = str(row.get(key, '')).encode('latin-1', 'replace').decode('latin-1')
            if len(val) > 40 and key == 'Client':
                val = val[:37] + '...'
            pdf.cell(width, 7, val, 1, 0, 'L' if key == 'Client' else 'C')
        pdf.ln()
    
    pdf.ln(20)
    # Zone de signature
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(100, 10, 'Signature de la logistique', 0, 0, 'C')
    pdf.cell(90, 10, 'Signature et cachet du livreur', 0, 1, 'C')
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')
'''

with open('C:/projects/PHARMACIEL/utils_pdf.py', 'a', encoding='utf-8') as f:
    f.write('\n\n' + pdf_code)
