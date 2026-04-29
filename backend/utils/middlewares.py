from aiohttp.web import json_response, middleware, Request, HTTPUnauthorized
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from aiohttp.web_exceptions import HTTPNotFound
import base64
import binascii
import hmac
import os


def basic_auth_enabled() -> bool:
  value = os.getenv('BASIC_AUTH_ENABLED', '1').lower()
  return value not in ('0', 'false', 'no', 'off')


@middleware
async def basic_auth_middleware(req: Request, handler, *args, **kwargs):
  if not basic_auth_enabled():
    return await handler(req, *args, **kwargs)

  auth_user = os.getenv('BASIC_AUTH_USER', '')
  auth_pass = os.getenv('BASIC_AUTH_PASS', '')
  if not auth_user:
    return await handler(req, *args, **kwargs)

  header = req.headers.get('Authorization', '')
  if not header.startswith('Basic '):
    raise HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic realm="Registry"'})

  try:
    decoded = base64.b64decode(header.split(' ', 1)[1]).decode('utf-8')
  except (ValueError, UnicodeDecodeError, binascii.Error):
    raise HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic realm="Registry"'})

  user, _, password = decoded.partition(':')
  if not hmac.compare_digest(user, auth_user) or not hmac.compare_digest(password, auth_pass):
    raise HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic realm="Registry"'})

  return await handler(req, *args, **kwargs)

@middleware
async def db_middleware(req: Request, handler, *args, **kwargs):
  if req.path != '/api' and not req.path.startswith('/api/'):
    return await handler(req, *args, **kwargs)

  session_factory: async_sessionmaker[AsyncSession] = req.app['db_sessionmaker']
  async with session_factory() as session:
    try:
      req['session'] = session
      kwargs['session'] = session
      response = await handler(req, *args, **kwargs)
      if getattr(response, 'status', 200) >= 400:
        await session.rollback()
      else:
        await session.commit()
        
      return response
    except HTTPNotFound:
      await session.rollback()
      return json_response(dict(status='error', message='Request page not found!'), status=404)
    except Exception as e:
      await session.rollback()
      return json_response(dict(status='error', message=str(e)), status=400)

middlewares = [basic_auth_middleware, db_middleware]
