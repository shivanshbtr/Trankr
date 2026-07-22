"""
schemas.py — Pydantic models for request validation and response serialization
"""
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str
    email:    EmailStr
    password: str

class RegisterResponse(BaseModel):
    message: str
    email:   str

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp:   str

class ResendOTPRequest(BaseModel):
    email: EmailStr

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    credential: str   # the ID token returned by Google Identity Services

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    name:         str


# ─── Goals & Milestones ──────────────────────────────────────────────────────

class MilestoneIn(BaseModel):
    id:          Optional[str] = None
    name:        str
    weight:      float
    deadline:    Optional[str] = None
    celebrated:  Optional[bool] = False

class MilestoneOut(MilestoneIn):
    id:          str
    goal_id:     str

    class Config:
        from_attributes = True

class GoalIn(BaseModel):
    id:          Optional[str] = None
    name:        str
    description: Optional[str] = ""
    start_date:  Optional[str] = None
    end_date:    Optional[str] = None
    priority:    Optional[str] = "med"
    emoji:       Optional[str] = "🎯"

class GoalOut(GoalIn):
    id:          str
    user_id:     int
    milestones:  List[MilestoneOut] = []

    class Config:
        from_attributes = True


# ─── Tasks ───────────────────────────────────────────────────────────────────

class TaskIn(BaseModel):
    id:           Optional[str] = None
    task_date:    str
    name:         str
    done:         Optional[bool] = False
    priority:     Optional[str] = "med"
    deadline:     Optional[str] = None
    est_time:     Optional[float] = 0
    notes:        Optional[str] = ""
    goal_id:      Optional[str] = None
    milestone_id: Optional[str] = None
    milestone_contribution: Optional[float] = None
    sort_order:   Optional[int] = 0

class TaskOut(TaskIn):
    id:           str
    user_id:      int

    class Config:
        from_attributes = True

class TasksForDate(BaseModel):
    date:  str
    tasks: List[TaskOut]


# ─── Habits ──────────────────────────────────────────────────────────────────

class HabitIn(BaseModel):
    id:       Optional[str] = None
    name:     str
    icon:     Optional[str] = "⭐"
    category: Optional[str] = "Custom"

class HabitOut(HabitIn):
    id:       str
    user_id:  int

    class Config:
        from_attributes = True

class HabitLogIn(BaseModel):
    habit_id: str
    log_date: str
    done:     bool

class HabitLogOut(HabitLogIn):
    id:       int
    user_id:  int

    class Config:
        from_attributes = True


# ─── Journal ─────────────────────────────────────────────────────────────────

class JournalIn(BaseModel):
    entry_date: str
    thoughts:   Optional[str] = ""
    ideas:      Optional[str] = ""
    mood:       Optional[str] = ""

class JournalOut(JournalIn):
    id:         int
    user_id:    int

    class Config:
        from_attributes = True


# ─── Targets ─────────────────────────────────────────────────────────────────

class TargetIn(BaseModel):
    target_date: str
    study:       Optional[float] = 0
    workout:     Optional[float] = 0
    reading:     Optional[float] = 0
    water:       Optional[float] = 0
    sleep:       Optional[float] = 0
    mood:        Optional[float] = 0
    energy:      Optional[float] = 0

class TargetOut(TargetIn):
    id:          int
    user_id:     int

    class Config:
        from_attributes = True


# ─── Top 3 ───────────────────────────────────────────────────────────────────

class Top3In(BaseModel):
    entry_date: str
    p1: Optional[str] = ""
    p2: Optional[str] = ""
    p3: Optional[str] = ""

class Top3Out(Top3In):
    id:      int
    user_id: int

    class Config:
        from_attributes = True
