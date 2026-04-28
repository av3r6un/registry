from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context

from backend.models.base import Base
from dotenv import load_dotenv
from backend.models import *
import sys
import os

config = context.config

if config.config_file_name is not None:
  fileConfig(config.config_file_name)

target_metadata = Base.metadata

if sys.platform == 'win32':
  load_dotenv('.env')
    
def get_env(name: str, default: str | None = None) -> str:
  value = os.getenv(name)
  if not value:
    if default is None:
      raise RuntimeError(f'Value {name} is missing')
    return default
  return value

config.set_main_option('sqlalchemy.url', get_env('DB_URL'))

def do_run_migrations(connection):
  context.configure(
    connection=connection,
    target_metadata=target_metadata,
    compare_type=True
  )
  with context.begin_transaction():
    context.run_migrations()
  
def run_migrations_offline() -> None:
  url = config.get_main_option("sqlalchemy.url")
  context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    compare_type=True,
    dialect_opts={"paramstyle": "named"},
  )

  with context.begin_transaction():
    context.run_migrations()

async def run_async_migrations():
  connectable = async_engine_from_config(
    config.get_section(config.config_ini_section),
    prefix='sqlalchemy.',
    poolclass=pool.NullPool,
  )
  async with connectable.connect() as connection:
    await connection.run_sync(do_run_migrations)

  await connectable.dispose()

def run_migrations_online() -> None:
  import asyncio
  asyncio.run(run_async_migrations())

if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()
