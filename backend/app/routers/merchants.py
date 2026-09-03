import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/merchants", tags=["merchants"])


def _risk_level(score: float) -> str:
    if score <= 30:
        return "LOW"
    elif score <= 70:
        return "MEDIUM"
    return "HIGH"


@router.post("", response_model=schemas.MerchantResponse)
def create_merchant(payload: schemas.MerchantCreate, db: Session = Depends(get_db)):
    mer_id = f"MER-{uuid.uuid4().hex[:6].upper()}"
    merchant = models.Merchant(
        id=mer_id,
        name=payload.name,
        category=payload.category,
        risk_score=payload.risk_score,
        risk_level=_risk_level(payload.risk_score),
        age_days=payload.age_days,
        refund_rate=payload.refund_rate,
        chargeback_rate=payload.chargeback_rate,
        failed_payment_rate=payload.failed_payment_rate,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


@router.get("", response_model=list[schemas.MerchantResponse])
def list_merchants(db: Session = Depends(get_db)):
    return db.query(models.Merchant).all()


@router.get("/{merchant_id}", response_model=schemas.MerchantResponse)
def get_merchant(merchant_id: str, db: Session = Depends(get_db)):
    m = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return m


@router.patch("/{merchant_id}/block")
def block_merchant(merchant_id: str, db: Session = Depends(get_db)):
    m = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Merchant not found")
    m.is_blocked = True
    db.commit()
    return {"message": f"Merchant {merchant_id} blocked"}
