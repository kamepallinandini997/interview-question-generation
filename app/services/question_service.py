from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.question_generation.workflow import build_workflow


async def generate_questions(payload: dict, db: AsyncSession) -> dict:
    workflow = build_workflow(db)
    result = await workflow.ainvoke(payload)
    return result
