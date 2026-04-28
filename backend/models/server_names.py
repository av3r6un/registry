from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class DomainServerName(Base):
  __tablename__ = 'domain_server_names'
  __table_args__ = (
    UniqueConstraint('domain_id', 'name', name='uq_domain_server_names_domain_name'),
    Index('ix_domain_server_names_name', 'name'),
  )

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  domain_id: Mapped[int] = mapped_column(ForeignKey('domains.id', ondelete='CASCADE'), nullable=False)
  name: Mapped[str] = mapped_column(String(255), nullable=False)
  is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

  domain: Mapped["Domain"] = relationship(back_populates='server_names') # type: ignore

  @property
  def json(self):
    return dict(id=self.id, domain_id=self.domain_id, name=self.name, is_primary=self.is_primary)
