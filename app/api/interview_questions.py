from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.services.question_service import generate_questions


router = APIRouter()


class CandidateProfile(BaseModel):
    name: str
    total_experience_years: int = 0
    current_title: str = ""


class ExperienceHighlight(BaseModel):
    company: str
    role: str
    duration_months: int = 0
    key_responsibilities: list[str] = Field(default_factory=list)
    technologies_used: list[str] = Field(default_factory=list)


class SkillProfileItem(BaseModel):
    skill: str
    proficiency: str = "Intermediate"
    years: int = 0


class QuestionConfig(BaseModel):
    total_questions: int = Field(default=12, ge=10, le=15)
    difficulty: str = "MID_SENIOR"
    include_behavioral: bool = True
    include_technical: bool = True
    include_experience_verification: bool = True


class GenerateQuestionsRequest(BaseModel):
    candidate_id: str
    interview_type: Literal["L1_SCREENING", "JOB_SPECIFIC"]
    target_position: str
    candidate_profile: CandidateProfile
    experience_highlights: list[ExperienceHighlight] = Field(default_factory=list)
    skill_profile: list[SkillProfileItem] = Field(default_factory=list)
    job_requirements: dict[str, Any] = Field(default_factory=dict)
    question_config: QuestionConfig = Field(default_factory=QuestionConfig)


class GenerateQuestionsResponse(BaseModel):
    interview_id: str
    candidate_id: str
    generated_at: datetime
    questions: list[dict[str, Any]]
    question_metadata: dict[str, Any]
    deduplication_check: dict[str, Any]


@router.post("/interview/questions")
async def generate(
    candidate_data: GenerateQuestionsRequest,
    db: AsyncSession = Depends(get_db_session),
) -> GenerateQuestionsResponse:
    result = await generate_questions(candidate_data.model_dump(), db)
    return result


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
