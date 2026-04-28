from aiohttp.web import run_app, Application
from dotenv import load_dotenv
from .utils import middlewares
from .config import Settings
from asyncio import Lock
import logging
import sys
import os

settings = Settings()

if sys.platform == 'win32':
  load_dotenv('.env')

LOG_FILENAME = 'logs/all.log' if sys.platform == 'win32' else '/var/log/registry/all.log'
async def db_ctx(app: Application):
  from .utils.engine import session_maker, dispose
  app['db_sessionmaker'] = session_maker
  yield
  await dispose()
  
def create_app():
  from .routes import rts
  app = Application(middlewares=middlewares)
  app['nginx_lock'] = Lock()
  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] WEB: %(message)s",
    datefmt="%Y-%d-%m %H:%M:%S",
    filename=LOG_FILENAME
  )
  app.add_routes(rts)
  app.cleanup_ctx.append(db_ctx)
  if os.getenv('DEBUG', False):
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S"))
    logging.getLogger().addHandler(console)
  return app

def start():
  run_app(
    create_app(),
    host='0.0.0.0',
    port=int(os.getenv('APP_PORT', '8090')),
    access_log_format='%{X-Forwarded-For}i %s - "%r" (%b | %D) %{User-Agent}i',
  )
