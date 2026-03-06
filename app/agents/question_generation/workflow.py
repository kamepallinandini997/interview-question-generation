from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.question_generation.nodes import (
    build_response,
    deduplicate_questions_node,
    generate_questions_node,
    initialize_state,
    persist_results_node,
)
from app.core.config import settings
from app.core.exceptions import AppException, DeduplicationError, WorkflowError


class QuestionGenerationWorkflow:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ainvoke(self, payload: dict) -> dict:
        last_error: Exception | None = None

        for _ in range(settings.MAX_REGEN_ATTEMPTS):
            try:
                state = initialize_state(payload)
                state = await generate_questions_node(state)
                state = await deduplicate_questions_node(state, self.db)
                state = await persist_results_node(state, self.db)
                return build_response(state)
            except DeduplicationError as exc:
                await self.db.rollback()
                last_error = exc
                continue
            except AppException:
                await self.db.rollback()
                raise
            except Exception as exc:
                await self.db.rollback()
                raise WorkflowError(
                    "Unexpected workflow failure",
                    {"step": "ainvoke", "reason": str(exc)},
                ) from exc

        if last_error:
            raise last_error
        raise DeduplicationError("Generation failed after retries")


def build_workflow(db: AsyncSession) -> QuestionGenerationWorkflow:
    return QuestionGenerationWorkflow(db)
