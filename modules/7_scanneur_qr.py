import streamlit as st
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="Scanner IA Premium", layout="wide")

st.markdown("""
<style>
    .stApp { background: #eef0f8; }
    .main .block-container { padding: 0; }
</style>
""", unsafe_allow_html=True)

# --- MOTEUR DE SCAN HTML/JS (Inspiré de votre code) ---
SCANNER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@800;900&display=swap" rel="stylesheet">
    <style>
        body { margin: 0; font-family: 'Nunito', sans-serif; background: #eef0f8; overflow: hidden; display: flex; flex-direction: column; height: 100vh; }
        #video-container { position: relative; flex: 1; background: #000; overflow: hidden; display: flex; align-items: center; justify-content: center; }
        video { width: 100%; height: 100%; object-fit: cover; }
        
        .overlay { 
            position: absolute; border: 3px solid #5b6cf9; border-radius: 20px;
            width: 80%; height: 150px; box-shadow: 0 0 0 1000px rgba(0,0,0,0.5);
            pointer-events: none; display: flex; align-items: center; justify-content: center;
        }
        .overlay::after { content: "PLACER LE LOT / DDP ICI"; color: #5b6cf9; font-weight: 900; font-size: 0.8rem; background: white; padding: 2px 10px; border-radius: 10px; margin-top: 180px; }

        .results-panel { 
            background: #eef0f8; padding: 20px; border-radius: 30px 30px 0 0;
            box-shadow: 0 -10px 20px rgba(0,0,0,0.1); display: flex; flex-direction: column; gap: 15px;
        }
        .res-row { display: flex; justify-content: space-between; align-items: center; }
        .res-val { background: white; padding: 10px 20px; border-radius: 15px; box-shadow: inset 2px 2px 5px #c0c5dc; font-weight: 900; color: #5b6cf9; }
        
        button { 
            background: linear-gradient(135deg, #5b6cf9, #3a47d5); color: white; border: none; 
            padding: 15px; border-radius: 20px; font-weight: 900; cursor: pointer;
            box-shadow: 0 5px 15px rgba(91,108,249,0.4);
        }
    </style>
</head>
<body>
    <div id="video-container">
        <video id="video" autoplay playsinline></video>
        <div class="overlay"></div>
    </div>

    <div class="results-panel">
        <div class="res-row">
            <span>PRODUIT DÉTECTÉ</span>
            <div id="res-prod" class="res-val">---</div>
        </div>
        <div class="res-row">
            <span>LOT / DDP</span>
            <div id="res-lot" class="res-val">EN ATTENTE...</div>
        </div>
        <button onclick="startOCR()">🤖 ANALYSER MAINTENANT</button>
        <button style="background: #e2e8f0; color: #64748b; margin-top:5px;" onclick="window.parent.location.reload()">RETOUR</button>
    </div>

    <script>
        const video = document.getElementById('video');
        const resLot = document.getElementById('res-lot');

        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
            .then(stream => { video.srcObject = stream; });

        async function startOCR() {
            resLot.innerText = "ANALYSE...";
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            
            const { data: { text } } = await Tesseract.recognize(canvas, 'eng', { logger: m => console.log(m) });
            
            // Extraction simple (Ex: Lot, DDP)
            const lotMatch = text.match(/[A-Z0-9]{5,10}/);
            const ddpMatch = text.match(/[0-9]{2}\\/[0-9]{2,4}/);
            
            resLot.innerText = (lotMatch ? lotMatch[0] : "") + " " + (ddpMatch ? ddpMatch[0] : "LOT NON TROUVÉ");
            
            // Envoyer à Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: { lot: lotMatch ? lotMatch[0] : "", ddp: ddpMatch ? ddpMatch[0] : "", raw: text }
            }, '*');
        }
    </script>
</body>
</html>
"""

st.markdown('<h2 style="text-align:center; color:#5b6cf9; font-weight:900;">Robot Scan DarPharm 🤖</h2>', unsafe_allow_html=True)

# Affichage du scanner haute performance
scan_result = components.html(SCANNER_HTML, height=700, scrolling=False)

if scan_result:
    st.success(f"Données extraites : {scan_result}")
    # Logique pour enregistrer le résultat
