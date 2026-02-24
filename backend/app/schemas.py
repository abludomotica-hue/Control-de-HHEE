from pydantic import BaseModel, Field
from datetime import date, time, datetime
from typing import Optional
from enum import Enum

class EstadoEnum(str, Enum):
    EJECUTADO = "Ejecutado"
    PENDIENTE = "Pendiente"

class TrabajoBase(BaseModel):
    fecha_inicio: date
    tarea_numero: str
    cliente_nombre: str
    estado: EstadoEnum
    categoria: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_finalizada: Optional[time] = None
    empleado_objetivo: str = "MSI Z08SO Team 3 1 Abrahan Rondon (ECC)"
    incompleto: bool = False

class TrabajoCreate(TrabajoBase):
    fuente_archivo_nombre: str
    fuente_archivo_tipo: str
    fuente_archivo_hash: str

class TrabajoUpdate(BaseModel):
    fecha_inicio: Optional[date] = None
    tarea_numero: Optional[str] = None
    cliente_nombre: Optional[str] = None
    estado: Optional[EstadoEnum] = None
    categoria: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_finalizada: Optional[time] = None
    empleado_objetivo: Optional[str] = None
    incompleto: Optional[bool] = None

class TrabajoResponse(TrabajoBase):
    id: str
    fuente_archivo_nombre: str
    fuente_archivo_tipo: str
    fuente_archivo_hash: str
    creado_en: datetime
    actualizado_en: datetime
    
    class Config:
        from_attributes = True

class ExtraccionPreview(BaseModel):
    tarea_numero: Optional[str] = None
    fecha_inicio: Optional[date] = None
    cliente_nombre: Optional[str] = None
    estado: Optional[EstadoEnum] = None
    categoria: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_finalizada: Optional[time] = None
    empleado_objetivo: str = "MSI Z08SO Team 3 1 Abrahan Rondon (ECC)"
    fuente_archivo_nombre: str
    fuente_archivo_tipo: str
    fuente_archivo_hash: str
    incompleto: bool = True
    raw_text: Optional[str] = None
    extraccion_confiable: bool = False

class FiltroDashboard(BaseModel):
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    estado: Optional[EstadoEnum] = None
    cliente_nombre: Optional[str] = None
    categoria: Optional[str] = None
    tarea_numero: Optional[str] = None
    periodo: Optional[str] = None  # "dia", "semana", "mes"

class UploadResponse(BaseModel):
    success: bool
    preview: ExtraccionPreview
    message: str

class ConfirmacionResponse(BaseModel):
    success: bool
    trabajo: Optional[TrabajoResponse] = None
    message: str
    duplicado: bool = False
