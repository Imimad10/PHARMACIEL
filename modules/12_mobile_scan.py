import streamlit as st
import pandas as pd
import os
import numpy as np
import cv2
from datetime import datetime
from utils import log_action
from utils_themes import apply_theme_css, load_themes_db

# --- CONFIGURATION ---
st.set_page_config(page_title="DarPharm Mobile", layout="centered")

# Application du thème Fluffy
_tdb = load_themes_db()
fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
apply_theme_css(fluffy)

st.markdown("""
<style>
    /* Style spécifique Mobile Fluffy */
    .stApp { background: #eef0f8 !important; }
    
    .mobile-header {
        text-align: center; margin-bottom: 25px;
    }
    .mobile-header h1 {
        font-weight: 900; color: #5b6cf9; font-size: 1.8rem; letter-spacing: -1px;
    }
    
    .mode-card {
        background: #eef0f8; padding: 20px; border-radius: 20px;
        box-shadow: 7px 7px 15px #c0c5dc, -7px -7px 15px #ffffff;
        text-align: center; margin-bottom: 15px; cursor: pointer;
        transition: all 0.2s; border: none; width: 100%;
    }
    .mode-card:active { box-shadow: inset 4px 4px 10px #c0c5dc, inset -4px -4px 10px #ffffff; transform: scale(0.98); }
    
    .mode-icon { font-size: 2rem; margin-bottom: 8px; }
    .mode-title { font-weight: 800; color: #1a1f3c; }

    /* Overlay Caméra Fluffy */
    .camera-overlay {
        border: 4px solid #5b6cf9; border-radius: 20px;
        position: relative; overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="mobile-header"><h1>DarPharm Mobile 📱</h1><p style="color:#6b7299; font-weight:700;">Interface Terrain Intelligente</p></div>', unsafe_allow_html=True)

# Navigation via Boutons Fluffy (Remplace pills)
if "mobile_mode" not in st.session_state:
    st.session_state.mobile_mode = "HOME"

if st.session_state.mobile_mode == "HOME":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦\nINVENTAIRE", key="btn_inv", use_container_width=True):
            st.session_state.mobile_mode = "INV"
            st.rerun()
    with col2:
        if st.button("🚛\nLIVRAISON", key="btn_liv", use_container_width=True):
            st.session_state.mobile_mode = "LIV"
            st.rerun()
    
    if st.button("💵 RECOUVREMENT CLIENTS", key="btn_rec", use_container_width=True):
        st.session_state.mobile_mode = "REC"
        st.rerun()

    st.markdown("---")
    st.info("💡 **Conseil :** Utilisez le flash de votre téléphone pour une lecture de code-barres optimale.")

elif st.session_state.mobile_mode == "INV":
    if st.button("⬅ Retour"):
        st.session_state.mobile_mode = "HOME"
        st.rerun()
        
    st.subheader("📦 Saisie Rapide")
    zone = st.selectbox("Zone de comptage", ["A", "B", "C", "D", "Frigo", "Vrac"], index=0)
    
    # Bouton Smart Scan IA (Inspiré de votre HTML)
    st.markdown("""
    <div style="background: linear-gradient(135deg, #7c3aed, #4c1d95); padding: 15px; border-radius: 15px; color: white; margin-bottom: 15px; text-align: center;">
        <div style="font-size: 1.5rem;">🤖</div>
        <div style="font-weight: 900;">AI SMART SCAN ACTIVÉ</div>
        <div style="font-size: 0.8rem; opacity: 0.8;">L'IA détectera automatiquement le lot et la DDP</div>
    </div>
    """, unsafe_allow_html=True)
    
    img = st.camera_input("📷 Viser le produit ou la vignette")
    
    if img:
        st.success("✅ Image capturée. Analyse IA en cours...")
        # Ici on appellerait le moteur IA
    
    with st.form("quick_entry"):
        prod = st.text_input("Désignation Produit")
        col_lot, col_ddp = st.columns(2)
        lot = col_lot.text_input("Lot")
        ddp = col_ddp.text_input("DDP (MM/AA)")
        qty = st.number_input("Quantité", min_value=1, step=1)
        
        if st.form_submit_button("💾 ENREGISTRER LA SAISIE"):
            if prod:
                st.balloons()
                st.success(f"Enregistré dans Zone {zone}")
                log_action(st.session_state.current_user['username'], f"Mobile INV: {prod} x{qty}", "Mobile")
            else:
                st.warning("Veuillez saisir au moins le nom du produit.")

elif st.session_state.mobile_mode == "LIV":
    if st.button("⬅ Retour"):
        st.session_state.mobile_mode = "HOME"
        st.rerun()
    
    st.subheader("🚛 Validation de Tournée")
    qr = st.camera_input("📷 Scannez le QR Code de la mission")
    
    if qr:
        # Logique de décodage QR (récupérée de l'original)
        try:
            file_bytes = np.asarray(bytearray(qr.read()), dtype=np.uint8)
            img_cv = cv2.imdecode(file_bytes, 1)
            det = cv2.QRCodeDetector()
            data, _, _ = det.detectAndDecode(img_cv)
            if data:
                st.markdown(f'<div style="background:#d4f5ea; padding:15px; border-radius:15px; border-left:5px solid #2db88a; margin-bottom:15px;">'
                            f'<b>Mission Détectée :</b><br>{data}</div>', unsafe_allow_html=True)
                if st.button("🏁 MARQUER COMME LIVRÉ"):
                    st.success("Tournée terminée !")
                    log_action(st.session_state.current_user['username'], "Mission finie via Mobile", "Mobile")
            else:
                st.warning("QR Code non lisible. Essayez de plus près.")
        except:
            st.error("Erreur technique de lecture.")

elif st.session_state.mobile_mode == "REC":
    if st.button("⬅ Retour"):
        st.session_state.mobile_mode = "HOME"
        st.rerun()
    
    st.subheader("💵 Encaissement Client")
    client = st.text_input("Nom du Client")
    montant = st.number_input("Montant perçu (DA)", min_value=0.0)
    mode_p = st.pills("Mode", ["Espèces", "Chèque", "Virement"], default="Espèces")
    
    if st.button("💰 VALIDER LE PAIEMENT", use_container_width=True):
        if client and montant > 0:
            st.success(f"Paiement de {montant} DA enregistré pour {client}")
            log_action(st.session_state.current_user['username'], f"Paiement Mobile: {client} ({montant})", "Mobile")
        else:
            st.error("Veuillez remplir les informations.")
