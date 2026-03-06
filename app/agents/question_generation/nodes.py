from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.question_generation.prompts import build_generation_prompt, load_role_template
from app.agents.question_generation.state import AgentState
from app.agents.question_generation.validators import (
    validate_deduplication_output,
    validate_generated_questions,
    validate_generation_payload,
    validate_state_for_node,
)
from app.core.config import settings
from app.core.exceptions import AppException, DeduplicationError, GenerationError, NodeExecutionError
from app.database.models import InterviewRun, QuestionHistory
from app.utils.hashing import hash_question, normalize_text
from app.utils.similarity import semantic_similarity


def initialize_state(payload: dict) -> AgentState:
    try:
        validate_generation_payload(payload)
    except Exception as exc:
        if isinstance(exc, AppException):
            raise
        raise GenerationError(
            "Failed in initialize_state",
            {"node": "initialize_state", "reason": str(exc)},
        ) from exc

    interview_type = payload["interview_type"]
    target_position = payload["target_position"]
    generated_id = f"INT-{uuid4().hex[:8].upper()}"

    if interview_type == "L1_SCREENING" and not payload.get("job_requirements"):
        payload["job_requirements"] = load_role_template(target_position)

    state: AgentState = {
        "candidate_id": payload["candidate_id"],
        "interview_type": interview_type,
        "target_position": target_position,
        "interview_id": generated_id,
        "payload": payload,
        "generation_prompt": build_generation_prompt(payload),
        "proposed_questions": [],
        "generated_questions": [],
        "metadata": {},
        "deduplication": {},
        "errors": [],
    }
    return state


def _default_question_config(payload: dict) -> dict:
    config = payload.get("question_config", {})
    return {
        "total_questions": int(config.get("total_questions", settings.DEFAULT_TOTAL_QUESTIONS)),
        "difficulty": config.get("difficulty", "MID_SENIOR"),
        "include_behavioral": bool(config.get("include_behavioral", True)),
        "include_technical": bool(config.get("include_technical", True)),
        "include_experience_verification": bool(config.get("include_experience_verification", True)),
    }


def _expand_experience_items(payload: dict) -> list[dict]:
    items: list[dict] = []
    for row in payload.get("experience_highlights", []):
        company = row.get("company", "Unknown Company")
        role = row.get("role", "Unknown Role")
        responsibilities = row.get("key_responsibilities", []) or []
        technologies = row.get("technologies_used", []) or []
        for responsibility in responsibilities:
            items.append(
                {
                    "company": company,
                    "role": role,
                    "responsibility": responsibility,
                    "technologies": technologies,
                }
            )
    return items


def _skill_items(payload: dict) -> list[dict]:
    return payload.get("skill_profile", []) or []


def _mk_question(
    q_id: int,
    category: str,
    question: str,
    targets_skill: str,
    difficulty: str,
    targets_experience: str = "",
    follow_up_questions: list[str] | None = None,
) -> dict:
    return {
        "q_id": f"Q-{q_id:03d}",
        "category": category,
        "question": question,
        "targets_skill": targets_skill,
        "targets_experience": targets_experience,
        "difficulty": difficulty,
        "expected_answer_points": [
            "Concrete examples from production work",
            "Design trade-offs and reasoning",
            "Failure handling / edge-case considerations",
        ],
        "follow_up_questions": follow_up_questions or [],
        "time_estimate_mins": 4,
    }


