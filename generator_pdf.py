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
    if isinstance(image_path, str) and image_path.strip() and image_path.lower() != 'nan' and os.path.exists(image_path):
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, "PREUVE VISUELLE (Photo):", 0, 1)
        # Redimensionnement auto pour tenir dans la page (max 180mm large)
        pdf.image(image_path, x=15, w=150)
    else:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "(Aucune photo jointe au dossier)", 0, 1)

    raw = pdf.output()
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
            
        # Entête de l'article avec fond gris clair
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(24, 119, 242)
        pdf.cell(0, 10, f"  ARTICLE #{i+1} : {item['produit']}", 0, 1, 'L', fill=True)
        pdf.set_text_color(0, 0, 0)
        
        y_start = pdf.get_y()
        
        # Détails (colonne gauche)
        pdf.set_font("Arial", '', 10)
        pdf.cell(130, 7, f"Lot: {item['lot']}  |  Quantite: {item['quantite']}  |  Motif: {item['type']}", 0, 1)
        pdf.set_font("Arial", 'I', 9)
        pdf.multi_cell(130, 6, f"Observations: {item.get('commentaire', 'N/A')}", 0, 'L')
        
        y_text_end = pdf.get_y()
        
        # Photo (colonne droite) - On fixe la HAUTEUR pour la cohérence
        photo_path = item.get('Photo_Path', '')
        if isinstance(photo_path, str) and photo_path.strip() and photo_path.lower() != 'nan' and os.path.exists(photo_path):
            try:
                # On utilise h=35 pour que toutes les photos fassent la même hauteur
                pdf.image(photo_path, x=145, y=y_start + 2, h=35)
                # On descend le curseur en dessous du texte ou de l'image
                y_final = max(y_text_end, y_start + 40)
                pdf.set_y(y_final)
            except: 
                pdf.set_y(y_text_end)
        else:
            pdf.set_y(y_text_end)
            
        pdf.ln(5)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 10, f"Rapport genere par {first.get('agent', 'Systeme')} le {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'R')

    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_team_performance_pdf(stats_list):
    """
    stats_list: list of dicts {agent, missions, xp, level, rank}
    """
    pdf = ReclamPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 15, "BILAN DE PERFORMANCE EQUIPE", 1, 1, 'C', fill=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 10, "AGENT", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "MISSIONS", 1, 0, 'C', fill=True)
    pdf.cell(30, 10, "XP", 1, 0, 'C', fill=True)
    pdf.cell(30, 10, "NIVEAU", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "RANG", 1, 1, 'C', fill=True)
    
    pdf.set_font("Arial", '', 11)
    for s in stats_list:
        pdf.cell(50, 10, str(s['agent']), 1)
        pdf.cell(40, 10, str(s['missions']), 1, 0, 'C')
        pdf.cell(30, 10, str(s['xp']), 1, 0, 'C')
        pdf.cell(30, 10, str(s['level']), 1, 0, 'C')
        # On nettoie les emojis pour latin-1
        rank_text = s['rank'].replace("🥉", "").replace("🥈", "").replace("🥇", "").replace("💎", "").replace("👑", "").strip()
        pdf.cell(40, 10, rank_text, 1, 1, 'C')
        
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 10, f"Rapport genere par DarPharm Solutions le {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
    
    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_programme_expedition_pdf(claims_by_region, livreurs_by_region, date_str):
    """
    claims_by_region: dict of region -> list of dicts/rows
    livreurs_by_region: dict of region -> str (livreur name)
    date_str: str (the date for the header)
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    
    for region, claims in claims_by_region.items():
        if not claims:
            continue
        pdf.add_page()
        
        # Header logo if exists
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, 8, 33)
            
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(80)
        pdf.cell(30, 10, 'PROG DE RECLAMATIONS', 0, 1, 'C')
        pdf.ln(15)
        
        # Info Block
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(30, 8, "Date:", 0, 0)
        pdf.set_font("Arial", '', 11)
        pdf.cell(50, 8, date_str, 0, 1)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(30, 8, "Region:", 0, 0)
        pdf.set_font("Arial", '', 11)
        pdf.cell(50, 8, region, 0, 1)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(30, 8, "Livreur:", 0, 0)
        pdf.set_font("Arial", '', 11)
        pdf.cell(50, 8, str(livreurs_by_region.get(region, "Non Assigné")), 0, 1)
        
        pdf.ln(10)
        
        # Table Headers
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        
        # Column widths: Client (65), Reference (35), Motif (45), Decision (45) -> Total = 190
        pdf.cell(65, 8, "Client", 1, 0, 'C', fill=True)
        pdf.cell(35, 8, "Reference", 1, 0, 'C', fill=True)
        pdf.cell(45, 8, "Motif", 1, 0, 'C', fill=True)
        pdf.cell(45, 8, "Decision", 1, 1, 'C', fill=True)
        
        # Table Body
        pdf.set_font("Arial", '', 9)
        for claim in claims:
            if pdf.get_y() > 260:
                pdf.add_page()
                # Repeat header-like structure if flowing
                pdf.set_font("Arial", 'I', 8)
                pdf.cell(0, 8, f"Suite - Region: {region} | Livreur: {livreurs_by_region.get(region, 'Non Assigné')}", 0, 1, 'L')
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(65, 8, "Client", 1, 0, 'C', fill=True)
                pdf.cell(35, 8, "Reference", 1, 0, 'C', fill=True)
                pdf.cell(45, 8, "Motif", 1, 0, 'C', fill=True)
                pdf.cell(45, 8, "Decision", 1, 1, 'C', fill=True)
                pdf.set_font("Arial", '', 9)
            
            client_name = str(claim.get("client", "N/A"))
            ref = str(claim.get("reference", "N/A"))
            motif = str(claim.get("motif", "N/A"))
            decision = str(claim.get("decision", ""))
            
            def clean_str(s, max_len=30):
                # Clean for latin-1 encoding used by standard FPDF core fonts
                s_clean = str(s).encode('latin-1', 'replace').decode('latin-1')
                if len(s_clean) > max_len:
                    return s_clean[:max_len-3] + "..."
                return s_clean
                
            pdf.cell(65, 8, clean_str(client_name, 35), 1, 0, 'L')
            pdf.cell(35, 8, clean_str(ref, 20), 1, 0, 'C')
            pdf.cell(45, 8, clean_str(motif, 25), 1, 0, 'L')
            pdf.cell(45, 8, clean_str(decision, 25), 1, 1, 'L')
            
    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_bon_retour_pdf(data):
    """
    Génère un Bon de Retour ultra-professionnel avec un talon détachable pour le livreur.
    data doit contenir: date, fournisseur, agent, produit, lot, quantite, type, facture, commentaire
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Génération d'une référence de traçabilité unique
    import random
    ref_traceability = f"RET-{datetime.now().strftime('%Y%m%d')}-{str(random.randint(1000,9999))}"
    
    def draw_half_page(is_talon=False):
        # Header
        if os.path.exists("logo.png"):
            pdf.image("logo.png", 10, pdf.get_y(), 25)
            
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(30)
        pdf.cell(100, 8, "BON DE RECLAMATION / RETOUR MARCHANDISE", 0, 0, 'C')
        
        # Etiquette Exemplaire
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(50, 50, 50)
        if is_talon:
            pdf.cell(0, 8, " EXEMPLAIRE PHARMACIE (TALON) ", 0, 1, 'R', fill=True)
        else:
            pdf.cell(0, 8, " EXEMPLAIRE FOURNISSEUR ", 0, 1, 'R', fill=True)
            
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        
        # Reference and Date
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(30)
        pdf.cell(100, 5, f"REFERENCE: {ref_traceability}", 0, 0, 'C')
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(0, 5, f"Imprime le: {datetime.now().strftime('%d/%m/%Y a %H:%M')}", 0, 1, 'R')
        pdf.ln(8)
        
        # Supplier & Agent Info
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 7, "INFORMATIONS FOURNISSEUR", 1, 0, 'L', fill=True)
        pdf.cell(5, 7, "", 0, 0) # Spacer
        pdf.cell(90, 7, "INFORMATIONS INTERNES", 1, 1, 'L', fill=True)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f" Fournisseur : {data.get('fournisseur', 'N/A')}", 1, 0, 'L')
        pdf.cell(5, 7, "", 0, 0)
        pdf.cell(90, 7, f" Agent Saisie : {data.get('agent', 'N/A')}", 1, 1, 'L')
        
        pdf.cell(95, 7, f" Facture / BL : {data.get('facture', 'N/A')}", 1, 0, 'L')
        pdf.cell(5, 7, "", 0, 0)
        pdf.cell(90, 7, f" Date Constat : {data.get('date', 'N/A')}", 1, 1, 'L')
        
        pdf.ln(5)
        
        # Product details table
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(75, 8, "Produit", 1, 0, 'C', fill=True)
        pdf.cell(30, 8, "Lot", 1, 0, 'C', fill=True)
        pdf.cell(20, 8, "Qte", 1, 0, 'C', fill=True)
        pdf.cell(65, 8, "Motif du Retour", 1, 1, 'C', fill=True)
        
        pdf.set_font("Arial", 'B', 9)
        # Nettoyage des chaînes pour latin-1
        prod = str(data.get('produit', '')).encode('latin-1', 'replace').decode('latin-1')
        motif = str(data.get('type', '')).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(75, 10, prod[:40], 1, 0, 'C')
        pdf.cell(30, 10, str(data.get('lot', '')), 1, 0, 'C')
        pdf.cell(20, 10, str(data.get('quantite', '')), 1, 0, 'C')
        pdf.cell(65, 10, motif[:35], 1, 1, 'C')
        
        pdf.ln(5)
        
        if not is_talon:
            # Partie Fournisseur: Mentions et signature Pharmacie
            pdf.set_font("Arial", 'I', 9)
            pdf.multi_cell(0, 5, "La marchandise citee ci-dessus a ete retournee au fournisseur pour non-conformite. Ce document accompagne la marchandise dans l'attente d'un echange ou d'un avoir financier.")
            pdf.ln(3)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 20, "Cachet et Signature (Pharmacie / Grossiste) :", 1, 1, 'L')
            
        else:
            # Partie Pharmacie (Talon): Signature Chauffeur (Preuve de traçabilité)
            pdf.set_fill_color(255, 245, 245)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 8, "CADRE RESERVE AU LIVREUR / CHAUFFEUR (PREUVE D'ENLEVEMENT)", 1, 1, 'C', fill=True)
            pdf.set_font("Arial", '', 9)
            
            y_start = pdf.get_y()
            pdf.cell(95, 10, " Nom du chauffeur : ...............................................", 'L,T', 0, 'L')
            pdf.cell(95, 10, " Date et Heure d'enlevement : ...../...../20... a ...h...", 'R,T', 1, 'L')
            
            pdf.cell(95, 10, " Matricule Vehicule : ..............................................", 'L', 0, 'L')
            pdf.cell(95, 10, " Visa et Cachet du fournisseur :", 'R', 1, 'L')
            
            pdf.cell(95, 15, "", 'L,B', 0, 'L')
            pdf.cell(95, 15, "", 'R,B', 1, 'L')
            
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 8)
            pdf.set_text_color(150, 0, 0)
            pdf.cell(0, 5, "ATTENTION : Ce talon doit obligatoirement etre signe par le livreur pour valider la decharge.", 0, 1, 'C')
            pdf.set_text_color(0, 0, 0)

    # Dessiner la moitié haute (Exemplaire Fournisseur)
    pdf.set_y(15)
    draw_half_page(is_talon=False)
    
    # Ligne de coupe
    pdf.set_y(140)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 5, "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - LIGNE DE DECOUPE - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", 0, 1, 'C')
    pdf.line(10, 143, 200, 143)
    
    # Dessiner la moitié basse (Talon Pharmacie)
    pdf.set_y(155)
    draw_half_page(is_talon=True)

    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

