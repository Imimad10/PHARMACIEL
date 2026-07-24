import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils_gsheets import load_gs_data
from utils_ia import ask_ai, is_ia_enabled
from utils_pdf import generate_inventory_report_pdf

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK  = "data_inventaire_detail/master_detail.csv"
VENTES_WORKSHEET = "Analyse_Ventes_Perf"
VENTES_FALLBACK  = "data/db_ventes_performance.csv"

# ─── PAGE HEADER ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.rupture-title {
    font-size: 2rem; font-weight: 900;
    background: linear-gradient(135deg, #ef4444, #f97316);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.rupture-sub { color: #94a3b8; font-size: 0.95rem; margin-bottom: 20px; }
.kpi-card {
    background: var(--bg-card, #1e293b);
    border-radius: 16px; padding: 18px 22px;
    border: 1px solid rgba(255,255,255,0.07);
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    margin-bottom: 12px;
}
.kpi-label { font-size: 0.8rem; color: #94a3b8; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.kpi-val   { font-size: 2rem; font-weight: 900; margin: 4px 0; }
.kpi-desc  { font-size: 0.78rem; color: #64748b; }
.alert-card-red    { background:#7f1d1d33; border-left:4px solid #ef4444; border-radius:10px; padding:14px 18px; margin:6px 0; }
.alert-card-orange { background:#7c2d1233; border-left:4px solid #f97316; border-radius:10px; padding:14px 18px; margin:6px 0; }
.alert-card-yellow { background:#71350033; border-left:4px solid #eab308; border-radius:10px; padding:14px 18px; margin:6px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="rupture-title">🔮 Prédiction de Rupture de Stock</h1>', unsafe_allow_html=True)
st.markdown('<p class="rupture-sub">Analyse intelligente du stock réel de la Liste des Lots pour estimer les risques de rupture.</p>', unsafe_allow_html=True)

# ─── CHARGEMENT DONNÉES LISTE DES LOTS ─────────────────────────────────────────
import unicodedata
def norm_col(c):
    c = str(c).strip().lower()
    return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')

def map_cols(df):
    """Mappage flexible des colonnes du master vers un format interne standard."""
    stock_kw   = ['quantit', 'stock', 'theorique', 'qte', 'dispo', 'logi', 'theor']
    mapping = {
        'designation': 'designation', 'produit': 'designation', 'article': 'designation', 'libelle': 'designation',
        'lot':         'lot',         'nlot': 'lot',            'n lot': 'lot',
        'ddp':         'ddp',         'peremption': 'ddp',      'exp': 'ddp',
        'ppa':         'ppa',         'shp': 'shp',
        'zone':        'zone',        'emplacement': 'zone',
        'depot':       'depot',       'magasin': 'depot',
    }
    new_cols, found = [], set()
    for col in df.columns:
        n = norm_col(col)
        target = None
        for k, v in mapping.items():
            if k == n and v not in found:
                target = v; found.add(v); break
        if not target:
            for k, v in mapping.items():
                if k in n and v not in found:
                    target = v; found.add(v); break
        if not target and any(kw in n for kw in stock_kw) and 'stock_theorique' not in found:
            target = 'stock_theorique'; found.add(target)
        new_cols.append(target if target else n)
    df.columns = new_cols
    return df

@st.cache_data(ttl=300)
def load_lots():
    df = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, None)
    if df.empty:
        return pd.DataFrame()
    df = map_cols(df.copy())
    
    # Assurer les colonnes essentielles
    if 'designation' not in df.columns:
        return pd.DataFrame()
    if 'stock_theorique' not in df.columns:
        df['stock_theorique'] = 0
    if 'ddp' not in df.columns:
        df['ddp'] = None
    if 'depot' not in df.columns:
        df['depot'] = 'N/A'
    if 'lot' not in df.columns:
        df['lot'] = ''

    df['designation'] = df['designation'].fillna('').astype(str).str.strip()
    df = df[df['designation'] != '']
    df['stock_theorique'] = pd.to_numeric(df['stock_theorique'], errors='coerce').fillna(0)
    return df

@st.cache_data(ttl=300)
def load_ventes():
    df = load_gs_data(VENTES_WORKSHEET, VENTES_FALLBACK, None)
    return df if not df.empty else pd.DataFrame()

df_lots  = load_lots()
df_ventes = load_ventes()

if df_lots.empty:
    st.error("❌ Impossible de charger la Liste des Lots. Vérifiez la synchronisation de la base de données.")
    st.info("👉 Allez dans **Administration Centrale** → chargez votre fichier Master de produits.")
    st.stop()

# ─── CALCUL ROTATION DEPUIS VENTES (si disponible) ─────────────────────────────
ventes_rotation = {}  # designation → unités/jour
if not df_ventes.empty:
    # Chercher colonne designation et quantite
    qte_col = next((c for c in df_ventes.columns if any(kw in norm_col(c) for kw in ['qte','quantit','vendu'])), None)
    prod_col = next((c for c in df_ventes.columns if any(kw in norm_col(c) for kw in ['produit','designation','article'])), None)
    date_col = next((c for c in df_ventes.columns if any(kw in norm_col(c) for kw in ['date','jour'])), None)
    
    if qte_col and prod_col:
        df_v = df_ventes.copy()
        df_v[qte_col] = pd.to_numeric(df_v[qte_col], errors='coerce').fillna(0)
        
        if date_col:
            df_v[date_col] = pd.to_datetime(df_v[date_col], errors='coerce')
            df_v = df_v.dropna(subset=[date_col])
            days_range = (df_v[date_col].max() - df_v[date_col].min()).days or 1
        else:
            days_range = 30  # fallback 30 jours
        
        grp = df_v.groupby(prod_col)[qte_col].sum()
        ventes_rotation = (grp / days_range).to_dict()

# ─── AGGREGATION PAR PRODUIT ────────────────────────────────────────────────────
# Agréger tous les lots par produit
df_agg = df_lots.groupby('designation').agg(
    stock_total=('stock_theorique', 'sum'),
    nb_lots=('lot', 'count'),
    depot=('depot', lambda x: ', '.join(sorted(x.dropna().astype(str).unique()[:3])))
).reset_index()

# Ajouter colonne zone si présente
if 'zone' in df_lots.columns:
    df_zone = df_lots.groupby('designation')['zone'].apply(
        lambda x: ', '.join(sorted(x.dropna().astype(str).unique()[:3]))
    ).reset_index()
    df_agg = df_agg.merge(df_zone, on='designation', how='left')
else:
    df_agg['zone'] = 'N/A'

# ─── CALCUL VITESSE DE ROTATION & JOURS RESTANTS ───────────────────────────────
SEUIL_CRITIQUE_JOURS = 15
SEUIL_VIGILANCE_JOURS = 30
SEUIL_OK_JOURS = 60

def vitesse_par_defaut(designation, stock):
    """Estimation par défaut si pas de données ventes réelles."""
    n = str(designation).lower()
    if any(k in n for k in ['serum', 'infusion', 'solute', 'soluté']): return max(stock * 0.08, 1)
    if any(k in n for k in ['antibio', 'antibi', 'amoxic', 'augmentin']): return max(stock * 0.05, 1)
    if any(k in n for k in ['comprime', 'capsule', 'gelule']): return max(stock * 0.04, 1)
    if any(k in n for k in ['sirop', 'suspension']): return max(stock * 0.06, 1)
    if any(k in n for k in ['injectable', 'poudre pour']): return max(stock * 0.03, 1)
    return max(stock * 0.02, 0.5)  # défaut conservateur

rows = []
for _, r in df_agg.iterrows():
    stock = r['stock_total']
    produit = r['designation']
    
    # Trouver la vitesse de rotation (depuis ventes réelles si dispo)
    vitesse = None
    for k, v in ventes_rotation.items():
        if str(k).lower()[:10] == str(produit).lower()[:10]:
            vitesse = v; break
    
    if vitesse is None or vitesse <= 0:
        vitesse = vitesse_par_defaut(produit, stock)

    jours_restants = int(stock / vitesse) if vitesse > 0 else 999
    
    if stock == 0:
        statut = "🔴 RUPTURE"
        jours_restants = 0
    elif jours_restants <= SEUIL_CRITIQUE_JOURS:
        statut = "🔴 CRITIQUE"
    elif jours_restants <= SEUIL_VIGILANCE_JOURS:
        statut = "🟠 VIGILANCE"
    elif jours_restants <= SEUIL_OK_JOURS:
        statut = "🟡 ATTENTION"
    else:
        statut = "✅ OK"
    
    date_rupture = (datetime.now() + timedelta(days=jours_restants)).strftime('%d/%m/%Y') if jours_restants < 365 else "> 1 an"
    
    rows.append({
        'Produit': produit,
        'Dépôt': r.get('depot', 'N/A'),
        'Zone': r.get('zone', 'N/A'),
        'Nb Lots': int(r['nb_lots']),
        'Stock Total': int(stock),
        'Rotation/Jour': round(vitesse, 1),
        'Jours Restants': jours_restants if jours_restants < 9999 else 999,
        'Date Rupture Estimée': date_rupture,
        'Statut': statut,
    })

df_pred = pd.DataFrame(rows).sort_values('Jours Restants')

# ─── FILTRES ─────────────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
with col_f1:
    depot_list = ['Tous'] + sorted(df_lots['depot'].dropna().astype(str).unique().tolist()) if 'depot' in df_lots.columns else ['Tous']
    depot_sel = st.selectbox("🏢 Filtrer par Dépôt :", depot_list)
with col_f2:
    statut_list = ['Tous', '🔴 RUPTURE', '🔴 CRITIQUE', '🟠 VIGILANCE', '🟡 ATTENTION', '✅ OK']
    statut_sel = st.selectbox("⚠️ Filtrer par Statut :", statut_list)
with col_f3:
    seuil_jours = st.slider("⏱️ Seuil d'alerte (jours) :", min_value=5, max_value=90, value=30, step=5)

df_view = df_pred.copy()
if depot_sel != 'Tous':
    df_view = df_view[df_view['Dépôt'].str.contains(depot_sel, case=False, na=False)]
if statut_sel != 'Tous':
    df_view = df_view[df_view['Statut'] == statut_sel]

df_alert = df_view[df_view['Jours Restants'] <= seuil_jours].copy()
df_ok    = df_view[df_view['Jours Restants'] > seuil_jours].copy()

# ─── KPIs ────────────────────────────────────────────────────────────────────────
st.markdown("---")
k1, k2, k3, k4, k5 = st.columns(5)
nb_rupture  = len(df_view[df_view['Statut'] == '🔴 RUPTURE'])
nb_critique = len(df_view[df_view['Statut'] == '🔴 CRITIQUE'])
nb_vigilance= len(df_view[df_view['Statut'] == '🟠 VIGILANCE'])
nb_attention= len(df_view[df_view['Statut'] == '🟡 ATTENTION'])
nb_ok_total = len(df_view[df_view['Statut'] == '✅ OK'])

k1.markdown(f'<div class="kpi-card"><div class="kpi-label">Ruptures Actives</div><div class="kpi-val" style="color:#ef4444">{nb_rupture}</div><div class="kpi-desc">Stock = 0</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-card"><div class="kpi-label">Critiques (&lt;{SEUIL_CRITIQUE_JOURS}j)</div><div class="kpi-val" style="color:#f97316">{nb_critique}</div><div class="kpi-desc">Commande urgente</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-card"><div class="kpi-label">Vigilance (&lt;{SEUIL_VIGILANCE_JOURS}j)</div><div class="kpi-val" style="color:#eab308">{nb_vigilance}</div><div class="kpi-desc">À surveiller</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-card"><div class="kpi-label">Attention (&lt;{SEUIL_OK_JOURS}j)</div><div class="kpi-val" style="color:#a78bfa">{nb_attention}</div><div class="kpi-desc">Planifier commande</div></div>', unsafe_allow_html=True)
k5.markdown(f'<div class="kpi-card"><div class="kpi-label">Stock OK</div><div class="kpi-val" style="color:#10b981">{nb_ok_total}</div><div class="kpi-desc">Produits sains</div></div>', unsafe_allow_html=True)

# ─── ALERTES ET TABLE ─────────────────────────────────────────────────────────────
st.markdown("---")
col_left, col_right = st.columns([3, 1])

with col_left:
    st.markdown(f"### 🚨 Alertes Rupture ({len(df_alert)} produit(s) sous {seuil_jours} jours)")
    
    if df_alert.empty:
        st.success(f"✅ Aucun produit n'est en risque de rupture dans les {seuil_jours} prochains jours.")
    else:
        def color_row(row):
            s = row['Jours Restants']
            if s == 0: return ['background-color:rgba(127,29,29,0.45); color:#ffffff'] * len(row)
            if s <= SEUIL_CRITIQUE_JOURS: return ['background-color:rgba(124,45,18,0.45); color:#ffffff'] * len(row)
            if s <= SEUIL_VIGILANCE_JOURS: return ['background-color:rgba(113,53,0,0.45); color:#ffffff'] * len(row)
            return [''] * len(row)
        
        cols_display = ['Statut', 'Produit', 'Dépôt', 'Zone', 'Nb Lots', 'Stock Total', 'Rotation/Jour', 'Jours Restants', 'Date Rupture Estimée']
        st.dataframe(
            df_alert[cols_display].style.apply(color_row, axis=1),
            use_container_width=True, hide_index=True
        )
        
        # Bouton PDF alertes
        pdf_alert_data = generate_inventory_report_pdf(
            df_alert, 
            title=f"RAPPORT ALERTES RUPTURE - {datetime.now().strftime('%d/%m/%Y')}",
            cols_to_include=cols_display,
            orientation='L'
        )
        st.download_button(
            "📥 Télécharger les Alertes en PDF",
            data=pdf_alert_data,
            file_name=f"Alertes_Rupture_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime='application/pdf',
            use_container_width=True,
            type="primary"
        )

with col_right:
    st.markdown("### 📋 Actions")
    if not df_alert.empty:
        for _, row in df_alert.head(8).iterrows():
            j = row['Jours Restants']
            produit_short = str(row['Produit'])[:30]
            if j == 0:
                st.markdown(f'<div class="alert-card-red">🔴 <b>{produit_short}</b><br><small>RUPTURE STOCK</small></div>', unsafe_allow_html=True)
            elif j <= SEUIL_CRITIQUE_JOURS:
                st.markdown(f'<div class="alert-card-orange">🟠 <b>{produit_short}</b><br><small>J-{j} → Commander maintenant</small></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-card-yellow">🟡 <b>{produit_short}</b><br><small>J-{j} → Planifier</small></div>', unsafe_allow_html=True)
    else:
        st.info("Aucune alerte active.")

# ─── GRAPHIQUE ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Vue d'ensemble — Jours Restants Estimés par Produit")

df_chart = df_view[df_view['Jours Restants'] < 365].nsmallest(40, 'Jours Restants')
if not df_chart.empty:
    color_map = {'🔴 RUPTURE': '#ef4444', '🔴 CRITIQUE': '#f97316', '🟠 VIGILANCE': '#f59e0b', '🟡 ATTENTION': '#a78bfa', '✅ OK': '#10b981'}
    fig = px.bar(
        df_chart, x='Jours Restants', y='Produit', orientation='h',
        color='Statut', color_discrete_map=color_map,
        text='Jours Restants',
        labels={'Jours Restants': 'Jours avant rupture estimée', 'Produit': ''},
        height=max(350, len(df_chart) * 22)
    )
    fig.add_vline(x=SEUIL_CRITIQUE_JOURS, line_dash="dash", line_color="#ef4444", annotation_text=f"Critique ({SEUIL_CRITIQUE_JOURS}j)")
    fig.add_vline(x=SEUIL_VIGILANCE_JOURS, line_dash="dash", line_color="#f59e0b", annotation_text=f"Vigilance ({SEUIL_VIGILANCE_JOURS}j)")
    fig.update_traces(textposition='outside')
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, l=10, r=80, b=10),
        yaxis={'categoryorder': 'total ascending'},
        legend=dict(orientation='h', yanchor='bottom', y=1.01),
        font=dict(family='Inter, sans-serif', size=11),
    )
    st.plotly_chart(fig, use_container_width=True)

# ─── TABLEAU COMPLET ───────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander(f"📋 Liste Complète des Produits ({len(df_view)} produits)", expanded=False):
    cols_display_all = ['Statut', 'Produit', 'Dépôt', 'Zone', 'Nb Lots', 'Stock Total', 'Rotation/Jour', 'Jours Restants', 'Date Rupture Estimée']
    st.dataframe(df_view[cols_display_all], use_container_width=True, hide_index=True)
    
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        pdf_full_data = generate_inventory_report_pdf(
            df_view, 
            title=f"RAPPORT COMPLET RUPTURES - {datetime.now().strftime('%d/%m/%Y')}",
            cols_to_include=cols_display_all,
            orientation='L'
        )
        st.download_button(
            "📥 Télécharger en PDF",
            data=pdf_full_data,
            file_name=f"Rapport_Ruptures_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime='application/pdf',
            use_container_width=True,
            type="primary"
        )
    with dl_col2:
        csv_data = df_view.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            "📥 Télécharger en CSV",
            data=csv_data.encode('utf-8-sig'),
            file_name=f"Rapport_Ruptures_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
            use_container_width=True
        )

# ─── IA EXPERT ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🧠 Analyse IA des Risques de Rupture")
if is_ia_enabled():
    if not df_alert.empty:
        if st.button("🤖 Générer un Plan d'Approvisionnement Intelligent", type="primary", use_container_width=True):
            with st.spinner("L'IA analyse vos risques de rupture..."):
                top_risks = df_alert.head(10)
                liste = "\n".join([
                    f"- {r['Produit']} : Stock={r['Stock Total']}, Rotation={r['Rotation/Jour']}/j, J-{r['Jours Restants']}"
                    for _, r in top_risks.iterrows()
                ])
                prompt = f"""Tu es expert en gestion de pharmacie et Supply Chain pharmaceutique.
Voici les produits en risque de rupture identifiés dans notre stock :
{liste}

Génère un plan d'approvisionnement priorisé :
1. Quels produits commander EN URGENCE (dans les 48h) ?
2. Quels produits planifier cette semaine ?
3. Comment optimiser les rotations pour éviter ces ruptures à l'avenir ?
Sois concis, professionnel et pratique. Utilise des emojis pour la lisibilité."""
                reponse = ask_ai(prompt)
                st.success(reponse)
    else:
        st.info("✅ Aucune alerte urgente à analyser. Votre stock est globalement sain.")
else:
    st.info("🔐 Activez la clé API IA pour obtenir des recommandations d'approvisionnement automatiques.")
