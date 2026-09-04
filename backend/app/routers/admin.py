from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.seed import run_seed

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/seed")
def seed_database(
    db: Session = Depends(get_db),
    x_admin_key: str = Header(default=""),
):
    """
    Populates demo agents/merchants/transaction history against THIS
    instance's own database. Exists for deployments without shell/filesystem
    access (e.g. Render's free tier) — scripts/seed_db.py does the same
    thing for local dev, connecting directly to the sqlite file instead.

    Protected by SECRET_KEY as a shared secret since this mutates data;
    idempotent (app.seed.run_seed skips any stage that already has data).
    """
    if not settings.SECRET_KEY or x_admin_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")
    return run_seed(db)
