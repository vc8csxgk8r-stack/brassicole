"""
api_brassicole.py
Mini API FastAPI pour exposer les données de Brassicole au dashboard TV.
À lancer en parallèle du Streamlit, port 8503.

Ajouter dans requirements.txt : fastapi uvicorn
Ajouter dans start.sh (ou Dockerfile CMD) :
  python api_brassicole.py &
  streamlit run app.py --server.port=8502 ...
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, os, datetime

DB_PATH = os.environ.get("DB_PATH", "/data/brassins.db")

app = FastAPI(title="Brassicole API", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

@app.get("/")
def root():
    return {
        "service": "Brassicole API",
        "routes": {
            "brassins":  "/api/brassins",
            "health":    "/api/health",
            "docs":      "/docs",
        }
    }

def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def _calcul_abv(og, fg):
    if og and fg:
        return round((og - fg) * 131.25, 2)
    return None

def _calcul_attenuation(og, fg_act, fg_target):
    """Pourcentage d'atténuation accompli vs cible."""
    if og and fg_act and fg_target:
        max_pts = (og - fg_target) * 1000
        done_pts = (og - fg_act) * 1000
        if max_pts > 0:
            return min(100, round(done_pts / max_pts * 100))
    return None

def _jours_depuis(date_str):
    if not date_str:
        return None
    try:
        d = datetime.date.fromisoformat(date_str)
        return (datetime.date.today() - d).days
    except Exception:
        return None

def _statut(row) -> str:
    """Détermine le statut d'un brassin depuis ses données."""
    if row["date_embouteillage"]:
        emb = _jours_depuis(row["date_embouteillage"])
        jours_ref = row["jours_referm_estimes"] or 14
        if emb is not None and emb >= jours_ref:
            return "done"
        return "bottled"
    if row["date_fin_cuve"]:
        fin = datetime.date.fromisoformat(row["date_fin_cuve"])
        if datetime.date.today() >= fin:
            return "ready"          # prêt à embouteiller
    return "fermenting"

@app.get("/api/brassins")
def get_brassins():
    con = _conn()
    brassins = con.execute(
        "SELECT * FROM brassins ORDER BY id DESC"
    ).fetchall()

    result = []
    for b in brassins:
        b = dict(b)
        pid = b["id"]

        # Dernière mesure de densité
        last_m = con.execute(
            "SELECT * FROM mesures WHERE brassin_id=? ORDER BY date DESC LIMIT 1", (pid,)
        ).fetchone()
        last_mesure = dict(last_m) if last_m else None

        # Historique densités (7 dernières)
        mesures_hist = [
            dict(m) for m in con.execute(
                "SELECT date, densite, temperature FROM mesures "
                "WHERE brassin_id=? ORDER BY date DESC LIMIT 7", (pid,)
            ).fetchall()
        ]
        mesures_hist.reverse()  # chronologique

        fg_act = last_mesure["densite"] if last_mesure else b.get("fg")
        statut = _statut(b)

        # Progression fermentation (cuve)
        jours_cuve = _jours_depuis(b["date_debut_cuve"])
        if b["date_fin_cuve"]:
            fin = datetime.date.fromisoformat(b["date_fin_cuve"])
            debut = datetime.date.fromisoformat(b["date_debut_cuve"])
            total = max(1, (fin - debut).days)
            pct_cuve = min(100, round((jours_cuve or 0) / total * 100))
        else:
            pct_cuve = None

        # Progression refermentation (bouteille)
        pct_bottle = None
        if b["date_embouteillage"]:
            jours_emb = _jours_depuis(b["date_embouteillage"])
            jours_ref  = b["jours_referm_estimes"] or 14
            pct_bottle = min(100, round((jours_emb or 0) / jours_ref * 100))

        result.append({
            "id":                  pid,
            "nom":                 b["nom"],
            "levure":              b["levure"],
            "date_debut_cuve":     b["date_debut_cuve"],
            "date_fin_cuve":       b["date_fin_cuve"],
            "date_embouteillage":  b["date_embouteillage"],
            "og":                  b["og"],
            "fg_cible":            b["fg"],
            "fg_actuelle":         fg_act,
            "volume_l":            b["volume_l"],
            "resucrage_g_per_l":   b["resucrage_g_per_l"],
            "jours_referm_estimes":b["jours_referm_estimes"],
            "abv":                 _calcul_abv(b["og"], fg_act),
            "attenuation_pct":     _calcul_attenuation(b["og"], fg_act, b["fg"]),
            "statut":              statut,
            "jours_cuve":          jours_cuve,
            "pct_cuve":            pct_cuve,
            "pct_bottle":          pct_bottle,
            "derniere_temp":       last_mesure["temperature"] if last_mesure else None,
            "derniere_densite":    last_mesure["densite"]     if last_mesure else None,
            "derniere_mesure_date":last_mesure["date"]        if last_mesure else None,
            "historique_densites": mesures_hist,
        })

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "brassins":  result,
        "count":     len(result),
        "actifs":    sum(1 for r in result if r["statut"] in ("fermenting","ready")),
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "db": DB_PATH}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8503, log_level="info")
