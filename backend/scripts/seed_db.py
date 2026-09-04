"""
Seed script (CLI) — creates demo agents, merchants, and ~200 test
transactions against the local database. Seeding logic lives in app.seed
so it can also run inside a deployed instance via POST /admin/seed
(backend/app/routers/admin.py) without needing direct DB/filesystem access.

Usage:
    python scripts/seed_db.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models
from app.seed import run_seed

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
result = run_seed(db)
db.close()

print("[OK] Seed complete.")
for k, v in result.items():
    print(f"   {k}: {v}")
