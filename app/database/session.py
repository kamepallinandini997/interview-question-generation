from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database.connection import engine


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
