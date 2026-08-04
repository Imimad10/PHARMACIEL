import streamlit as st
import pandas as pd
import os
import numpy as np
import cv2
import base64
import json
import re
from io import BytesIO
from PIL import Image
from datetime import datetime

from utils import log_action
from utils_themes import apply_theme_css, load_themes_db
from utils_ia import ask_ai_vision, is_ia_scanner_enabled
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION BASE DE DONNÉES SCAN ---
DB_IA_SCANS = "data/db_ia_scans.csv"
COLS_IA_SCANS = ["date_scan", "designation", "lot", "ddp", "ppa", "shp", "couleur"]

# --- CONFIGURATION PAGE ---
etab_nom = "Pharmaciel" if st.session_state.get('etablissement') == 'pharmaciel' else "DarPharm"
st.set_page_config(page_title=f"{etab_nom} Mobile", layout="centered")

# Application du thème Fluffy
_tdb = load_themes_db()
fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
apply_theme_css(fluffy)

st.markdown("""
<style>
    /* Style spécifique Mobile Fluffy */
    .stApp { background: #eef0f8 !important; }
    
    .mobile-header {
        text-align: center; margin-bottom: 20px;
    }
    .mobile-header h1 {
        font-weight: 900; color: #5b6cf9; font-size: 1.8rem; letter-spacing: -1px; margin-bottom: 0px;
    }
    
    .mode-card {
        background: #eef0f8; padding: 18px; border-radius: 20px;
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
    
    .cam-info-box {
        background: linear-gradient(135deg, #1e1b4b, #312e81);
        color: white;
        padding: 14px;
        border-radius: 16px;
        margin-bottom: 15px;
        font-size: 0.88rem;
    }
    
    .vignette-badge {
        background: #dbeafe;
        color: #1e40af;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(f'<div class="mobile-header"><h1>{etab_nom} Mobile 📱</h1><p style="color:#6b7299; font-weight:700;">Interface Terrain Intelligente</p></div>', unsafe_allow_html=True)

# Navigation via Boutons Fluffy
if "mobile_mode" not in st.session_state:
    st.session_state.mobile_mode = "HOME"

# --- HELPER ANALYSE VIGNETTES IA ---
def process_vignette_image(img_input):
    """Prend une image (UploadedFile, BytesIO ou Image PIL) et retourne les données extraites par l'IA."""
    if isinstance(img_input, (BytesIO, Image.Image)):
        img = Image.open(img_input) if isinstance(img_input, BytesIO) else img_input
    else:
        img = Image.open(img_input)
    
    buffered = BytesIO()
    img.convert('RGB').save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Chargement des règles IA personnalisées si disponibles
    regles_ia = ""
    try:
        if os.path.exists("data/db_ia_rules.csv"):
            df_rules = pd.read_csv("data/db_ia_rules.csv", encoding='utf-8')
            active_rules = df_rules[df_rules['actif'] == True]
            if not active_rules.empty:
                regles_ia = "\n\nRÈGLES D'APPRENTISSAGE SPÉCIFIQUES AJOUTÉES PAR L'ADMIN :\n"
                for _, rule in active_rules.iterrows():
                    regles_ia += f"- Si tu détectes '{rule.get('mot_cle', '')}' : {rule.get('instruction', '')}\n"
    except Exception:
        pass

    prompt = f"""
    Tu es un expert en lecture de vignettes pharmaceutiques algériennes et boîtes de médicaments.
    Extrais les informations de cette image avec une très grande précision.
    
    Règles très strictes :
    1. designation: Nom commercial + dosage + forme + conditionnement (ex: LAVIDA 4mg Boite de 30 cps). Ignore le laboratoire.
    2. ppa et shp: 
       ATTENTION PIÈGE ! Sur la vignette, il est souvent écrit "PPA : 808.00 DA" tout en bas, mais c'est le PRIX TOTAL.
       Regarde attentivement la ligne du haut. Si tu lis "Prix: 805.50 + SHP 2.50", alors:
       - ppa = 805.50 (c'est le prix de base)
       - shp = 2.50
       Le SHP ne peut être que 0.0, 1.5 ou 2.5. Si tu ne vois pas de SHP, mets 0.0.
       NE METS JAMAIS le prix total (ex: 808.00) dans le champ ppa si un SHP de 2.50 est appliqué.
    3. lot: Le numéro de lot (ex: 16001).
    4. ddp: Date de péremption ou Exp (ex: 02/2019).
    5. couleur: La couleur dominante de la bande de la vignette (ex: Vert, Rouge, Bleu, Jaune, Blanc).
    {regles_ia}

    Retourne UNIQUEMENT un JSON brut sans markdown avec ces clés exactes :
    {{
        "designation": "...",
        "lot": "...",
        "ddp": "...",
        "ppa": 0.0,
        "shp": 0.0,
        "qte": 1,
        "couleur": "..."
    }}
    """
    
    res_raw = ask_ai_vision(prompt, img_str)
    if res_raw.startswith("⚠️") or res_raw.startswith("Erreur"):
        raise ValueError(res_raw)
        
    json_match = re.search(r'\{.*\}', res_raw, re.DOTALL)
    if not json_match:
        raise ValueError(f"Aucune donnée analysable sur l'image.")
        
    return json.loads(json_match.group(0))


# --- HOMEPAGE / MENU PRINCIPAL ---
if st.session_state.mobile_mode == "HOME":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏷️\nSCAN VIGNETTES", key="btn_vig", use_container_width=True):
            st.session_state.mobile_mode = "VIG"
            st.rerun()
        if st.button("📦\nINVENTAIRE", key="btn_inv", use_container_width=True):
            st.session_state.mobile_mode = "INV"
            st.rerun()
    with col2:
        if st.button("🚛\nLIVRAISON", key="btn_liv", use_container_width=True):
            st.session_state.mobile_mode = "LIV"
            st.rerun()
        if st.button("💵\nRECOUVREMENT", key="btn_rec", use_container_width=True):
            st.session_state.mobile_mode = "REC"
            st.rerun()

    st.markdown("---")
    st.info("💡 **Conseil Terrain :** Activez le flash et privilégiez la **caméra arrière** de votre smartphone pour une lisibilité maximale des vignettes et codes-barres.")


# --- MODE VIG : SCAN VIGNETTES IA (MULTI-UPLOADER & CAMÉRA ARRIÈRE) ---
elif st.session_state.mobile_mode == "VIG":
    if st.button("⬅ Retour Accueil"):
        st.session_state.mobile_mode = "HOME"
        st.rerun()

    st.subheader("🏷️ Scan IA de Vignettes")
    st.markdown("""
    <div class="cam-info-box">
        <b>📷 Mode Caméra Arrière & Multi-Photos</b><br>
        • Uploadez <b>une ou plusieurs images</b> de vignettes simultanément depuis votre téléphone.<br>
        • Ou utilisez la <b>caméra arrière direct</b> en cliquant sur le commutateur d'objectif.
    </div>
    """, unsafe_allow_html=True)

    tab_upload, tab_camera = st.tabs(["📁 Uploader Vignette(s) (1 ou +)", "📷 Caméra Arrière Live"])

    images_to_process = []

    with tab_upload:
        uploaded_files = st.file_uploader(
            "📤 Choisissez une ou plusieurs photos de vignettes",
            type=['png', 'jpg', 'jpeg', 'webp'],
            accept_multiple_files=True,
            key="vignette_multi_uploader"
        )
        if uploaded_files:
            st.success(f"📥 {len(uploaded_files)} image(s) sélectionnée(s).")
            cols = st.columns(min(len(uploaded_files), 4))
            for idx, file in enumerate(uploaded_files):
                with cols[idx % 4]:
                    st.image(file, use_container_width=True, caption=f"Img {idx+1}")
            images_to_process = uploaded_files

    with tab_camera:
        st.markdown("**📸 Prise de vue (Caméra Arrière)**")
        st.caption("💡 Sur mobile, si l'objectif par défaut est la caméra selfie, appuyez sur l'icône de retournement 🔄 en haut de la zone de capture.")
        
        st.markdown("""
        <div style="background:#f1f5f9; padding:12px; border-radius:12px; text-align:center; border:1px dashed #5b6cf9; margin-bottom:10px;">
            <p style="margin:0 0 6px 0; font-size:0.85rem; font-weight:700; color:#334155;">📷 Capture Directe Caméra Arrière (Mobile)</p>
            <input type="file" accept="image/*" capture="environment" id="html5_rear_cam" style="display:none;" onchange="
                const file = this.files[0];
                if(file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        window.parent.postMessage({type: 'streamlit:setComponentValue', value: e.target.result}, '*');
                    };
                    reader.readAsDataURL(file);
                }
            ">
        </div>
        """, unsafe_allow_html=True)

        cam_img = st.camera_input("Viser la vignette", key="cam_vignette_input")
        if cam_img and not uploaded_files:
            images_to_process = [cam_img]

    # --- TRAITEMENT ET ANALYSE IA ---
    if images_to_process:
        if st.button("🚀 LANCER L'ANALYSE IA DES VIGNETTES", type="primary", use_container_width=True):
            st.session_state.vignette_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, img_file in enumerate(images_to_process):
                status_text.text(f"Analyse de l'image {i+1}/{len(images_to_process)} par l'IA...")
                try:
                    data = process_vignette_image(img_file)
                    data["date_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.vignette_results.append(data)
                except Exception as e:
                    st.error(f"Erreur sur l'image {i+1} : {str(e)}")
                progress_bar.progress((i + 1) / len(images_to_process))

            status_text.empty()
            st.success(f"✅ {len(st.session_state.vignette_results)} vignette(s) analysée(s) avec succès !")

    # --- AFFICHAGE & ENREGISTREMENT DES RÉSULTATS ---
    if "vignette_results" in st.session_state and st.session_state.vignette_results:
        st.markdown("---")
        st.markdown("### 📋 Résultats & Validation")
        df_res = pd.DataFrame(st.session_state.vignette_results)

        edited_df = st.data_editor(
            df_res,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "designation": st.column_config.TextColumn("Désignation Produit", required=True),
                "lot": st.column_config.TextColumn("N° Lot"),
                "ddp": st.column_config.TextColumn("DDP (MM/AA)"),
                "ppa": st.column_config.NumberColumn("PPA (DA)", format="%.2f DA"),
                "shp": st.column_config.NumberColumn("SHP (DA)", format="%.2f DA"),
                "qte": st.column_config.NumberColumn("Quantité", min_value=1, step=1),
                "couleur": st.column_config.TextColumn("Couleur Vignette"),
            },
            key="vignette_data_editor"
        )

        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("💾 ENREGISTRER DANS LA BASE", type="primary", use_container_width=True):
                try:
                    df_ia = load_gs_data("IA_Scans", DB_IA_SCANS, COLS_IA_SCANS)
                    records = edited_df.to_dict(orient="records")
                    new_rows = []
                    for r in records:
                        new_rows.append({
                            "date_scan": r.get("date_scan", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                            "designation": r.get("designation", ""),
                            "lot": r.get("lot", ""),
                            "ddp": r.get("ddp", ""),
                            "ppa": float(r.get("ppa", 0.0) or 0.0),
                            "shp": float(r.get("shp", 0.0) or 0.0),
                            "couleur": r.get("couleur", "")
                        })
                    
                    df_new = pd.DataFrame(new_rows)
                    df_final = pd.concat([df_ia, df_new], ignore_index=True)
                    save_gs_data(df_final, "IA_Scans", DB_IA_SCANS)

                    user = st.session_state.get('current_user', {}).get('username', 'MobileUser')
                    log_action(user, f"Mobile: Scan de {len(new_rows)} vignette(s)", "Mobile")
                    
                    st.balloons()
                    st.success("🎉 Données enregistrées avec succès dans la base des scans IA !")
                    st.session_state.vignette_results = []
                except Exception as ex:
                    st.error(f"Erreur lors de l'enregistrement : {str(ex)}")

        with col_reset:
            if st.button("🔄 Effacer", use_container_width=True):
                st.session_state.vignette_results = []
                st.rerun()


# --- MODE INV : INVENTAIRE SAISIE RAPIDE ---
elif st.session_state.mobile_mode == "INV":
    if st.button("⬅ Retour"):
        st.session_state.mobile_mode = "HOME"
        st.rerun()
        
    st.subheader("📦 Saisie Inventaire Rapide")
    zone = st.selectbox("Zone de comptage", ["A", "B", "C", "D", "Frigo", "Vrac"], index=0)
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #7c3aed, #4c1d95); padding: 15px; border-radius: 15px; color: white; margin-bottom: 15px; text-align: center;">
        <div style="font-size: 1.4rem;">🤖 SMART SCAN IA & CAMÉRA ARRIÈRE</div>
        <div style="font-size: 0.8rem; opacity: 0.85;">Prenez une photo avec la caméra arrière ou importez des vignettes</div>
    </div>
    """, unsafe_allow_html=True)
    
    inv_tab1, inv_tab2 = st.tabs(["📷 Caméra Directe", "📁 Importer Photo/Vignette"])
    inv_img = None
    with inv_tab1:
        st.caption("💡 Basculez sur l'objectif arrière pour la visée produit")
        cam_inv = st.camera_input("📷 Viser le produit ou la vignette", key="inv_cam_input")
        if cam_inv: inv_img = cam_inv
    with inv_tab2:
        up_inv = st.file_uploader("Upload photo produit / vignette", type=['png', 'jpg', 'jpeg', 'webp'], key="inv_file_up")
        if up_inv: inv_img = up_inv

    ai_data = {}
    if inv_img:
        if st.button("🧠 PRÉ-REMPLIR PAR IA", type="primary", use_container_width=True):
            with st.spinner("Analyse par l'IA en cours..."):
                try:
                    ai_data = process_vignette_image(inv_img)
                    st.success("✅ Données extraites par l'IA !")
                except Exception as err:
                    st.warning(f"Analyse partielle : {err}")
    
    with st.form("quick_entry"):
        prod = st.text_input("Désignation Produit", value=ai_data.get("designation", ""))
        col_lot, col_ddp = st.columns(2)
        lot = col_lot.text_input("Lot", value=ai_data.get("lot", ""))
        ddp = col_ddp.text_input("DDP (MM/AA)", value=ai_data.get("ddp", ""))
        qty = st.number_input("Quantité", min_value=1, value=int(ai_data.get("qte", 1)), step=1)
        
        if st.form_submit_button("💾 ENREGISTRER LA SAISIE"):
            if prod:
                st.balloons()
                st.success(f"Produit enregistré dans Zone {zone}")
                user = st.session_state.get('current_user', {}).get('username', 'MobileUser')
                log_action(user, f"Mobile INV: {prod} (Lot: {lot}) x{qty}", "Mobile")
            else:
                st.warning("Veuillez saisir au moins le nom du produit.")


# --- MODE LIV : VALIDATION DE TOURNÉE ---
elif st.session_state.mobile_mode == "LIV":
    if st.button("⬅ Retour"):
        st.session_state.mobile_mode = "HOME"
        st.rerun()
    
    st.subheader("🚛 Validation de Tournée")
    st.caption("💡 Utilisez la caméra arrière pour scanner le QR code de la mission")
    qr = st.camera_input("📷 Scannez le QR Code de la mission", key="liv_cam_qr")
    
    if qr:
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
                    user = st.session_state.get('current_user', {}).get('username', 'MobileUser')
                    log_action(user, "Mission finie via Mobile", "Mobile")
            else:
                st.warning("QR Code non lisible. Rapprochez la caméra arrière.")
        except Exception as e:
            st.error(f"Erreur technique de lecture : {e}")


# --- MODE REC : ENCAISSEMENT CLIENT ---
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
            user = st.session_state.get('current_user', {}).get('username', 'MobileUser')
            log_action(user, f"Paiement Mobile: {client} ({montant} DA)", "Mobile")
        else:
            st.error("Veuillez remplir les informations.")
