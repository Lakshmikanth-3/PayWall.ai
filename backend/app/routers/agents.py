import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.simulator import simulate_policy

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=schemas.AgentResponse)
def create_agent(payload: schemas.AgentCreate, db: Session = Depends(get_db)):
    agent_id = f"AGT-{uuid.uuid4().hex[:6].upper()}"
    agent = models.Agent(
        id=agent_id,
        name=payload.name,
        owner_id=payload.owner_id,
        max_transaction=payload.max_transaction,
        daily_limit=payload.daily_limit,
        allowed_categories=payload.allowed_categories,
        blocked_categories=payload.blocked_categories,
        requires_approval_above=payload.requires_approval_above,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[schemas.AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(models.Agent).all()


@router.get("/{agent_id}", response_model=schemas.AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}/suspend")
def suspend_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "SUSPENDED"
    db.commit()
    return {"message": f"Agent {agent_id} suspended"}


@router.patch("/{agent_id}/activate")
def activate_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "ACTIVE"
    db.commit()
    return {"message": f"Agent {agent_id} activated"}


@router.post("/{agent_id}/simulate-policy", response_model=schemas.PolicySimulationResponse)
def simulate_agent_policy(
    agent_id: str,
    payload: schemas.PolicySimulationRequest,
    db: Session = Depends(get_db),
):
    """
    Replays this agent's historical transactions against a proposed policy
    change (without applying it) and reports the shift in ALLOW/REVIEW/BLOCK
    outcomes. Section 26 "Policy Simulator" — demonstrates the economic
    tradeoff between loosening automation and taking on more risk.
    """
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return simulate_policy(agent, payload, db)