def _generate_base_questions(payload: dict) -> list[dict]:
    config = _default_question_config(payload)
    difficulty = config["difficulty"]
    total_questions = config["total_questions"]
    candidate_profile = payload.get("candidate_profile", {})
    candidate_name = candidate_profile.get("name", "Candidate")
    experience_items = _expand_experience_items(payload)
    skills = _skill_items(payload)

    if not skills and not experience_items:
        raise GenerationError("Insufficient profile data to generate personalized questions")

    rng_seed_input = f"{payload.get('candidate_id')}|{payload.get('target_position')}|{datetime.now(timezone.utc).date()}"
    rng = random.Random(hash(rng_seed_input))

    technical_pool: list[dict] = []
    behavioral_pool: list[dict] = []
    experience_pool: list[dict] = []
    q_index = 1

    for skill in skills:
        skill_name = skill.get("skill", "General Engineering")
        technical_pool.append(
            _mk_question(
                q_id=q_index,
                category="TECHNICAL",
                question=(
                    f"{candidate_name}, explain an advanced concept in {skill_name} you used in production. "
                    "What trade-offs did you make and why?"
                ),
                targets_skill=skill_name,
                difficulty=difficulty,
            )
        )
        q_index += 1

    for item in experience_items:
        responsibility = item["responsibility"]
        company = item["company"]
        tech_text = ", ".join(item["technologies"][:3]) if item["technologies"] else "your stack"

        experience_pool.append(
            _mk_question(
                q_id=q_index,
                category="EXPERIENCE_VERIFICATION",
                question=(
                    f"In {company}, you mentioned '{responsibility}'. Walk through your exact implementation approach, "
                    f"including architecture and measurable outcomes using {tech_text}."
                ),
                targets_skill="Experience Validation",
                targets_experience=f"{company} - {item['role']}",
                difficulty=difficulty,
                follow_up_questions=[
                    "What bottlenecks did you face and how did you resolve them?",
                    "What would you redesign now?",
                ],
            )
        )
        q_index += 1

    if config["include_behavioral"]:
        behavioral_pool.extend(
            [
                _mk_question(
                    q_id=q_index,
                    category="BEHAVIORAL",
                    question=(
                        "Describe a disagreement with your team on a technical decision. "
                        "How did you drive alignment and what was the final outcome?"
                    ),
                    targets_skill="Team Collaboration",
                    difficulty="MID",
                ),
                _mk_question(
                    q_id=q_index + 1,
                    category="BEHAVIORAL",
                    question=(
                        "Share a high-pressure production incident you handled. "
                        "How did you prioritize, communicate, and stabilize systems?"
                    ),
                    targets_skill="Ownership",
                    difficulty="MID",
                ),
            ]
        )
        q_index += 2

    rng.shuffle(technical_pool)
    rng.shuffle(experience_pool)
    rng.shuffle(behavioral_pool)

    required_categories = []
    if config["include_technical"]:
        required_categories.append(("TECHNICAL", technical_pool))
    if config["include_experience_verification"]:
        required_categories.append(("EXPERIENCE_VERIFICATION", experience_pool))
    if config["include_behavioral"]:
        required_categories.append(("BEHAVIORAL", behavioral_pool))

    selected: list[dict] = []
    for _, category_pool in required_categories:
        if not category_pool:
            continue
        selected.append(category_pool.pop(0))

    merged_pool = technical_pool + experience_pool + behavioral_pool
    rng.shuffle(merged_pool)
    while len(selected) < total_questions and merged_pool:
        selected.append(merged_pool.pop(0))

    if len(selected) < total_questions:
        for _ in range(total_questions - len(selected)):
            selected.append(
                _mk_question(
                    q_id=q_index,
                    category="TECHNICAL",
                    question=(
                        f"For the role {payload.get('target_position')}, describe a production-quality API design "
                        "you would propose and justify your key decisions."
                    ),
                    targets_skill="System Design",
                    difficulty=difficulty,
                )
            )
            q_index += 1

    for idx, question in enumerate(selected, start=1):
        question["q_id"] = f"Q-{idx:03d}"

    return selected[:total_questions]


async def generate_questions_node(state: AgentState) -> AgentState:
    try:
        validate_state_for_node(state, "generate_questions_node", ["payload", "candidate_id", "interview_id"])
        payload = state["payload"]
        proposed_questions = _generate_base_questions(payload)
        validate_generated_questions(proposed_questions)
        state["proposed_questions"] = proposed_questions
        return state
    except Exception as exc:
        if isinstance(exc, (GenerationError, DeduplicationError)):
            raise
        raise NodeExecutionError(
            "Question generation node failed",
            {"node": "generate_questions_node", "reason": str(exc)},
        ) from exc


