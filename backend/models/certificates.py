from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime as dt
from .base import Base
import enum


class CertificateStatus(enum.Enum):
  PENDING = 'pending'
  ACTIVE = 'active'
  EXPIRED = 'expired'
  REVOKED = 'revoked'
  ERROR = 'error'

class DomainCertificate(Base):
  __tablename__ = 'domain_certificates'
  __table_args__ = (
    Index('ix_domain_certificates_domain_status', 'domain_id', 'status'),
    Index('ix_domain_certificates_expires_at', 'expires_at'),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  domain_id: Mapped[int] = mapped_column(ForeignKey('domains.id', ondelete='CASCADE'), nullable=False)
  provider: Mapped[str] = mapped_column(String(64), nullable=False, default='certbot')
  cert_name: Mapped[str] = mapped_column(String(255), nullable=False)
  status: Mapped[CertificateStatus] = mapped_column(Enum(CertificateStatus, native_enum=False), nullable=False, default=CertificateStatus.PENDING)

  issued_at: Mapped[dt | None] = mapped_column(DateTime)
  expires_at: Mapped[dt | None] = mapped_column(DateTime)
  last_renewal_attempt_at: Mapped[dt | None] = mapped_column(DateTime)
  fullchain_path: Mapped[str | None] = mapped_column(Text)
  private_key_path: Mapped[str | None] = mapped_column(Text)
  last_error: Mapped[str | None] = mapped_column(Text)

  domain: Mapped["Domain"] = relationship(back_populates='certificates') # type: ignore

  @property
  def json(self):
    return dict(
      id=self.id, domain_id=self.domain_id, provider=self.provider, cert_name=self.cert_name, status=self.status.value,
      issued_at=self.issued_at.isoformat() if self.issued_at else None,
      expires_at=self.expires_at.isoformat() if self.expires_at else None,
      last_renewal_attempt_at=self.last_renewal_attempt_at.isoformat() if self.last_renewal_attempt_at else None,
      fullchain=self.fullchain_path, private_key=self.private_key_path, last_error=self.last_error
    )
