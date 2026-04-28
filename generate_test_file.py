import pandas as pd

data = [
    {"Client": "PHARMACIE CENTRALE", "Référence": "F2026-001", "Région": "ALGER 1"},
    {"Client": "PHARMACIE EL AMEL", "Référence": "F2026-002", "Région": "ALGER 2"},
    {"Client": "PHARMACIE CHIFA", "Référence": "F2026-003", "Région": "BLIDA"},
    {"Client": "PHARMACIE DU NORD", "Référence": "F2026-004", "Région": "TIPAZA"},
    {"Client": "PHARMACIE SOLEIL", "Référence": "F2026-005", "Région": "ORAN"},
    {"Client": "PHARMACIE BENI", "Référence": "F2026-006", "Région": "CHLEF"}
]

df = pd.DataFrame(data)
df.to_excel("export_test_logipharm.xlsx", index=False)
print("Fichier de test généré avec succès !")
