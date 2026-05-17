import pandas as pd
import streamlit as st
from utils_gsheets import load_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK
from utils_ia import ask_ai

# Configuration des sources de données pour le Cortex
DB_RECLAM_WORKSHEET = "Reclamations"
DB_RECLAM_FALLBACK = "data/db_reclamations.csv"

DB_VENTES_WORKSHEET = "Ventes_Performance"
DB_VENTES_FALLBACK = "data/db_ventes.csv"

DB_STOCK_WORKSHEET = "Inventaire"
DB_STOCK_FALLBACK = "data/db_inventaire.csv"

def get_strategic_snapshot():
    """Agrège toutes les données de la plateforme pour créer un contexte global pour l'IA."""
    snapshot = {}
    
    # 1. Données Utilisateurs & Rôles
    df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
    snapshot['users_count'] = len(df_users) if not df_users.empty else 0
    
    # 2. Données Réclamations (Analyse des fautes)
    df_reclam = load_gs_data(DB_RECLAM_WORKSHEET, DB_RECLAM_FALLBACK)
    if not df_reclam.empty:
        snapshot['total_reclamations'] = len(df_reclam)
        snapshot['top_motif'] = df_reclam['motif'].value_counts().idxmax() if 'motif' in df_reclam.columns else "N/A"
        snapshot['critical_agent'] = df_reclam['cree_par'].value_counts().idxmax() if 'cree_par' in df_reclam.columns else "N/A"
    
    # 3. Données Ventes (Rentabilité & Pertes)
    df_ventes = load_gs_data(DB_VENTES_WORKSHEET, DB_VENTES_FALLBACK)
    if not df_ventes.empty:
        snapshot['total_ca'] = df_ventes['prix_vente'].sum() if 'prix_vente' in df_ventes.columns else 0
        snapshot['total_marge'] = df_ventes['marge'].sum() if 'marge' in df_ventes.columns else 0
        snapshot['peak_hour'] = df_ventes['heure'].mode()[0] if 'heure' in df_ventes.columns else "N/A"
    
    # 4. Données Stock (Péremptions & Dormants)
    df_stock = load_gs_data(DB_STOCK_WORKSHEET, DB_STOCK_FALLBACK)
    if not df_stock.empty:
        snapshot['stock_value'] = len(df_stock) # Simplifié pour l'exemple
        # On pourrait ajouter ici la détection des produits proches de péremption
        
    # 5. Master Inventaire (Liste des Lots partagée)
    try:
        df_master = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", [])
        snapshot['master_lots'] = len(df_master) if not df_master.empty else 0
        if not df_master.empty and "designation" in df_master.columns:
            snapshot['top_products'] = df_master["designation"].dropna().unique()[:10].tolist()
    except: pass
    
    # 6. IA Rules (Règles apprises partagées)
    try:
        df_rules = load_gs_data("IA_Rules", "data/db_ia_rules.csv", [])
        snapshot['active_rules'] = df_rules[df_rules['actif'] == True].to_dict('records') if not df_rules.empty else []
    except: pass
    
    return snapshot

def ask_cortex(question):
    """Interroge l'IA avec le contexte complet de l'entreprise et de l'environnement sanitaire Algérien."""
    snapshot = get_strategic_snapshot()
    
    # Contexte environnemental simulé (on pourrait le rendre dynamique via un autre module)
    env_context = """
    CONTEXTE ENVIRONNEMENTAL (ALGERIE 2026) :
    - Nature des produits : Médicaments et parapharmacie (Régulé).
    - Risques actuels : Ruptures fréquentes sur les DCI essentielles, maladies saisonnières (Grippe, allergies printanières), vigilance virus régionaux.
    - Objectif : Minimiser les pertes (périssables) et liquider les stocks stagnants via des associations intelligentes (cross-selling).
    """
    
    rules_text = ""
    if snapshot.get('active_rules'):
        rules_text = "- RÈGLES MÉTIER APPRISES (Base Commune) :\n"
        for r in snapshot['active_rules']:
            rules_text += f"  * Si '{r.get('mot_cle')}' -> {r.get('instruction')}\n"

    products_text = f"Exemples de stock : {', '.join(snapshot.get('top_products', []))}" if snapshot.get('top_products') else ""

    context = f"""
    Tu es le Cortex Stratégique de DarPharm Pro, expert en logistique pharmaceutique en Algérie. 
    Tu as également le rôle d'IA MÉDICALE INTÉGRÉE : tu connais les classes thérapeutiques, interactions et recommandations des médicaments.
    
    Voici l'état actuel de l'entreprise :
    - Équipe : {snapshot.get('users_count', 0)} collaborateurs.
    - Réclamations : {snapshot.get('total_reclamations', 0)} enregistrées (Taux de fautes à surveiller).
    - Performance : CA {snapshot.get('total_ca', 0):,.0f} DA | Marge {snapshot.get('total_marge', 0):,.0f} DA.
    - Stock Global (Lots) : {snapshot.get('master_lots', 0)} lots. {products_text}
    
    {rules_text}
    
    {env_context}
    
    TA MISSION : 
    1. Proposer des plans de vente agressifs pour les produits stagnants.
    2. Créer des associations (bundles) entre produits stagnants et médicaments de saison/épidémie.
    3. Anticiper les ruptures et proposer des alternatives.
    
    Question de l'administrateur : {question}
    """
    
    return ask_ai(context)

def generate_daily_diagnostics():
    """Génère un rapport de diagnostic automatique basé sur les données."""
    prompt = "Analyse les données actuelles de DarPharm et donne 3 actions prioritaires pour minimiser les pertes et les erreurs aujourd'hui."
    return ask_cortex(prompt)
