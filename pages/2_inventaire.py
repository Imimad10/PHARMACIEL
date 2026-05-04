# --- ONGLET CONFRONTATION (CORRIGÉ) ---
with tabs[2]:
    st.subheader("🔍 Analyse des écarts")
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(SAISIE_PATH, sep=';')
            
            if 'lot_master' not in saisie.columns:
                st.error("Fichier de saisie ancien. Réinitialisez en Admin.")
            else:
                # 1. On groupe les saisies pour être sûr de n'avoir qu'une ligne par lot
                s_grouped = saisie.groupby(['designation', 'lot_master']).agg({
                    'qte_saisie': 'sum', 
                    'ddp_saisi': 'first', 
                    'ppa_saisi': 'first', 
                    'shp_saisi': 'first'
                }).reset_index()
                
                # 2. Préparation du Master (on s'assure que les types correspondent)
                df_temp_master = df_master.copy()
                df_temp_master['lot'] = df_temp_master['lot'].astype(str)
                s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
                
                # 3. Fusion (Merge)
                res = pd.merge(
                    df_temp_master, 
                    s_grouped, 
                    left_on=['designation', 'lot'], 
                    right_on=['designation', 'lot_master'], 
                    how='left'
                )
                
                # 4. Nettoyage des valeurs vides
                res['qte_saisie'] = res['qte_saisie'].fillna(0)
                res['stock_theorique'] = pd.to_numeric(res['stock_theorique'], errors='coerce').fillna(0)
                
                # 5. CALCUL SÉCURISÉ (Ligne par ligne pour éviter l'erreur de réindexation)
                res['écart'] = res['qte_saisie'] - res['stock_theorique']

                # --- FONCTION DE COLORATION ---
                def highlight_diff(row):
                    styles = [''] * len(row)
                    if str(row['ddp']) != str(row['ddp_saisi']) and row['qte_saisie'] > 0:
                        styles[row.index.get_loc('ddp_saisi')] = 'background-color: #ffcccc; color: red; font-weight: bold'
                    
                    if 'ppa' in row and 'ppa_saisi' in row:
                        try:
                            if float(row['ppa']) != float(row['ppa_saisi']) and row['qte_saisie'] > 0:
                                styles[row.index.get_loc('ppa_saisi')] = 'background-color: #ffcccc; color: red; font-weight: bold'
                        except: pass
                    
                    if row['écart'] != 0:
                        styles[row.index.get_loc('écart')] = 'color: orange; font-weight: bold'
                    return styles

                cols_to_show = ['designation', 'lot', 'ddp', 'ddp_saisi', 'ppa', 'ppa_saisi', 'stock_theorique', 'qte_saisie', 'écart']
                final_cols = [c for c in cols_to_show if c in res.columns]
                
                st.dataframe(res[final_cols].style.apply(highlight_diff, axis=1), use_container_width=True)

        except Exception as e:
            st.error(f"Erreur technique : {e}")
            st.info("Conseil : Vérifiez que votre fichier Master ne contient pas de lignes totalement identiques.")
