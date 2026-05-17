import streamlit as st
import base64
from utils_ia import ask_ai_vision, is_ia_scanner_enabled

# --- CONFIGURATION ---
st.set_page_config(page_title="Scanner IA Premium", layout="wide")

etab_nom = "Pharmaciel" if st.session_state.get('etablissement') == 'pharmaciel' else "DarPharm"
st.markdown(f'<h1 style="text-align:center; color:#5b6cf9; font-weight:900;">Robot Scan IA {etab_nom} 🤖</h1>', unsafe_allow_html=True)

st.markdown("""
<style>
    .stApp { background: #eef0f8; }
    .scan-card {
        background: white;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(91,108,249,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .res-label { font-size: 0.8rem; color: #64748b; font-weight: 800; margin-top: 10px; }
    .res-val { font-size: 1.2rem; color: #5b6cf9; font-weight: 900; background: #f8fafc; padding: 10px; border-radius: 12px; margin-top: 5px; border: 1px dashed #5b6cf9; }
</style>
""", unsafe_allow_html=True)

if not is_ia_scanner_enabled():
    st.warning("⚠️ Le Scanner IA n'est pas activé. Activez-le dans Administration > Configuration IA.")
    st.stop()

# --- INTERFACE DE SCAN ---
col_scan, col_res = st.columns([1, 1])

with col_scan:
    st.markdown('<div class="scan-card">📸 CAPTURER LE PRODUIT</div>', unsafe_allow_html=True)
    img_file = st.camera_input("Scanner le Lot/DDP", label_visibility="collapsed")

with col_res:
    st.markdown('<div class="scan-card">🧠 RÉSULTATS IA</div>', unsafe_allow_html=True)
    
    if img_file:
        with st.spinner("L'IA analyse l'image..."):
            # Encodage en base64 pour l'IA
            bytes_data = img_file.getvalue()
            b64_img = base64.b64encode(bytes_data).decode()
            
            prompt = """Analyse cette photo de produit pharmaceutique. 
            Extrait UNIQUEMENT le numéro de LOT et la date de péremption (DDP).
            Format de réponse attendu (JSON uniquement) : {"lot": "...", "ddp": "..."}
            Si non trouvé, laisse vide."""
            
            res_raw = ask_ai_vision(prompt, b64_img)
            
            try:
                import json
                # Nettoyage si l'IA ajoute du markdown
                clean_res = res_raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_res)
                
                st.markdown(f'<div class="res-label">LOT DÉTECTÉ</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="res-val">{data.get("lot", "Non trouvé")}</div>', unsafe_allow_html=True)
                
                st.markdown(f'<div class="res-label">DDP DÉTECTÉE</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="res-val">{data.get("ddp", "Non trouvée")}</div>', unsafe_allow_html=True)
                
                if st.button("✅ Valider et Utiliser", type="primary", use_container_width=True):
                    st.session_state.last_scanned_lot = data.get("lot")
                    st.session_state.last_scanned_ddp = data.get("ddp")
                    st.success("Données enregistrées !")
                    
            except Exception as e:
                st.error("Erreur d'interprétation des données IA.")
                st.write(res_raw)
    else:
        st.info("Veuillez prendre une photo nette du Lot et de la DDP sur la boîte.")

st.divider()
if st.button("🔄 Réinitialiser le scanner", use_container_width=True):
    st.rerun()
