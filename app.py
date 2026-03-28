import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sqlite3
import os

st.set_page_config(page_title="Brassicole", layout="wide", page_icon="🍺")
st.title("🍺 Brassicole - Suivi Brassins Pro")

# ====================== DB ======================
# ====================== DB + MIGRATION AUTOMATIQUE ======================
DB_PATH = "/data/brassins.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# Création table si elle n'existe pas
c.execute('''CREATE TABLE IF NOT EXISTS brassins (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    levure TEXT,
    date_debut_cuve TEXT,
    date_fin_cuve TEXT,
    og REAL,
    fg REAL,
    volume_l REAL,
    date_embouteillage TEXT,
    resucrage_g_per_l REAL,
    jours_referm_estimes INTEGER
)''')

# === MIGRATION : ajout des colonnes manquantes (compatibilité ancienne DB) ===
migration_queries = [
    "ALTER TABLE brassins ADD COLUMN og REAL",
    "ALTER TABLE brassins ADD COLUMN fg REAL",
    "ALTER TABLE brassins ADD COLUMN volume_l REAL",
    "ALTER TABLE brassins ADD COLUMN date_fin_cuve TEXT",
    "ALTER TABLE brassins ADD COLUMN resucrage_g_per_l REAL",
    "ALTER TABLE brassins ADD COLUMN jours_referm_estimes INTEGER"
]

for query in migration_queries:
    try:
        c.execute(query)
        conn.commit()
    except sqlite3.OperationalError:
        pass  # colonne déjà présente → on ignore

# Table mesures (inchangée)
c.execute('''CREATE TABLE IF NOT EXISTS mesures (
    id INTEGER PRIMARY KEY,
    brassin_id INTEGER,
    date TEXT,
    densite REAL,
    temperature REAL,
    FOREIGN KEY(brassin_id) REFERENCES brassins(id)
)''')
conn.commit()
# ====================== CONSTANTES ======================
LEVURES = ["Kveik (Lallemand)", "House Ale (Lallemand)"]

def calcul_abv(og: float, fg: float) -> float:
    if og and fg:
        return round((og - fg) * 131.25, 2)
    return 0.0

# ====================== SIDEBAR ======================
menu = st.sidebar.selectbox("Menu", ["Liste des brassins", "Nouveau brassin", "Ajouter mesure"])

# ====================== NOUVEAU BRASSIN ======================
if menu == "Nouveau brassin":
    st.header("Créer un nouveau brassin")
    
    with st.form("new_brassin"):
        nom = st.text_input("Nom du brassin", placeholder="IPA Citra #12")
        levure = st.selectbox("Levure", LEVURES)
        col1, col2, col3 = st.columns(3)
        date_debut = col1.date_input("Début cuve", value=date.today())
        og = col2.number_input("OG (densité initiale)", value=1.050, step=0.001, format="%.3f")
        volume = col3.number_input("Volume (L)", value=20.0, step=0.5)
        
        jours_estimes = 4 if "House Ale" in levure else 8
        date_fin = st.date_input("Fin cuve estimée", value=date_debut + timedelta(days=jours_estimes))
        
        if st.form_submit_button("Créer le brassin", type="primary"):
            try:
                c.execute("""INSERT INTO brassins 
                            (nom, levure, date_debut_cuve, date_fin_cuve, og, volume_l)
                            VALUES (?,?,?,?,?,?)""",
                          (nom, levure, str(date_debut), str(date_fin), og, volume))
                conn.commit()
                st.success(f"✅ Brassin **{nom}** créé avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la création : {e}")

