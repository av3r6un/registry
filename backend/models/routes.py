from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum, ForeignKey, Integer, String
from .base import Base
import enum


class UpstreamScheme(enum.Enum):
  HTTP = 'http'
  HTTPS = 'https'
  STREAM = 'stream'

class StreamProtocol(enum.Enum):
  TCP = 'tcp'
  UDP = 'udp'


class DomainRoute(Base):
  __tablename__ = 'domain_routes'

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  domain_id: Mapped[int] = mapped_column(ForeignKey('domains.id', ondelete='CASCADE'), nullable=False, unique=True)
  upstream_host: Mapped[str] = mapped_column(String(255), nullable=False)
  upstream_port: Mapped[int] = mapped_column(Integer, nullable=False)
  upstream_scheme: Mapped[UpstreamScheme] = mapped_column(Enum(UpstreamScheme, native_enum=False), nullable=False, default=UpstreamScheme.HTTP)

  listen_port: Mapped[int | None] = mapped_column(Integer)
  stream_protocol: Mapped[StreamProtocol] = mapped_column(Enum(StreamProtocol, native_enum=False), nullable=False, default=StreamProtocol.TCP)
  
  domain: Mapped["Domain"] = relationship(back_populates='route') # type: ignore


  @property
  def json(self):
    return dict(
      id=self.id, domain_id=self.domain_id, upstream_host=self.upstream_host, upstream_port=self.upstream_port,
      upstream_scheme=self.upstream_scheme.value, listen_port=self.listen_port, stream_protocol=self.stream_protocol.value
    )
