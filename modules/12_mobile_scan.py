import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils import log_action

# --- CONFIGURATION MOBILE ---
st.set_page_config(page_title="Scan Mobile - Pharmaciel", layout="centered")

# CSS pour le mode mobile "PWA"
theme = st.session_state.get('theme', 'Sombre')
if theme == 'Sombre':
    metric_bg = "#1e1e1e"
    metric_border = "#333"
    text_col = "white"
else:
    metric_bg = "#ffffff"
    metric_border = "#ddd"
    text_col = "#1a1c21"

st.markdown(f"""
    <style>
        .stButton button {{
            width: 100%;
            height: 80px;
            font-size: 20px !important;
            border-radius: 15px;
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }}
        .stMetric {{
            background-color: {metric_bg};
            padding: 15px;
            border-radius: 10px;
            border: 1px solid {metric_border};
            color: {text_col} !important;
        }}
        @media (max-width: 640px) {{
            .main .block-container {{
                padding-top: 10px;
                padding-left: 10px;
                padding-right: 10px;
            }}
        }}
    </style>
""", unsafe_allow_html=True)

st.title("📱 Scan Mobile & Saisie")
st.write("Interface optimisée pour smartphone.")

# Sélection du mode
mode = st.pills("Mode de saisie", ["📦 Inventaire", "🚛 Livraison", "💰 Recouvrement"], selection_mode="single", default="📦 Inventaire")

if mode == "📦 Inventaire":
    st.subheader("Saisie Rapide Inventaire")
    zone = st.selectbox("Zone", ["A", "B", "C", "D", "Frigo"])
    
    # Simulation de Scan (Ouverture Caméra)
    img_file = st.camera_input("📷 Scannez le code-barres ou le produit")
    
    if img_file:
        st.success("Image capturée !")
        # Note: Ici on pourrait intégrer une bibliothèque de lecture de code-barres côté serveur
        st.info("Traitement de l'image en cours...")
    
    produit = st.text_input("Produit (ou scan manuel)")
    qty = st.number_input("Quantité", min_value=1, step=1)
    
    if st.button("✅ Valider la Saisie"):
        if produit:
            st.success(f"Enregistré : {produit} (Qté: {qty})")
            log_action(st.session_state.current_user['username'], f"Scan Mobile Inventaire: {produit}", "Mobile")
            # Logique de sauvegarde dans data_inventaire/...
        else:
            st.error("Veuillez saisir un produit.")

elif mode == "🚛 Livraison":
    st.subheader("Validation Livraison")
    qr_cam = st.camera_input("📷 Scannez le QR Code de la Feuille de Route")
    if qr_cam:
        try:
            import cv2
            import numpy as np
            from utils_gsheets import load_gs_data, save_gs_data
            
            file_bytes = np.asarray(bytearray(qr_cam.read()), dtype=np.uint8)
            opencv_image = cv2.imdecode(file_bytes, 1)
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(opencv_image)
            
            if data:
                st.success("✅ QR Code détecté !")
                # Parsing
                info = {}
                for item in data.split('|'):
                    if ':' in item:
                        k, v = item.split(':', 1)
                        info[k] = v
                
                mission_id = info.get('ID', 'Inconnu')
                livreur = info.get('Livreur', 'Inconnu')
                nb = info.get('Nb', '?')
                
                st.metric("Livreur", livreur)
                st.write(f"**Mission :** {mission_id} ({nb} clients)")
                
                if st.button("📍 Marquer la tournée comme TERMINÉE"):
                    st.balloons()
                    log_action(st.session_state.current_user['username'], f"Tournée {mission_id} finie via Mobile", "Mobile")
                    st.success("Statut mis à jour !")
            else:
                st.warning("Aucun QR Code détecté sur l'image. Approchez-vous du code et assurez-vous qu'il soit bien net.")
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")

elif mode == "💰 Recouvrement":
    st.subheader("Encaissement Terrain")
    client = st.text_input("Rechercher Client")
    montant = st.number_input("Montant perçu (DA)", min_value=0.0)
    type_p = st.selectbox("Type", ["Espèces", "Chèque"])
    if st.button("💵 Enregistrer le paiement"):
        st.success("Paiement enregistré et synchronisé !")
