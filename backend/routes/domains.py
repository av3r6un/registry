from aiohttp.web import RouteTableDef, Request, json_response
from backend.services import DomainService, DomainNotFound
from sqlalchemy.ext.asyncio import AsyncSession

domains = RouteTableDef()
domain_service = DomainService()

@domains.get('/api/domains')
async def index(req: Request, session: AsyncSession):
  domains = await domain_service.all(session)
  return json_response(dict(status='success', body=domains))


@domains.get('/api/domains/{id}')
async def get_domain(req: Request, session: AsyncSession):
  domain_id = req.match_info.get('id')
  try:
    domain = await domain_service.find(session, **dict(id=domain_id))
    return json_response(dict(status='success', body=domain.json))
  except DomainNotFound:
    return json_response(dict(status='error', message=f'Domain[{domain_id}] not found!'), status=404)
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)


@domains.post('/api/domains')
async def create_domain(req: Request, session: AsyncSession):
  data = (await req.json())
  print(data)
  try:
    row = await domain_service.create_domain(session, data)
    return json_response(dict(status='success', body=row), status=201)
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)


@domains.put('/api/domains/{id}')
async def update_domain(req: Request, session: AsyncSession):
  data = (await req.json())
  data['id'] = req.match_info.get('id')
  try:
    row = await domain_service.update_domain(session, data)
    return json_response(dict(status='success', body=row))
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)


@domains.post('/api/domains/{id}/apply')
async def apply_domain(req: Request, session: AsyncSession):
  domain_id = req.match_info.get('id')
  try:
    row = await domain_service.apply_domain(session, domain_id)
    return json_response(dict(status='success', body=row))
  
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)


@domains.post('/api/domains/{id}/certificate')
async def issue_certificate(req: Request, session: AsyncSession):
  domain_id = req.match_info.get('id')
  try:
    row = await domain_service.issue_certificate(session, domain_id)
    return json_response(dict(status='success', body=row))
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)


@domains.post('/api/domains/{id}/disable')
async def disable_domain(req: Request, session: AsyncSession):
  domain_id = req.match_info.get('id')
  try:
    row = await domain_service.disable_domain(session, domain_id)
    return json_response(dict(status='success', body=row))
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)

  
@domains.delete('/api/domains/{id}')
async def delete_domain(req: Request, session: AsyncSession):
  domain_id = req.match_info.get('id')
  try:
    row = await domain_service.delete(session, domain_id)
    return json_response(dict(status='success', message='Successfully deleted!', body=row))
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=400)
  
