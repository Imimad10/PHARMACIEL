import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
from utils_gsheets import load_gs_data
from utils_themes import apply_user_theme

# Configuration de la page (si lancée seule, mais généralement incluse dans app.py)
# st.set_page_config(page_title="Dashboard Premium", layout="wide")

def get_premium_dashboard():
    # 1. Collecte des données réelles du projet
    # Ces colonnes correspondent à ce que le dashboard HTML attend
    # data_inventaire/saisie.csv semble être la source principale
    df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", 
                          ["designation", "ddp_saisi", "num_lot", "quantite"])
    
    meds_list = []
    total_units = 0
    expired_count = 0
    expiring_soon_count = 0
    
    now = datetime.now()
    
    if not df_inv.empty:
        for i, row in df_inv.iterrows():
            name = str(row.get('designation', 'Inconnu'))
            expiry_str = str(row.get('ddp_saisi', '')) # Format MM/YYYY ou YYYY-MM
            lot = str(row.get('num_lot', '—'))
            qty = 0
            try:
                qty = int(float(row.get('quantite', 0)))
            except: pass
            
            total_units += qty
            
            # Calcul de l'état de péremption
            status = "ok"
            if expiry_str:
                try:
                    # Tentative de parsing
                    if '/' in expiry_str:
                        exp_dt = datetime.strptime(expiry_str, '%m/%Y')
                    else:
                        exp_dt = datetime.strptime(expiry_str, '%Y-%m')
                    
                    diff_months = (exp_dt.year - now.year) * 12 + (exp_dt.month - now.month)
                    
                    if diff_months < 0:
                        status = "expired"
                        expired_count += 1
                    elif diff_months <= 3:
                        status = "soon"
                        expiring_soon_count += 1
                except: pass

            meds_list.append({
                "id": i,
                "name": name,
                "letter": name[0].upper() if name else "?",
                "shelf": qty,
                "store": 0,
                "lot": lot,
                "expiry": expiry_str,
                "ppa": 0, # Donnée manquante dans saisie.csv ?
                "lab": "",
                "unitPerBox": 0
            })

    # 2. Collecte des transactions (Dernières actions)
    df_logs = load_gs_data("Logs", "data/db_logs.csv", ["timestamp", "user", "action", "module"])
    recent_actions = []
    if not df_logs.empty:
        for i, row in df_logs.tail(10).iterrows():
            recent_actions.append({
                "user": row.get('user', 'Système'),
                "action": row.get('action', ''),
                "module": row.get('module', ''),
                "time": row.get('timestamp', '')
            })

    # 3. Chargement et Modification du HTML
    # Priorité 1 : assets/ (importé via Admin Centrale)
    html_path = os.path.join(os.getcwd(), "assets", "dashboard_premium.html")

    # Priorité 2 : Bureau (chemin historique)
    if not os.path.exists(html_path):
        html_path = r"C:\Users\DARPHARM DEPOT 2\Desktop\DARNA_integrated.html"

    if not os.path.exists(html_path):
        st.error(f"❌ Aucun fichier HTML premium trouvé.")
        st.info("💡 **Solution :** Allez dans **Administration Centrale** → onglet **🎨 Gestion des Thèmes** → section **📂 Dashboard Premium** pour importer votre fichier HTML.")
        if st.button("📂 Aller à l'Administration Centrale"):
            st.switch_page("modules/0_admin_centrale.py")
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Injection des données Python dans le JavaScript du HTML
    # On cherche la section 'var imported = [...]' et on la remplace
    
    # Préparation du script d'injection
    injection_script = f"""
    <script>
    // Injection des données depuis Python
    (function() {{
        console.log("Injection des données Python en cours...");
        const medsData = {json.dumps(meds_list)};
        const kpis = {{
            totalMeds: {len(meds_list)},
            totalUnits: {total_units},
            expired: {expired_count},
            expiringSoon: {expiring_soon_count}
        }};
        
        // On attend que l'application soit chargée pour écraser les données
        window.addEventListener('load', function() {{
            if (typeof localStorage !== 'undefined') {{
                localStorage.setItem('pharma_meds', JSON.stringify(medsData));
                // Optionnel: on peut aussi injecter les KPIs directement dans le DOM si besoin
                document.getElementById('s-total').textContent = kpis.totalMeds;
                document.getElementById('s-units').textContent = kpis.totalUnits;
                document.getElementById('s-expired').textContent = kpis.expired;
                document.getElementById('s-expiring').textContent = kpis.expiringSoon;
                
                // Mettre à jour la date
                const now = new Date();
                const options = {{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }};
                document.getElementById('headerDate').textContent = now.toLocaleDateString('ar-DZ', options);
            }}
        }});
    }})();
    </script>
    """
    
    # On insère le script juste avant la fermeture du body
    final_html = html_content.replace("</body>", injection_script + "</body>")

    # 4. Rendu
    # Note: On définit une hauteur importante pour éviter le double scroll si possible
    components.html(final_html, height=850, scrolling=True)

# Interface Streamlit
st.title("💎 Dashboard Premium — Darpharm")

# Application automatique du thème de l'utilisateur
if "current_user" in st.session_state and st.session_state.current_user:
    apply_user_theme(st.session_state.current_user.get("username", ""))

get_premium_dashboard()
