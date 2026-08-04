from fpdf import FPDF
import pandas as pd
from datetime import datetime
import io

class InventoryPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        safe_title = self.title_text.encode('latin-1', 'replace').decode('latin-1')
        self.cell(0, 10, safe_title, 0, 1, 'C')
        if hasattr(self, 'subtitle_text') and self.subtitle_text:
            self.set_font('Arial', 'B', 10)
            safe_subtitle = self.subtitle_text.encode('latin-1', 'replace').decode('latin-1')
            self.cell(0, 8, safe_subtitle, 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, 8, f"Date d'édition : {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
        self.ln(2)

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

def generate_inventory_report_pdf(df_diff, title="RAPPORT D'INVENTAIRE", cols_to_include=None, orientation='P'):
    """
    df_diff: DataFrame contenant les données
    cols_to_include: Liste de colonnes spécifiques (facultatif)
    orientation: 'P' (Portrait) ou 'L' (Landscape)
    """
    pdf = InventoryPDF(orientation=orientation)
    pdf.title_text = title.upper()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Statistiques de base
    total_items = len(df_diff)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. RESUME DU RAPPORT", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f"- Nombre total de lignes : {total_items}", 0, 1)
    
    if 'Ecart' in df_diff.columns:
        manquants = len(df_diff[df_diff['Ecart'] < 0])
        excedents = len(df_diff[df_diff['Ecart'] > 0])
        pdf.cell(0, 8, f"- Produits manquants : {manquants}", 0, 1)
        pdf.cell(0, 8, f"- Produits en excedent : {excedents}", 0, 1)
    pdf.ln(5)
    
    # Configuration des colonnes
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    
    if cols_to_include:
        # On définit des largeurs automatiques simplifiées
        max_w = 280 if orientation == 'L' else 190
        w_main = 90 if orientation == 'L' else 80
        w_others = (max_w - w_main) / (len(cols_to_include) - 1) if len(cols_to_include) > 1 else (max_w - w_main)
        cols_config = []
        for i, col in enumerate(cols_to_include):
            w = w_main if i == 0 else w_others
            label = str(col).capitalize().replace('_', ' ')
            cols_config.append((col, label, w))
    else:
        # Default Inventory Cols
        cols_config = [('produit', 'Produit', 70), ('lot', 'Lot', 30), ('qte_logi', 'Logi', 20), ('Total', 'Reel', 20), ('Ecart', 'Ecart', 20), ('Incohérence', 'Obs', 30)]
    
    # Affichage en-têtes
    for _, label, w in cols_config:
        pdf.cell(w, 8, label, 1, 0, 'C', 1)
    pdf.ln()
    
    # Affichage lignes
    pdf.set_font('Arial', '', 8)
    page_break_y = 180 if orientation == 'L' else 260
    for _, row in df_diff.iterrows():
        if pdf.get_y() > page_break_y:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 9)
            for _, label, w in cols_config: pdf.cell(w, 8, label, 1, 0, 'C', 1)
            pdf.ln()
            pdf.set_font('Arial', '', 8)
        for i, (key, _, w) in enumerate(cols_config):
            val = str(row.get(key, ""))
            
            # Formater la DDP si c'est une date
            if key in ['ddp', 'ddp_saisi']:
                try:
                    dt = pd.to_datetime(val, errors='coerce')
                    if pd.notna(dt): val = dt.strftime('%m/%y')
                except: pass
                
            # Nettoyer les emojis pour le PDF (FPDF ne supporte pas Unicode par défaut)
            val = val.replace("❌", "[PERIME]").replace("⚠️", "[CRITIQUE]").replace("🟠", "[VIGILANCE]").replace("✅", "[SAIN]").replace("🔴", "[!]").replace("🟡", "[ATT]")
            val = val[:45]
            
            align = 'L' if i == 0 else 'C'
            pdf.cell(w, 7, val.encode('latin-1', 'replace').decode('latin-1'), 1, 0, align)
        pdf.ln()
        
    # --- PLAN DE LIBERATION STRATEGIQUE ---
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, "3. PLAN DE LIBERATION DES PRODUITS", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    
    plan_text = """
    - ZONE ROUGE (PERIMES) : Retrait immediat des rayons. Mise en quarantaine physique et inventaire de destruction.
    - ZONE JAUNE (CRITIQUES < 3M) : Action commerciale agressive (Remise -30% a -50%). Placement en 'Tete de Gondole'.
    - ZONE ORANGE (VIGILANCE 3-6M) : Mise en avant proactive. Verifier les possibilites de retour fournisseur/labo.
    - ZONE VERTE (SAINS > 6M) : Gestion standard FEFO (Premier expire, premier sorti).
    """
    pdf.multi_cell(0, 7, plan_text.encode('latin-1', 'replace').decode('latin-1'))
    
    # Conclusion
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. VALIDATION", 0, 1)
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(0, 8, "Ce document constitue un rapport officiel genere par DarPharm Solution. Il doit etre conserve et utilise pour la regularisation des stocks ou la gestion des peremptions.")
    pdf.ln(15)
    
    # Signatures
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(95, 10, "L'Agent Responsable", 0, 0, 'C')
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
    pdf.set_margins(left=7, top=10, right=7)
    pdf.title_text = "FICHE DE RECEPTION & POINTAGE"
    pdf.subtitle_text = f"Fournisseur: {reception_data['fournisseur']} | Facture: {reception_data['facture_num']}"
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Tableau
    pdf.set_font('Arial', 'B', 8)
    pdf.set_fill_color(230, 230, 230)
    # Total width: 85 + 24 + 18 + 12 + 15 + 16 + 12 + 14 = 196mm
    cols = [
        ('produit', 'Désignation', 85), 
        ('lot', 'Lot', 24), 
        ('ddp', 'DDP', 18), 
        ('qte', 'Qte', 12), 
        ('colissage', 'Colis.', 15),
        ('ppa', 'PPA', 16), 
        ('shp', 'SHP', 12),
        ('couleur', 'Vig.', 14)
    ]
    
    for _, label, w in cols:
        pdf.cell(w, 8, label, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for item in reception_data['items']:
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 8)
            pdf.set_fill_color(230, 230, 230)
            for _, label, w in cols: pdf.cell(w, 8, label, 1, 0, 'C', 1)
            pdf.ln()
            pdf.set_font('Arial', '', 8)
        
        # Calcul de la hauteur nécessaire pour la désignation (multi-ligne)
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        designation = str(item.get('produit', ""))
        
        # On écrit la désignation et on récupère la hauteur
        pdf.multi_cell(85, 5, designation.encode('latin-1', 'replace').decode('latin-1'), 1, 'L')
        end_y = pdf.get_y()
        row_h = end_y - start_y
        
        # On revient en haut de la ligne pour les autres colonnes
        curr_x = start_x + 85
        
        for key, _, w in cols[1:]:
            pdf.set_xy(curr_x, start_y)
            if key == 'couleur':
                # Dessiner le cercle de couleur
                pdf.cell(w, row_h, "", 1, 0, 'C') # Bordure de la cellule
                c = item.get('couleur', 'blanche').lower()
                
                # Coordonnées pour le cercle (centré dans la cellule)
                circle_size = 4
                cx = curr_x + (w / 2) - (circle_size / 2)
                cy = start_y + (row_h / 2) - (circle_size / 2)
                
                if c == "verte":
                    pdf.set_fill_color(0, 180, 0)
                elif c == "rouge":
                    pdf.set_fill_color(220, 0, 0)
                else: # blanche
                    pdf.set_fill_color(255, 255, 255)
                
                pdf.ellipse(cx, cy, circle_size, circle_size, 'FD')
                pdf.set_fill_color(255, 255, 255) # Reset fill
            else:
                val = str(item.get(key, ""))
                # Formater si numérique
                try:
                    if key in ['ppa', 'shp', 'qte', 'colissage']:
                        val = str(round(float(val), 2)) if '.' in str(val) else str(int(float(val)))
                except:
                    pass
                
                pdf.cell(w, row_h, val.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
            
            curr_x += w
        
        pdf.set_y(end_y) # On se positionne pour la ligne suivante
    
    # Pied de page
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    pdf.write(5, f"Reception terminee le {reception_data['date']} par {reception_data.get('created_by', 'Equipe Reception')}")
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_rotation_report_pdf(df, module_name, ia_analysis=""):
    pdf = InventoryPDF()
    pdf.title_text = f"RAPPORT DE ROTATION - {module_name.upper()}"
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Header du tableau
    pdf.set_fill_color(31, 41, 55) # Dark gray
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 10)
    
    # Largeurs : Désignation (100), Qte (30), Rotation (30), Statut (30)
    pdf.cell(100, 10, "Designation", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Stock", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Rotation", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Statut", 1, 1, 'C', 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    
    for _, row in df.iterrows():
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_fill_color(31, 41, 55)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(100, 10, "Designation", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Stock", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Rotation", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Statut", 1, 1, 'C', 1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 9)

        # Désignation multi-ligne si nécessaire
        designation = str(row.iloc[0])
        qte = str(row.iloc[1])
        rot = str(row.iloc[2])
        statut = str(row.iloc[3])
        
        # Coloration selon statut
        if "Dormant" in statut: pdf.set_text_color(200, 0, 0)
        elif "Star" in statut: pdf.set_text_color(0, 150, 0)
        else: pdf.set_text_color(0, 0, 0)
        
        pdf.cell(100, 8, designation[:45].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(30, 8, qte, 1, 0, 'C')
        pdf.cell(30, 8, rot, 1, 0, 'C')
        pdf.cell(30, 8, statut.split(' ')[-1], 1, 1, 'C') # On garde juste le texte après l'emoji

    # Bloc IA si présent
    if ia_analysis:
        pdf.ln(10)
        if pdf.get_y() > 230: pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(91, 108, 249) # IA blue
        pdf.cell(0, 10, "ANALYSE STRATEGIQUE DE L'ASSISTANT IA", 0, 1, 'L')
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 6, ia_analysis.encode('latin-1', 'replace').decode('latin-1'), 1)

    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_rh_planning_pdf(df, title="PLANNING & PERMANENCES", model="Classique"):
    pdf = InventoryPDF()
    pdf.title_text = title.upper()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    cols_config = [
        ('Date_Debut', 'Date', 30),
        ('Agent', 'Agent', 40),
        ('Type', 'Type d\'evenement', 50),
        ('Statut', 'Statut', 25),
        ('Commentaire', 'Observations', 45)
    ]
    
    # Dictionnaire de ciblage des équipes
    team_rdc_keywords = ['admin_imad', 'ayoub', 'islem', 'seif', 'karim', 'abdelmalek', 'samra']
    
    def is_rdc(agent_name):
        a_lower = str(agent_name).lower()
        for k in team_rdc_keywords:
            if k in a_lower:
                return True
        return False

    # Séparation des données
    df_rdc = df[df['Agent'].apply(is_rdc)]
    df_etage = df[~df['Agent'].apply(is_rdc)]

    def draw_team_table(team_df, team_title):
        if team_df.empty:
            return
        
        pdf.ln(5)
        # Titre de la section
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(31, 41, 55) # Dark navy header
        pdf.cell(0, 10, f"  {team_title.encode('latin-1', 'replace').decode('latin-1')}", 0, 1, 'L', 1)
        
        # En-têtes du tableau
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(240, 240, 240)
        
        for _, label, w in cols_config:
            pdf.cell(w, 10, label.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C', 1)
        pdf.ln()
        
        # Lignes
        pdf.set_font('Arial', '', 8)
        for _, row in team_df.iterrows():
            if pdf.get_y() > 260:
                pdf.add_page()
                pdf.set_font('Arial', 'B', 9)
                for _, label, w in cols_config: 
                    pdf.cell(w, 10, label.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C', 1)
                pdf.ln()
                pdf.set_font('Arial', '', 8)
                
            for key, _, w in cols_config:
                val = str(row.get(key, ""))
                if val.lower() == 'nan': val = ""
                val = val.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(w, 8, val[:50], 1, 0, 'C')
            pdf.ln()

    # Dessiner les deux tableaux
    title_rdc = "ÉQUIPE RDC & FILIALE (Direction, Stock, Logistique)"
    if model != "Classique":
        title_rdc = "ÉQUIPE RDC (Stock, Preparation)"
        
    draw_team_table(df_rdc, title_rdc)
    draw_team_table(df_etage, "ÉQUIPE 1ER ÉTAGE (Supervision & Préparation)")
    
    # Pied de page administratif
    pdf.ln(15)
    pdf.set_font('Arial', 'B', 10)
    
    if model == "Classique":
        pdf.cell(95, 10, "Mme Samra (DRH / DG)", 0, 0, 'C')
        pdf.cell(95, 10, "VALIDATION SUPERVISEUR", 0, 1, 'C')
        pdf.ln(10)
        pdf.cell(95, 0, "__________________", 0, 0, 'C')
        pdf.cell(95, 0, "__________________", 0, 1, 'C')
    else:
        pdf.cell(190, 10, "VALIDATION SUPERVISEUR", 0, 1, 'C')
        pdf.ln(10)
        pdf.cell(190, 0, "__________________", 0, 1, 'C')

    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def generate_cheques_report_pdf(df, subtitle=""):
    """
    Génère un rapport PDF de la liste des chèques (filtrée ou complète).
    df doit contenir les colonnes : N, Chauffeur, Client, Montant, N_Cheque,
    Date_Sortie, Date_Retour, Statut.
    Les lignes sont colorées selon le statut (vert=Réglé, jaune=En attente, rouge=Refusée).
    """
    STATUT_FILL = {
        "Réglé": (209, 250, 229),
        "En attente": (254, 243, 199),
        "Refusée": (254, 226, 226),
    }

    pdf = InventoryPDF()
    pdf.title_text = "SUIVI DES CHEQUES"
    pdf.subtitle_text = subtitle
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Résumé ---
    total = len(df)
    montant_total = pd.to_numeric(df['Montant'], errors='coerce').fillna(0).sum() if not df.empty else 0
    n_regle = len(df[df['Statut'] == 'Réglé']) if not df.empty else 0
    n_attente = len(df[df['Statut'] == 'En attente']) if not df.empty else 0
    n_refuse = len(df[df['Statut'] == 'Refusée']) if not df.empty else 0

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "RESUME", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, f"Nombre total de cheques : {total}   |   Montant total : {montant_total:,.0f} DA".replace(",", " "), 0, 1)
    pdf.cell(0, 6, f"Regles : {n_regle}   |   En attente : {n_attente}   |   Refuses : {n_refuse}", 0, 1)
    pdf.ln(4)

    # --- Tableau ---
    cols_config = [
        ("N", "N", 10),
        ("Chauffeur", "Chauffeur", 33),
        ("Client", "Client", 33),
        ("Montant", "Montant", 24),
        ("N_Cheque", "N Cheque", 27),
        ("Date_Sortie", "Sortie", 21),
        ("Date_Retour", "Retour", 21),
        ("Statut", "Statut", 21),
    ]

    def draw_header():
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(224, 228, 255)
        for _, label, w in cols_config:
            pdf.cell(w, 8, label, 1, 0, 'C', 1)
        pdf.ln()

    draw_header()
    pdf.set_font('Arial', '', 8)

    for _, row in df.iterrows():
        if pdf.get_y() > 265:
            pdf.add_page()
            draw_header()
            pdf.set_font('Arial', '', 8)

        statut = str(row.get('Statut', ''))
        fill_rgb = STATUT_FILL.get(statut, (255, 255, 255))
        pdf.set_fill_color(*fill_rgb)

        for key, _, w in cols_config:
            val = row.get(key, "")
            if key == "Montant":
                try:
                    val = f"{float(val):,.0f}".replace(",", " ")
                except (ValueError, TypeError):
                    val = str(val)
            else:
                val = str(val)
            val = val[:22].encode('latin-1', 'replace').decode('latin-1')
            align = 'L' if key in ("Chauffeur", "Client") else 'C'
            pdf.cell(w, 7, val, 1, 0, align, 1)
        pdf.ln()

    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')


def generate_fiche_temperature_pdf(year=None, month=None, hours=None, chambres=None, mois_label=None, temp_min=2.0, temp_max=8.0):
    """
    Génère une fiche de relevé de température vierge pour une ou plusieurs unités
    (Chambre Froide, Stock, Salle de Préparation...).
    Chaque unité tient sur UNE SEULE page A4 grâce à un format compact en colonnes.

    temp_min / temp_max : bornes de la plage conforme à afficher sur la fiche.
    Par défaut +2°C / +8°C (Chambre Froide) pour rester rétro-compatible avec
    les appels existants qui ne précisent pas de plage.
    """
    import calendar
    from datetime import datetime
    
    # Résolution robuste du mois et de l'année
    if year is None or month is None:
        if mois_label and isinstance(mois_label, str):
            try:
                parts = mois_label.strip().split()
                if len(parts) == 2:
                    french_months = [
                        "janvier", "février", "mars", "avril", "mai", "juin",
                        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
                    ]
                    m_name = parts[0].lower()
                    if m_name in french_months:
                        month = french_months.index(m_name) + 1
                    year = int(parts[1])
            except:
                pass
        
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
            
    if not hours:
        hours = ["08:00", "17:00"]
    if not chambres:
        chambres = ["Chambre Froide 1", "Chambre Froide 2"]

    french_months = [
        "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]
    mois_label = f"{french_months[month]} {year}"

    # Formatage propre des bornes de température (ex: 2.0 -> "+2°C", 23.5 -> "+23.5°C")
    def fmt_temp(t):
        t = float(t)
        val = f"{t:+.0f}" if t.is_integer() else f"{t:+.1f}"
        return f"{val}\u00b0C"

    plage_txt = f"{fmt_temp(temp_min)} a {fmt_temp(temp_max)}"

    pdf = InventoryPDF()
    # Supprimer les marges superflues du haut (5mm) et du bas (5mm de garde) pour maximiser l'espace A4
    pdf.set_margins(10, 5, 10)
    pdf.set_auto_page_break(True, margin=5)
    pdf.title_text = "FICHE DE POINTAGE DES TEMPERATURES"
    pdf.subtitle_text = f"Mois : {mois_label}   |   Plage conforme : {plage_txt}"
    pdf.alias_nb_pages()

    # Mapping jours
    french_days_short = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    num_days = calendar.monthrange(year, month)[1]

    # Calcul dynamique des largeurs de colonnes (Largeur totale imprimable = 190mm)
    w_date = 30
    w_comm = 50
    w_remaining = 190 - w_date - w_comm # 110mm pour les relevés d'heures
    
    num_hours = len(hours)
    w_pair = w_remaining / num_hours
    w_temp = round(w_pair * 0.52)
    w_visa = round(w_pair * 0.48)
    
    # Ajustement de w_comm pour tomber pile à 190mm
    total_calculated_w = w_date + w_comm + (num_hours * (w_temp + w_visa))
    w_comm += (190 - total_calculated_w)

    for chambre in chambres:
        pdf.add_page()

        # Bloc d'information pharmacie
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(230, 240, 255)
        pdf.cell(0, 7, f"  Unite : {chambre}".encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L', 1)
        pdf.ln(1)

        # Info conformite
        pdf.set_font('Arial', 'I', 8)
        pdf.set_text_color(80, 80, 80)
        min_txt = f"{temp_min:+.0f}" if float(temp_min).is_integer() else f"{temp_min:+.1f}"
        max_txt = f"{temp_max:+.0f}" if float(temp_max).is_integer() else f"{temp_max:+.1f}"
        pdf.cell(0, 5, f"Plage ideale : {min_txt} degres C a {max_txt} degres C  |  Frequence : Saisie manuelle  |  ALERTE si hors plage", 0, 1, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)

        # En-tête du tableau
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(31, 41, 55)
        pdf.set_text_color(255, 255, 255)
        
        pdf.cell(w_date, 7, "Date", 1, 0, 'C', 1)
        for hr in hours:
            pdf.cell(w_temp, 7, f"T\u00b0 ({hr})", 1, 0, 'C', 1)
            pdf.cell(w_visa, 7, "Visa", 1, 0, 'C', 1)
        pdf.cell(w_comm, 7, "Commentaire / Action corrective", 1, 1, 'C', 1)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 8)

        # Génération des lignes de jours (excluant vendredi & samedi)
        row_idx = 0
        for day in range(1, num_days + 1):
            dt = datetime(year, month, day)
            weekday = dt.weekday()
            
            # Exclure vendredi (4) et samedi (5)
            if weekday in [4, 5]:
                continue
                
            day_str = f"{day:02d}/{month:02d} ({french_days_short[weekday]})"
            
            # Couleur alternée
            if row_idx % 2 == 0:
                pdf.set_fill_color(245, 248, 255)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            # Dessiner la ligne (hauteur à 5.5mm pour tenir à 100% sur une seule page A4)
            pdf.cell(w_date, 5.5, day_str.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C', 1)
            for _ in hours:
                pdf.cell(w_temp, 5.5, "", 1, 0, 'C', 1)
                pdf.cell(w_visa, 5.5, "", 1, 0, 'C', 1)
            pdf.cell(w_comm, 5.5, "", 1, 1, 'L', 1)
            
            row_idx += 1

        # Zone de validation administrative en bas de page resserrée
        pdf.ln(4)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(95, 5, "Responsable / Superviseur :", 0, 0, 'L')
        pdf.cell(95, 5, "Visa Direction :", 0, 1, 'L')
        pdf.ln(8)
        pdf.cell(95, 0, "__________________________", 0, 0, 'C')
        pdf.cell(95, 0, "__________________________", 0, 1, 'C')
        pdf.ln(4)
        pdf.set_font('Arial', 'I', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, "DarPharm Solution | Supervision Thermique | Document de Tracabilite Unique", 0, 1, 'C')
        pdf.set_text_color(0, 0, 0)

    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')


def generate_suivi_direct_pdf(df):
    pdf = InventoryPDF()
    pdf.title_text = "RAPPORT SUIVI EN DIRECT"
    pdf.alias_nb_pages()
    pdf.add_page()
    
    cols = [('timestamp', 'Heure', 35), ('utilisateur', 'Agent', 25), ('methode', 'Methode', 25), ('designation', 'Produit', 75), ('qte', 'Qte', 10), ('ppa', 'PPA', 20)]
    
    pdf.set_font('Arial', 'B', 8)
    pdf.set_fill_color(240, 240, 240)
    for _, label, w in cols:
        pdf.cell(w, 8, label, 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    for _, row in df.iterrows():
        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 8)
            for _, label, w in cols: pdf.cell(w, 8, label, 1, 0, 'C', 1)
            pdf.ln()
            pdf.set_font('Arial', '', 8)
            
        for i, (key, _, w) in enumerate(cols):
            val = str(row.get(key, ''))
            # Simplify timestamp to just time if it has date
            if key == 'timestamp' and ' ' in val: val = val.split(' ')[-1]
            val = val[:40].encode('latin-1', 'replace').decode('latin-1')
            align = 'L' if key == 'designation' else 'C'
            pdf.cell(w, 7, val, 1, 0, align)
        pdf.ln()
        
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')




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
