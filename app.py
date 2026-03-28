import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

st.set_page_config(page_title="🍺 Suivi Brassins", layout="wide")
st.title("🍺 Suivi Brassins - Cuve + Bouteille")

# ====================== CSS GLOBAL (une seule fois) ======================
st.markdown("""
<style>
    @keyframes bubble {
        0% { transform: translateY(0); opacity: 0.9; }
        100% { transform: translateY(-280px); opacity: 0; }
    }
</style>
""", unsafe_allow_html=True)
# ========================================================================

# Connexion DB
DB_PATH = "/data/brassins.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS brassins (
    id INTEGER PRIMARY KEY,
    nom TEXT,
    levure TEXT,
    date_debut_cuve TEXT,
    date_fin_cuve TEXT,
    date_embouteillage TEXT,
    resucrage_g_per_l REAL,
    jours_referm_estimes INTEGER
)''')
conn.commit()

# Liste des levures
LEVURES = ["Kveik (Lallemand)", "House Ale (Lallemand)"]

# Sidebar
menu = st.sidebar.selectbox("Menu", ["Liste des brassins", "Nouveau brassin"])

if menu == "Nouveau brassin":
    st.header("➕ Nouveau brassin")
    nom = st.text_input("Nom du brassin")
    levure = st.selectbox("Levure", LEVURES)
    
    col1, col2 = st.columns(2)
    date_debut = col1.date_input("Début fermentation cuve", value=date.today())
    
    if levure.startswith("House Ale"):
        jours_estimes = 4
        info_levure = "✅ **House Ale** à 20°C : fermentation complète en ~4 jours"
    else:
        jours_estimes = 8
        info_levure = "⚠️ **Kveik** à 20°C : plus lente (5–12 jours). Idéalement 25–40°C pour rester rapide."
    
    st.info(info_levure)
    date_fin_suggeree = date_debut + timedelta(days=jours_estimes)
    date_fin = col2.date_input("Fin fermentation cuve (estimée)", value=date_fin_suggeree)
    
    if st.button("Créer le brassin", type="primary"):
        c.execute("INSERT INTO brassins (nom, levure, date_debut_cuve, date_fin_cuve) VALUES (?,?,?,?)",
                  (nom, levure, str(date_debut), str(date_fin)))
        conn.commit()
        st.success(f"Brassin **{nom}** créé !")
        st.rerun()

else:
    st.header("📋 Mes brassins")
    df = pd.read_sql("SELECT * FROM brassins ORDER BY id DESC", conn)
    
    if df.empty:
        st.info("Aucun brassin encore. Crée le premier !")
    else:
        for _, row in df.iterrows():
            with st.expander(f"🍺 {row['nom']} - {row['levure']}"):
                # PHASE CUVE
                debut = datetime.strptime(row['date_debut_cuve'], "%Y-%m-%d").date()
                fin = datetime.strptime(row['date_fin_cuve'], "%Y-%m-%d").date()
                today = date.today()
                
                if today < debut:
                    progress_cuve = 0
                elif today > fin:
                    progress_cuve = 100
                else:
                    total = (fin - debut).days
                    ecoule = (today - debut).days
                    progress_cuve = int((ecoule / total) * 100) if total > 0 else 100
                
                st.subheader("Fermentation en cuve")
                st.progress(progress_cuve / 100)
                st.caption(f"{progress_cuve}% • {debut} → {fin}")
                
                # PHASE BOUTEILLE
                if row['date_embouteillage']:
                    st.subheader("Refermentation en bouteille")
                    emb = datetime.strptime(row['date_embouteillage'], "%Y-%m-%d").date()
                    jours_estimes = row['jours_referm_estimes']
                    fin_bottle = emb + pd.Timedelta(days=jours_estimes)
                    
                    progress_bottle = min(100, int(((today - emb).days / jours_estimes) * 100))
                    
                    st.progress(progress_bottle / 100)
                    st.caption(f"{progress_bottle}% • Resucrage : {row['resucrage_g_per_l']} g/L • Fin estimée : {fin_bottle}")
                    
                    # === BOUTEILLE RÉALISTE (style global déjà chargé) ===
                    st.markdown(f"""
                    <div style="text-align:center; margin:30px 0;">
                        <div style="width:140px; height:320px; margin:0 auto; position:relative;">
                            <!-- Corps -->
                            <div style="position:absolute; bottom:0; left:20px; width:100px; height:240px; 
                                        background:linear-gradient(180deg, #f5d88a 0%, #e8b76b 70%, #d4a05a 100%);
                                        border-radius: 15px 15px 60px 60px; border:8px solid #333; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
                            </div>
                            <!-- Col -->
                            <div style="position:absolute; top:60px; left:48px; width:44px; height:100px; 
                                        background:linear-gradient(#333, #222); border:8px solid #333; border-bottom:none; border-radius:20px 20px 0 0;">
                            </div>
                            <!-- Bouchon -->
                            <div style="position:absolute; top:45px; left:42px; width:56px; height:28px; 
                                        background:linear-gradient(#f1c40f, #e67e22); border:6px solid #333; border-radius:8px; box-shadow:0 4px 8px rgba(0,0,0,0.4);">
                            </div>
                            <!-- Bière qui monte -->
                            <div style="position:absolute; bottom:8px; left:28px; width:104px; height:{progress_bottle}%; 
                                        background:linear-gradient(180deg, #f5d88a, #e8b76b); border-radius:0 0 50px 50px; overflow:hidden;">
                                <div style="position:absolute; top:-20px; left:0; right:0; height:30px; 
                                            background:linear-gradient(#fff, #f5f5f5); border-radius:50px; opacity:0.75;"></div>
                            </div>
                            <!-- Bulles -->
                            <div style="position:absolute; bottom:20%; left:40%; width:10px; height:10px; background:#fff; border-radius:50%; opacity:0.85; animation:bubble 1.8s infinite;"></div>
                            <div style="position:absolute; bottom:35%; left:55%; width:8px; height:8px; background:#fff; border-radius:50%; opacity:0.75; animation:bubble 2.3s infinite 0.4s;"></div>
                            <div style="position:absolute; bottom:15%; left:70%; width:14px; height:14px; background:#fff; border-radius:50%; opacity:0.9; animation:bubble 1.4s infinite 0.8s;"></div>
                            <div style="position:absolute; bottom:45%; left:35%; width:7px; height:7px; background:#fff; border-radius:50%; opacity:0.6; animation:bubble 2.1s infinite 1.2s;"></div>
                        </div>
                        <p style="margin-top:15px; font-size:1em; color:#333;">Bouteille en refermentation • {progress_bottle}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.subheader("Refermentation en bouteille")
                    mode_key = f"bottle_mode_{row['id']}"
                    if mode_key not in st.session_state:
                        st.session_state[mode_key] = False
                    
                    if st.button("🚀 Passer en refermentation bouteille", key=f"bottle_btn_{row['id']}"):
                        st.session_state[mode_key] = True
                        st.rerun()
                    
                    if st.session_state[mode_key]:
                        col1, col2 = st.columns(2)
                        date_bottle = col1.date_input("Date d'embouteillage", value=date.today(), key=f"date_{row['id']}")
                        resucrage = col2.number_input("Resucrage (g/L)", value=6.0, step=0.5, key=f"res_{row['id']}")
                        jours_est = st.slider("Jours estimés de refermentation", 7, 21, 12, key=f"jours_{row['id']}")
                        
                        col_val, col_ann = st.columns(2)
                        if col_val.button("✅ Valider la mise en bouteille", type="primary", key=f"val_{row['id']}"):
                            c.execute("""UPDATE brassins SET 
                                       date_embouteillage=?, resucrage_g_per_l=?, jours_referm_estimes=?
                                       WHERE id=?""",
                                      (str(date_bottle), resucrage, jours_est, row['id']))
                            conn.commit()
                            st.session_state[mode_key] = False
                            st.success("Phase bouteille activée !")
                            st.rerun()
                        
                        if col_ann.button("❌ Annuler", key=f"cancel_{row['id']}"):
                            st.session_state[mode_key] = False
                            st.rerun()

                # Suppression
                st.divider()
                delete_key = f"delete_confirm_{row['id']}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False
                
                if st.button("🗑️ Supprimer ce brassin", key=f"del_btn_{row['id']}", type="secondary"):
                    st.session_state[delete_key] = True
                    st.rerun()
                
                if st.session_state[delete_key]:
                    st.warning("⚠️ Tu es sûr de vouloir supprimer définitivement ce brassin ? Cette action est irréversible.")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Oui, supprimer", type="primary", key=f"confirm_del_{row['id']}"):
                        c.execute("DELETE FROM brassins WHERE id=?", (row['id'],))
                        conn.commit()
                        st.session_state[delete_key] = False
                        st.success("Brassin supprimé !")
                        st.rerun()
                    if col2.button("❌ Annuler", key=f"cancel_del_{row['id']}"):
                        st.session_state[delete_key] = False
                        st.rerun()

st.caption("✅ Bouteille corrigée • Animation propre • Port 8502")
