import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
from jinja2 import Template
from utils_gsheets import load_gs_data
from utils_themes import apply_user_theme

# --- CONFIGURATION ---
def get_dashboard_data():
    """Collecte et prépare les données pour le dashboard HTML."""
    df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", 
                          ["designation", "n°lot", "ddp", "qte_saisie", "ppa", "laboratoire"])
    
    total_valeur = 0
    total_produits = 0
    expired_soon = 0
    now = datetime.now()
    inventory_summary = []
    
    if not df_inv.empty:
        for _, row in df_inv.iterrows():
            try:
                qte = float(row.get('qte_saisie', 0))
                ppa = float(row.get('ppa', 0))
                total_produits += qte
                total_valeur += (qte * ppa)
                
                expiry_str = str(row.get('ddp', ''))
                status = "ok"
                if expiry_str and expiry_str != 'nan':
                    try:
                        exp_dt = pd.to_datetime(expiry_str)
                        diff_months = (exp_dt.year - now.year) * 12 + (exp_dt.month - now.month)
                        if diff_months < 0: status = "expired"
                        elif diff_months <= 6: 
                            status = "soon"
                            expired_soon += 1
                    except: pass

                inventory_summary.append({
                    "name": str(row.get('designation', 'Inconnu')),
                    "lot": str(row.get('n°lot', '—')),
                    "qte": int(qte),
                    "status": status,
                    "valeur": f"{qte * ppa:,.0f} DA"
                })
            except: continue

    df_logs = load_gs_data("Logs", "data/db_logs.csv", ["timestamp", "user", "action", "module"])
    recent_actions = []
    if not df_logs.empty:
        for _, row in df_logs.tail(8).iloc[::-1].iterrows():
            recent_actions.append({
                "time": str(row.get('timestamp', ''))[-8:], 
                "user": str(row.get('user', 'User')),
                "action": str(row.get('action', '')),
                "module": str(row.get('module', ''))
            })

    stats = {
        "labels": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "data_stock": [total_produits * 0.8, total_produits * 0.85, total_produits * 0.9, total_produits, total_produits * 1.1, total_produits, total_produits * 0.95]
    }

    return {
        "inventory": inventory_summary[:10],
        "kpis": {
            "total_valeur": f"{total_valeur:,.0f} DA",
            "total_produits": f"{int(total_produits):,}",
            "expired_soon": expired_soon,
            "active_users": df_logs['user'].nunique() if not df_logs.empty else 1
        },
        "actions": recent_actions,
        "stats": stats,
        "user": st.session_state.current_user.get('username', 'Admin'),
        "date": datetime.now().strftime("%d/%m/%Y")
    }

