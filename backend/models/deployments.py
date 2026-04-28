from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime as dt
from .base import Base
import enum


class DeploymentStatus(enum.Enum):
  DRAFT = 'draft'
  APPLIED = 'applied'
  ERROR = 'error'

class DomainDeployment(Base):
  __tablename__ = 'domain_deployments'
  __table_args__ = (Index('ix_domain_deployments_domain_status', 'domain_id', 'status'),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  domain_id: Mapped[int] = mapped_column(ForeignKey('domains.id', ondelete='CASCADE'), nullable=False)
  status: Mapped[DeploymentStatus] = mapped_column(Enum(DeploymentStatus, native_enum=False), nullable=False, default=DeploymentStatus.DRAFT)
  nginx_filename: Mapped[str] = mapped_column(String(255), nullable=False)
  sites_available_path: Mapped[str] = mapped_column(Text, nullable=False)
  sites_enabled_path: Mapped[str] = mapped_column(Text, nullable=False)
  config_text: Mapped[str] = mapped_column(Text, nullable=False)
  applied_at: Mapped[dt | None] = mapped_column(DateTime)
  last_error: Mapped[str | None] = mapped_column(Text)

  domain: Mapped["Domain"] = relationship(back_populates='deployments') # type: ignore

  @property
  def json(self):
    return dict(
      id=self.id, domain_id=self.domain_id, status=self.status.value, nginx_filename=self.nginx_filename,
      config_text=self.config_text,
      applied_at=self.applied_at.isoformat() if self.applied_at else None,
      last_error=self.last_error
    )
