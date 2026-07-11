import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from utils_gsheets import load_gs_data, save_gs_data
from datetime import datetime

# --- Configuration ---
KNOWLEDGE_WORKSHEET = "DB_Knowledge_Base"
KNOWLEDGE_FALLBACK = "data/db_knowledge.csv"
COLS_KB = ["id", "categorie", "titre", "contenu", "date_maj"]

# --- Les cours ---
courses = [
    {
        "categorie": "Logistique",
        "titre": "Introduction au Portail & Tableau de Bord",
        "contenu": """### Bienvenue sur le Portail DarPharm / Pharmaciel !

Ce portail centralise toutes les opérations de la société. Voici comment bien démarrer :

**1. Navigation (Barre latérale)**
- Sur votre gauche, vous trouverez tous les modules auxquels vous avez accès. 
- Votre accès dépend de votre rôle (Admin, Saisie, Superviseur, etc.).

**2. Le Tableau de Bord (Dashboard)**
- C'est la page d'accueil de l'application.
- Elle affiche les statistiques en temps réel : Chiffre d'affaires, nombre de commandes, alertes.
- Vous pouvez filtrer les données par période ou par type de produit.

**3. Personnalisation (Thèmes)**
- Vous pouvez changer l'apparence du site en allant dans votre profil ou via le menu des thèmes.
- Des thèmes clairs, sombres, ou aux couleurs des équipes (USMH, CRB, etc.) sont disponibles.
"""
    },
    {
        "categorie": "Inventaire",
        "titre": "Procédure d'Inventaire et Utilisation des Scans",
        "contenu": """### Comment faire un inventaire efficace ?

L'inventaire est une tâche critique. Voici les étapes à suivre :

**1. Choix du Module d'Inventaire**
- **Inventaire :** Pour un inventaire global du stock.
- **Inventaire Détail :** Pour compter les produits avec précision (lot, date de péremption).
- **Inventaire Triple :** Procédure stricte nécessitant la validation de 3 agents différents.

**2. Utilisation des Scanneurs**
- **Scanneur QR :** Utilisez la douchette ou la webcam pour scanner un produit. Il s'ajoutera automatiquement à la liste.
- **Scan Mobile :** Un module optimisé pour les téléphones portables. Très pratique pour circuler dans les rayons.

**3. Gestion des Péremptions**
- Le module **Péremptions** vous permet de surveiller les produits arrivant à date courte.
- N'oubliez pas d'isoler physiquement les produits identifiés comme périmés sur l'application.
"""
    },
    {
        "categorie": "Logistique",
        "titre": "Logistique, Expédition et Pointage",
        "contenu": """### Préparation et Expédition des commandes

Ce workflow garantit que les clients reçoivent les bons produits à temps :

**1. Suivi des commandes**
- Le module **Suivi** permet de voir l'état des commandes en cours (En préparation, Prête, Expédiée).

**2. Expédition**
- Dans le module **Expédition**, vous validez les colis avant leur départ.
- Vous devez scanner ou cocher chaque commande une fois qu'elle est chargée dans le véhicule de livraison.

**3. Pointage Expéditeur**
- Utilisez **Pointage Expéditeur** pour vérifier que tous les cartons prévus pour une tournée sont bien présents.

**4. Réception et Transferts**
- Les modules **Réception** et **Transferts** servent à gérer les arrivages de fournisseurs ou les transferts entre dépôts (ex: de DarPharm vers Pharmaciel).
"""
    },
    {
        "categorie": "RH & Primes",
        "titre": "Ressources Humaines & Coordination",
        "contenu": """### Gestion de votre temps et de votre équipe

Le portail inclut des outils pour la gestion RH :

**1. Pointage**
- Le module **Pointage** vous permet de signaler votre présence (arrivée / départ). 
- Ces données sont utilisées pour le calcul des primes.

**2. Coordination d'équipe**
- Utilisez **Coordination Équipe** pour communiquer avec les autres départements.
- Vous pouvez y laisser des notes ou des consignes pour l'équipe du soir.

**3. Permanence et Maintenance**
- Les modules **RH Permanence** et **Maintenance Flotte** permettent aux superviseurs de gérer les plannings et l'état des véhicules de livraison.
"""
    },
    {
        "categorie": "Logistique",
        "titre": "Utilisation de l'Assistant IA",
        "contenu": """### Comment travailler avec l'Intelligence Artificielle ?

L'application intègre des assistants IA avancés pour vous faire gagner du temps :

**1. L'IA Formateur (Académie)**
- C'est ce que vous utilisez actuellement ! Demandez-lui *"Comment faire une expédition ?"* et il cherchera la réponse dans ces procédures.

**2. Le Chat Pharmaciel / DarPharm IA**
- Accessible depuis la barre latérale, c'est votre assistant personnel.
- Posez-lui des questions sur vos tâches, demandez-lui d'analyser des données ou de rédiger des messages.

**3. Le Briefing IA**
- Il analyse les données de la veille et vous génère un rapport de briefing complet pour la réunion du matin.

**4. Cortex IA & Analyse de Ventes**
- Ces modules utilisent l'IA pour prédire les ruptures de stock ou analyser les réclamations.
- *Astuce : Plus vos prompts (questions) sont précis, plus l'IA vous donnera de bonnes réponses !*
"""
    }
]

def run():
    print("Chargement de la base de connaissances...")
    df_kb = load_gs_data(KNOWLEDGE_WORKSHEET, KNOWLEDGE_FALLBACK, COLS_KB)
    
    # On vide l'ancienne base pour être propre, ou on ajoute à la suite. 
    # Pour ne pas recréer de doublons si le script est lancé plusieurs fois, on supprime ceux avec le même titre
    titles_to_remove = [c["titre"] for c in courses]
    if not df_kb.empty:
        df_kb = df_kb[~df_kb['titre'].isin(titles_to_remove)]
    
    current_id = int(df_kb['id'].max()) if (not df_kb.empty and not pd.isna(df_kb['id'].max())) else 0

    new_rows = []
    for course in courses:
        current_id += 1
        new_rows.append({
            "id": current_id,
            "categorie": course["categorie"],
            "titre": course["titre"],
            "contenu": course["contenu"],
            "date_maj": datetime.now().strftime("%d/%m/%Y")
        })
    
    df_kb = pd.concat([df_kb, pd.DataFrame(new_rows)], ignore_index=True)
    
    print("Sauvegarde des cours interactifs...")
    save_gs_data(df_kb, KNOWLEDGE_WORKSHEET, KNOWLEDGE_FALLBACK)
    print("Terminé avec succès !")

if __name__ == "__main__":
    run()
