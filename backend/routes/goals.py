"""
routes/goals.py — CRUD for goals and milestones
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/goals", tags=["Goals"])


def _uid(): return str(uuid.uuid4())


# ─── Goals ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[schemas.GoalOut])
def list_goals(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Goal).filter(models.Goal.user_id == user.id).all()


@router.post("/", response_model=schemas.GoalOut)
def create_goal(body: schemas.GoalIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    goal = models.Goal(
        id          = body.id or _uid(),
        user_id     = user.id,
        name        = body.name,
        description = body.description or "",
        start_date  = body.start_date,
        end_date    = body.end_date,
        priority    = body.priority or "med",
        emoji       = body.emoji or "🎯",
    )
    db.add(goal); db.commit(); db.refresh(goal)
    return goal


@router.put("/{goal_id}", response_model=schemas.GoalOut)
def update_goal(goal_id: str, body: schemas.GoalIn,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(
        models.Goal.id == goal_id, models.Goal.user_id == user.id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    goal.name        = body.name
    goal.description = body.description or ""
    goal.start_date  = body.start_date
    goal.end_date    = body.end_date
    goal.priority    = body.priority or "med"
    goal.emoji       = body.emoji or "🎯"
    db.commit(); db.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def delete_goal(goal_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(
        models.Goal.id == goal_id, models.Goal.user_id == user.id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    db.delete(goal); db.commit()
    return {"ok": True}


# ─── Milestones ──────────────────────────────────────────────────────────────

@router.post("/{goal_id}/milestones", response_model=schemas.MilestoneOut)
def add_milestone(goal_id: str, body: schemas.MilestoneIn,
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(
        models.Goal.id == goal_id, models.Goal.user_id == user.id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")

    # Weight guard
    current_total = sum(m.weight for m in goal.milestones)
    if current_total + body.weight > 100.001:
        raise HTTPException(400, f"Total weights would exceed 100% ({current_total + body.weight:.1f}%)")

    m = models.Milestone(
        id         = body.id or _uid(),
        goal_id    = goal_id,
        name       = body.name,
        weight     = body.weight,
        deadline   = body.deadline,
        celebrated = body.celebrated or False,
    )
    db.add(m); db.commit(); db.refresh(m)
    return m


@router.put("/{goal_id}/milestones/{milestone_id}", response_model=schemas.MilestoneOut)
def update_milestone(goal_id: str, milestone_id: str, body: schemas.MilestoneIn,
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(
        models.Goal.id == goal_id, models.Goal.user_id == user.id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    m = db.query(models.Milestone).filter(
        models.Milestone.id == milestone_id, models.Milestone.goal_id == goal_id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")

    # Weight guard (exclude self)
    others = sum(x.weight for x in goal.milestones if x.id != milestone_id)
    if others + body.weight > 100.001:
        raise HTTPException(400, f"Total weights would exceed 100%")

    m.name       = body.name
    m.weight     = body.weight
    m.deadline   = body.deadline
    m.celebrated = body.celebrated or False
    db.commit(); db.refresh(m)
    return m


@router.delete("/{goal_id}/milestones/{milestone_id}")
def delete_milestone(goal_id: str, milestone_id: str,
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(models.Milestone).join(models.Goal).filter(
        models.Milestone.id == milestone_id,
        models.Goal.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")
    db.delete(m); db.commit()
    return {"ok": True}


@router.patch("/{goal_id}/milestones/{milestone_id}/celebrate")
def mark_celebrated(goal_id: str, milestone_id: str,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(models.Milestone).join(models.Goal).filter(
        models.Milestone.id == milestone_id,
        models.Goal.user_id == user.id).first()
    if not m:
        raise HTTPException(404, "Milestone not found")
    m.celebrated = True
    db.commit()
    return {"ok": True}
