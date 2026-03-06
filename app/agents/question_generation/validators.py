from __future__ import annotations

from typing import Any

from app.core.exceptions import NodeValidationError, ValidationError


def validate_generation_payload(payload: dict[str, Any]) -> None:
    required_fields = ["candidate_id", "interview_type", "target_position", "candidate_profile"]
    missing = [field for field in required_fields if field not in payload or payload.get(field) in (None, "")]
    if missing:
        raise ValidationError("Missing required payload fields", {"missing_fields": missing})

    question_config = payload.get("question_config", {})
    total = question_config.get("total_questions", 12)
    if total < 10 or total > 15:
        raise ValidationError("question_config.total_questions must be between 10 and 15")


def _count_by_category(questions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "TECHNICAL": 0,
        "BEHAVIORAL": 0,
        "EXPERIENCE_VERIFICATION": 0,
    }
    for item in questions:
        category = str(item.get("category", "")).upper()
        if category in counts:
            counts[category] += 1
    return counts


def validate_generated_questions(questions: list[dict[str, Any]]) -> None:
    if not questions:
        raise ValidationError("No questions generated")

    for index, item in enumerate(questions, start=1):
        if not item.get("question"):
            raise ValidationError("Generated question is empty", {"question_index": index})

        answer_points = item.get("expected_answer_points", [])
        if len(answer_points) < 2:
            raise ValidationError(
                "Each question must include at least 2 expected answer points",
                {"question_index": index},
            )

    counts = _count_by_category(questions)
    if counts["TECHNICAL"] < 1 or counts["BEHAVIORAL"] < 1 or counts["EXPERIENCE_VERIFICATION"] < 1:
        raise ValidationError(
            "Minimum category distribution not met",
            {"counts": counts},
        )


def validate_state_for_node(state: dict[str, Any], node_name: str, required_keys: list[str]) -> None:
    missing = [key for key in required_keys if key not in state or state.get(key) in (None, "")]
    if missing:
        raise NodeValidationError(
            f"Invalid state before '{node_name}' node",
            {
                "node": node_name,
                "missing_keys": missing,
            },
        )


def validate_deduplication_output(state: dict[str, Any], requested_total: int) -> None:
    questions = state.get("generated_questions", [])
    if len(questions) < requested_total:
        raise NodeValidationError(
            "Deduplication output has fewer questions than requested",
            {
                "requested_total": requested_total,
                "generated_total": len(questions),
            },
        )
