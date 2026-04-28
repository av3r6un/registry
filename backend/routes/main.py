from aiohttp.web import RouteTableDef, Request, json_response

main = RouteTableDef()

@main.get('/health')
async def check_health(req: Request):
  return json_response(dict(status='success', message='Healthy'))
