import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random

BASE_URL = "https://www.pharmnet-dz.com"

def scrape_pharmnet():
    print("🚀 Démarrage du Scraper PharmNet-DZ...")
    
    # 1. Parcourir l'alphabet pour récupérer tous les liens de médicaments
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    all_product_links = []
    
    for char in alphabet:
        print(f"Recherche des produits commençant par la lettre : {char}")
        url = f"{BASE_URL}/alphabet.aspx?char={char}"
        try:
            res = requests.get(url, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Les liens vers les médicaments ont la structure 'medic.aspx?id='
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if "medic.aspx?id=" in href:
                    full_url = BASE_URL + "/" + href if not href.startswith("http") else href
                    # Eviter les doublons
                    if full_url not in [p['url'] for p in all_product_links]:
                        # On sauvegarde aussi le nom visible sur le lien
                        all_product_links.append({
                            "nom": link.text.strip(),
                            "url": full_url
                        })
            
            # Pause aléatoire pour ne pas bloquer le serveur (Anti-bot)
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            print(f"Erreur sur la lettre {char} : {e}")

    print(f"✅ {len(all_product_links)} produits trouvés au total !")
    
    # Si vous voulez tester, décommentez ceci pour ne scraper que 10 produits :
    # all_product_links = all_product_links[:10]
    
    # 2. Extraire les détails de chaque produit
    produits_detailles = []
    total = len(all_product_links)
    
    for i, prod_info in enumerate(all_product_links):
        url = prod_info['url']
        nom_base = prod_info['nom']
        print(f"[{i+1}/{total}] Extraction : {nom_base}")
        
        try:
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            details = {"Nom": nom_base, "URL": url}
            
            # Trouver l'image
            img_tag = soup.find('img', src=lambda s: s and 'upload' in s.lower() or 'medicament' in s.lower())
            if img_tag:
                img_src = img_tag['src']
                details["Image"] = BASE_URL + "/" + img_src if not img_src.startswith("http") else img_src
            else:
                details["Image"] = ""

            # Extraire le texte de toute la page pour chercher des mots-clés
            text_elements = soup.stripped_strings
            text_list = list(text_elements)
            
            # Extraction heuristique (basée sur l'image envoyée)
            for j, text in enumerate(text_list):
                t_lower = text.lower()
                if "nom commercial" in t_lower and j+1 < len(text_list):
                    details["Nom Commercial"] = text_list[j+1]
                elif "code dci" in t_lower and j+1 < len(text_list):
                    details["Code DCI"] = text_list[j+1]
                elif "forme:" in t_lower or "forme :" in t_lower and j+1 < len(text_list):
                    details["Forme"] = text_list[j+1]
                elif "dosage" in t_lower and j+1 < len(text_list):
                    details["Dosage"] = text_list[j+1]
                elif "conditionnement" in t_lower and j+1 < len(text_list):
                    details["Conditionnement"] = text_list[j+1]
                elif "type" in t_lower and j+1 < len(text_list):
                    details["Type"] = text_list[j+1]
                elif "liste" in t_lower and j+1 < len(text_list):
                    details["Liste"] = text_list[j+1]
                elif "pays" in t_lower and j+1 < len(text_list):
                    details["Pays"] = text_list[j+1]
                elif "ppa" in t_lower and "indicatif" in t_lower and j+1 < len(text_list):
                    details["PPA"] = text_list[j+1]
                elif "tarif de référence" in t_lower and j+1 < len(text_list):
                    details["Tarif de référence"] = text_list[j+1]

            produits_detailles.append(details)
            time.sleep(random.uniform(0.5, 2))
            
        except Exception as e:
            print(f"Erreur sur {url} : {e}")
            
    # 3. Sauvegarder en CSV
    df = pd.DataFrame(produits_detailles)
    df.to_csv("catalogue_pharmnet.csv", index=False, encoding="utf-8-sig")
    print("\n🎉 TERMINÉ ! Les données ont été sauvegardées dans 'catalogue_pharmnet.csv'")

if __name__ == "__main__":
    scrape_pharmnet()
