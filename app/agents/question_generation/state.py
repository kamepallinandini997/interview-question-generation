from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    candidate_id: str
    interview_type: str
    target_position: str
    interview_id: str
    payload: dict[str, Any]
    generation_prompt: str
    proposed_questions: list[dict[str, Any]]
    generated_questions: list[dict[str, Any]]
    metadata: dict[str, Any]
    deduplication: dict[str, Any]
    errors: list[str]
