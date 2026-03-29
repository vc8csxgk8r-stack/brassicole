#!/bin/bash
python api_brassicole.py &
streamlit run app.py \
  --server.port=8502 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
