import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta

st.set_page_config(page_title="🍺 Suivi Brassins", layout="wide")
st.title("🍺 Suivi Brassins - Cuve + Bouteille")

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

else:  # Liste des brassins
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
                    
                    # Visuel bouteille
                    st.markdown(f"""
                    <div style="text-align:center; margin:20px 0;">
                        <div style="width:120px; height:280px; margin:0 auto; border:8px solid #333; border-radius:20px 20px 60px 60px; position:relative; background:#f8f8f8; overflow:hidden;">
                            <div style="position:absolute; bottom:0; left:10px; right:10px; height:{progress_bottle}%; background:linear-gradient(180deg, #ffcc00, #ff
