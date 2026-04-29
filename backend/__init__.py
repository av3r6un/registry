from aiohttp.web import FileResponse, HTTPNotFound, Application, Request, json_response, run_app
from dotenv import load_dotenv
from .utils import middlewares
from .config import Settings
from asyncio import Lock
from pathlib import Path
import logging
import sys
import os

if sys.platform == 'win32':
  load_dotenv('.env')

settings = Settings()

LOG_FILENAME = 'logs/all.log' if sys.platform == 'win32' else '/var/log/registry/all.log'
async def db_ctx(app: Application):
  from .utils.engine import session_maker, dispose
  from .services.config_importer import NginxConfigImporter
  app['db_sessionmaker'] = session_maker
  async with session_maker() as session:
    stats = await NginxConfigImporter(settings).import_current_configs(session)
    logging.info('Nginx config import completed: %s', stats)
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
  setup_static_routes(app)
  return app

def setup_static_routes(app: Application) -> None:
  static_dir = os.getenv('STATIC_DIR')
  if not static_dir:
    return

  root = Path(static_dir).resolve()
  index = root / 'index.html'
  if not index.is_file():
    logging.warning('STATIC_DIR is set but index.html was not found: %s', root)
    return

  app['static_dir'] = root
  app.router.add_get('/{tail:.*}', serve_frontend)

async def serve_frontend(req: Request):
  if req.path == '/api' or req.path.startswith('/api/'):
    return json_response(dict(status='error', message='Request page not found!'), status=404)

  root: Path = req.app['static_dir']
  index = root / 'index.html'
  tail = req.match_info.get('tail', '').strip('/')
  target = (root / tail).resolve() if tail else index

  if not is_relative_to(target, root):
    raise HTTPNotFound()
  if target.is_file():
    return FileResponse(target)
  if target.suffix:
    raise HTTPNotFound()
  return FileResponse(index)

def is_relative_to(path: Path, root: Path) -> bool:
  return path == root or root in path.parents

def start():
  run_app(
    create_app(),
    host='0.0.0.0',
    port=int(os.getenv('APP_PORT', '8090')),
    access_log_format='%{X-Forwarded-For}i %s - "%r" (%b | %D) %{User-Agent}i',
  )
