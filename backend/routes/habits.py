"""
routes/habits.py — habits, habit logs, journal, targets, top-3
All in one file to keep things compact.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(tags=["Habits & Journal"])


def _uid(): return str(uuid.uuid4())


# ─── Habits ──────────────────────────────────────────────────────────────────

@router.get("/habits", response_model=List[schemas.HabitOut])
def list_habits(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Habit).filter(models.Habit.user_id == user.id).all()


@router.post("/habits", response_model=schemas.HabitOut)
def create_habit(body: schemas.HabitIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    h = models.Habit(
        id       = body.id or _uid(),
        user_id  = user.id,
        name     = body.name,
        icon     = body.icon or "⭐",
        category = body.category or "Custom",
    )
    db.add(h); db.commit(); db.refresh(h)
    return h


@router.delete("/habits/{habit_id}")
def delete_habit(habit_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    h = db.query(models.Habit).filter(
        models.Habit.id == habit_id, models.Habit.user_id == user.id).first()
    if not h:
        raise HTTPException(404, "Habit not found")
    db.delete(h); db.commit()
    return {"ok": True}


# ─── Habit Logs ──────────────────────────────────────────────────────────────

@router.get("/habits/logs", response_model=List[schemas.HabitLogOut])
def get_habit_logs(
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(models.HabitLog).filter(models.HabitLog.user_id == user.id)
    if start_date: q = q.filter(models.HabitLog.log_date >= start_date)
    if end_date:   q = q.filter(models.HabitLog.log_date <= end_date)
    return q.all()


@router.post("/habits/logs/toggle", response_model=schemas.HabitLogOut)
def toggle_habit_log(body: schemas.HabitLogIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Upsert a habit log entry — creates or toggles."""
    existing = db.query(models.HabitLog).filter(
        models.HabitLog.habit_id == body.habit_id,
        models.HabitLog.user_id  == user.id,
        models.HabitLog.log_date == body.log_date,
    ).first()
    if existing:
        existing.done = body.done
        db.commit(); db.refresh(existing)
        return existing
    log = models.HabitLog(
        habit_id = body.habit_id,
        user_id  = user.id,
        log_date = body.log_date,
        done     = body.done,
    )
    db.add(log); db.commit(); db.refresh(log)
    return log


# ─── Journal ─────────────────────────────────────────────────────────────────

@router.get("/journal", response_model=List[schemas.JournalOut])
def list_journal(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Journal).filter(
        models.Journal.user_id == user.id
    ).order_by(models.Journal.entry_date.desc()).all()


@router.post("/journal", response_model=schemas.JournalOut)
def upsert_journal(body: schemas.JournalIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(models.Journal).filter(
        models.Journal.user_id    == user.id,
        models.Journal.entry_date == body.entry_date,
    ).first()
    if existing:
        existing.thoughts = body.thoughts or ""
        existing.ideas    = body.ideas    or ""
        existing.mood     = body.mood     or ""
        db.commit(); db.refresh(existing)
        return existing
    j = models.Journal(
        user_id    = user.id,
        entry_date = body.entry_date,
        thoughts   = body.thoughts or "",
        ideas      = body.ideas    or "",
        mood       = body.mood     or "",
    )
    db.add(j); db.commit(); db.refresh(j)
    return j


# ─── Targets ─────────────────────────────────────────────────────────────────

@router.get("/targets/{date}", response_model=Optional[schemas.TargetOut])
def get_target(date: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Target).filter(
        models.Target.user_id     == user.id,
        models.Target.target_date == date,
    ).first()


@router.post("/targets", response_model=schemas.TargetOut)
def upsert_target(body: schemas.TargetIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(models.Target).filter(
        models.Target.user_id     == user.id,
        models.Target.target_date == body.target_date,
    ).first()
    if existing:
        for field in ["study","workout","reading","water","sleep","mood","energy"]:
            setattr(existing, field, getattr(body, field, 0) or 0)
        db.commit(); db.refresh(existing)
        return existing
    t = models.Target(user_id=user.id, **body.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t


# ─── Top 3 ───────────────────────────────────────────────────────────────────

@router.get("/top3/{date}", response_model=Optional[schemas.Top3Out])
def get_top3(date: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Top3).filter(
        models.Top3.user_id    == user.id,
        models.Top3.entry_date == date,
    ).first()


@router.post("/top3", response_model=schemas.Top3Out)
def upsert_top3(body: schemas.Top3In, user=Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(models.Top3).filter(
        models.Top3.user_id    == user.id,
        models.Top3.entry_date == body.entry_date,
    ).first()
    if existing:
        existing.p1 = body.p1 or ""
        existing.p2 = body.p2 or ""
        existing.p3 = body.p3 or ""
        db.commit(); db.refresh(existing)
        return existing
    t = models.Top3(user_id=user.id, **body.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t
