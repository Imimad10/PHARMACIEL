import streamlit as st
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_pdf import generate_reception_pdf
from utils_ia import ask_ai_vision, is_ia_enabled
from utils_themes import apply_theme_css, load_themes_db
import difflib
import base64
import re
from PIL import Image
from io import BytesIO

# --- CONFIGURATION ---
st.set_page_config(page_title="Réception Premium - Pharmaciel", layout="wide")

# Application du thème Fluffy
_tdb = load_themes_db()
fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
apply_theme_css(fluffy)

DB_RECEPTIONS = "data/db_receptions.csv"
DB_PRODUITS_RECEPTION = "data/db_reception_produits.csv"
DB_IA_SCANS = "data/db_ia_scans.csv"
DB_SUIVI_DIRECT = "data/db_suivi_direct.csv"
COLS_RECEPTIONS = ["id", "date", "fournisseur", "facture_num", "statut", "items", "created_by"]
COLS_PRODUITS = ["Designation", "PPA", "SHP", "Colissage"]
COLS_IA_SCANS = ["date_scan", "designation", "lot", "ddp", "ppa", "shp", "couleur"]
COLS_SUIVI_DIRECT = ["timestamp", "utilisateur", "methode", "designation", "qte", "lot", "ddp", "ppa"]

def log_saisie_en_cours(methode, designation, qte, lot, ddp, ppa):
    df_live = load_gs_data("Suivi_Direct", DB_SUIVI_DIRECT, COLS_SUIVI_DIRECT)
    
    user = "Inconnu"
    if "current_user" in st.session_state and st.session_state.current_user:
        user = st.session_state.current_user.get('username', 'Inconnu')
        
    new_row = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "utilisateur": user,
        "methode": methode,
        "designation": designation,
        "qte": qte,
        "lot": lot,
        "ddp": ddp,
        "ppa": ppa
    }])
    
    df_live = pd.concat([df_live, new_row], ignore_index=True)
    df_live = df_live.tail(500) # Garder les 500 dernières saisies
    save_gs_data(df_live, "Suivi_Direct", DB_SUIVI_DIRECT)

def verifier_ddp_courte(ddp_str):
    if not ddp_str: return False
    try:
        ddp_clean = ddp_str.strip().replace('-', '/').replace('.', '/')
        parts = ddp_clean.split('/')
        if len(parts) != 2: return False
        m = int(parts[0])
        y = int(parts[1])
        if y < 100: y += 2000
        now = datetime.now()
        ddp_date = datetime(y, m, 1)
        if (ddp_date - now).days < 365:
            return True
    except:
        pass
    return False

