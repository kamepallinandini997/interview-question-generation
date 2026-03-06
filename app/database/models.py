from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func

from app.database.base import Base


class InterviewRun(Base):
    __tablename__ = "interview_runs"

    interview_id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
        default=lambda: f"INT-{uuid4().hex[:8].upper()}",
    )
    candidate_id: Mapped[str] = mapped_column(String(80), index=True)
    interview_type: Mapped[str] = mapped_column(String(40), index=True)
    target_position: Mapped[str] = mapped_column(String(120))
    total_questions: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionHistory(Base):
    __tablename__ = "question_history"
    __table_args__ = (
        Index("ix_qh_candidate_created", "candidate_id", "created_at"),
        Index("ix_qh_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id: Mapped[str] = mapped_column(String(40), index=True)
    candidate_id: Mapped[str] = mapped_column(String(80), index=True)
    interview_type: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(40))
    targets_skill: Mapped[str] = mapped_column(String(120), default="")
    question_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    question_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    similarity_score: Mapped[float] = mapped_column(default=0.0)
    is_unique: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
