# VERSION 5 - FULL MODES & CONFRONTATION
import streamlit as st
import pandas as pd
import os
import unicodedata
import shutil
from datetime import datetime
from tinydb import TinyDB, Query
from utils_ia import ask_ai, is_ia_enabled

st.set_page_config(page_title="Inventaire Détail", layout="wide")

# --- 1. CONFIGURATION ---
from utils_gsheets import load_gs_data, save_gs_data
# --- 1. CONFIGURATION ---
DATA_DIR = "data_inventaire_detail"
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = os.path.join(DATA_DIR, "master_detail.csv")
SAISIE_WORKSHEET = "Saisie_Inventaire_Zone"
SAISIE_FALLBACK = os.path.join(DATA_DIR, "saisie_detail.csv")
os.makedirs(DATA_DIR, exist_ok=True)
COLS_MASTER = ["designation", "lot", "zone", "ddp", "ppa", "shp", "stock_theorique"]
COLS_SAISIE = ['designation', 'lot_master', 'lot', 'qte_vrac_prepa', 'qte_colis_prepa', 'qte_vrac_mini', 'qte_colis_mini', 'qte_vrac', 'qte_colis', 'qte_saisie', 'ddp_saisi', 'ppa_saisi', 'zone', 'agent']

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def robust_num(s):
    if pd.isna(s) or s == "": return 0.0
    if isinstance(s, (int, float)): return float(s)
    # Si c'est un objet (ex: datetime), on le convertit en string d'abord
    s_str = str(s).replace('\xa0', '').replace(' ', '').replace(',', '.')
    try:
        val = pd.to_numeric(s_str, errors='coerce')
        return float(val) if pd.notna(val) else 0.0
    except: return 0.0

def clean_cols_v5(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation', 'article': 'designation', 'libelle': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp', 'date': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone', 'sector': 'zone'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte', 'dispo']
    new_cols = []
    found = set()
    for col in df.columns:
        norm = normalize_text(col)
        target = None
        for k, v in mapping.items():
            if k in norm and v not in found:
                target = v; found.add(v); break
        if not target and any(key in norm for key in stock_keywords) and 'stock_theorique' not in found:
            target = 'stock_theorique'; found.add(target)
        new_cols.append(target if target else norm)
    df.columns = new_cols
    return df

@st.cache_data(ttl=60)
def load_master_v5(path, mtime):
    try:
        df = pd.read_excel(path, engine='openpyxl')
        df = clean_cols_v5(df)
        req = ['designation', 'lot', 'zone']
        if not all(c in df.columns for c in req): return f"Colonnes manquantes : {[c for c in req if c not in df.columns]}"
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
        
        # Forcer en string pour éviter les erreurs de comparaison (ex: lot qui ressemble à une date)
        for col in ['designation', 'lot', 'zone']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        
        return df
    except Exception as e: return str(e)

# --- 3. UI ---
st.title("🔍 Inventaire Détail (Zones)")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
user_zone = user.get('zone', 'Aucune')

# Chargement du Master
df_master = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
if not df_master.empty:
    df_master = clean_cols_v5(df_master)
else:
    df_master = None

# Chargement de la Saisie
df_saisie_global = load_gs_data(SAISIE_WORKSHEET, SAISIE_FALLBACK, COLS_SAISIE)

if user_zone == "Aucune":
    selected_zone = st.sidebar.selectbox("📍 Zone de travail :", ["A", "B", "C", "D", "Frigo"])
else:
    selected_zone = user_zone
    st.sidebar.success(f"📍 Zone assignée : **{selected_zone}**")

tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]:
    if df_master is not None:
        st.subheader("📈 Progression de l'Inventaire par Zone")
        
        # Utiliser les saisies déjà chargées
        df_saisie_prog = df_saisie_global
            
        zones_dispo = sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
        
        # Filtrer par zone si non admin
        if user.get('role') not in ["Admin", "Superviseur"] and user_zone != "Aucune":
            zones_dispo = [str(selected_zone)] if selected_zone in zones_dispo else []
        
        for z in zones_dispo:
            # Produits totaux dans le master pour cette zone
            df_m_z = df_master[df_master['zone'] == z]
            total_items = df_m_z['designation'].nunique()
            
            # Produits déjà scannés dans cette zone
            if not df_saisie_prog.empty:
                df_s_z = df_saisie_prog[df_saisie_prog['zone'] == z]
                done_items = df_s_z['designation'].nunique()
            else:
                done_items = 0
                
            percent = (done_items / total_items) if total_items > 0 else 0
            
            # Affichage
            c_label, c_bar = st.columns([1, 3])
            c_label.write(f"**Zone {z}**")
            c_bar.progress(min(percent, 1.0), text=f"{done_items} / {total_items} ({percent*100:.1f}%)")
            
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Total Articles Master", len(df_master))
        df_user_z = df_master[df_master['zone'] == selected_zone]
        c2.metric(f"Votre Zone ({selected_zone})", len(df_user_z))
    else:
        st.info("💡 Veuillez importer un fichier Master dans l'onglet Admin pour activer le suivi.")

    if df_master is not None:
        st.divider()
        with st.expander("🖨️ Impression des Fiches Terrain (Zones)"):
            from utils_pdf import generate_blank_inventory_pdf
            
            c_p1, c_p2 = st.columns([2, 1])
            with c_p1:
                st.write("Générer une fiche d'inventaire vierge filtrée par zone.")
            with c_p2:
                # Filtrage par zone pour l'impression
                zones = ["Toutes"] + sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
                z_sel = st.selectbox("Zone à imprimer :", zones, key="print_z_inv_det")
                
                df_print = df_master if z_sel == "Toutes" else df_master[df_master['zone'] == z_sel]
                
                cols_to_print = [('designation', 'Produit', 55), ('lot', 'Lot', 25), ('zone', 'Zone', 15)]
                pdf_bytes = generate_blank_inventory_pdf(df_print, f"Inventaire Zone {z_sel}", cols_to_print)
                
                st.download_button(
                    "📥 Télécharger la Fiche Vierge",
                    pdf_bytes,
                    f"Fiche_Vierge_Detail_Zone_{z_sel}.pdf",
                    "application/pdf",
                    use_container_width=True
                )


