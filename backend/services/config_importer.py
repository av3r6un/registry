import logging
import re
from dataclasses import dataclass
from datetime import datetime as dt
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.functions.normalization import normalize_payload
from backend.models import Domain, DomainCertificate, DomainDeployment, DomainRoute, DomainServerName
from backend.models.certificates import CertificateStatus
from backend.models.deployments import DeploymentStatus
from backend.models.domains import DomainStatus, DomainType


logger = logging.getLogger(__name__)


@dataclass
class ImportedConfig:
  payload: dict[str, Any]
  config_text: str
  filename: str
  available_path: str
  enabled_path: str
  ssl_enabled: bool = False
  cert_name: str | None = None


class NginxConfigImporter:
  def __init__(self, settings) -> None:
    self.settings = settings

  async def import_current_configs(self, session: AsyncSession) -> dict[str, int]:
    stats = dict(imported=0, updated=0, skipped=0, errors=0)
    for config in self.parse_current_configs():
      try:
        action = await self.upsert_config(session, config)
        stats[action] += 1
      except Exception:
        stats['errors'] += 1
        logger.exception('Failed to import nginx config: %s', config.enabled_path)
    await session.commit()
    return stats

  def parse_current_configs(self) -> list[ImportedConfig]:
    return [
      *self.parse_http_configs(),
      *self.parse_stream_configs(),
    ]

  def parse_http_configs(self) -> list[ImportedConfig]:
    return self.parse_files(
      self.config_files(getattr(self.settings, 'NGINX_SITES_ENABLED', '')),
      self.parse_http_file,
    )

  def parse_stream_configs(self) -> list[ImportedConfig]:
    return self.parse_files(
      self.config_files(getattr(self.settings, 'NGINX_STREAMS_ENABLED', '')),
      self.parse_stream_file,
    )

  def config_files(self, directory: str) -> list[Path]:
    if not directory:
      return []
    path = Path(directory)
    if not path.exists() or not path.is_dir():
      logger.info('Nginx config import skipped missing directory: %s', path)
      return []
    return sorted(a for a in path.iterdir() if a.is_file() and a.suffix == '.conf')

  def parse_files(self, paths: list[Path], parser) -> list[ImportedConfig]:
    configs = []
    for path in paths:
      try:
        configs.extend(parser(path))
      except Exception:
        logger.exception('Failed to parse nginx config: %s', path)
    return configs

  def parse_http_file(self, path: Path) -> list[ImportedConfig]:
    text = path.read_text(encoding='utf-8')
    blocks = self.server_blocks(text)
    proxy_block = next((block for block in blocks if self.directive(block, 'proxy_pass')), None)
    if not proxy_block:
      return []

    proxy_pass = self.directive(proxy_block, 'proxy_pass')
    match = re.match(r'(?P<scheme>https?)://(?P<host>[^:/\s;]+):(?P<port>\d+)', proxy_pass or '')
    if not match:
      logger.info('Nginx HTTP config import skipped unsupported proxy_pass in %s', path)
      return []

    server_names = self.server_names(proxy_block)
    if not server_names:
      for block in blocks:
        server_names = self.server_names(block)
        if server_names:
          break
    if not server_names:
      logger.info('Nginx HTTP config import skipped missing server_name in %s', path)
      return []

    ssl_block = next((block for block in blocks if self.block_has_ssl(block)), None)
    cert_name = self.cert_name(ssl_block) if ssl_block else None
    payload = dict(
      type=DomainType.HOSTNAME.value,
      name=server_names[0],
      server_names=server_names,
      upstream_scheme=match.group('scheme'),
      upstream_host=match.group('host'),
      upstream_port=int(match.group('port')),
    )
    return [ImportedConfig(
      payload=normalize_payload(payload),
      config_text=text,
      filename=path.name,
      available_path=self.available_path('http', path.name),
      enabled_path=str(path),
      ssl_enabled=bool(ssl_block),
      cert_name=cert_name,
    )]

  def parse_stream_file(self, path: Path) -> list[ImportedConfig]:
    text = path.read_text(encoding='utf-8')
    imports = []
    for block in self.server_blocks(text):
      listen = self.directive(block, 'listen')
      proxy_pass = self.directive(block, 'proxy_pass')
      if not listen or not proxy_pass:
        continue

      listen_match = re.match(r'(?P<port>\d+)(?:\s+(?P<protocol>udp))?$', listen)
      proxy_match = re.match(r'(?P<host>[^:/\s;]+):(?P<port>\d+)$', proxy_pass)
      if not listen_match or not proxy_match:
        logger.info('Nginx stream config import skipped unsupported block in %s', path)
        continue

      payload = dict(
        type=DomainType.PORT_PROXY.value,
        name=path.stem,
        listen_port=int(listen_match.group('port')),
        stream_protocol=listen_match.group('protocol') or 'tcp',
        upstream_host=proxy_match.group('host'),
        upstream_port=int(proxy_match.group('port')),
      )
      imports.append(ImportedConfig(
        payload=normalize_payload(payload),
        config_text=text,
        filename=path.name,
        available_path=self.available_path('stream', path.name),
        enabled_path=str(path),
      ))
    return imports

  async def upsert_config(self, session: AsyncSession, config: ImportedConfig) -> str:
    payload = config.payload
    domain_data = payload['domain']
    route_data = payload['route']
    domain = await Domain.first(session, name=domain_data['name'])
    deployment = self.build_deployment(config)

    if not domain:
      domain = Domain(**domain_data)
      domain.enabled = True
      domain.status = DomainStatus.ACTIVE
      domain.route = DomainRoute(**route_data)
      domain.server_names = [DomainServerName(**a) for a in payload['server_names']]
      domain.deployments = [deployment]
      if config.ssl_enabled:
        domain.certificates = [self.build_certificate(config, domain_data['name'])]
      session.add(domain)
      return 'imported'

    changed = False
    for key, value in domain_data.items():
      if key in ('enabled', 'status'):
        continue
      if getattr(domain, key) != value:
        setattr(domain, key, value)
        changed = True
    if not domain.enabled or domain.status != DomainStatus.ACTIVE:
      domain.enabled = True
      domain.status = DomainStatus.ACTIVE
      changed = True

    if domain.route:
      for key, value in route_data.items():
        if getattr(domain.route, key) != value:
          setattr(domain.route, key, value)
          changed = True
    else:
      domain.route = DomainRoute(**route_data)
      changed = True

    names = [a['name'] for a in payload['server_names']]
    if [a.name for a in domain.server_names] != names:
      domain.server_names = [DomainServerName(**a) for a in payload['server_names']]
      changed = True

    latest = max(domain.deployments, key=lambda a: a.created) if domain.deployments else None
    if not latest or latest.config_text != config.config_text:
      domain.deployments.append(deployment)
      changed = True

    if config.ssl_enabled and not domain.certificates:
      domain.certificates = [self.build_certificate(config, domain.name)]
      changed = True

    return 'updated' if changed else 'skipped'

  def build_deployment(self, config: ImportedConfig) -> DomainDeployment:
    return DomainDeployment(
      status=DeploymentStatus.APPLIED,
      nginx_filename=config.filename,
      sites_available_path=config.available_path,
      sites_enabled_path=config.enabled_path,
      config_text=config.config_text,
      applied_at=dt.utcnow(),
    )

  def build_certificate(self, config: ImportedConfig, domain_name: str) -> DomainCertificate:
    cert_name = config.cert_name or domain_name
    return DomainCertificate(
      provider='certbot',
      cert_name=cert_name,
      status=CertificateStatus.ACTIVE,
      issued_at=dt.utcnow(),
      fullchain_path=f'{self.settings.LETSENCRYPT_DIR}/live/{cert_name}/fullchain.pem',
      private_key_path=f'{self.settings.LETSENCRYPT_DIR}/live/{cert_name}/privkey.pem',
    )

  def available_path(self, config_type: str, filename: str) -> str:
    setting = 'NGINX_STREAMS_AVAILABLE' if config_type == 'stream' else 'NGINX_SITES_AVAILABLE'
    return str(Path(getattr(self.settings, setting)) / filename)

  def server_blocks(self, text: str) -> list[str]:
    sanitized = self.strip_comments(text)
    blocks = []
    for match in re.finditer(r'\bserver\s*\{', sanitized):
      start = match.end()
      depth = 1
      index = start
      while index < len(sanitized) and depth:
        if sanitized[index] == '{':
          depth += 1
        elif sanitized[index] == '}':
          depth -= 1
        index += 1
      if depth == 0:
        blocks.append(sanitized[start:index - 1])
    return blocks

  def directive(self, block: str, name: str) -> str | None:
    match = re.search(rf'^\s*{re.escape(name)}\s+([^;]+);', block, flags=re.MULTILINE)
    return match.group(1).strip() if match else None

  def server_names(self, block: str) -> list[str]:
    value = self.directive(block, 'server_name')
    return value.split() if value else []

  def block_has_ssl(self, block: str) -> bool:
    return bool(re.search(r'^\s*listen\s+[^;]*\bssl\b[^;]*;', block, flags=re.MULTILINE))

  def cert_name(self, block: str | None) -> str | None:
    if not block:
      return None
    cert = self.directive(block, 'ssl_certificate')
    match = re.search(r'/live/([^/]+)/fullchain\.pem$', cert or '')
    return match.group(1) if match else None

  def strip_comments(self, text: str) -> str:
    return re.sub(r'#.*$', '', text, flags=re.MULTILINE)
