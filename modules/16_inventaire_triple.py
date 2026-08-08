import streamlit as st
import pandas as pd
import os
import json
import unicodedata
from utils_ia import ask_ai, ask_ai_vision, is_ia_enabled, is_ia_scanner_enabled
import base64
import difflib
import re

# --- CONFIGURATION ---

from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui

# --- CONFIGURATION DES BASES ---
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = "data_inventaire_detail/master_detail.csv"
WS_ZONE = "Triple_Saisie_Zone"
FB_ZONE = "data/db_triple_zone.csv"
WS_MINI = "Triple_Saisie_Mini"
FB_MINI = "data/db_triple_mini.csv"

# Colonnes minimales garanties dans le master
COLS_MASTER = ["depot", "zone", "produit", "lot", "qte_logi", "colissage", "ppa", "shp", "ddp", "laboratoire", "categorie", "statut_stock", "is_depot_secondaire"]
COLS_ENTRY = ["zone", "produit", "lot", "qte", "ddp", "ppa", "shp", "agent"]

if 'current_user' not in st.session_state:
    st.warning("⚠️ Veuillez vous connecter.")
    st.stop()

# --- STYLE CSS PREMIUM FLUFFY ---
st.markdown("""
    <style>
    .stApp { background-color: var(--bg) !important; }
    .entry-card { 
        background: var(--bg); 
        padding: 25px; 
        border-radius: 24px; 
        box-shadow: var(--neu-shadow); 
        margin-bottom: 25px; 
    }
    .section-title { 
        color: var(--primary); 
        font-weight: 900; 
        font-size: 1.4rem; 
        margin-bottom: 25px; 
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .admin-box { 
        background: var(--bg); 
        padding: 20px; 
        border-radius: 20px; 
        box-shadow: var(--neu-shadow-inset); 
        margin-bottom: 25px;
        color: #6b7299;
        font-weight: 800;
        border-left: 5px solid var(--primary);
    }
    .stTabs [data-baseweb="tab-list"] { 
        gap: 15px; 
        background: transparent; 
        padding: 10px;
    }
    .stTabs [data-baseweb="tab"] { 
        background-color: var(--bg); 
        border-radius: 15px; 
        padding: 12px 30px; 
        box-shadow: var(--neu-shadow);
        border: none !important;
        font-weight: 800 !important;
    }
    .stTabs [aria-selected="true"] { 
        background: linear-gradient(135deg, #7c8fff, #5b6cf9) !important; 
        color: white !important; 
        box-shadow: 0 8px 15px rgba(91,108,249,0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').upper().strip()

def sanitize_str_col(series):
    def _clean(val):
        if pd.isna(val) or val is None or str(val).lower() in ['nan', 'none', 'null']:
            return ""
        if isinstance(val, float) and val.is_integer():
            return str(int(val)).upper().strip()
        s = str(val).upper().strip()
        if s.endswith('.0'):
            s = s[:-2]
        return s
    return series.apply(_clean)

# --- CHARGEMENT ---
@st.cache_data(ttl=300)
def get_master():
    # Chargement de la base produits centrale (importée via Admin Centrale)
    df = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK)
    if df.empty: return pd.DataFrame(columns=COLS_MASTER)
    
    # Normalisation des colonnes
    df.columns = [c.lower().strip() for c in df.columns]
    mapping = {'dépôt':'depot', 'désignation':'produit', 'n°lot':'lot',
               'quantité dépôt':'qte_logi', 'qte.globale':'qte_logi',
               'colis':'colissage', 'marge ph.':'marge_ph', 'marge ph':'marge_ph'}
    df = df.rename(columns=mapping)
    
    # Champs essentiels avec valeurs par défaut
    for c in ['depot','zone','produit','lot','qte_logi','colissage','ppa','shp','ddp','laboratoire','categorie']:
        if c not in df.columns: df[c] = ""
    
    df['produit'] = sanitize_str_col(df['produit'])
    df['lot']     = sanitize_str_col(df['lot'])
    df['zone']    = sanitize_str_col(df['zone'])
    df['qte_logi'] = pd.to_numeric(df['qte_logi'], errors='coerce').fillna(0)
    
    # Exclure les produits du dépôt secondaire (périmés, abimés, SV...)
    if 'is_depot_secondaire' in df.columns:
        df = df[df['is_depot_secondaire'].astype(str).str.upper() != 'TRUE']
    elif 'statut_stock' in df.columns:
        df = df[df['statut_stock'].astype(str) == 'Conforme']
    else:
        # Détection automatique par code dépôt
        depot_nc = df['depot'].astype(str).str.upper()
        df = df[~(depot_nc.isin(['2', '02', 'SEC', 'SECONDAIRE', 'NC', 'SV']) |
                  depot_nc.str.contains('SEC|PERIMES|ABIMES|NON.CONF|S\.V\.', na=False, regex=True))]
    
    return df

df_m = get_master()
df_z = load_gs_data(WS_ZONE, FB_ZONE, COLS_ENTRY)
df_mi = load_gs_data(WS_MINI, FB_MINI, COLS_ENTRY)

for _d in [df_z, df_mi]:
    if not _d.empty:
        if 'produit' in _d.columns: _d['produit'] = sanitize_str_col(_d['produit'])
        if 'lot' in _d.columns: _d['lot'] = sanitize_str_col(_d['lot'])

# --- LOGIQUE D'ACCÈS ---
user_role = st.session_state.current_user.get('role', 'Saisie')
is_admin = user_role in ['Admin', 'Superviseur']
user_zone = str(st.session_state.current_user.get('zone', '')).upper()

# --- INTERFACE HEADER ---
st.title("🛡️ Inventaire Triple & Réconciliation")

if is_admin:
    st.markdown('<div class="admin-box">🛡️ MODE SUPERVISEUR : Accès complet à toutes les zones.</div>', unsafe_allow_html=True)
    raw_zones = df_m['zone'].dropna().astype(str).unique().tolist()
    zones_list = ["Toutes"] + sorted(raw_zones)
    
    col_zone, col_sync = st.columns([4, 1])
    selected_zone_filter = col_zone.selectbox("🎯 Filtrer la vue globale par Zone :", zones_list)
    
    n_produits = df_m['produit'].nunique() if not df_m.empty else 0
    n_lots     = len(df_m) if not df_m.empty else 0
    
    with col_sync:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        if st.button("🔄 Sync DB", use_container_width=True, help="Recharger la liste des produits depuis la base centrale"):
            get_master.clear()
            st.cache_data.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    if n_produits > 0:
        st.caption(f"✅ Base chargée : **{n_produits} produits** · **{n_lots} lots** (Dépôt secondaire exclu automatiquement)")
    else:
        st.warning("⚠️ Aucune donnée trouvée. Importez d'abord votre liste de produits via **Administration Centrale > Importateur Universel**.")
else:
    st.info(f"📍 Votre Zone assignée : **{user_zone}**")
    selected_zone_filter = user_zone

def get_working_master():
    if is_admin and selected_zone_filter != "Toutes":
        return df_m[df_m['zone'] == selected_zone_filter]
    elif is_admin:
        return df_m
    else:
        return df_m[df_m['zone'].astype(str).str.upper().str.contains(user_zone, na=False)]

def get_working_entries(df):
    if is_admin and selected_zone_filter != "Toutes":
        return df[df['zone'].astype(str) == selected_zone_filter]
    elif is_admin:
        return df
    else:
        return df[df['zone'].astype(str).str.upper().str.contains(user_zone, na=False)]

# --- FICHES VIERGES ---
with st.expander("🖨️ Impression des Fiches Terrain"):
    from utils_pdf import generate_blank_inventory_pdf
    st.write("Générez une fiche vierge pour le comptage papier.")
    # TRI ALPHABÉTIQUE
    df_blank = get_working_master().sort_values(by='produit')
    if st.download_button("📥 Télécharger Fiche Vierge (Zone Actuelle)", generate_blank_inventory_pdf(df_blank, "Triple", [('produit','Produit',55),('lot','Lot',25)]), "Fiche_Vierge.pdf", "application/pdf"):
        st.success("Généré !")

t_zone, t_mini, t_final, t_conf, t_admin = st.tabs(["📍 Saisie Zone", "📦 Saisie Mini", "📊 Compilation", "📉 Confrontation", "⚙️ Gestion Admin"])

# --- LOGIQUE DE SAISIE ---
def render_saisie(df_full, ws_name, fb_path, title, key_prefix):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    
    # AI SCANNER
    if is_ia_scanner_enabled():
        with st.expander("📷 Scanner IA (Vignette/Produit)", expanded=False):
            img = st.camera_input(f"Photo {title}", key=f"cam_{key_prefix}")
            if img and st.button("🔍 Analyser Photo", key=f"btn_ia_{key_prefix}"):
                b64 = base64.b64encode(img.getvalue()).decode()
                res = ask_ai_vision("Extrais JSON: {\"designation\": \"...\", \"lot\": \"...\"}", b64)
                try:
                    data = json.loads(re.search(r'\{.*\}', res, re.DOTALL).group())
                    st.session_state[f'ai_{key_prefix}'] = data
                    st.success(f"Détecté : {data.get('designation')}")
                except: st.error("Erreur lecture IA")

    master_w = get_working_master()
    if master_w.empty:
        st.warning("Aucun produit à saisir dans ce périmètre.")
        return df_full

    lp = sorted(master_w['produit'].unique().tolist())
    ai_d = st.session_state.get(f'ai_{key_prefix}', {})
    
    idx_p = 0
    if ai_d.get('designation'):
        matches = difflib.get_close_matches(ai_d['designation'].upper(), lp, n=1, cutoff=0.3)
        if matches: idx_p = lp.index(matches[0])

    c1, c2 = st.columns([3, 1])
    sp = c1.selectbox(f"Produit", lp, index=idx_p, key=f"p_{key_prefix}")
    
    prod_rows = master_w[master_w['produit'] == sp]
    lm_list = sorted(prod_rows['lot'].unique().tolist())
    p_zone = prod_rows['zone'].iloc[0] if not prod_rows.empty else ""
    
    idx_l = 0
    if ai_d.get('lot'):
        l_matches = difflib.get_close_matches(ai_d['lot'].upper(), lm_list, n=1, cutoff=0.5)
        if l_matches: idx_l = lm_list.index(l_matches[0])

    slm = c2.selectbox(f"Lot Master", lm_list, index=idx_l, key=f"lm_{key_prefix}")
    
    # Pré-remplissage automatique depuis la base produits (PPA, DDP, SHP)
    lot_row = prod_rows[prod_rows['lot'] == slm]
    pre_ppa = float(pd.to_numeric(lot_row['ppa'].values[0], errors='coerce') or 0) if not lot_row.empty and 'ppa' in lot_row.columns else 0.0
    pre_shp = float(pd.to_numeric(lot_row['shp'].values[0], errors='coerce') or 0) if not lot_row.empty and 'shp' in lot_row.columns else 0.0
    pre_ddp = str(lot_row['ddp'].values[0]) if not lot_row.empty and 'ddp' in lot_row.columns else ""
    pre_labo = str(lot_row['laboratoire'].values[0]) if not lot_row.empty and 'laboratoire' in lot_row.columns else ""
    
    if pre_labo and pre_labo not in ['', 'nan']:
        st.caption(f"🏭 Laboratoire : **{pre_labo}** | 📅 DDP Master : **{pre_ddp}** | 💰 PPA : **{pre_ppa}**")
    
    st.markdown('<div class="entry-card">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 1, 1])
    lot_r = f1.text_input("Lot Réel", value=slm, key=f"lr_{key_prefix}")
    qte = f2.number_input("Quantité", min_value=0.0, step=1.0, key=f"q_{key_prefix}")
    ddp = f3.text_input("DDP (MM/AAAA)", value=pre_ddp if pre_ddp not in ['', 'nan'] else "", key=f"d_{key_prefix}")
    
    f4, f5 = st.columns(2)
    ppa = f4.number_input("PPA", min_value=0.0, value=pre_ppa, key=f"pp_{key_prefix}")
    shp = f5.number_input("SHP", min_value=0.0, value=pre_shp, key=f"sh_{key_prefix}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button(f"💾 Enregistrer Saisie", type="primary", use_container_width=True, key=f"btn_s_{key_prefix}"):
        new = {
            "zone": p_zone, "produit": sp, "lot": lot_r.upper(), 
            "qte": qte, "ddp": ddp, "ppa": ppa, "shp": shp, 
            "agent": st.session_state.current_user.get('username')
        }
        mask = (df_full['produit'] == sp) & (df_full['lot'] == lot_r.upper())
        if mask.any():
            for k, v in new.items(): df_full.loc[mask, k] = v
        else:
            df_full = pd.concat([df_full, pd.DataFrame([new])], ignore_index=True)
        
        save_gs_data(df_full, ws_name, fb_path)
        st.success("Saisie enregistrée avec succès !")
        if f'ai_{key_prefix}' in st.session_state: del st.session_state[f'ai_{key_prefix}']
        st.rerun()
    
    st.write("---")
    hist = get_working_entries(df_full)
    st.dataframe(hist[hist['produit'] == sp], use_container_width=True)
    return df_full

with t_zone:
    df_z = render_saisie(df_z, WS_ZONE, FB_ZONE, "Saisie en Zone (Vrac)", "z")

with t_mini:
    df_mi = render_saisie(df_mi, WS_MINI, FB_MINI, "Saisie Mini Stock (Colis)", "m")

# --- COMPILATION ---
with t_final:
    st.markdown('<div class="section-title">📊 Réconciliation & Compilation</div>', unsafe_allow_html=True)
    w_z = get_working_entries(df_z).copy()
    w_mi = get_working_entries(df_mi).copy()
    
    if not w_z.empty:
        w_z['produit'] = sanitize_str_col(w_z['produit'])
        w_z['lot'] = sanitize_str_col(w_z['lot'])
    if not w_mi.empty:
        w_mi['produit'] = sanitize_str_col(w_mi['produit'])
        w_mi['lot'] = sanitize_str_col(w_mi['lot'])
    
    df_c = pd.merge(w_z, w_mi, on=['produit', 'lot'], how='outer', suffixes=('_z', '_m')).fillna(0)
    
    if df_c.empty:
        st.info("Aucune donnée saisie pour le moment.")
    else:
        df_c['zone'] = df_c.apply(lambda r: r['zone_z'] if r['zone_z'] != 0 else r['zone_m'], axis=1)
        df_c['qte_z'] = pd.to_numeric(df_c['qte_z'], errors='coerce').fillna(0)
        df_c['qte_m'] = pd.to_numeric(df_c['qte_m'], errors='coerce').fillna(0)
        df_c['Total'] = df_c['qte_z'] + df_c['qte_m']
        
        def check_inc(r):
            if r['qte_z'] > 0 and r['qte_m'] > 0:
                e = []
                if str(r['ddp_z']) != str(r['ddp_m']): e.append("DDP")
                if float(r['ppa_z'] or 0) != float(r['ppa_m'] or 0): e.append("PPA")
                if float(r['shp_z'] or 0) != float(r['shp_m'] or 0): e.append("SHP")
                return ", ".join(e) if e else "OK"
            return "OK"
        
        df_c['Incohérence'] = df_c.apply(check_inc, axis=1)
        
        cols_final = ['zone', 'produit', 'lot', 'qte_z', 'qte_m', 'Total', 'Incohérence', 'agent_z', 'agent_m']
        st.dataframe(df_c[cols_final].style.apply(lambda r: ['background-color: #ffebee' if r['Incohérence'] != "OK" else '' for _ in r], axis=1), use_container_width=True)
        
        if st.button("📥 Valider pour Confrontation"):
            st.session_state.it_ready = df_c
            st.success("Compilation validée !")

# --- CONFRONTATION ---
with t_conf:
    st.markdown('<div class="section-title">📉 Confrontation avec Logipharm</div>', unsafe_allow_html=True)
    if 'it_ready' not in st.session_state:
        st.info("Veuillez d'abord valider la compilation dans l'onglet précédent.")
    else:
        ready = st.session_state.it_ready.copy()
        m_w = get_working_master().copy()
        
        if not ready.empty:
            ready['produit'] = sanitize_str_col(ready['produit'])
            ready['lot'] = sanitize_str_col(ready['lot'])
        if not m_w.empty:
            m_w['produit'] = sanitize_str_col(m_w['produit'])
            m_w['lot'] = sanitize_str_col(m_w['lot'])
            
        final = pd.merge(m_w, ready[['produit', 'lot', 'Total', 'Incohérence']], on=['produit', 'lot'], how='left').fillna(0)
        final['Total'] = pd.to_numeric(final['Total'], errors='coerce').fillna(0)
        final['qte_logi'] = pd.to_numeric(final['qte_logi'], errors='coerce').fillna(0)
        final['Ecart'] = final['Total'] - final['qte_logi']
        
        c_show = ['zone', 'produit', 'lot', 'qte_logi', 'Total', 'Ecart', 'Incohérence']
        st.dataframe(final[c_show].style.applymap(lambda v: 'color: red' if v<0 else ('color: green' if v>0 else ''), subset=['Ecart']), use_container_width=True)
        
        if st.button("📄 Rapport Final PDF"):
            from utils_pdf import generate_inventory_report_pdf
            # TRI ALPHABÉTIQUE
            final_sorted = final.sort_values(by='produit')
            st.download_button("Télécharger le Rapport", generate_inventory_report_pdf(final_sorted, f"RAPPORT TRIPLE - {selected_zone_filter}"), f"Rapport_Triple_{selected_zone_filter}.pdf", "application/pdf")

# --- GESTION ADMIN ---
with t_admin:
    st.markdown('<div class="section-title">⚙️ Administration de l\'Inventaire</div>', unsafe_allow_html=True)
    if not is_admin:
        st.error("Accès réservé aux administrateurs.")
    else:
        st.warning("⚠️ Attention : Les actions ci-dessous sont irréversibles.")
        
        with st.expander("🗑️ Réinitialisation des données", expanded=False):
            st.write("Voulez-vous vider toutes les saisies effectuées (Zone + Mini) pour recommencer à zéro ?")
            confirm = st.checkbox("Je confirme vouloir tout supprimer")
            if st.button("🚨 VIDER TOUT L'INVENTAIRE", type="primary", disabled=not confirm):
                save_gs_data(pd.DataFrame(columns=COLS_ENTRY), WS_ZONE, FB_ZONE)
                save_gs_data(pd.DataFrame(columns=COLS_ENTRY), WS_MINI, FB_MINI)
                if 'it_ready' in st.session_state: del st.session_state.it_ready
                st.success("Toutes les bases ont été vidées.")
                st.rerun()
        
        with st.expander("📊 Export de secours", expanded=False):
            st.write("Téléchargez une sauvegarde Excel avant de vider les bases.")
            try:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_z.sort_values(by='produit').to_excel(writer, sheet_name="Zone", index=False)
                    df_mi.sort_values(by='produit').to_excel(writer, sheet_name="Mini", index=False)
                st.download_button("📥 Télécharger Sauvegarde Excel", output.getvalue(), "backup_inventaire.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as e:
                st.error(f"Erreur d'export : {e}")
