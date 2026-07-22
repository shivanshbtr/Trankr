"""
routes/tasks.py — CRUD for daily tasks
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models, schemas

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _uid(): return str(uuid.uuid4())


@router.get("/", response_model=List[schemas.TaskOut])
def get_tasks(
    date:  Optional[str] = Query(None, description="YYYY-MM-DD — returns tasks for that date"),
    user   = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(models.Task).filter(models.Task.user_id == user.id)
    if date:
        q = q.filter(models.Task.task_date == date)
    return q.order_by(models.Task.sort_order, models.Task.created_at).all()


@router.post("/", response_model=schemas.TaskOut)
def create_task(body: schemas.TaskIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    task = models.Task(
        id           = body.id or _uid(),
        user_id      = user.id,
        task_date    = body.task_date,
        name         = body.name,
        done         = body.done or False,
        priority     = body.priority or "med",
        deadline     = body.deadline,
        est_time     = body.est_time or 0,
        notes        = body.notes or "",
        goal_id      = body.goal_id or None,
        milestone_id = body.milestone_id or None,
        milestone_contribution = body.milestone_contribution,
        sort_order   = body.sort_order or 0,
    )
    db.add(task); db.commit(); db.refresh(task)
    return task


@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: str, body: schemas.TaskIn,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(
        models.Task.id == task_id, models.Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.name         = body.name
    task.done         = body.done
    task.priority     = body.priority or "med"
    task.deadline     = body.deadline
    task.est_time     = body.est_time or 0
    task.notes        = body.notes or ""
    task.goal_id      = body.goal_id or None
    task.milestone_id = body.milestone_id or None
    task.milestone_contribution = body.milestone_contribution
    task.sort_order   = body.sort_order or 0
    db.commit(); db.refresh(task)
    return task


@router.patch("/{task_id}/toggle", response_model=schemas.TaskOut)
def toggle_task(task_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle done/undone — called on checkbox click for minimal payload."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id, models.Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.done = not task.done
    db.commit(); db.refresh(task)
    return task


@router.patch("/reorder")
def reorder_tasks(
    task_ids: List[str],
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept ordered list of task IDs and update sort_order."""
    for idx, task_id in enumerate(task_ids):
        db.query(models.Task).filter(
            models.Task.id == task_id,
            models.Task.user_id == user.id
        ).update({"sort_order": idx})
    db.commit()
    return {"ok": True}


@router.delete("/{task_id}")
def delete_task(task_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(
        models.Task.id == task_id, models.Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task); db.commit()
    return {"ok": True}
