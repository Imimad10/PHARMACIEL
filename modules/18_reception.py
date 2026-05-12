import streamlit as st
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_pdf import generate_reception_pdf
from utils_ia import ask_ai_vision, is_ia_enabled
import difflib
import base64
import re

# --- CONFIGURATION ---
DB_RECEPTIONS = "data/db_receptions.csv"
DB_PRODUITS_RECEPTION = "data/db_reception_produits.csv"
COLS_RECEPTIONS = ["id", "date", "fournisseur", "facture_num", "statut", "items", "created_by"]
COLS_PRODUITS = ["Designation", "PPA", "SHP", "Colissage"]

def load_produits_reception():
    if os.path.exists(DB_PRODUITS_RECEPTION):
        try:
            df = pd.read_csv(DB_PRODUITS_RECEPTION, encoding='utf-8-sig')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.read_csv(DB_PRODUITS_RECEPTION)
    return pd.DataFrame(columns=COLS_PRODUITS)

def save_reception(reception_data):
    df_old = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    if not reception_data.get('id'):
        reception_data['id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    
    if reception_data['id'] in df_old['id'].astype(str).values:
        df_old.loc[df_old['id'].astype(str) == str(reception_data['id']), :] = [
            reception_data['id'],
            reception_data['date'],
            reception_data['fournisseur'],
            reception_data['facture_num'],
            reception_data['statut'],
            json.dumps(reception_data['items']),
            reception_data['created_by']
        ]
    else:
        new_row = pd.DataFrame([{
            "id": reception_data['id'],
            "date": reception_data['date'],
            "fournisseur": reception_data['fournisseur'],
            "facture_num": reception_data['facture_num'],
            "statut": reception_data['statut'],
            "items": json.dumps(reception_data['items']),
            "created_by": reception_data['created_by']
        }])
        df_old = pd.concat([df_old, new_row], ignore_index=True)
    save_gs_data(df_old, "Receptions", DB_RECEPTIONS)

def get_share_link(platform, filename):
    msg = f"Bonjour, voici la facture de réception : {filename}"
    encoded_msg = urllib.parse.quote(msg)
    if platform == "whatsapp":
        return f"https://wa.me/?text={encoded_msg}"
    elif platform == "viber":
        return f"viber://forward?text={encoded_msg}"
    return "#"

# --- UI ---
st.title("📦 Pointage de Marchandise & Réception")

if "current_reception" not in st.session_state:
    user_name = "Utilisateur"
    if 'current_user' in st.session_state:
        user_name = st.session_state.current_user.get('prenom', st.session_state.current_user.get('username', 'Utilisateur'))
    
    st.session_state.current_reception = {
        "id": None,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "fournisseur": "",
        "facture_num": "",
        "statut": "En cours",
        "items": [],
        "created_by": user_name
    }

# Toujours privilégier le prénom de l'utilisateur actuel pour les nouveaux pointages
if 'current_user' in st.session_state:
    st.session_state.current_reception['created_by'] = st.session_state.current_user.get('prenom', st.session_state.current_user.get('username', 'Utilisateur'))

tabs = st.tabs(["⚡ Nouvelle Réception", "📋 Historique & Suivi", "🏛️ Administration"])

# --- ONGLET 1 : NOUVELLE RÉCEPTION ---
with tabs[0]:
    with st.expander("📝 Informations de la Facture", expanded=True):
        col_h1, col_h2, col_h3 = st.columns(3)
        st.session_state.current_reception['date'] = col_h1.date_input("Date Réception", value=datetime.strptime(st.session_state.current_reception['date'], "%Y-%m-%d")).strftime("%Y-%m-%d")
        st.session_state.current_reception['fournisseur'] = col_h2.text_input("Fournisseur", value=st.session_state.current_reception['fournisseur'])
        st.session_state.current_reception['facture_num'] = col_h3.text_input("N° Facture / BL", value=st.session_state.current_reception['facture_num'])

    st.divider()

    # --- AI VISION SCANNER ---
    if is_ia_enabled():
        with st.expander("📷 Scanner avec l'IA (Vignettes / Produits)", expanded=False):
            scan_mode = st.radio("Mode de capture", ["Par Produit (Unique)", "Par Groupe (Vignettes multiples)"], horizontal=True)
            
            c_img1, c_img2 = st.columns(2)
            img_cam = c_img1.camera_input("Prendre une photo")
            img_files = c_img2.file_uploader("Importer image(s)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=(scan_mode == "Par Groupe (Vignettes multiples)"))
            
            if st.button("🔍 Lancer l'Analyse IA", use_container_width=True, type="primary"):
                all_images = []
                if img_cam: all_images.append(img_cam)
                if img_files:
                    if isinstance(img_files, list): all_images.extend(img_files)
                    else: all_images.append(img_files)
                
                if all_images:
                    with st.spinner("L'IA analyse les images..."):
                        results = []
                        for img in all_images:
                            base64_img = base64.b64encode(img.getvalue()).decode("utf-8")
                            
                            system_prompt = """
                            Tu es un expert en vignettes pharmaceutiques algériennes.
                            Règles de lecture :
                            1. "designation" : ORDRE OBLIGATOIRE = Nom Commercial (en majuscules) suivi de la DCI entre parenthèses, puis Dosage et Conditionnement.
                               Exemple: "ONYCAL (Terbinafine chlorhydrate) 250mg Boite de 14 Comps".
                            2. "lot" : Numéro de lot.
                            3. "ddp" : Date péremption (MM/AAAA).
                            4. PPA / SHP : Cherche le format "PRIX_A + PRIX_B".
                               - "ppa_reel" est PRIX_A (le prix AVANT le symbole '+').
                               - "shp_val" est PRIX_B (la valeur APRÈS le symbole '+', ex: 1.50 ou 2.50).
                               - Ne renvoie JAMAIS la somme totale comme PPA si une décomposition est visible.
                            5. "couleur" : Couleur de la bande (verte, rouge, blanche).
                            """
                            
                            if scan_mode == "Par Produit (Unique)":
                                prompt = system_prompt + '\nRetourne UNIQUEMENT un objet JSON : {"designation": "...", "lot": "...", "ddp": "...", "ppa_reel": 0.0, "shp_val": 0.0, "couleur": "..."}.'
                            else:
                                prompt = system_prompt + '\nRetourne UNIQUEMENT une LISTE d\'objets JSON : [{"designation": "...", "lot": "...", "ddp": "...", "ppa_reel": 0.0, "shp_val": 0.0, "couleur": "..."}, ...].'
                            
                            resp = ask_ai_vision(prompt, base64_img)
                            try:
                                match = re.search(r'\[.*\]|\{.*\}', resp, re.DOTALL)
                                if match:
                                    data = json.loads(match.group(0))
                                    if isinstance(data, list): results.extend(data)
                                    else: results.append(data)
                            except:
                                st.error("Erreur de lecture sur une image.")
                        
                        if results:
                            st.session_state['ai_results_rec'] = results
                            st.success(f"✅ {len(results)} produit(s) détecté(s) !")
                else:
                    st.warning("Veuillez fournir une image.")

    # --- MÉTHODE DE SAISIE ---
    st.subheader("🔍 Ajouter un Produit")
    saisie_mode = st.radio("Méthode de saisie", ["Traditionnel (Liste)", "Libre (IA / Manuel)"], horizontal=True)
    
    df_prod = load_produits_reception()
    col_candidates = ["Designation", "Désignation", "Produit", "Nom"]
    col_name = next((c for c in col_candidates if c in df_prod.columns), df_prod.columns[0] if not df_prod.empty else None)
    search_list = sorted(df_prod[col_name].dropna().unique().tolist()) if col_name else []

    # Gestion de la file d'attente IA
    ai_queue = st.session_state.get('ai_results_rec', [])
    current_ai_item = ai_queue[0] if ai_queue else {}

    if saisie_mode == "Traditionnel (Liste)":
        default_idx = 0
        if current_ai_item.get('designation'):
            matches = difflib.get_close_matches(current_ai_item['designation'].upper(), search_list, n=1, cutoff=0.4)
            if matches: default_idx = search_list.index(matches[0]) + 1
        
        selected_prod = st.selectbox("Sélectionner dans la liste", [""] + search_list, index=default_idx)
        prod_name = selected_prod
    else:
        prod_name = st.text_input("Désignation Libre (NOM (DCI) Dosage Cond.)", value=current_ai_item.get('designation', ""))

    if prod_name or current_ai_item:
        with st.form("form_add_rec", clear_on_submit=True):
            v_color = current_ai_item.get('couleur', 'blanche').lower()
            color_map = {"verte": "🟢 Verte (Remboursable)", "rouge": "🔴 Rouge", "blanche": "⚪ Blanche (Non remboursable)"}
            st.markdown(f"Produit : **{prod_name}** | Vignette : **{color_map.get(v_color, v_color)}**")
            
            col1, col2, col3 = st.columns(3)
            qte = col1.number_input("Quantité", min_value=1, step=1)
            lot = col2.text_input("Lot", value=str(current_ai_item.get('lot', ""))).upper()
            ddp = col3.text_input("DDP (MM/AAAA)", value=str(current_ai_item.get('ddp', "")))
            
            st.markdown("---")
            c_ppa, c_shp, c_col = st.columns(3)
            
            base_ppa = 0.0
            if saisie_mode == "Traditionnel (Liste)" and selected_prod:
                row = df_prod[df_prod[col_name] == selected_prod].iloc[0]
                base_ppa = float(str(row.get('PPA', 0)).replace(',','.'))
            
            if current_ai_item.get('ppa_reel'): 
                base_ppa = float(current_ai_item['ppa_reel'])
            elif current_ai_item.get('ppa'): 
                base_ppa = float(current_ai_item['ppa'])
            
            ppa = c_ppa.number_input("PPA (Prix sans SHP)", value=base_ppa, step=0.01)
            
            detected_shp = 0.0
            if current_ai_item.get('shp_val'):
                try: detected_shp = float(current_ai_item['shp_val'])
                except: pass
            
            shp_options = [2.5, 1.5, 0.0]
            default_shp_idx = 0
            if detected_shp is not None:
                for i, opt in enumerate(shp_options):
                    if abs(opt - detected_shp) < 0.1:
                        default_shp_idx = i
                        break
            
            shp_choice = c_shp.selectbox("SHP (Taux)", shp_options, index=default_shp_idx)
            
            colissage = c_col.number_input("Colissage", min_value=1, value=1)
            
            if st.form_submit_button("➕ Ajouter au pointage"):
                new_item = {
                    "produit": prod_name,
                    "lot": lot,
                    "ddp": ddp,
                    "qte": qte,
                    "ppa": ppa,
                    "shp": shp_choice,
                    "couleur": v_color,
                    "colissage": colissage,
                    "total_colis": qte / colissage if colissage > 0 else 0
                }
                st.session_state.current_reception['items'].append(new_item)
                if ai_queue: st.session_state['ai_results_rec'].pop(0)
                st.success(f"Ajouté : {prod_name}")
                st.rerun()

    # Liste des produits
    if st.session_state.current_reception['items']:
        st.divider()
        st.subheader("📋 Produits pointés")
        for i, item in enumerate(st.session_state.current_reception['items']):
            c1, c2, c3, c4 = st.columns([4, 2, 2, 0.5])
            c_icon = "🟢" if item.get('couleur') == "verte" else "🔴" if item.get('couleur') == "rouge" else "⚪"
            c1.write(f"{c_icon} **{item['produit']}**")
            c2.write(f"Lot: {item['lot']} | DDP: {item['ddp']} | Colis: {item.get('colissage', 1)}")
            c3.write(f"PPA: {item['ppa']} | SHP: {item['shp']}")
            if c4.button("🗑️", key=f"del_{i}"):
                st.session_state.current_reception['items'].pop(i)
                st.rerun()
        
        st.divider()
        c_save, c_pdf, c_reset = st.columns(3)
        
        if c_save.button("💾 Clôturer la Réception", type="primary", use_container_width=True):
            st.session_state.current_reception['statut'] = "Terminée"
            save_reception(st.session_state.current_reception)
            st.success("✅ Réception enregistrée !")
            st.session_state.current_reception['items'] = []
            st.rerun()

        if c_pdf.button("📄 Générer Facture PDF", use_container_width=True):
            pdf_data = generate_reception_pdf(st.session_state.current_reception)
            fname = f"Reception_{st.session_state.current_reception['fournisseur']}.pdf"
            st.download_button("📥 Télécharger PDF", pdf_data, fname, "application/pdf", use_container_width=True)
            
            st.markdown("### 📲 Partager via :")
            col_wa, col_vi = st.columns(2)
            col_wa.markdown(f'[![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)]({get_share_link("whatsapp", fname)})', unsafe_allow_html=True)
            col_vi.markdown(f'[![Viber](https://img.shields.io/badge/Viber-7360F2?style=for-the-badge&logo=viber&logoColor=white)]({get_share_link("viber", fname)})', unsafe_allow_html=True)

        if c_reset.button("⚠️ Tout effacer", use_container_width=True):
            st.session_state.current_reception['items'] = []
            if 'ai_results_rec' in st.session_state: del st.session_state['ai_results_rec']
            # On remet le prénom correct au reset
            if 'current_user' in st.session_state:
                st.session_state.current_reception['created_by'] = st.session_state.current_user.get('prenom', st.session_state.current_user.get('username', 'Utilisateur'))
            st.rerun()

with tabs[1]:
    st.subheader("📊 Tableau de Bord & Suivi des Réceptions")
    df_rec = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
    
    if not df_rec.empty:
        # --- FILTRES ET RECHERCHE ---
        c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
        search_q = c_f1.text_input("🔍 Rechercher par Fournisseur ou N° Facture", placeholder="Ex: BIO-PHARM...")
        date_filter = c_f2.date_input("📅 Filtrer par Date", value=None)
        
        # Application des filtres
        df_filtered = df_rec.copy()
        if search_q:
            df_filtered = df_filtered[
                df_filtered['fournisseur'].str.contains(search_q, case=False, na=False) | 
                df_filtered['facture_num'].astype(str).str.contains(search_q, case=False, na=False)
            ]
        if date_filter:
            df_filtered = df_filtered[df_filtered['date'] == str(date_filter)]
            
        # --- DASHBOARD KPIs ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("📦 Total Réceptions", len(df_filtered))
        
        # Calcul du total des items
        def count_items(items_str):
            try:
                items = json.loads(items_str)
                return sum(item.get('qte', 0) for item in items)
            except: return 0
            
        total_qte = df_filtered['items'].apply(count_items).sum()
        kpi2.metric("🔢 Total Produits", f"{total_qte:,}")
        kpi3.metric("🏢 Fournisseurs", df_filtered['fournisseur'].nunique())
        kpi4.metric("📅 Dernier Import", df_filtered['date'].max() if not df_filtered.empty else "N/A")

        # --- GRAPHIQUES ANALYTIQUES ---
        import plotly.express as px
        g1, g2 = st.columns(2)
        
        with g1:
            # Réceptions par fournisseur
            df_counts = df_filtered['fournisseur'].value_counts().reset_index()
            df_counts.columns = ['Fournisseur', 'Nombre']
            fig_prov = px.bar(df_counts.head(10), x='Nombre', y='Fournisseur', orientation='h', 
                             title="Top 10 Fournisseurs (Nb Réceptions)",
                             color='Nombre', color_continuous_scale='Blues')
            fig_prov.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0))
            st.plotly_chart(fig_prov, use_container_width=True)
            
        with g2:
            # Évolution temporelle
            df_time = df_filtered.groupby('date').size().reset_index(name='Nombre')
            fig_time = px.line(df_time, x='date', y='Nombre', title="Activité de Réception par Jour",
                              markers=True, line_shape='spline')
            fig_time.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0))
            st.plotly_chart(fig_time, use_container_width=True)
        
        # --- EXPORT GLOBAL ---
        csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
        c_f3.download_button("📥 Exporter Historique (CSV)", csv, f"historique_receptions_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

        st.divider()

        # --- LISTE DES RÉCEPTIONS ---
        # On utilise une liste extensible pour chaque réception
        for _, row in df_filtered.sort_values("date", ascending=False).iterrows():
            with st.expander(f"📄 {row['date']} | {row['fournisseur']} | Facture: {row['facture_num']}"):
                col_d1, col_d2 = st.columns([3, 1])
                
                with col_d1:
                    st.markdown(f"**Saisi par :** {row.get('created_by', 'N/A')} | **Statut :** {row['statut']}")
                    try:
                        items = json.loads(row['items'])
                        df_items = pd.DataFrame(items)
                        if not df_items.empty:
                            # Renommer pour l'affichage
                            display_cols = {
                                "produit": "Désignation",
                                "lot": "Lot",
                                "ddp": "DDP",
                                "qte": "Qte",
                                "ppa": "PPA",
                                "shp": "SHP",
                                "couleur": "Vig."
                            }
                            df_display = df_items.rename(columns=display_cols)
                            st.dataframe(df_display[[c for c in display_cols.values() if c in df_display.columns]], use_container_width=True, hide_index=True)
                        else:
                            st.info("Aucun produit dans cette réception.")
                    except Exception as e:
                        st.error(f"Erreur de lecture des données : {e}")

                with col_d2:
                    st.write("🛠️ **Actions**")
                    # Bouton PDF
                    reception_data = {
                        "id": row['id'],
                        "date": row['date'],
                        "fournisseur": row['fournisseur'],
                        "facture_num": row['facture_num'],
                        "items": items,
                        "created_by": row.get('created_by', 'Utilisateur')
                    }
                    pdf_bytes = generate_reception_pdf(reception_data)
                    st.download_button(
                        label="📥 Télécharger PDF",
                        data=pdf_bytes,
                        file_name=f"Facture_{row['fournisseur']}_{row['facture_num']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{row['id']}",
                        use_container_width=True
                    )
                    
                    # Bouton Excel (CSV)
                    if not df_items.empty:
                        item_csv = df_items.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📊 Export Excel (Produits)",
                            data=item_csv,
                            file_name=f"Produits_{row['fournisseur']}_{row['facture_num']}.csv",
                            mime="text/csv",
                            key=f"csv_{row['id']}",
                            use_container_width=True
                        )
                    
                    if st.button("🗑️ Supprimer", key=f"del_hist_{row['id']}", type="secondary", use_container_width=True):
                        df_all = load_gs_data("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
                        df_all = df_all[df_all['id'].astype(str) != str(row['id'])]
                        save_gs_data(df_all, "Receptions", DB_RECEPTIONS)
                        st.success("Réception supprimée.")
                        st.rerun()

    else:
        st.info("Aucun historique de réception disponible.")

with tabs[2]:
    st.subheader("🏛️ Administration & Synchronisation")
    show_sync_ui("Receptions", DB_RECEPTIONS, COLS_RECEPTIONS)