# --- CSS ADDITIONNEL RÉCEPTION ---
st.markdown("""
<style>
    .reception-header {
        background: #eef0f8; padding: 25px; border-radius: 30px;
        box-shadow: 7px 7px 18px #c0c5dc, -7px -7px 18px #ffffff;
        margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;
    }
    .facture-card {
        background: #eef0f8; padding: 20px; border-radius: 20px;
        box-shadow: inset 4px 4px 10px #c0c5dc, inset -4px -4px 10px #ffffff;
        margin-bottom: 20px;
    }
    .item-row {
        background: white; padding: 15px; border-radius: 15px;
        margin-bottom: 10px; display: flex; justify-content: space-between;
        align-items: center; box-shadow: 4px 4px 10px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

def load_produits_reception():
    if os.path.exists(DB_PRODUITS_RECEPTION):
        try:
            # Essayer plusieurs encodages et séparateurs avec une tolérance accrue
            df = None
            for sep in [',', ';']:
                for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(DB_PRODUITS_RECEPTION, sep=sep, encoding=enc, engine='python', on_bad_lines='skip')
                        if len(df.columns) > 1: break
                    except: continue
                if df is not None and len(df.columns) > 1: break
            
            if df is None:
                # Dernier recours : lecture brute sans séparateur
                df = pd.read_csv(DB_PRODUITS_RECEPTION, sep='\t', on_bad_lines='skip')

            # Normalisation des colonnes
            mapping = {
                'designation': 'Designation', 'produit': 'Designation', 'article': 'Designation',
                'ppa': 'PPA', 'shp': 'SHP', 'colissage': 'Colissage', 'colis': 'Colissage'
            }
            new_cols = []
            for c in df.columns:
                norm = str(c).lower().strip()
                target = c
                for k, v in mapping.items():
                    if k in norm: target = v; break
                new_cols.append(target)
            df.columns = new_cols
            
            # Vérifier si Designation existe
            if 'Designation' not in df.columns:
                if len(df.columns) == 1: df.columns = ['Designation']
            
            return df
        except Exception as e:
            st.error(f"Erreur lecture produits : {e}")
            return pd.DataFrame(columns=COLS_PRODUITS)
    return pd.DataFrame(columns=COLS_PRODUITS)

def save_reception(reception_data):
    df_old = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    if not reception_data.get('id'):
        reception_data['id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    
    new_row = pd.DataFrame([{
        "id": reception_data['id'], "date": reception_data['date'],
        "fournisseur": reception_data['fournisseur'], "facture_num": reception_data['facture_num'],
        "statut": reception_data['statut'], "items": json.dumps(reception_data['items']),
        "created_by": reception_data['created_by']
    }])
    df_old = pd.concat([df_old, new_row], ignore_index=True)
    save_gs_data(df_old, "Receptions", DB_RECEPTIONS)

if "current_reception" not in st.session_state:
    user_creator = "Utilisateur"
    if "current_user" in st.session_state and st.session_state.current_user:
        user_creator = st.session_state.current_user.get('username', 'Utilisateur')
        
    st.session_state.current_reception = {
        "id": None, "date": datetime.now().strftime("%Y-%m-%d"),
        "fournisseur": "", "facture_num": "", "statut": "En cours", "items": [], "created_by": user_creator
    }

# Chargement fournisseurs
df_fourn = load_gs_data("Fournisseurs", "data/db_fournisseurs.csv", ["Etablissement", "Wilaya", "Activité", "Logo"])
liste_fournisseurs = df_fourn['Etablissement'].dropna().unique().tolist() if not df_fourn.empty else []

# Chargement produits
df_prod = load_produits_reception()

st.markdown('<div class="reception-header"><div><h1 style="color:#5b6cf9; font-weight:900;">Pointage Marchandise 📦</h1><p style="color:#6b7299; font-weight:700;">Vérifiez vos arrivages avec précision</p></div><div style="background:#d4f5ea; padding:10px 20px; border-radius:15px; color:#2db88a; font-weight:900;">⚡ MODE PREMIUM ACTIF</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["⚡ Nouveau Pointage", "📋 Historique", "🧠 Base IA", "📡 En Direct", "🏛️ Administration"])

with tabs[0]:
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        st.subheader("📝 Infos Facture")
        with st.container(border=True):
            f_index = 0
            if st.session_state.current_reception['fournisseur'] in liste_fournisseurs:
                f_index = liste_fournisseurs.index(st.session_state.current_reception['fournisseur']) + 1
            
            st.session_state.current_reception['fournisseur'] = st.selectbox("Fournisseur", [""] + liste_fournisseurs, index=f_index)
            if not st.session_state.current_reception['fournisseur']:
                st.session_state.current_reception['fournisseur'] = st.text_input("Fournisseur (Manuel)", placeholder="Saisir manuellement...")

            st.session_state.current_reception['facture_num'] = st.text_input("N° Facture / BL", value=st.session_state.current_reception['facture_num'])
            st.session_state.current_reception['date'] = st.date_input("Date Réception").strftime("%Y-%m-%d")

        if is_ia_enabled():
            st.markdown("### 🤖 Assistant IA")
            
            # Paramètres IA
            ia_mode = st.radio("Mode de détection", ["Base Système 🔍", "Libre (Nouveau produit) ✨"], horizontal=True)
            
            # Upload d'images
            uploaded_files = st.file_uploader("📸 Scanner des vignettes (Images)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="ia_uploader")
            
            if uploaded_files:
                if st.button("🚀 ANALYSER TOUTES LES IMAGES", use_container_width=True, type="primary"):
                    st.session_state.ia_results = []
                    progress_bar = st.progress(0)
                    
                    for i, file in enumerate(uploaded_files):
                        # Conversion image en base64
                        img = Image.open(file)
                        buffered = BytesIO()
                        img.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Chargement des règles IA personnalisées
                        regles_ia = ""
                        try:
                            df_rules = pd.read_csv("data/db_ia_rules.csv", encoding='utf-8')
                            active_rules = df_rules[df_rules['actif'] == True]
                            if not active_rules.empty:
                                regles_ia = "\n\nRÈGLES D'APPRENTISSAGE SPÉCIFIQUES AJOUTÉES PAR L'ADMIN (TRÈS IMPORTANT) :\n"
                                for _, rule in active_rules.iterrows():
                                    regles_ia += f"- Si tu détectes le mot clé '{rule.get('mot_cle', '')}' : {rule.get('instruction', '')}\n"
                        except Exception:
                            pass
                            
                        prompt = f"""
                        Tu es un expert en lecture de vignettes pharmaceutiques algériennes.
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
                        {
                            "designation": "...",
                            "lot": "...",
                            "ddp": "...",
                            "ppa": 0.0,
                            "shp": 0.0,
                            "qte": 1,
                            "couleur": "..."
                        }
                        """
                        
                        try:
                            res_raw = ask_ai_vision(prompt, img_str)
                            
                            if res_raw.startswith("⚠️") or res_raw.startswith("Erreur"):
                                raise ValueError(res_raw)
                                
                            # Extraction robuste du JSON
                            import re
                            json_match = re.search(r'\{.*\}', res_raw, re.DOTALL)
                            if not json_match:
                                raise ValueError(f"Aucun JSON trouvé dans la réponse: {res_raw[:100]}...")
                                
                            data = json.loads(json_match.group(0))
                            
                            # Matching Base Système si activé
                            if "Base Système" in ia_mode:
                                lp = df_prod['Designation'].dropna().unique().tolist()
                                if lp:
                                    matches = difflib.get_close_matches(data.get('designation', '').upper(), lp, n=1, cutoff=0.4)
                                    if matches:
                                        target_prod = matches[0]
                                        data['designation'] = target_prod
                                        
                                        # Récupération PPA/SHP depuis la base
                                        prod_info = df_prod[df_prod['Designation'] == target_prod].iloc[0]
                                        if pd.notna(prod_info.get('PPA')): data['ppa'] = float(prod_info['PPA'])
                                        if pd.notna(prod_info.get('SHP')): data['shp'] = float(prod_info['SHP'])
                            
                            st.session_state.ia_results.append(data)
                        except Exception as e:
                            st.warning(f"Erreur sur {file.name} : {e}")
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    st.success(f"{len(st.session_state.ia_results)} vignettes analysées !")

            # Affichage des résultats IA pour validation
            if "ia_results" in st.session_state and st.session_state.ia_results:
                st.markdown("#### ✅ Validation des scans")
                df_res = pd.DataFrame(st.session_state.ia_results)
                
                # Édition des résultats avant ajout
                edited_df = st.data_editor(
                    df_res, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "designation": st.column_config.TextColumn("Produit (Extrait IA)"),
                        "couleur": st.column_config.TextColumn("Couleur Vignette"),
                        "ddp": st.column_config.TextColumn("DDP (MM/AAAA)"),
                        "ppa": st.column_config.NumberColumn("PPA", format="%.2f DA"),
                        "shp": st.column_config.NumberColumn("SHP", format="%.2f DA"),
                        "qte": st.column_config.NumberColumn("Quantité"),
                    }
                )
                
                if st.button("➕ AJOUTER TOUT À LA RÉCEPTION", use_container_width=True):
                    df_ia = load_gs_data("IA_Scans", DB_IA_SCANS, COLS_IA_SCANS)
                    new_ia_rows = []
                    
                    for _, row in edited_df.iterrows():
                        new_row = {
                            "produit": row.get('designation', ''),
                            "qte": row.get('qte', 1),
                            "lot": row.get('lot', ''),
                            "ddp": row.get('ddp', ''),
                            "ppa": row.get('ppa', 0.0),
                            "shp": row.get('shp', 0.0),
                            "colissage": 1,
                            "couleur": row.get('couleur', '')
                        }
                        st.session_state.current_reception['items'].append(new_row)
                        
                        log_saisie_en_cours("IA Vision", row.get('designation', ''), row.get('qte', 1), row.get('lot', ''), row.get('ddp', ''), row.get('ppa', 0.0))
                        
                        new_ia_rows.append({
                            "date_scan": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "designation": row.get('designation', ''),
                            "lot": row.get('lot', ''),
                            "ddp": row.get('ddp', ''),
                            "ppa": row.get('ppa', 0.0),
                            "shp": row.get('shp', 0.0),
                            "couleur": row.get('couleur', '')
                        })
                        
                    if new_ia_rows:
                        df_ia = pd.concat([df_ia, pd.DataFrame(new_ia_rows)], ignore_index=True)
                        save_gs_data(df_ia, "IA_Scans", DB_IA_SCANS)
                        
                    st.session_state.ia_results = []
                    # Vérifier les péremptions courtes dans le lot
                    has_short_ddp = any(verifier_ddp_courte(r.get('ddp','')) for r in new_ia_rows)
                    if has_short_ddp:
                        st.toast("⚠️ Attention: Certains articles scannés ont une date de péremption courte (< 12 mois) !", icon="⚠️")
                    st.rerun()

    with col_f2:
        st.subheader("🔍 Saisie des Produits")
        search_list = sorted(df_prod['Designation'].dropna().unique().tolist()) if not df_prod.empty else []
        
        with st.form("add_item_form"):
            selected_prod = st.selectbox("Rechercher un produit", [""] + search_list)
            c1, c2, c3 = st.columns(3)
            qte = c1.number_input("Quantité", min_value=1, step=1)
            lot = c2.text_input("Lot").upper()
            ddp = c3.text_input("DDP (MM/AAAA)")
            
            c4, c5, c6 = st.columns(3)
            ppa = c4.number_input("PPA", min_value=0.0, step=0.01)
            shp = c5.selectbox("SHP", [2.5, 1.5, 0.0])
            colis = c6.number_input("Colissage", min_value=1, value=1)
            
            if st.form_submit_button("➕ AJOUTER À LA LISTE", use_container_width=True):
                if selected_prod:
                    st.session_state.current_reception['items'].append({
                        "produit": selected_prod, "lot": lot, "ddp": ddp, "qte": qte,
                        "ppa": ppa, "shp": shp, "colissage": colis
                    })
                    log_saisie_en_cours("Manuelle", selected_prod, qte, lot, ddp, ppa)
                    if verifier_ddp_courte(ddp):
                        st.toast(f"⚠️ Attention: Date de péremption courte détectée pour {selected_prod} !", icon="⚠️")
                    st.rerun()

        # Liste des produits pointés
        if st.session_state.current_reception['items']:
            st.markdown("### 📑 Récapitulatif Pointage")
            for i, it in enumerate(st.session_state.current_reception['items']):
                is_courte = verifier_ddp_courte(it.get('ddp', ''))
                alert_html = ""
                ddp_color = "#6b7299"
                if is_courte:
                    alert_html = "<span style='background:#fee2e2; color:#ef4444; padding:2px 6px; border-radius:4px; margin-left:10px; font-weight:bold; font-size:0.8rem;'>⚠️ DDP COURTE</span>"
                    ddp_color = "#ef4444"
                
                st.markdown(f"""
                <div class="item-row">
                    <div><b>{it['produit']}</b><br><small style="color:#6b7299">Lot: {it['lot']} | <span style="color:{ddp_color}; font-weight:bold;">Exp: {it['ddp']}</span></small>{alert_html}</div>
                    <div style="font-weight:900; color:#5b6cf9;">{it['qte']} Unités</div>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("💾 CLÔTURER ET ENREGISTRER LA RÉCEPTION", type="primary", use_container_width=True):
                save_reception(st.session_state.current_reception)
                st.balloons()
                st.success("Réception clôturée avec succès !")
                st.session_state.current_reception['items'] = []
                st.rerun()

with tabs[1]:
    st.subheader("📋 Historique des Réceptions")
    df_rec = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    if not df_rec.empty:
        st.dataframe(df_rec.sort_values("date", ascending=False), use_container_width=True)
    else:
        st.info("Aucune réception enregistrée.")

with tabs[2]:
    st.subheader("🧠 Base de Données IA (Produits Collectés)")
    df_ia = load_gs_data("IA_Scans", DB_IA_SCANS, COLS_IA_SCANS)
    if not df_ia.empty:
        st.dataframe(df_ia.sort_values("date_scan", ascending=False), use_container_width=True)
        csv = df_ia.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exporter la base IA (CSV)", csv, "base_ia.csv", "text/csv")
    else:
        st.info("La base de données de l'IA est vide. Scannez des vignettes pour l'alimenter !")

with tabs[3]:
    st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <div>
                <h3 style="margin:0; color:#1a1f3c;">📡 Feed en Direct</h3>
                <p style="margin:0; color:#6b7299; font-size:0.9rem;">Surveillance temps réel des saisies de l'équipe</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("🔄 Actualiser le feed", use_container_width=True):
            st.rerun()
    with col2:
        mode_edition = st.toggle("✏️ Mode Édition")

    df_live = load_gs_data("Suivi_Direct", DB_SUIVI_DIRECT, COLS_SUIVI_DIRECT)
    
    with col3:
        if not df_live.empty:
            try:
                pdf_live_bytes = generate_suivi_direct_pdf(df_live.sort_values("timestamp", ascending=False).head(200))
                st.download_button("📄 Générer et Télécharger Rapport PDF", pdf_live_bytes, f"Rapport_Suivi_{datetime.now().strftime('%Y-%m-%d')}.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Erreur PDF : {e}")

    if not df_live.empty:
        df_live = df_live.sort_values("timestamp", ascending=False).head(100)
        
        if mode_edition:
            st.info("Vous êtes en mode édition globale. Modifiez les cellules puis cliquez sur Sauvegarder.")
            edited_live = st.data_editor(df_live, use_container_width=True)
            if st.button("💾 Sauvegarder les modifications du flux"):
                save_gs_data(edited_live, "Suivi_Direct", DB_SUIVI_DIRECT)
                st.success("Flux mis à jour avec succès !")
                st.rerun()
        else:
            feed_html = "<div style='display:flex; flex-direction:column; gap:15px; margin-top:10px;'>"
            for _, row in df_live.iterrows():
                method = str(row.get('methode', ''))
                is_ia = "IA" in method.upper()
                
                icon = "🤖" if is_ia else "✍️"
                bg_color = "linear-gradient(135deg, #f8f9fc 0%, #ffffff 100%)"
                border_color = "#5b6cf9" if is_ia else "#2db88a"
                badge_bg = "#eef0f8" if is_ia else "#e6f8f1"
                badge_color = "#5b6cf9" if is_ia else "#2db88a"
                
                try: ppa_val = f"{float(row.get('ppa', 0)):.2f}"
                except: ppa_val = row.get('ppa', '0')
                    
                try: qte_val = int(float(row.get('qte', 0)))
                except: qte_val = row.get('qte', '0')
                
                feed_html += f"""
<div style="background:{bg_color}; border-left: 5px solid {border_color}; border-radius: 12px; padding: 15px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); display:flex; justify-content:space-between; align-items:center;">
    <div style="display:flex; align-items:center; gap: 15px;">
        <div style="font-size: 1.8rem; background: {badge_bg}; width: 55px; height: 55px; display:flex; justify-content:center; align-items:center; border-radius: 12px; flex-shrink: 0;">{icon}</div>
        <div>
            <div style="font-size: 0.85rem; color: #6b7299; font-weight: 600; margin-bottom:3px;">
                <span style="color:#1a1f3c; font-weight:800; text-transform:uppercase;">{row.get('utilisateur', 'Inconnu')}</span> • {row.get('timestamp', '')}
            </div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #1a1f3c; margin-bottom: 8px;">
                {row.get('designation', '')}
            </div>
            <div style="display:flex; flex-wrap:wrap; gap: 10px; font-size: 0.85rem;">
                <span style="background: rgba(0,0,0,0.03); padding: 4px 10px; border-radius: 8px;">📦 Qte: <b style="color:#1a1f3c;">{qte_val}</b></span>
                <span style="background: rgba(0,0,0,0.03); padding: 4px 10px; border-radius: 8px;">🏷️ Lot: <b style="color:#1a1f3c;">{row.get('lot', '')}</b></span>
                <span style="background: rgba(0,0,0,0.03); padding: 4px 10px; border-radius: 8px;">⏳ Exp: <b style="color:#1a1f3c;">{row.get('ddp', '')}</b></span>
                <span style="background: rgba(0,0,0,0.03); padding: 4px 10px; border-radius: 8px;">💵 PPA: <b style="color:#1a1f3c;">{ppa_val} DA</b></span>
            </div>
        </div>
    </div>
    <div style="background: {badge_bg}; color: {badge_color}; padding: 6px 12px; border-radius: 20px; font-weight: 800; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">
        {method}
    </div>
</div>
"""
            feed_html += "</div>"
            st.markdown(feed_html, unsafe_allow_html=True)
    else:
        st.info("Aucune saisie n'a été effectuée pour le moment.")

with tabs[4]:
    show_sync_ui("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
