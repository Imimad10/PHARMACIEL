import streamlit as st
import streamlit.components.v1 as components

st.title("Test Translation")
st.write("Bonjour, voici un test.")

components.html("""
<script>
const doc = window.parent.document;
if (!doc.getElementById('google_translate_script')) {
    const script1 = doc.createElement('script');
    script1.type = 'text/javascript';
    script1.innerHTML = `
        function googleTranslateElementInit() {
          new window.google.translate.TranslateElement({pageLanguage: 'fr', includedLanguages: 'ar,fr', layout: window.google.translate.TranslateElement.InlineLayout.SIMPLE}, 'google_translate_element');
        }
    `;
    doc.head.appendChild(script1);
    
    const script2 = doc.createElement('script');
    script2.id = 'google_translate_script';
    script2.type = 'text/javascript';
    script2.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    doc.head.appendChild(script2);
    
    const floatingDiv = doc.createElement('div');
    floatingDiv.id = 'google_translate_element';
    floatingDiv.style.position = 'fixed';
    floatingDiv.style.top = '10px';
    floatingDiv.style.right = '10px';
    floatingDiv.style.zIndex = '999999';
    doc.body.appendChild(floatingDiv);
}
</script>
""", height=0)
