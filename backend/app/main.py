from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date, datetime, timedelta
from typing import Optional, List
import os
import io
import json
import pandas as pd
import uuid
import shutil

from app.database import init_db, get_db
from app.models import Trabajo
from app.schemas import (
    TrabajoCreate, TrabajoResponse, TrabajoUpdate, 
    ExtraccionPreview, FiltroDashboard, UploadResponse, ConfirmacionResponse
)
from app.pdf_parser import parsear_pdf
from app.ocr_parser import parsear_imagen

# Inicializar la app
app = FastAPI(
    title="Work Tracker API",
    description="API para control de trabajos por día, semana y mes",
    version="1.0.0"
)

# CORS para permitir requests del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorio para uploads
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Directorio del frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

# Servir archivos estáticos del frontend
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Extensiones permitidas
ALLOWED_PDF = {'.pdf'}
ALLOWED_IMAGES = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
ALLOWED_EXTENSIONS = ALLOWED_PDF | ALLOWED_IMAGES

@app.on_event("startup")
async def startup_event():
    """Inicializa la base de datos al arrancar"""
    init_db()

@app.get("/")
async def root():
    """Sirve el index.html del frontend"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Work Tracker API - Use /docs para la documentación"}

@app.get("/app.js")
async def app_js():
    """Sirve el app.js del frontend"""
    js_path = os.path.join(FRONTEND_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not found")

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Recibe un archivo PDF o imagen, extrae los datos y devuelve una previsualización.
    """
    # Validar extensión
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Extensión no permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Guardar archivo temporalmente
    temp_id = str(uuid.uuid4())
    temp_path = os.path.join(UPLOAD_DIR, f"{temp_id}{ext}")
    
    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Procesar según tipo de archivo
        if ext in ALLOWED_PDF:
            preview = parsear_pdf(temp_path, file.filename)
        else:
            preview = parsear_imagen(temp_path, file.filename)
        
        # Guardar archivo permanentemente con nombre basado en hash
        permanent_name = f"{preview.fuente_archivo_hash}{ext}"
        permanent_path = os.path.join(UPLOAD_DIR, permanent_name)
        
        # Si ya existe, eliminar el temporal
        if os.path.exists(permanent_path):
            os.remove(temp_path)
        else:
            # Usar copy+remove en lugar de rename por problemas de I/O en algunos sistemas
            shutil.copy2(temp_path, permanent_path)
            os.remove(temp_path)
        
        return UploadResponse(
            success=True,
            preview=preview,
            message="Archivo procesado correctamente. Revise la previsualización antes de confirmar."
        )
        
    except Exception as e:
        # Limpiar archivo temporal en caso de error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")

@app.post("/api/confirmar", response_model=ConfirmacionResponse)
async def confirmar_trabajo(
    trabajo: TrabajoCreate,
    db: Session = Depends(get_db)
):
    """
    Confirma y guarda un trabajo en la base de datos.
    Verifica duplicados antes de insertar.
    """
    # Verificar duplicado
    existente = db.query(Trabajo).filter(
        and_(
            Trabajo.fuente_archivo_hash == trabajo.fuente_archivo_hash,
            Trabajo.tarea_numero == trabajo.tarea_numero,
            Trabajo.fecha_inicio == trabajo.fecha_inicio,
            Trabajo.empleado_objetivo == trabajo.empleado_objetivo
        )
    ).first()
    
    if existente:
        return ConfirmacionResponse(
            success=False,
            message="Este trabajo ya existe en la base de datos.",
            duplicado=True
        )
    
    # Crear nuevo trabajo
    nuevo_trabajo = Trabajo(
        fecha_inicio=trabajo.fecha_inicio,
        tarea_numero=trabajo.tarea_numero,
        cliente_nombre=trabajo.cliente_nombre,
        estado=trabajo.estado.value if hasattr(trabajo.estado, 'value') else str(trabajo.estado),
        categoria=trabajo.categoria,
        hora_inicio=trabajo.hora_inicio,
        hora_finalizada=trabajo.hora_finalizada,
        empleado_objetivo=trabajo.empleado_objetivo,
        fuente_archivo_nombre=trabajo.fuente_archivo_nombre,
        fuente_archivo_tipo=trabajo.fuente_archivo_tipo,
        fuente_archivo_hash=trabajo.fuente_archivo_hash,
        incompleto=trabajo.incompleto
    )
    
    db.add(nuevo_trabajo)
    db.commit()
    db.refresh(nuevo_trabajo)
    
    return ConfirmacionResponse(
        success=True,
        trabajo=TrabajoResponse.from_orm(nuevo_trabajo),
        message="Trabajo guardado correctamente.",
        duplicado=False
    )

