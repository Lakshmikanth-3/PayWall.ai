from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app import models
from app.seed import run_seed

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/seed")
def seed_database(
    db: Session = Depends(get_db),
    x_admin_key: str = Header(default=""),
    force: bool = Query(False, description="Wipe existing transactions/audit logs first for a full clean reseed"),
):
    """
    Populates demo agents/merchants/transaction history against THIS
    instance's own database. Exists for deployments without shell/filesystem
    access (e.g. Render's free tier) — scripts/seed_db.py does the same
    thing for local dev, connecting directly to the sqlite file instead.

    Protected by SECRET_KEY as a shared secret since this mutates data;
    idempotent by default (app.seed.run_seed skips any stage that already
    has data) — e.g. a request that times out mid-run (a slow free-tier
    instance scoring 100+ transactions can outlast an HTTP client's
    timeout) leaves a partial history that a plain retry won't top up,
    since "any transaction exists" is what each stage checks. force=true
    clears transactions/audit logs (never agents/merchants) so the next
    call regenerates the full history from scratch.
    """
    if not settings.SECRET_KEY or x_admin_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")
    if force:
        db.query(models.AuditLog).delete()
        db.query(models.Transaction).delete()
        for agent in db.query(models.Agent).all():
            agent.daily_spent = 0.0
        db.commit()
    return run_seed(db)
