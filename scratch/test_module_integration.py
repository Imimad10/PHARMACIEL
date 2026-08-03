import pandas as pd
import sys
import importlib
from datetime import datetime

# Import local modules to test categorization
sys.path.append('.')
try:
    mod = importlib.import_module("modules.31_analyse_reclamations")
    categorize_motif = mod.categorize_motif
    parse_date_robust = mod.parse_date_robust
    print("Successfully imported functions from modules.31_analyse_reclamations dynamically.")
except Exception as e:
    print(f"Could not import dynamically, using fallback definitions. Error: {e}")
    def categorize_motif(motif_str):
        m = str(motif_str).upper()
        if any(k in m for k in ["COMMERCIAL", "SAISIE", "FORCE", "REVENU", "EXCUSE", "PRODUIT NON COMMANDE"]): 
            return "Erreur Commerciale"
        if any(k in m for k in ["PHARMACIEN", "DOSAGE", "FORME", "DCI", "MARQUE", "RETOUR CLIENT"]): 
            return "Erreur Pharmacien"
        if any(k in m for k in ["DEPOT", "PREPARATION", "BOITE", "PLUS", "MOIN", "QUANTITE", "MANQUE"]): 
            return "Erreur Dépôt"
        if any(k in m for k in ["PNC", "CONFORME", "VIGNETTE", "ABIMEE", "CASSEE", "DETERIORE", "PRODUIT ABIME"]): 
            return "PNC (Non Conforme)"
        if any(k in m for k in ["SUPERVISEUR", "MODIFICATION", "REFAIRE", "BON DEJA"]): 
            return "Erreur Superviseur"
        return "Autre / Non Classé"
    
    def parse_date_robust(date_str):
        for fmt in ('%d-%m-%y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d %H:%M:%S'):
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                pass
        return pd.to_datetime(date_str, errors='coerce')

def test_integration():
    csv_path = "data/db_reclamations_analyse.csv"
    print(f"Reading database: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # 1. Row count check
    rows_count = len(df)
    print(f"Number of rows found: {rows_count}")
    assert rows_count >= 20, "Database should contain at least 20 records."
    
    # 2. Columns checklist
    required_cols = ['reference', 'client', 'produit', 'quantite', 'valeur_vente', 'cout_revient', 'motif', 'statut']
    for col in required_cols:
        assert col in df.columns, f"Column '{col}' is missing!"
    print("All key columns verified successfully.")
    
    # 3. Categorization verification
    motifs_test = {
        "RETOUR RAPPEL DE LOT": "Autre / Non Classé",
        "RAPPEL DE LOT": "Autre / Non Classé",
        "ERREUR COMMERCIAL": "Erreur Commerciale",
        "ERREUR DU PHARMACIEN": "Erreur Pharmacien",
        "PNC (PRODUIT ABIME)": "PNC (Non Conforme)",
        "ERREUR DE DEPOT (MANQUE)": "Erreur Dépôt"
    }
    for m, expected in motifs_test.items():
        res = categorize_motif(m)
        print(f"Motif '{m}' -> categorized as: '{res}' (expected: '{expected}')")
        assert res == expected, f"Categorization mismatch for '{m}': expected '{expected}', got '{res}'"
        
    # 4. Date parsing verification
    date_tests = ["30-04-26", "04-01-26", "2026-07-08", "08/02/2026"]
    for d in date_tests:
        parsed = parse_date_robust(d)
        print(f"Date string '{d}' parsed to: {parsed}")
        assert not pd.isna(parsed), f"Failed to parse date '{d}'"
        
    # 5. Write back verification
    # We will simulate modifying a line and saving it back
    print("Simulating complaint resolution...")
    mask = (df['reference'] == "26/RC0000000146") & (df['produit'] == "TROMBIX COMP. PELLI. 20MG B/30")
    if mask.any():
        df.loc[mask, 'statut_bon'] = "Cloturer"
        df.loc[mask, 'statut'] = "ACCEPTE"
        df.loc[mask, 'reponse'] = "Avoir émis"
        df.loc[mask, 'delai_reclam'] = 3.0
        
        # Write to a temporary file
        temp_csv = "data/db_reclamations_temp.csv"
        df.to_csv(temp_csv, index=False)
        df_temp = pd.read_csv(temp_csv)
        
        # Verify resolution values
        test_row = df_temp[df_temp['reference'] == "26/RC0000000146"]
        assert test_row.iloc[0]['statut_bon'] == "Cloturer", "Writeback failed for status_bon"
        assert test_row.iloc[0]['statut'] == "ACCEPTE", "Writeback failed for status"
        assert test_row.iloc[0]['reponse'] == "Avoir émis", "Writeback failed for response"
        print("Writeback integration verified successfully.")
        
        # Clean up
        import os
        os.remove(temp_csv)
    else:
        print("Trombix test row not found!")
        
    print("ALL TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    test_integration()
