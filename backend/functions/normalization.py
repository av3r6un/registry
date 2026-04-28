from typing import Any
from backend.models.routes import UpstreamScheme, StreamProtocol 
from backend.models.domains import DomainStatus, DomainType 
import re


HOSTNAME_RE = re.compile(r'^(?=.{1,253}$)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)*[a-zA-Z0-9-]{1,63}$')


def normalize_payload(initial: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
  domain_type = normalize_domain_type(initial.get('type', initial.get('proxy_type', DomainType.HOSTNAME.value)))
  name = normalize_name(initial.get('name', initial.get('domain')), domain_type)
  route = normalize_route(initial, domain_type)
  server_names = normalize_server_names(initial.get('server_names'), name) if domain_type == DomainType.HOSTNAME else []

  return dict(
    domain=dict(
      name=name,
      type=domain_type,
      enabled=existing.get('enabled', False) if existing else False,
      status=normalize_enum(existing.get('status'), DomainStatus, DomainStatus.DRAFT) if existing else DomainStatus.DRAFT,
    ),
    server_names=server_names,
    route=route,
    certificates=[],
    deployments=[],
  )


def normalize_domain_type(value: Any) -> DomainType:
  if isinstance(value, DomainType):
    return value
  if value in ('hostname', 'http'):
    return DomainType.HOSTNAME
  if value in ('port_proxy', 'stream'):
    return DomainType.PORT_PROXY
  raise ValueError('invalid_domain_type')


def normalize_name(value: Any, domain_type: DomainType) -> str:
  if domain_type == DomainType.HOSTNAME:
    return normalize_hostname(value, 'invalid_domain')
  if not isinstance(value, str) or not value.strip():
    raise ValueError('invalid_name')
  name = value.strip().lower()
  if len(name) > 255:
    raise ValueError('invalid_name')
  return name


def normalize_route(initial: dict[str, Any], domain_type: DomainType) -> dict[str, Any]:
  scheme = normalize_enum(initial.get('upstream_scheme', initial.get('scheme')), UpstreamScheme, UpstreamScheme.HTTP)
  listen_port = initial.get('listen_port')
  stream_protocol = normalize_enum(initial.get('stream_protocol'), StreamProtocol, StreamProtocol.TCP)

  if domain_type == DomainType.PORT_PROXY:
    scheme = UpstreamScheme.STREAM
    listen_port = normalize_port(listen_port, 'invalid_listen_port')
  else:
    if scheme == UpstreamScheme.STREAM:
      raise ValueError('invalid_upstream_scheme')
    listen_port = None

  return dict(
    upstream_host=normalize_hostname(initial.get('upstream_host'), 'invalid_upstream_host'),
    upstream_port=normalize_port(initial.get('upstream_port'), 'invalid_upstream_port'),
    upstream_scheme=scheme,
    listen_port=listen_port,
    stream_protocol=stream_protocol,
  )


def normalize_server_names(value: Any, domain: str) -> list[dict[str, Any]]:
  if value is None:
    names = [domain]
  elif isinstance(value, str):
    names = [a.strip() for a in value.replace(',', ' ').split() if a.strip()]
  elif isinstance(value, list):
    names = [str(a).strip() for a in value if str(a).strip()]
  else:
    raise ValueError('invalid_server_names')

  names = [normalize_hostname(a, 'invalid_server_names') for a in names]
  if domain not in names:
    names.insert(0, domain)
  if len(names) != len(set(names)):
    raise ValueError('duplicate_server_names')
  return [dict(name=name, is_primary=i == 0) for i, name in enumerate(names)]


def normalize_hostname(value: Any, error: str) -> str:
  if not isinstance(value, str):
    raise ValueError(error)
  host = value.strip().lower()
  if not host or ' ' in host:
    raise ValueError(error)
  try:
    host = host.encode('idna').decode('ascii')
  except UnicodeError as exc:
    raise ValueError(error) from exc
  if not HOSTNAME_RE.match(host):
    raise ValueError(error)
  return host


def normalize_port(value: Any, error: str) -> int:
  if not isinstance(value, int) or not (1 <= value <= 65535):
    raise ValueError(error)
  return value


def normalize_enum(value: Any, enum_cls, default):
  if value is None:
    return default
  if isinstance(value, enum_cls):
    return value
  try:
    return enum_cls(value)
  except ValueError as exc:
    raise ValueError(f'invalid_{enum_cls.__name__.lower()}') from exc
