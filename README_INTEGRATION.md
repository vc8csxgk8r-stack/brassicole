# Intégration API Dashboard TV dans Brassicole

## Fichiers à ajouter dans le repo brassicole

### 1. `api_brassicole.py`
Copier le fichier `api_brassicole.py` à la racine du repo brassicole.

### 2. `requirements.txt` — ajouter les lignes :
```
fastapi==0.111.0
uvicorn==0.29.0
```

### 3. `Dockerfile` — remplacer le CMD par un script de démarrage :

```dockerfile
# Remplacer la dernière ligne CMD par :
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
```

### 4. Créer `start.sh` à la racine :
```bash
#!/bin/bash
# Lance l'API (port 8503) + Streamlit (port 8502) en parallèle
python api_brassicole.py &
streamlit run app.py \
  --server.port=8502 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
```

### 5. `docker-compose.yml` — exposer le port 8503 :
```yaml
services:
  brassin-tracker:
    build: .
    ports:
      - "8502:8502"   # Streamlit (inchangé)
      - "8503:8503"   # API dashboard TV  ← AJOUTER
    volumes:
      - ./data:/data
    restart: unless-stopped
```

## Test rapide
Après redéploiement :
```
curl http://ton-ip:8503/api/brassins
curl http://ton-ip:8503/api/health
```
