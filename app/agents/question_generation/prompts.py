from __future__ import annotations

from typing import Any


GENERIC_ROLE_TEMPLATES: dict[str, dict[str, list[str] | str]] = {
    "Senior Python Developer": {
        "required_skills": ["Python", "REST API Design", "SQL"],
        "nice_to_have": ["Docker", "AWS", "Microservices"],
        "focus_areas": ["Backend Development", "System Design"],
    },
    "Backend Engineer": {
        "required_skills": ["Python", "API Development", "Databases"],
        "nice_to_have": ["Distributed Systems", "Cloud", "Docker"],
        "focus_areas": ["Backend Development", "Reliability"],
    },
}


def load_role_template(target_role: str) -> dict[str, Any]:
    template = GENERIC_ROLE_TEMPLATES.get(target_role)
    if template:
        return {
            "source": "GENERIC_ROLE_TEMPLATE",
            "target_role": target_role,
            **template,
        }
    return {
        "source": "GENERIC_ROLE_TEMPLATE",
        "target_role": target_role,
        "required_skills": [],
        "nice_to_have": [],
        "focus_areas": [],
    }


def build_generation_prompt(payload: dict[str, Any]) -> str:
    candidate_profile = payload.get("candidate_profile", {})
    skills = payload.get("skill_profile", [])
    experience = payload.get("experience_highlights", [])
    requirements = payload.get("job_requirements", {})
    config = payload.get("question_config", {})

    return (
        "Generate personalized interview questions.\n"
        f"Candidate: {candidate_profile}\n"
        f"Skills: {skills}\n"
        f"Experience: {experience}\n"
        f"Requirements: {requirements}\n"
        f"Question config: {config}\n"
        "Constraints:\n"
        "- Questions must verify claimed skills and real project experience.\n"
        "- Include technical, behavioral, and experience verification categories.\n"
        "- Difficulty should match role seniority.\n"
        "- Provide expected answer points for each question.\n"
    )
