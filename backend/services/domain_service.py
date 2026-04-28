from datetime import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession
from backend.config.config import Settings
from backend.functions.normalization import normalize_payload
from backend.models import Domain, DomainCertificate, DomainDeployment, DomainRoute, DomainServerName
from backend.models.certificates import CertificateStatus
from backend.models.deployments import DeploymentStatus
from backend.models.domains import DomainStatus, DomainType
from .nginx import Nginx
from typing import Any


class DomainNotFound(Exception):
  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args)


class DomainService:
  def __init__(self,) -> None:
    self.nginx = Nginx()
    self.settings = Settings()
  
  async def find(self, session, **kwargs) -> Domain:
    domain = await Domain.first(session, **kwargs)
    if not domain: raise DomainNotFound()
    return domain
  
  async def all(self, session, **kwargs) -> dict[str, Any]:
    return await Domain.get_json(session, **kwargs)
  
  async def create_domain(self, session: AsyncSession, data: dict[str, Any]) -> dict:
    payload = normalize_payload(data)
    domain = Domain(**payload['domain'])
    domain.route = DomainRoute(**payload['route'])
    domain.server_names = [DomainServerName(**a) for a in payload['server_names']]
    domain.certificates = []
    domain.deployments = [self.build_deployment(payload)]
    session.add(domain)
    await session.commit()
    return domain.json
  
  async def update_domain(self, session: AsyncSession, data: dict[str, Any]) -> dict:
    domain = await self.find(session, id=data.get('id'))
    payload = normalize_payload(data, existing=domain.json)
    for k, v in payload['domain'].items():
      setattr(domain, k, v)
    if domain.route:
      for k, v in payload['route'].items():
        setattr(domain.route, k, v)
    else:
      domain.route = DomainRoute(**payload['route'])
    domain.server_names = [DomainServerName(**a) for a in payload['server_names']]
    domain.deployments.append(self.build_deployment(payload))
    await session.commit()
    return domain.json
  
  async def apply_domain(self, session: AsyncSession, domain_id: int, **kwargs) -> dict:
    domain = await self.find(session, id=domain_id)
    deployment = self.latest_deployment(domain)
    if not deployment:
      deployment = self.build_deployment(self.payload_from_domain(domain))
      domain.deployments.append(deployment)

    result = await self.nginx.apply_deployment(deployment, self.settings)
    if not result['success']:
      deployment.status = DeploymentStatus.ERROR
      deployment.last_error = result['stderr'] or result['stdout'] or 'nginx_apply_failed'
      domain.enabled = False
      domain.status = DomainStatus.ERROR
      await session.commit()
      raise RuntimeError(deployment.last_error)

    deployment.status = DeploymentStatus.APPLIED
    deployment.applied_at = dt.utcnow()
    deployment.last_error = None
    domain.enabled = True
    domain.status = DomainStatus.ACTIVE
    await session.commit()
    return domain.json
  
  async def issue_certificate(self, session: AsyncSession, domain_id: int) -> dict:
    domain = await self.find(session, id=domain_id)
    if domain.type != DomainType.HOSTNAME:
      raise ValueError('ssl_only_supported_for_hostname')

    cert = DomainCertificate(
      provider='certbot',
      cert_name=domain.name,
      status=CertificateStatus.PENDING,
      last_renewal_attempt_at=dt.utcnow(),
    )
    domain.certificates.append(cert)

    challenge_deployment = self.build_deployment(self.payload_from_domain(domain), ssl_enabled=False)
    domain.deployments.append(challenge_deployment)
    await session.commit()

    challenge_result = await self.nginx.apply_deployment(challenge_deployment, self.settings)
    if not challenge_result['success']:
      error = challenge_result['stderr'] or challenge_result['stdout'] or 'nginx_challenge_apply_failed'
      cert.status = CertificateStatus.ERROR
      cert.last_error = error
      challenge_deployment.status = DeploymentStatus.ERROR
      challenge_deployment.last_error = error
      domain.status = DomainStatus.ERROR
      await session.commit()
      raise RuntimeError(error)

    challenge_deployment.status = DeploymentStatus.APPLIED
    challenge_deployment.applied_at = dt.utcnow()
    challenge_deployment.last_error = None
    await session.commit()

    cert_result = await self.nginx.issue_certificate(domain.name, self.domain_server_names(domain), self.settings)
    if not cert_result['success']:
      error = cert_result['stderr'] or cert_result['stdout'] or 'certbot_failed'
      cert.status = CertificateStatus.ERROR
      cert.last_error = error
      domain.status = DomainStatus.ERROR
      await session.commit()
      raise RuntimeError(error)

    ssl_deployment = self.build_deployment(self.payload_from_domain(domain), ssl_enabled=True)
    domain.deployments.append(ssl_deployment)
    await session.commit()

    ssl_result = await self.nginx.apply_deployment(ssl_deployment, self.settings)
    if not ssl_result['success']:
      error = ssl_result['stderr'] or ssl_result['stdout'] or 'nginx_ssl_apply_failed'
      cert.status = CertificateStatus.ERROR
      cert.last_error = error
      ssl_deployment.status = DeploymentStatus.ERROR
      ssl_deployment.last_error = error
      domain.status = DomainStatus.ERROR
      await session.commit()
      raise RuntimeError(error)

    cert.status = CertificateStatus.ACTIVE
    cert.issued_at = dt.utcnow()
    cert.fullchain_path = f'{self.settings.LETSENCRYPT_DIR}/live/{domain.name}/fullchain.pem'
    cert.private_key_path = f'{self.settings.LETSENCRYPT_DIR}/live/{domain.name}/privkey.pem'
    cert.last_error = None
    ssl_deployment.status = DeploymentStatus.APPLIED
    ssl_deployment.applied_at = dt.utcnow()
    ssl_deployment.last_error = None
    domain.enabled = True
    domain.status = DomainStatus.ACTIVE
    await session.commit()
    return domain.json
  
  async def disable_domain(self, session: AsyncSession, domain_id: int) -> dict:
    domain = await self.find(session, id=domain_id)
    result = await self.nginx.disable_deployment(self.latest_deployment(domain), self.settings)
    if result and not result['success']:
      raise RuntimeError(result['stderr'] or result['stdout'] or 'nginx_reload_failed')
    domain.enabled = False
    domain.status = DomainStatus.DISABLED
    await session.commit()
    return domain.json
  
  async def delete(self, session: AsyncSession, domain_id: int) -> dict:
    domain = await self.find(session, id=domain_id)
    data = domain.json
    result = await self.nginx.delete_deployment(self.latest_deployment(domain), self.settings)
    if result and not result['success']:
      raise RuntimeError(result['stderr'] or result['stdout'] or 'nginx_reload_failed')
    await session.delete(domain)
    await session.commit()
    return data

  def build_deployment(self, payload: dict[str, Any], ssl_enabled: bool = False) -> DomainDeployment:
    kwargs = self.render_kwargs(payload, ssl_enabled)
    filename = self.domain_to_filename(kwargs['name'])
    available, enabled = self.nginx_paths(kwargs['type'], filename)
    return DomainDeployment(
      status=DeploymentStatus.DRAFT,
      nginx_filename=filename,
      sites_available_path=available,
      sites_enabled_path=enabled,
      config_text=self.nginx.render_config(**kwargs),
    )

  def render_kwargs(self, payload: dict[str, Any], ssl_enabled: bool = False) -> dict[str, Any]:
    domain, route = payload['domain'], payload['route']
    return dict(
      **domain,
      **route,
      server_names=payload.get('server_names', []),
      ssl_enabled=ssl_enabled,
      cert_name=domain['name'],
      certbot_webroot=self.settings.CERTBOT_WEBROOT,
      letsencrypt_dir=self.settings.LETSENCRYPT_DIR,
    )

  def payload_from_domain(self, domain: Domain) -> dict[str, Any]:
    return dict(
      domain=dict(name=domain.name, type=domain.type, enabled=domain.enabled, status=domain.status),
      server_names=[a.json for a in domain.server_names],
      route=domain.route.json,
      certificates=[],
      deployments=[],
    )

  def latest_deployment(self, domain: Domain) -> DomainDeployment | None:
    if not domain.deployments:
      return None
    return max(domain.deployments, key=lambda a: a.created)

  def domain_server_names(self, domain: Domain) -> list[str]:
    names = [a.name for a in domain.server_names]
    if domain.name not in names:
      names.insert(0, domain.name)
    return names

  def domain_to_filename(self, name: str) -> str:
    safe = ''.join(ch for ch in name.lower() if ch.isalnum() or ch in '.-')
    return f'{safe}.conf'

  def nginx_paths(self, domain_type: DomainType, filename: str) -> tuple[str, str]:
    if domain_type == DomainType.PORT_PROXY:
      return (
        f'{self.settings.NGINX_STREAMS_AVAILABLE}/{filename}',
        f'{self.settings.NGINX_STREAMS_ENABLED}/{filename}',
      )
    return (
      f'{self.settings.NGINX_SITES_AVAILABLE}/{filename}',
      f'{self.settings.NGINX_SITES_ENABLED}/{filename}',
    )