async def deduplicate_questions_node(state: AgentState, db: AsyncSession) -> AgentState:
    try:
        validate_state_for_node(
            state,
            "deduplicate_questions_node",
            ["payload", "candidate_id", "interview_id", "interview_type", "proposed_questions"],
        )
        payload = state["payload"]
        candidate_id = state["candidate_id"]
        interview_id = state["interview_id"]
        interview_type = state["interview_type"]
        threshold = settings.DEFAULT_SIMILARITY_THRESHOLD
        lookback_date = datetime.utcnow() - timedelta(days=settings.QUESTION_LOOKBACK_DAYS)

        recent_stmt = (
            select(QuestionHistory)
            .where(QuestionHistory.created_at >= lookback_date)
            .order_by(desc(QuestionHistory.created_at))
        )
        recent_rows = (await db.execute(recent_stmt)).scalars().all()

        selected: list[dict] = []
        skipped = 0
        for item in state["proposed_questions"]:
            question_text = item["question"]
            q_hash = hash_question(question_text)

            exact_duplicate = any(history.question_hash == q_hash for history in recent_rows)
            if exact_duplicate:
                skipped += 1
                continue

            max_similarity = 0.0
            for history in recent_rows:
                score = semantic_similarity(question_text, history.question_text)
                if score > max_similarity:
                    max_similarity = score
                if score >= threshold:
                    break
            if max_similarity >= threshold:
                skipped += 1
                continue

            selected.append(item)
            recent_rows.append(
                QuestionHistory(
                    interview_id=interview_id,
                    candidate_id=candidate_id,
                    interview_type=interview_type,
                    category=item["category"],
                    targets_skill=item.get("targets_skill", ""),
                    question_hash=q_hash,
                    question_text=question_text,
                    normalized_text=normalize_text(question_text),
                    similarity_score=max_similarity,
                    is_unique=True,
                )
            )

        requested_total = int(payload.get("question_config", {}).get("total_questions", settings.DEFAULT_TOTAL_QUESTIONS))
        if len(selected) < requested_total:
            raise DeduplicationError(
                "Unable to produce enough unique questions after deduplication",
                {
                    "requested_total": requested_total,
                    "generated_unique": len(selected),
                    "skipped_due_to_duplicates": skipped,
                },
            )

        selected = selected[:requested_total]
        for idx, question in enumerate(selected, start=1):
            question["q_id"] = f"Q-{idx:03d}"

        state["generated_questions"] = selected
        state["deduplication"] = {
            "checked_against_history": True,
            "similar_questions_found": skipped,
            "unique_questions_generated": True,
            "question_hashes_stored": True,
        }
        validate_deduplication_output(state, requested_total)
        return state
    except Exception as exc:
        if isinstance(exc, DeduplicationError):
            raise
        raise NodeExecutionError(
            "Deduplication node failed",
            {"node": "deduplicate_questions_node", "reason": str(exc)},
        ) from exc


async def persist_results_node(state: AgentState, db: AsyncSession) -> AgentState:
    try:
        validate_state_for_node(
            state,
            "persist_results_node",
            ["interview_id", "candidate_id", "interview_type", "target_position", "generated_questions"],
        )
        interview_run = InterviewRun(
            interview_id=state["interview_id"],
            candidate_id=state["candidate_id"],
            interview_type=state["interview_type"],
            target_position=state["target_position"],
            total_questions=len(state["generated_questions"]),
        )
        db.add(interview_run)

        for item in state["generated_questions"]:
            q_text = item["question"]
            db.add(
                QuestionHistory(
                    interview_id=state["interview_id"],
                    candidate_id=state["candidate_id"],
                    interview_type=state["interview_type"],
                    category=item["category"],
                    targets_skill=item.get("targets_skill", ""),
                    question_hash=hash_question(q_text),
                    question_text=q_text,
                    normalized_text=normalize_text(q_text),
                    similarity_score=0.0,
                    is_unique=True,
                )
            )

        await db.commit()
        return state
    except Exception as exc:
        raise NodeExecutionError(
            "Persist results node failed",
            {"node": "persist_results_node", "reason": str(exc)},
        ) from exc


def build_response(state: AgentState) -> dict:
    validate_state_for_node(state, "build_response", ["interview_id", "candidate_id", "generated_questions", "deduplication"])
    technical_count = len([q for q in state["generated_questions"] if q["category"] == "TECHNICAL"])
    behavioral_count = len([q for q in state["generated_questions"] if q["category"] == "BEHAVIORAL"])
    experience_count = len([q for q in state["generated_questions"] if q["category"] == "EXPERIENCE_VERIFICATION"])

    return {
        "interview_id": state["interview_id"],
        "candidate_id": state["candidate_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "questions": state["generated_questions"],
        "question_metadata": {
            "total_generated": len(state["generated_questions"]),
            "technical_questions": technical_count,
            "behavioral_questions": behavioral_count,
            "experience_verification": experience_count,
            "estimated_interview_duration_mins": len(state["generated_questions"]) * 4,
        },
        "deduplication_check": state["deduplication"],
    }
