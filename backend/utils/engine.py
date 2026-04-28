from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.models.base import Base
import os

db_url = os.getenv('DB_URL')

engine = create_async_engine(db_url, echo=False)

session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def dispose():
  await engine.dispose()
