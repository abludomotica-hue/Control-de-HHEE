from sqlalchemy import Column, String, Date, Time, DateTime, Boolean, Enum, create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()

class EstadoEnum(str, enum.Enum):
    EJECUTADO = "Ejecutado"
    PENDIENTE = "Pendiente"

class Trabajo(Base):
    __tablename__ = "trabajos"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fecha_inicio = Column(Date, nullable=False, index=True)
    tarea_numero = Column(String(50), nullable=False, index=True)
    cliente_nombre = Column(String(200), nullable=False, index=True)
    estado = Column(String(20), nullable=False, index=True)  # Ejecutado | Pendiente
    categoria = Column(String(200), nullable=True)
    hora_inicio = Column(Time, nullable=True)
    hora_finalizada = Column(Time, nullable=True)
    empleado_objetivo = Column(String(200), nullable=False, default="MSI Z08SO Team 3 1 Abrahan Rondon (ECC)")
    fuente_archivo_nombre = Column(String(500), nullable=False)
    fuente_archivo_tipo = Column(String(50), nullable=False)
    fuente_archivo_hash = Column(String(64), nullable=False)
    incompleto = Column(Boolean, default=False)
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_dedup', 'fuente_archivo_hash', 'tarea_numero', 'fecha_inicio', 'empleado_objetivo', unique=True),
    )
