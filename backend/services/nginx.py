import asyncio
import logging
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os

from mako.template import Template


logger = logging.getLogger(__name__)


class Nginx:
  def __init__(self) -> None:
    self.templates_dir = Path(__file__).resolve().parents[1] / 'templates'

  def render_config(self, **kwargs) -> str:
    proxy_type = kwargs.get('type', kwargs.get('proxy_type', 'hostname'))
    if self._value(proxy_type) in ('port_proxy', 'stream'):
      return self.render_stream_config(**kwargs)
    return self.render_http_config(**kwargs)

  def render_http_config(self, **kwargs) -> str:
    name = kwargs.get('name', kwargs.get('domain'))
    server_names = kwargs.get('server_names') or [name]
    return self._render(
      'nginx_http_config.mako',
      server_names=self._server_names(server_names),
      upstream_host=kwargs['upstream_host'],
      upstream_port=kwargs['upstream_port'],
      upstream_scheme=self._value(kwargs.get('upstream_scheme', kwargs.get('scheme', 'http'))),
      ssl_enabled=bool(kwargs.get('ssl_enabled', False)),
      cert_name=kwargs.get('cert_name', name),
      certbot_webroot=self._path(kwargs.get('certbot_webroot', '/var/www/certbot')),
      letsencrypt_dir=self._path(kwargs.get('letsencrypt_dir', '/etc/letsencrypt')),
      client_max_body_size=kwargs.get('client_max_body_size', '50m'),
    )

  def render_stream_config(self, **kwargs) -> str:
    return self._render(
      'nginx_stream_config.mako',
      listen_port=kwargs['listen_port'],
      stream_protocol=self._value(kwargs.get('stream_protocol', 'tcp')),
      upstream_host=kwargs['upstream_host'],
      upstream_port=kwargs['upstream_port'],
      proxy_connect_timeout=kwargs.get('proxy_connect_timeout', '10s'),
      proxy_timeout=kwargs.get('proxy_timeout', '1h'),
    )

  def _render(self, template: str, **kwargs) -> str:
    text = Template(filename=str(self.templates_dir / template)).render(**kwargs)
    return text.strip() + '\n'

  def _server_names(self, value: Any) -> list[str]:
    if isinstance(value, str):
      return [a for a in value.replace(',', ' ').split() if a]
    return [self._server_name(a) for a in value]

  def _server_name(self, value: Any) -> str:
    if isinstance(value, dict):
      return str(value['name'])
    if hasattr(value, 'name'):
      return str(value.name)
    return str(value)

  def _value(self, value: Any) -> Any:
    return value.value if hasattr(value, 'value') else value

  def _path(self, value: Any) -> str:
    return str(value).replace('\\', '/')

  async def apply_deployment(self, deployment, settings) -> dict[str, Any]:
    available_path = Path(deployment.sites_available_path)
    enabled_path = Path(deployment.sites_enabled_path)
    backup_dir = self.backup_dir(settings)

    available_backup = self.write_config_atomic(available_path, deployment.config_text, backup_dir)
    enabled_backup = self.enable_site(available_path, enabled_path, backup_dir)

    test_result = await self.test(settings)
    if not test_result['success']:
      self.rollback(available_path, enabled_path, available_backup, enabled_backup)
      return test_result

    reload_result = await self.reload(settings)
    if reload_result and not reload_result['success']:
      self.rollback(available_path, enabled_path, available_backup, enabled_backup)
      return reload_result

    return reload_result or test_result

  async def disable_deployment(self, deployment, settings) -> dict[str, Any] | None:
    if not deployment:
      return None
    self.disable_site(Path(deployment.sites_enabled_path))
    return await self.reload(settings)

  async def delete_deployment(self, deployment, settings) -> dict[str, Any] | None:
    if not deployment:
      return None
    self.disable_site(Path(deployment.sites_enabled_path))
    self.remove_site_file(Path(deployment.sites_available_path))
    return await self.reload(settings)

  async def issue_certificate(self, domain_name: str, server_names: list[str], settings) -> dict[str, Any]:
    self.prepare_certbot_dirs(settings)
    args = [
      os.getenv('CERTBOT_BIN', '/usr/bin/certbot'),
      'certonly',
      '--webroot',
      '-w',
      str(getattr(settings, 'CERTBOT_WEBROOT', '/var/www/certbot')),
      '--non-interactive',
      '--agree-tos',
      '--config-dir',
      str(getattr(settings, 'LETSENCRYPT_DIR', '/etc/letsencrypt')),
      '--work-dir',
      str(getattr(settings, 'CERTBOT_WORK_DIR', '/var/lib/letsencrypt')),
      '--logs-dir',
      str(getattr(settings, 'CERTBOT_LOGS_DIR', '/var/log/letsencrypt')),
      '--cert-name',
      domain_name,
    ]
    if getattr(settings, 'CERTBOT_STAGING', False):
      args.append('--staging')
    email = os.getenv('CERTBOT_EMAIL')
    if email:
      args.extend(['--email', email])
    else:
      args.append('--register-unsafely-without-email')
    for name in server_names:
      args.extend(['-d', name])
    return await self.run_command(*args)

  def prepare_certbot_dirs(self, settings) -> None:
    for key, default in (
      ('CERTBOT_WEBROOT', '/var/www/certbot'),
      ('LETSENCRYPT_DIR', '/etc/letsencrypt'),
      ('CERTBOT_WORK_DIR', '/var/lib/letsencrypt'),
      ('CERTBOT_LOGS_DIR', '/var/log/letsencrypt'),
    ):
      Path(getattr(settings, key, default)).mkdir(parents=True, exist_ok=True)

  def write_config_atomic(self, path: Path, content: str, backup_dir: Path) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    backup_path = self.build_backup_path(path, backup_dir) if path.exists() else None
    if backup_path:
      shutil.copy2(path, backup_path)
    tmp_path.write_text(content, encoding='utf-8')
    tmp_path.replace(path)
    return backup_path

  def enable_site(self, available_path: Path, enabled_path: Path, backup_dir: Path) -> Path | None:
    enabled_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = self.build_backup_path(enabled_path, backup_dir) if enabled_path.exists() or enabled_path.is_symlink() else None
    if backup_path:
      backup_dir.mkdir(parents=True, exist_ok=True)
      shutil.copy2(enabled_path, backup_path)
    shutil.copy2(available_path, enabled_path)
    return backup_path

  def disable_site(self, enabled_path: Path) -> bool:
    if enabled_path.exists() or enabled_path.is_symlink():
      enabled_path.unlink()
      return True
    return False

  def remove_site_file(self, path: Path) -> bool:
    if path.exists():
      path.unlink()
      return True
    return False

  def rollback(
    self,
    available_path: Path,
    enabled_path: Path,
    available_backup: Path | None,
    enabled_backup: Path | None,
  ) -> None:
    self.restore_backup(available_path, available_backup)
    self.restore_backup(enabled_path, enabled_backup)

  def restore_backup(self, path: Path, backup_path: Path | None) -> None:
    if backup_path and backup_path.exists():
      shutil.copy2(backup_path, path)
      return
    if path.exists():
      path.unlink()

  def build_backup_path(self, path: Path, backup_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return backup_dir / f'{path.name}.{stamp}.bak'

  async def test(self, settings) -> dict[str, Any]:
    return await self.run_config_command(settings, 'NGINX_TEST_COMMAND')

  async def reload(self, settings) -> dict[str, Any] | None:
    command = getattr(settings, 'NGINX_RELOAD_COMMAND', None)
    if not command:
      return None
    return await self.run_command(*self.command_args(command))

  async def run_config_command(self, settings, key: str) -> dict[str, Any]:
    command = getattr(settings, key)
    return await self.run_command(*self.command_args(command))

  async def run_command(self, *args: str) -> dict[str, Any]:
    logger.info('Running command: %s', ' '.join(args))
    process = await asyncio.create_subprocess_exec(
      *args,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return dict(
      success=process.returncode == 0,
      command=list(args),
      stdout=stdout.decode('utf-8', errors='replace').strip(),
      stderr=stderr.decode('utf-8', errors='replace').strip(),
      returncode=process.returncode,
    )

  def command_args(self, command: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(command, str):
      return shlex.split(command)
    return [str(a) for a in command]

  def backup_dir(self, settings) -> Path:
    return Path(getattr(settings, 'NGINX_BACKUP_DIR', 'backend/runtime/backups'))