# ====================== LISTE DES BRASSINS ======================
elif menu == "Liste des brassins":
    st.header("Mes brassins")
    df = pd.read_sql("SELECT * FROM brassins ORDER BY id DESC", conn)
    
    if df.empty:
        st.info("Aucun brassin pour le moment. Crée le premier !")
    else:
        for _, row in df.iterrows():
            with st.expander(f"#{row['id']} — {row['nom']} • {row['levure']}"):
                today = date.today()
                debut = datetime.strptime(row['date_debut_cuve'], "%Y-%m-%d").date()
                
                # ==================== CUVE ====================
                st.subheader("🧪 Fermentation en cuve")
                if row['date_fin_cuve']:
                    fin_cuve = datetime.strptime(row['date_fin_cuve'], "%Y-%m-%d").date()
                    total_jours = (fin_cuve - debut).days or 1
                    jours_ecoules = (today - debut).days
                    progress_cuve = max(0, min(100, int((jours_ecoules / total_jours) * 100)))
                    
                    # Progress bar améliorée
                    color = "#00ff00" if progress_cuve == 100 else "#ffaa00"
                    st.markdown(f"""
                    <div style="background:#333; border-radius:10px; padding:5px;">
                        <div style="background:{color}; width:{progress_cuve}%; height:25px; border-radius:8px; 
                                    text-align:center; color:white; font-weight:bold;">
                            {progress_cuve}% 
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"{debut} → {fin_cuve} • {jours_ecoules}/{total_jours} jours")
                
                # ABV
                abv = calcul_abv(row['og'], row.get('fg'))
                st.metric("ABV estimé", f"{abv}%", delta=None)
                
                # ==================== COURBE FERMENTATION ====================
                mesures = pd.read_sql(f"SELECT * FROM mesures WHERE brassin_id = {row['id']} ORDER BY date", conn)
                if not mesures.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=mesures['date'], y=mesures['densite'],
                                           mode='lines+markers', name='Densité', line=dict(color='#00ffaa')))
                    fig.update_layout(title="Courbe de fermentation", xaxis_title="Date", yaxis_title="Densité",
                                      template="plotly_dark", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune mesure de densité enregistrée pour l'instant.")
                
                # ==================== BOUTEILLE ====================
                if row['date_embouteillage']:
                    st.subheader("🍾 Refermentation en bouteille")
                    emb = datetime.strptime(row['date_embouteillage'], "%Y-%m-%d").date()
                    jours_estimes = row['jours_referm_estimes'] or 14
                    progress_bottle = min(100, int(((today - emb).days / jours_estimes) * 100))
                    
                    st.progress(progress_bottle / 100)
                    st.caption(f"{progress_bottle}% • Resucrage : {row['resucrage_g_per_l']} g/L")
                else:
                    # Formulaire embouteillage
                    with st.form(f"embouteiller_{row['id']}"):
                        st.subheader("Embouteiller ce brassin")
                        date_emb = st.date_input("Date embouteillage", value=today, key=f"date_{row['id']}")
                        fg = st.number_input("FG (densité finale)", value=1.010, step=0.001, format="%.3f", key=f"fg_{row['id']}")
                        resucrage = st.number_input("Resucrage (g/L)", value=6.0, step=0.5, key=f"res_{row['id']}")
                        jours_referm = st.number_input("Jours refermentation estimés", value=14, step=1, key=f"jours_{row['id']}")
                        
                        if st.form_submit_button("✅ Embouteiller"):
                            try:
                                c.execute("""UPDATE brassins 
                                           SET date_embouteillage=?, fg=?, resucrage_g_per_l=?, jours_referm_estimes=?
                                           WHERE id=?""",
                                          (str(date_emb), fg, resucrage, jours_referm, row['id']))
                                conn.commit()
                                st.success("Embouteillé !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")

# ====================== AJOUTER MESURE ======================
else:
    st.header("Ajouter une mesure de fermentation")
    brassins = pd.read_sql("SELECT id, nom FROM brassins", conn)
    if brassins.empty:
        st.warning("Crée d'abord un brassin !")
    else:
        choix = st.selectbox("Brassin", brassins['nom'], index=0)
        brassin_id = brassins[brassins['nom'] == choix]['id'].iloc[0]
        
        with st.form("mesure"):
            date_mesure = st.date_input("Date", value=date.today())
            densite = st.number_input("Densité", value=1.020, step=0.001, format="%.3f")
            temp = st.number_input("Température (°C)", value=20.0, step=0.5)
            
            if st.form_submit_button("Enregistrer mesure"):
                try:
                    c.execute("INSERT INTO mesures (brassin_id, date, densite, temperature) VALUES (?,?,?,?)",
                              (brassin_id, str(date_mesure), densite, temp))
                    conn.commit()
                    st.success("Mesure enregistrée !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

# Footer
st.caption("Brassicole v2.0 • Déployé avec ❤️ via Docker + Portainer")
