from __future__ import annotations

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
import enum


class DomainType(enum.Enum):
  HOSTNAME = 'hostname'
  PORT_PROXY = 'port_proxy'

class DomainStatus(enum.Enum):
  DRAFT = 'draft'
  ACTIVE = 'active'
  DISABLED = 'disabled'
  ERROR = 'error'

class Domain(Base):
  __tablename__ = 'domains'

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
  type: Mapped[DomainType] = mapped_column(Enum(DomainType, native_enum=False), nullable=False, default=DomainType.HOSTNAME)
  enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  status: Mapped[DomainStatus] = mapped_column(Enum(DomainStatus, native_enum=False), nullable=False, default=DomainStatus.DRAFT)

  server_names: Mapped[list[DomainServerName]] = relationship(back_populates='domain', cascade='all, delete-orphan') # type: ignore
  route: Mapped[DomainRoute | None] = relationship(back_populates='domain', cascade='all, delete-orphan', uselist=False) # type: ignore
  certificates: Mapped[list[DomainCertificate]] = relationship(back_populates='domain', cascade='all, delete-orphan') # type: ignore
  deployments: Mapped[list[DomainDeployment]] = relationship(back_populates='domain', cascade='all, delete-orphan') # type: ignore

  @property
  def json(self):
    return dict(
      id=self.id, name=self.name, type=self.type.value, enabled=self.enabled, status=self.status.value,
      server_names=[a.name for a in self.server_names],
      route=self.route.json if self.route else None,
      certificates=[a.json for a in self.certificates],
      deployments=[a.json for a in self.deployments]
    )
  
  async def set_state(self, session, state) -> None:
    self.status = DomainStatus(state)
    await session.commit()
  