# --- TEMPLATE HTML FLUFFY PREMIUM (Inspiré de votre code) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr" dir="ltr">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #eef0f8;
            --primary: #5b6cf9;
            --neu-shadow: 7px 7px 18px #c0c5dc, -7px -7px 18px #ffffff;
            --neu-shadow-inset: inset 4px 4px 12px #c0c5dc, inset -4px -4px 12px #ffffff;
            --text: #1a1f3c;
            --muted: #6b7299;
            --green: #2db88a;
            --red: #f06585;
            --yellow: #e8a020;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Nunito', sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 25px; }

        .dashboard-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }

        /* Header */
        .header { grid-column: span 4; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .welcome h1 { font-size: 2rem; font-weight: 900; color: var(--primary); }
        
        /* KPI Cards Neumorphic */
        .stat-card { 
            background: var(--bg); padding: 20px; border-radius: 24px; 
            box-shadow: var(--neu-shadow); display: flex; align-items: center; gap: 15px;
            transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-icon { 
            width: 55px; height: 55px; border-radius: 18px; 
            display: flex; align-items: center; justify-content: center;
            box-shadow: var(--neu-shadow); font-size: 24px;
        }
        .blue { background: linear-gradient(135deg, #7c8fff, #5b6cf9); color: white; }
        .green { background: linear-gradient(135deg, #34d399, #2db88a); color: white; }
        .yellow { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: white; }
        
        .stat-val { font-size: 1.6rem; font-weight: 900; }
        .stat-lbl { font-size: 0.8rem; color: var(--muted); font-weight: 700; }

        /* Robot AI Scan Button */
        .ai-scan-btn {
            grid-column: span 4;
            background: linear-gradient(135deg, #7c3aed, #4c1d95);
            padding: 20px; border-radius: 20px; color: white;
            display: flex; align-items: center; justify-content: center; gap: 15px;
            cursor: pointer; box-shadow: 0 10px 30px rgba(124,58,237,0.4);
            font-weight: 900; font-size: 1.2rem; margin: 10px 0;
            border: none;
        }
        .ai-scan-btn:active { transform: scale(0.98); }

        /* Panels */
        .panel { 
            grid-column: span 2; background: var(--bg); padding: 25px; 
            border-radius: 28px; box-shadow: var(--neu-shadow); 
        }
        .panel-title { font-weight: 900; font-size: 1.1rem; margin-bottom: 20px; color: var(--primary); }

        table { width: 100%; border-collapse: collapse; }
        td, th { padding: 12px; text-align: left; font-size: 0.9rem; }
        th { color: var(--muted); font-weight: 800; border-bottom: 2px solid #e2e8f0; }
        tr:last-child td { border: none; }
        
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; }
        .badge-ok { background: #d4f5ea; color: var(--green); }
        .badge-soon { background: #fef5dc; color: var(--yellow); }
        .badge-expired { background: #fde8ef; color: var(--red); }

        /* Feed */
        .feed-item { display: flex; gap: 12px; padding: 15px 0; border-bottom: 1px solid #e2e8f0; }
        .feed-icon { 
            width: 40px; height: 40px; border-radius: 12px; 
            background: var(--bg); box-shadow: var(--neu-shadow);
            display: flex; align-items: center; justify-content: center;
            font-weight: 900; color: var(--primary);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="welcome">
            <h1>Bonjour, {{ user }} 👋</h1>
            <p style="color: var(--muted); font-weight: 700;">Dashboard DarPharm Fluffy • {{ date }}</p>
        </div>
        <div class="stat-icon blue" style="width: auto; padding: 0 20px; border-radius: 12px; font-size: 14px; font-weight: 800;">⚡ SYSTÈME LIVE</div>
    </div>

    <div class="dashboard-grid">
        <!-- KPIs -->
        <div class="stat-card">
            <div class="stat-icon blue">💰</div>
            <div class="stat-info">
                <div class="stat-val">{{ kpis.total_valeur }}</div>
                <div class="stat-lbl">VALEUR STOCK</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon green">📦</div>
            <div class="stat-info">
                <div class="stat-val">{{ kpis.total_produits }}</div>
                <div class="stat-lbl">UNITÉS TOTALES</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon yellow">🔔</div>
            <div class="stat-info">
                <div class="stat-val">{{ kpis.expired_soon }}</div>
                <div class="stat-lbl">PÉREMPTIONS PROCHES</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon blue">👥</div>
            <div class="stat-info">
                <div class="stat-val">{{ kpis.active_users }}</div>
                <div class="stat-lbl">AGENTS ACTIFS</div>
            </div>
        </div>

        <!-- Robot AI Scan Button -->
        <button class="ai-scan-btn" onclick="parent.postMessage('open_ai_scan', '*')">
            🤖 MASQUER & SCAN INTELLIGENT — (AI SMART SCAN)
        </button>

        <!-- Charts & Tables -->
        <div class="panel">
            <div class="panel-title">📈 Tendance du Stock</div>
            <canvas id="stockChart" style="max-height: 250px;"></canvas>
        </div>

        <div class="panel">
            <div class="panel-title">📋 Inventaire (Aperçu)</div>
            <table>
                <thead>
                    <tr><th>Produit</th><th>Lot</th><th>Statut</th></tr>
                </thead>
                <tbody>
                    {% for item in inventory %}
                    <tr>
                        <td style="font-weight: 800;">{{ item.name }}</td>
                        <td style="color: var(--muted);">{{ item.lot }}</td>
                        <td><span class="badge badge-{{ item.status }}">{{ item.status | upper }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="panel">
            <div class="panel-title">🔄 Activités Récentes</div>
            {% for action in actions %}
            <div class="feed-item">
                <div class="feed-icon">{{ action.user[0] | upper }}</div>
                <div class="feed-info">
                    <div style="font-weight: 800; font-size: 0.9rem;">{{ action.user }}</div>
                    <div style="font-size: 0.8rem; color: var(--muted);">{{ action.action }}</div>
                    <div style="font-size: 0.75rem; color: var(--primary); font-weight: 700;">{{ action.time }} • {{ action.module }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        const ctxStock = document.getElementById('stockChart').getContext('2d');
        new Chart(ctxStock, {
            type: 'line',
            data: {
                labels: {{ stats.labels | safe }},
                datasets: [{
                    label: 'Unités',
                    data: {{ stats.data_stock | safe }},
                    borderColor: '#5b6cf9',
                    backgroundColor: 'rgba(91, 108, 249, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { plugins: { legend: { display: false } }, scales: { y: { display: false }, x: { grid: { display: false } } } }
        });
    </script>
</body>
</html>
"""

# --- RENDU ---
data = get_dashboard_data()
template = Template(HTML_TEMPLATE)
final_html = template.render(**data)

# Communication entre Iframe et Streamlit pour# --- BOUTONS D'ACTION FLUFFY (Streamlit Natif pour assurer le fonctionnement) ---
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #7c3aed, #4c1d95) !important;
        color: white !important;
        border-radius: 20px !important;
        padding: 20px !important;
        font-weight: 900 !important;
        font-size: 1.2rem !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(124, 58, 237, 0.3) !important;
        transition: all 0.3s ease !important;
        margin-top: 20px;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 35px rgba(124, 58, 237, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("🤖 LANCER LE SCAN IA (INTELLIGENT SCAN)"):
        st.session_state.current_page = "7_scanneur_qr" # Ou le module de scan IA dédié
        st.rerun()

with col2:
    if st.button("📊 ACTUALISER LES STATISTIQUES LIVE"):
        st.rerun()