@app.get("/api/trabajos", response_model=List[TrabajoResponse])
async def listar_trabajos(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    cliente_nombre: Optional[str] = None,
    categoria: Optional[str] = None,
    tarea_numero: Optional[str] = None,
    periodo: Optional[str] = None,  # dia, semana, mes
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Lista trabajos con filtros opcionales.
    """
    query = db.query(Trabajo)
    
    # Aplicar filtros de fecha
    if fecha_desde:
        query = query.filter(Trabajo.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Trabajo.fecha_inicio <= fecha_hasta)
    
    # Filtro por período (sobrescribe fechas si se especifica)
    if periodo:
        hoy = date.today()
        if periodo == "dia":
            query = query.filter(Trabajo.fecha_inicio == hoy)
        elif periodo == "semana":
            # Semana actual (lunes a domingo)
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            fin_semana = inicio_semana + timedelta(days=6)
            query = query.filter(
                and_(
                    Trabajo.fecha_inicio >= inicio_semana,
                    Trabajo.fecha_inicio <= fin_semana
                )
            )
        elif periodo == "mes":
            # Mes actual
            inicio_mes = hoy.replace(day=1)
            if hoy.month == 12:
                fin_mes = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                fin_mes = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
            query = query.filter(
                and_(
                    Trabajo.fecha_inicio >= inicio_mes,
                    Trabajo.fecha_inicio <= fin_mes
                )
            )
    
    # Otros filtros
    if estado:
        query = query.filter(Trabajo.estado == estado)
    if cliente_nombre:
        query = query.filter(Trabajo.cliente_nombre.ilike(f"%{cliente_nombre}%"))
    if categoria:
        query = query.filter(Trabajo.categoria.ilike(f"%{categoria}%"))
    if tarea_numero:
        query = query.filter(Trabajo.tarea_numero.ilike(f"%{tarea_numero}%"))
    
    # Ordenar por fecha descendente
    query = query.order_by(Trabajo.fecha_inicio.desc())
    
    # Paginación
    trabajos = query.offset(skip).limit(limit).all()
    
    return [TrabajoResponse.model_validate(t) for t in trabajos]

@app.get("/api/trabajos/{trabajo_id}", response_model=TrabajoResponse)
async def obtener_trabajo(trabajo_id: str, db: Session = Depends(get_db)):
    """Obtiene un trabajo por su ID"""
    trabajo = db.query(Trabajo).filter(Trabajo.id == trabajo_id).first()
    if not trabajo:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return TrabajoResponse.model_validate(trabajo)

@app.put("/api/trabajos/{trabajo_id}", response_model=TrabajoResponse)
async def actualizar_trabajo(
    trabajo_id: str,
    datos: TrabajoUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza un trabajo existente"""
    trabajo = db.query(Trabajo).filter(Trabajo.id == trabajo_id).first()
    if not trabajo:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    # Actualizar campos
    for field, value in datos.dict(exclude_unset=True).items():
        setattr(trabajo, field, value)
    
    db.commit()
    db.refresh(trabajo)
    return TrabajoResponse.model_validate(trabajo)

@app.delete("/api/trabajos/{trabajo_id}")
async def eliminar_trabajo(trabajo_id: str, db: Session = Depends(get_db)):
    """Elimina un trabajo"""
    trabajo = db.query(Trabajo).filter(Trabajo.id == trabajo_id).first()
    if not trabajo:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    db.delete(trabajo)
    db.commit()
    return {"success": True, "message": "Trabajo eliminado correctamente"}

@app.get("/api/estadisticas")
async def obtener_estadisticas(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Obtiene estadísticas de trabajos"""
    query = db.query(Trabajo)
    
    if fecha_desde:
        query = query.filter(Trabajo.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Trabajo.fecha_inicio <= fecha_hasta)
    
    total = query.count()
    ejecutados = query.filter(Trabajo.estado == "Ejecutado").count()
    pendientes = query.filter(Trabajo.estado == "Pendiente").count()
    incompletos = query.filter(Trabajo.incompleto == True).count()
    
    # Por categoría
    categorias = db.query(
        Trabajo.categoria,
        func.count(Trabajo.id).label('count')
    ).group_by(Trabajo.categoria).all()
    
    return {
        "total": total,
        "ejecutados": ejecutados,
        "pendientes": pendientes,
        "incompletos": incompletos,
        "por_categoria": [{"categoria": c[0], "count": c[1]} for c in categorias if c[0]]
    }

@app.get("/api/export/csv")
async def exportar_csv(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    cliente_nombre: Optional[str] = None,
    categoria: Optional[str] = None,
    tarea_numero: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Exporta trabajos a CSV"""
    query = db.query(Trabajo)
    
    if fecha_desde:
        query = query.filter(Trabajo.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Trabajo.fecha_inicio <= fecha_hasta)
    if estado:
        query = query.filter(Trabajo.estado == estado)
    if cliente_nombre:
        query = query.filter(Trabajo.cliente_nombre.ilike(f"%{cliente_nombre}%"))
    if categoria:
        query = query.filter(Trabajo.categoria.ilike(f"%{categoria}%"))
    if tarea_numero:
        query = query.filter(Trabajo.tarea_numero.ilike(f"%{tarea_numero}%"))
    
    trabajos = query.all()
    
    # Crear DataFrame
    data = []
    for t in trabajos:
        data.append({
            'ID': t.id,
            'Fecha Inicio': t.fecha_inicio.strftime('%Y-%m-%d') if t.fecha_inicio else '',
            'Tarea Número': t.tarea_numero,
            'Cliente': t.cliente_nombre,
            'Estado': t.estado,
            'Categoría': t.categoria or '',
            'Hora Inicio': t.hora_inicio.strftime('%H:%M') if t.hora_inicio else '',
            'Hora Finalizada': t.hora_finalizada.strftime('%H:%M') if t.hora_finalizada else '',
            'Empleado': t.empleado_objetivo,
            'Incompleto': 'Sí' if t.incompleto else 'No',
            'Archivo Origen': t.fuente_archivo_nombre,
            'Creado': t.creado_en.strftime('%Y-%m-%d %H:%M') if t.creado_en else ''
        })
    
    df = pd.DataFrame(data)
    
    # Generar CSV en memoria
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trabajos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@app.get("/api/export/xlsx")
async def exportar_xlsx(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    cliente_nombre: Optional[str] = None,
    categoria: Optional[str] = None,
    tarea_numero: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Exporta trabajos a Excel (XLSX)"""
    query = db.query(Trabajo)
    
    if fecha_desde:
        query = query.filter(Trabajo.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Trabajo.fecha_inicio <= fecha_hasta)
    if estado:
        query = query.filter(Trabajo.estado == estado)
    if cliente_nombre:
        query = query.filter(Trabajo.cliente_nombre.ilike(f"%{cliente_nombre}%"))
    if categoria:
        query = query.filter(Trabajo.categoria.ilike(f"%{categoria}%"))
    if tarea_numero:
        query = query.filter(Trabajo.tarea_numero.ilike(f"%{tarea_numero}%"))
    
    trabajos = query.all()
    
    # Crear DataFrame
    data = []
    for t in trabajos:
        data.append({
            'ID': t.id,
            'Fecha Inicio': t.fecha_inicio,
            'Tarea Número': t.tarea_numero,
            'Cliente': t.cliente_nombre,
            'Estado': t.estado,
            'Categoría': t.categoria,
            'Hora Inicio': t.hora_inicio.strftime('%H:%M') if t.hora_inicio else '',
            'Hora Finalizada': t.hora_finalizada.strftime('%H:%M') if t.hora_finalizada else '',
            'Empleado': t.empleado_objetivo,
            'Incompleto': 'Sí' if t.incompleto else 'No',
            'Archivo Origen': t.fuente_archivo_nombre,
            'Creado': t.creado_en.strftime('%Y-%m-%d %H:%M') if t.creado_en else ''
        })
    
    df = pd.DataFrame(data)
    
    # Generar Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Trabajos')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=trabajos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
    )

@app.get("/api/export/json")
async def exportar_json(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    cliente_nombre: Optional[str] = None,
    categoria: Optional[str] = None,
    tarea_numero: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Exporta trabajos a JSON"""
    query = db.query(Trabajo)
    
    if fecha_desde:
        query = query.filter(Trabajo.fecha_inicio >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Trabajo.fecha_inicio <= fecha_hasta)
    if estado:
        query = query.filter(Trabajo.estado == estado)
    if cliente_nombre:
        query = query.filter(Trabajo.cliente_nombre.ilike(f"%{cliente_nombre}%"))
    if categoria:
        query = query.filter(Trabajo.categoria.ilike(f"%{categoria}%"))
    if tarea_numero:
        query = query.filter(Trabajo.tarea_numero.ilike(f"%{tarea_numero}%"))
    
    trabajos = query.all()
    
    data = []
    for t in trabajos:
        data.append({
            'id': t.id,
            'fecha_inicio': t.fecha_inicio.isoformat() if t.fecha_inicio else None,
            'tarea_numero': t.tarea_numero,
            'cliente_nombre': t.cliente_nombre,
            'estado': t.estado,
            'categoria': t.categoria,
            'hora_inicio': t.hora_inicio.isoformat() if t.hora_inicio else None,
            'hora_finalizada': t.hora_finalizada.isoformat() if t.hora_finalizada else None,
            'empleado_objetivo': t.empleado_objetivo,
            'incompleto': t.incompleto,
            'fuente_archivo_nombre': t.fuente_archivo_nombre,
            'fuente_archivo_tipo': t.fuente_archivo_tipo,
            'creado_en': t.creado_en.isoformat() if t.creado_en else None
        })
    
    output = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'))
    
    return StreamingResponse(
        output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=trabajos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )

@app.get("/api/clientes")
async def listar_clientes(db: Session = Depends(get_db)):
    """Lista todos los clientes únicos"""
    clientes = db.query(Trabajo.cliente_nombre).distinct().all()
    return [c[0] for c in clientes if c[0]]

@app.get("/api/categorias")
async def listar_categorias(db: Session = Depends(get_db)):
    """Lista todas las categorías únicas"""
    categorias = db.query(Trabajo.categoria).distinct().all()
    return [c[0] for c in categorias if c[0]]
