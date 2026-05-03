import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import os
import tempfile
import traceback

# --- CONFIGURATION ---
# st.set_page_config(page_title="Darpharm Solution - Automatisation & IA", layout="wide")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

is_admin = st.session_state.current_user.get('role') == 'Admin'

st.title("🤖 Automatisation & IA - Scanner de Factures")

st.info("Ce module utilise l'Intelligence Artificielle de Google (Gemini) pour lire vos factures fournisseurs (Photos ou PDF) et extraire automatiquement les informations structurées des produits.")

from tinydb import TinyDB, Query

# ...

# Récupération de la clé API
api_key = None

# 1. Vérifier la configuration Administrateur (Base de données)
if os.path.exists('data/db_settings.json'):
    db_settings = TinyDB('data/db_settings.json')
    Setting = Query()
    ia_setting = db_settings.search(Setting.name == 'gemini_api_key')
    if ia_setting and ia_setting[0]['value']:
        api_key = ia_setting[0]['value']

# 2. Secours : Vérifier les secrets Streamlit
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except:
        pass

if not api_key:
    st.error("⚠️ Clé API Gemini introuvable.")
    st.markdown("""
    **Comment configurer l'IA très facilement :**
    1. Obtenez une clé API gratuite sur [Google AI Studio](https://aistudio.google.com/app/apikey).
    2. Allez dans le menu **Administration Centrale** > **Gestion des Accès**.
    3. Allez dans l'onglet **🤖 Configuration IA**, collez votre clé et cliquez sur sauvegarder.
    """)
    st.stop()

genai.configure(api_key=api_key)

# Interface de chargement
uploaded_files = st.file_uploader("Chargez une ou plusieurs factures (Photos ou PDF)", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Lancer l'extraction IA", use_container_width=True):
        
        all_results = []
        
        with st.spinner("L'IA lit vos documents... Cela peut prendre quelques secondes."):
            
            for file in uploaded_files:
                # Sauvegarde temporaire pour l'API Gemini
                ext = file.name.split('.')[-1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp_file:
                    tmp_file.write(file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Upload vers Google AI
                    sample_file = genai.upload_file(path=tmp_path)
                    
                    # Prompt strict
                    prompt = """
                    Tu es un assistant expert en logistique pharmaceutique.
                    Analyse cette facture fournisseur et extrait la liste des produits sous forme de tableau JSON strict.
                    Le JSON doit être un tableau (une liste) d'objets avec EXACTEMENT ces clés en minuscules :
                    - "nom_produit" (chaîne)
                    - "lot" (chaîne)
                    - "ddp" (date de péremption, format JJ/MM/AAAA si possible, sinon chaîne)
                    - "qte" (nombre entier)
                    - "ppa" (nombre, prix public algérien)
                    - "shp" (nombre, tarif grossiste/prix d'achat)
                    
                    Ne renvoie RIEN D'AUTRE que le JSON valide. Pas de balises ```json, pas d'explications.
                    S'il manque une information sur la facture, mets la valeur null.
                    S'il n'y a aucun produit détecté, renvoie [].
                    """
                    
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content([sample_file, prompt])
                    
                    # Nettoyage de la réponse
                    res_text = response.text.strip()
                    if res_text.startswith("```json"):
                        res_text = res_text[7:]
                    if res_text.endswith("```"):
                        res_text = res_text[:-3]
                    
                    res_text = res_text.strip()
                    
                    try:
                        data = json.loads(res_text)
                        if isinstance(data, list):
                            for item in data:
                                item['_Source'] = file.name
                            all_results.extend(data)
                        else:
                            st.warning(f"Format inattendu pour le fichier {file.name}")
                    except json.JSONDecodeError:
                        st.error(f"Erreur de décodage JSON pour le fichier {file.name}. Réponse de l'IA : {res_text}")
                        
                except Exception as e:
                    st.error(f"Erreur lors de l'analyse de {file.name} : {str(e)}")
                    st.code(traceback.format_exc())
                finally:
                    # Nettoyage
                    os.remove(tmp_path)
                    
        if all_results:
            st.success("✅ Extraction terminée avec succès !")
            df_factures = pd.DataFrame(all_results)
            
            st.subheader("📊 Résultats consolidés de l'extraction")
            
            # Formatage des colonnes si besoin
            st.dataframe(df_factures, use_container_width=True)
            
            # Export
            csv = df_factures.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Télécharger les données en CSV",
                data=csv,
                file_name="extraction_factures.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("Aucun produit extrait des documents fournis.")
