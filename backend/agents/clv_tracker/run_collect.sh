#!/bin/bash
cd /home/Mon_ps
source /home/Mon_ps/venv/bin/activate 2>/dev/null || true
export DB_HOST=localhost
export API_BASE=http://localhost:8001
python3 backend/agents/clv_tracker/agent_clv_tracker.py