with tabs[1]:
    if df_master is not None:
        df_z = df_master[df_master['zone'] == selected_zone].copy()
        if df_z.empty: st.warning(f"Zone {selected_zone} vide.")
        else:
            mode = st.radio("Méthode de saisie :", ["🚀 Rapide", "📋 Détaillée"], horizontal=True)
            prods = sorted(df_z['designation'].unique())
            sel_prod = st.selectbox("Produit :", [""] + prods)
            
            if sel_prod:
                df_p = df_z[df_z['designation'] == sel_prod]
                lots = sorted(df_p['lot'].unique())
                sel_lot = st.selectbox("Lot Master :", lots)
                info = df_p[df_p['lot'] == sel_lot].iloc[0]
                
                with st.form("form_saisie_det_v5", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    ddp_m = str(info.get('ddp', ''))
                    ppa_m = robust_num(info.get('ppa', 0))
                    
                    if mode == "🚀 Rapide":
                        st.markdown("##### 📍 Zone de Préparation")
                        c_p1, c_p2 = st.columns(2)
                        qte_vrac_p = c_p1.number_input("📦 Vrac (Prépa)", min_value=0.0, step=1.0)
                        qte_colis_p = c_p2.number_input("📦 Colis Fermé (Prépa)", min_value=0.0, step=1.0)
                        
                        st.markdown("##### 🏢 Mini Stock (Fond de salle)")
                        c_m1, c_m2 = st.columns(2)
                        qte_vrac_m = c_m1.number_input("📦 Vrac (Mini Stock)", min_value=0.0, step=1.0)
                        qte_colis_m = c_m2.number_input("📦 Colis Fermé (Mini Stock)", min_value=0.0, step=1.0)
                        
                        st.warning("⚠️ **Remarque :** Veuillez saisir la qte des **BOITES** et pas le nombre des colis.")
                        lot_r, ddp_r, ppa_r = sel_lot, ddp_m, ppa_m
                    else:
                        c1, c2 = st.columns(2)
                        lot_r = c1.text_input("🏷️ Lot Réel", value=str(sel_lot))
                        ddp_r = c2.text_input("📅 DDP (MM/AAAA)", value=ddp_m)
                        ppa_r = c1.number_input("💰 PPA Saisi", value=ppa_m)
                        
                        st.markdown("##### 📍 Zone de Préparation")
                        c_p1, c_p2 = st.columns(2)
                        qte_vrac_p = c_p1.number_input("📦 Vrac (Prépa)", min_value=0.0, step=1.0)
                        qte_colis_p = c_p2.number_input("📦 Colis Fermé (Prépa)", min_value=0.0, step=1.0)
                        
                        st.markdown("##### 🏢 Mini Stock (Fond de salle)")
                        c_m1, c_m2 = st.columns(2)
                        qte_vrac_m = c_m1.number_input("📦 Vrac (Mini Stock)", min_value=0.0, step=1.0)
                        qte_colis_m = c_m2.number_input("📦 Colis Fermé (Mini Stock)", min_value=0.0, step=1.0)
                        
                        st.warning("⚠️ **Remarque :** Veuillez saisir la qte des **BOITES** et pas le nombre des colis.")
                    
                    if st.form_submit_button("💾 Enregistrer"):
                        qte_vrac = qte_vrac_p + qte_vrac_m
                        qte_colis = qte_colis_p + qte_colis_m
                        total_qte = qte_vrac + qte_colis
                        new_line = pd.DataFrame([{
                            'designation': sel_prod, 'lot_master': sel_lot, 'lot': lot_r,
                            'qte_vrac_prepa': qte_vrac_p, 'qte_colis_prepa': qte_colis_p,
                            'qte_vrac_mini': qte_vrac_m, 'qte_colis_mini': qte_colis_m,
                            'qte_vrac': qte_vrac, 'qte_colis': qte_colis,
                            'qte_saisie': total_qte, 'ddp_saisi': ddp_r, 'ppa_saisi': ppa_r,
                            'zone': selected_zone, 'agent': user['username']
                        }])
                        df_saisie_global = pd.concat([df_saisie_global, new_line], ignore_index=True)
                        save_gs_data(df_saisie_global, SAISIE_WORKSHEET, SAISIE_FALLBACK)
                        st.success(f"Saisie OK : {sel_prod} (Total: {total_qte})")
                        st.rerun()
    else: st.info("Master requis.")

with tabs[2]:
    st.subheader("🔍 Analyse des écarts")
    if user['role'] in ["Admin", "Superviseur"] and not df_saisie_global.empty and df_master is not None:
        try:
            saisie = df_saisie_global
            
            st.write(f"📊 **Statut :** {len(saisie)} saisies totales détectées dans le journal.")
            
            if 'qte_vrac' not in saisie.columns:
                st.warning("⚠️ Le format du fichier de saisie est ancien (manque Qte Vrac/Colis). Veuillez le vider dans l'onglet Admin pour repartir à neuf.")
                st.dataframe(saisie.head())
            else:
                mode_conf = st.radio("Type d'Analyse :", ["⚡ Rapide (Global)", "🔬 Détaillée (Par Lot)"], horizontal=True)
                
                # Filtrage par zone pour l'analyse
                unique_zones = [str(z) for z in df_master['zone'].unique() if pd.notna(z)]
                z_ana = st.selectbox("Filtrer par Zone :", ["Toutes"] + sorted(unique_zones))
                
                df_m_f = df_master if z_ana == "Toutes" else df_master[df_master['zone'] == z_ana]
                df_s_f = saisie if z_ana == "Toutes" else saisie[saisie['zone'] == z_ana]
                
                if df_s_f.empty:
                    st.warning(f"Aucune saisie trouvée pour la zone {z_ana}.")
                else:
                    # Nettoyage numérique
                    q_col = 'stock_theorique' if 'stock_theorique' in df_m_f.columns else None
                    
                    if q_col:
                        df_m_f[q_col] = df_m_f[q_col].apply(robust_num).fillna(0)
                        df_s_f['qte_saisie'] = df_s_f['qte_saisie'].apply(robust_num).fillna(0)
                    
                    if "Rapide" in mode_conf:
                        m_g = df_m_f.groupby('designation')[q_col].sum().reset_index()
                        s_g = df_s_f.groupby('designation')['qte_saisie'].sum().reset_index()
                        comp = pd.merge(m_g, s_g, on='designation', how='outer').fillna(0)
                        comp['écart'] = comp['qte_saisie'] - comp[q_col]
                        
                        def style_ecart(row):
                            return ['background-color: #9e1a1a; color: white' if row['écart'] != 0 else '' for _ in row]
                        
                        st.write("### 📊 Écarts de Quantités Globales")
                        st.dataframe(comp.style.apply(style_ecart, axis=1), use_container_width=True, hide_index=True)
                    else:
                        # Analyse détaillée par Lot
                        m_sub = df_m_f[['designation', 'lot', q_col, 'ddp', 'ppa', 'shp'] if 'shp' in df_m_f.columns else ['designation', 'lot', q_col, 'ddp', 'ppa']].copy()
                        m_sub.columns = [c + '_master' if c != 'designation' and c != 'lot' else ('lot_master' if c == 'lot' else c) for c in m_sub.columns]
                        
                        # Agréger les saisies par lot pour éviter les doublons lors du multi-pass
                        df_s_g = df_s_f.groupby(['designation', 'lot_master']).agg({
                            'lot': 'last',
                            'ddp_saisi': 'last',
                            'ppa_saisi': 'last',
                            'qte_saisie': 'sum'
                        }).reset_index()
                        
                        comp_d = pd.merge(m_sub, df_s_g, on=['designation', 'lot_master'], how='outer')
                        # Remplissage intelligent au lieu du .fillna(0) global qui corrompt les types
                        for c in comp_d.columns:
                            if any(k in c.lower() for k in ['qte', 'ppa', 'theorique', 'shp']):
                                comp_d[c] = comp_d[c].fillna(0)
                            else:
                                comp_d[c] = comp_d[c].fillna('')
                        
                        def highlight_diffs_detail(row):
                            styles = ['' for _ in row.index]
                            red = 'background-color: #9e1a1a; color: white'
                            
                            # Qte
                            q_m = robust_num(row.get(f'{q_col}_master' if q_col else 'stock_theorique_master', 0))
                            q_s = robust_num(row.get('qte_saisie', 0))
                            if q_s != q_m:
                                styles[row.index.get_loc('qte_saisie')] = red
                            
                            # Lot
                            if str(row.get('lot')) != str(row.get('lot_master')) and pd.notna(row.get('lot')):
                                styles[row.index.get_loc('lot')] = red
                            
                            # DDP
                            if str(row.get('ddp_saisi')) != str(row.get('ddp_master')) and pd.notna(row.get('ddp_saisi')):
                                styles[row.index.get_loc('ddp_saisi')] = red
                            
                            # PPA
                            p_m = robust_num(row.get('ppa_master', 0))
                            p_s = robust_num(row.get('ppa_saisi', 0))
                            if p_s != p_m and p_s != 0:
                                styles[row.index.get_loc('ppa_saisi')] = red
                            return styles

                        st.write("### 🔬 Confrontation Minutieuse (Lots & Métadonnées)")
                        st.dataframe(comp_d.style.apply(highlight_diffs_detail, axis=1), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")
    else: st.warning("Accès réservé aux Administrateurs et Superviseurs.")

with tabs[3]:
    if user['role'] in ["Admin", "Superviseur"]:
        st.subheader("👥 Gestion des Équipes & Zones")
        # Charger les utilisateurs via GSheets (Utilisateurs worksheet)
        from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
        df_users_inv = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "password", "role", "pages", "zone"])
        saisie_users = df_users_inv[df_users_inv['pages'].str.contains('Inventaire Détail', na=False)]['username'].tolist()
        
        col_u1, col_u2, col_u3 = st.columns([2, 1, 1])
        target_user = col_u1.selectbox("Sélectionner un agent de saisie :", saisie_users)
        
        # Trouver la zone actuelle
        match_u = df_users_inv[df_users_inv['username'] == target_user]
        current_z = match_u['zone'].values[0] if not match_u.empty else "Aucune"
        
        # Liste des zones possibles du Master
        z_list = ["Aucune"]
        if df_master is not None:
            z_list += sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
        else:
            z_list += ["A", "B", "C", "D", "Frigo"]
            
        new_z = col_u2.selectbox(f"Assigner Zone (Actuelle: {current_z})", z_list, index=z_list.index(current_z) if current_z in z_list else 0)
        
        if col_u3.button("✅ Confirmer l'affectation", use_container_width=True):
            df_users_inv.loc[df_users_inv['username'] == target_user, 'zone'] = new_z
            save_gs_data(df_users_inv, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"Zone de **{target_user}** mise à jour : **{new_z}**")
            st.rerun()

        st.divider()
        st.subheader("⚙️ Gestion des fichiers")
        up = st.file_uploader("Importer Master Détail (XLSX)", type="xlsx")
        if up:
            df_up = pd.read_excel(up)
            df_up = clean_cols_v5(df_up)
            save_gs_data(df_up, MASTER_WORKSHEET, MASTER_FALLBACK)
            st.success("Master Détail synchronisé sur GSheets !")
            st.rerun()
                
        st.divider()
        c1, c2 = st.columns(2)
        
        if c1.button("🗑️ Vider Inventaire (Saisie)", use_container_width=True):
            save_gs_data(pd.DataFrame(columns=COLS_SAISIE), SAISIE_WORKSHEET, SAISIE_FALLBACK)
            st.success("Toutes les saisies terrain ont été effacées sur GSheets.")
            st.rerun()
                
        if c2.button("🔴 Supprimer Master", use_container_width=True):
            save_gs_data(pd.DataFrame(columns=COLS_MASTER), MASTER_WORKSHEET, MASTER_FALLBACK)
            st.success("Fichier Master vidé sur GSheets.")
            st.rerun()

        st.divider()
        st.subheader("💾 Sauvegarde & Archivage")
        col_b1, col_b2 = st.columns(2)

        if col_b1.button("📂 Créer un Backup (Détail)", use_container_width=True):
            if os.path.exists(SAISIE_PATH):
                bak_dir = os.path.join(DATA_DIR, "backups")
                os.makedirs(bak_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak_path = os.path.join(bak_dir, f"saisie_detail_backup_{ts}.csv")
                shutil.copy(SAISIE_PATH, bak_path)
                st.success(f"Sauvegarde créée : {bak_path}")
            else:
                st.warning("Aucune donnée à sauvegarder.")

        if col_b2.button("📦 Archiver la journée (Détail)", use_container_width=True):
            if os.path.exists(SAISIE_PATH):
                arc_dir = os.path.join(DATA_DIR, "archives")
                os.makedirs(arc_dir, exist_ok=True)
                date_s = datetime.now().strftime("%Y-%m-%d")
                arc_path = os.path.join(arc_dir, f"saisie_detail_archive_{date_s}.csv")
                shutil.move(SAISIE_PATH, arc_path)
                st.success(f"Archivé et vidé : {arc_path}")
                st.rerun()
            else:
                st.warning("Rien à archiver.")
    else:
        st.warning("L'onglet Admin est réservé aux administrateurs et superviseurs.")
