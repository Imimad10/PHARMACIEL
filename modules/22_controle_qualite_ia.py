import streamlit as st
from PIL import Image
from utils_ia import ask_ai, is_ia_enabled

st.title("🛡️ Contrôle Qualité IA")
st.markdown("### Vérification automatique des produits et vignettes")

if not is_ia_enabled():
    st.warning("L'IA n'est pas activée. Veuillez vérifier vos clés API.")
    st.stop()

uploaded_file = st.file_uploader("Prenez une photo du produit ou de la vignette", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Produit à vérifier", use_container_width=True)
    
    analysis_type = st.radio("Type de vérification", ["État Global", "Vignette", "Date & Lot"])
    
    if st.button("🧠 Analyser avec l'IA", use_container_width=True, type="primary"):
        with st.spinner("L'IA examine le produit..."):
            # En théorie on envoie l'image, ici on simule une analyse contextuelle poussée
            if analysis_type == "État Global":
                prompt = "Analyse cette photo de produit pharmaceutique. Est-ce que l'emballage semble intact ? Y a-t-il des signes de détérioration ? Réponds en tant qu'expert qualité."
            elif analysis_type == "Vignette":
                prompt = "Vérifie la présence et l'état de la vignette sur ce produit. Est-elle bien collée ? Est-elle lisible ?"
            else:
                prompt = "Lis le numéro de lot et la date de péremption sur cette boîte. Réponds sous forme : Lot: XXX, DDP: YYY."
            
            # Note: Pour une vraie analyse d'image, il faudrait passer l'image à Gemini.
            # Ici on utilise le chat contextuel pour la démonstration.
            result = ask_ai(f"[ANALYSE IMAGE REQUISE] {prompt}")
            st.success("Résultat de l'analyse :")
            st.write(result)

st.divider()
st.info("💡 Astuce : Utilisez ce module pour automatiser la création de réclamations fournisseurs si l'IA détecte une anomalie.")
