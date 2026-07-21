"""
models.py — ORM table definitions
Each class maps to one SQLite table.
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Float,
    Date, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False)
    email        = Column(String(200), unique=True, index=True, nullable=False)
    hashed_pw    = Column(String(200), nullable=True)   # null for Google-only accounts
    created_at   = Column(DateTime, default=datetime.utcnow)

    is_verified      = Column(Boolean, default=False, nullable=False)
    otp_hash         = Column(String(200), nullable=True)
    otp_expires_at   = Column(DateTime, nullable=True)
    otp_sent_at      = Column(DateTime, nullable=True)   # for resend cooldown

    # relationships
    goals        = relationship("Goal",    back_populates="user", cascade="all, delete")
    tasks        = relationship("Task",    back_populates="user", cascade="all, delete")
    habits       = relationship("Habit",   back_populates="user", cascade="all, delete")
    habit_logs   = relationship("HabitLog",back_populates="user", cascade="all, delete")
    journals     = relationship("Journal", back_populates="user", cascade="all, delete")
    targets      = relationship("Target",  back_populates="user", cascade="all, delete")
    top3s        = relationship("Top3",    back_populates="user", cascade="all, delete")


class Goal(Base):
    __tablename__ = "goals"

    id           = Column(String(36), primary_key=True)   # uid string
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    name         = Column(String(200), nullable=False)
    description  = Column(Text, default="")
    start_date   = Column(String(10))   # YYYY-MM-DD
    end_date     = Column(String(10))
    priority     = Column(String(10), default="med")
    emoji        = Column(String(10),  default="🎯")
    created_at   = Column(DateTime, default=datetime.utcnow)

    user         = relationship("User",      back_populates="goals")
    milestones   = relationship("Milestone", back_populates="goal", cascade="all, delete",
                                order_by="Milestone.created_at")


class Milestone(Base):
    __tablename__ = "milestones"

    id           = Column(String(36), primary_key=True)
    goal_id      = Column(String(36), ForeignKey("goals.id"), nullable=False)
    name         = Column(String(200), nullable=False)
    weight       = Column(Float,  default=0)
    deadline     = Column(String(10))
    celebrated   = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    goal         = relationship("Goal", back_populates="milestones")
    tasks        = relationship("Task", back_populates="milestone")


class Task(Base):
    __tablename__ = "tasks"

    id           = Column(String(36), primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_date    = Column(String(10), nullable=False, index=True)   # YYYY-MM-DD
    name         = Column(String(500), nullable=False)
    done         = Column(Boolean, default=False)
    priority     = Column(String(10), default="med")
    deadline     = Column(String(10))
    est_time     = Column(Float, default=0)
    notes        = Column(Text, default="")
    goal_id      = Column(String(36), ForeignKey("goals.id"), nullable=True)
    milestone_id = Column(String(36), ForeignKey("milestones.id"), nullable=True)
    sort_order   = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)

    user         = relationship("User",      back_populates="tasks")
    goal         = relationship("Goal")
    milestone    = relationship("Milestone", back_populates="tasks")


class Habit(Base):
    __tablename__ = "habits"

    id           = Column(String(36), primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    name         = Column(String(200), nullable=False)
    icon         = Column(String(10),  default="⭐")
    category     = Column(String(100), default="Custom")
    created_at   = Column(DateTime, default=datetime.utcnow)

    user         = relationship("User",     back_populates="habits")
    logs         = relationship("HabitLog", back_populates="habit", cascade="all, delete")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    habit_id     = Column(String(36), ForeignKey("habits.id"), nullable=False)
    user_id      = Column(Integer,    ForeignKey("users.id"),  nullable=False)
    log_date     = Column(String(10), nullable=False, index=True)
    done         = Column(Boolean, default=False)

    habit        = relationship("Habit", back_populates="logs")
    user         = relationship("User",  back_populates="habit_logs")


class Journal(Base):
    __tablename__ = "journals"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_date   = Column(String(10), nullable=False, index=True)
    thoughts     = Column(Text, default="")
    ideas        = Column(Text, default="")
    mood         = Column(String(10), default="")
    saved_at     = Column(DateTime, default=datetime.utcnow)

    user         = relationship("User", back_populates="journals")


class Target(Base):
    __tablename__ = "targets"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_date  = Column(String(10), nullable=False, index=True)
    study        = Column(Float, default=0)
    workout      = Column(Float, default=0)
    reading      = Column(Float, default=0)
    water        = Column(Float, default=0)
    sleep        = Column(Float, default=0)
    mood         = Column(Float, default=0)
    energy       = Column(Float, default=0)

    user         = relationship("User", back_populates="targets")


class Top3(Base):
    __tablename__ = "top3"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_date   = Column(String(10), nullable=False, index=True)
    p1           = Column(String(500), default="")
    p2           = Column(String(500), default="")
    p3           = Column(String(500), default="")

    user         = relationship("User", back_populates="top3s")
