import pdfplumber
import re
from datetime import datetime, date, time
from typing import Optional, Dict, List, Tuple
from app.schemas import ExtraccionPreview, EstadoEnum
import hashlib

# Empleado objetivo canónico
EMPLEADO_OBJETIVO = "MSI Z08SO Team 3 1 Abrahan Rondon (ECC)"

def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin espacios extra, sin puntuación menor"""
    if not texto:
        return ""
    # Reemplazar saltos de línea por espacios
    texto = texto.replace('\n', ' ').replace('\r', ' ')
    # Colapsar espacios múltiples
    texto = ' '.join(texto.split())
    # Remover puntuación menor (.,)
    texto = texto.replace('.', ' ').replace(',', ' ')
    # Colapsar espacios nuevamente
    texto = ' '.join(texto.split())
    return texto.lower().strip()

def empleado_matchea_objetivo(empleado_texto: str) -> bool:
    """Verifica si el texto del empleado matchea el empleado objetivo"""
    if not empleado_texto:
        return False
    
    normalizado = normalizar_texto(empleado_texto)
    
    # Tokens que deben estar presentes (case-insensitive)
    tokens_requeridos = [
        "msi z08so",
        "team 3 1",
        "abrahan",
        "rondon (ecc)"
    ]
    
    for token in tokens_requeridos:
        if token not in normalizado:
            return False
    return True

def parsear_fecha(fecha_str: str) -> Optional[date]:
    """Parsea fechas en formato DD/MM/YYYY o variantes"""
    if not fecha_str:
        return None
    
    # Limpiar la cadena
    fecha_str = fecha_str.strip()
    
    # Patrones comunes
    patrones = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY o DD-MM-YYYY
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})',   # DD/MM/YY o DD-MM-YY
    ]
    
    for patron in patrones:
        match = re.search(patron, fecha_str)
        if match:
            dia, mes, anio = match.groups()
            dia = int(dia)
            mes = int(mes)
            anio = int(anio)
            if anio < 100:
                anio += 2000 if anio < 50 else 1900
            try:
                return date(anio, mes, dia)
            except ValueError:
                continue
    return None

def parsear_hora(hora_str: str) -> Optional[time]:
    """Parsea horas en formato HH:MM con a.m./p.m. o variantes"""
    if not hora_str:
        return None
    
    # Normalizar
    hora_str = hora_str.lower().strip()
    hora_str = hora_str.replace('a. m.', 'am').replace('p. m.', 'pm')
    hora_str = hora_str.replace('a.m.', 'am').replace('p.m.', 'pm')
    hora_str = hora_str.replace('a m', 'am').replace('p m', 'pm')
    
    # Patrón para extraer hora, minutos y período opcional
    patron = r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?'
    match = re.search(patron, hora_str)
    
    if match:
        hora = int(match.group(1))
        minutos = int(match.group(2))
        segundos = int(match.group(3)) if match.group(3) else 0
        periodo = match.group(4)
        
        # Convertir a formato 24h
        if periodo == 'pm' and hora != 12:
            hora += 12
        elif periodo == 'am' and hora == 12:
            hora = 0
        
        try:
            return time(hora, minutos, segundos)
        except ValueError:
            return None
    return None

def extraer_campo_encabezado(texto: str, campo: str, siguiente_campo: str = None) -> Optional[str]:
    """Extrae un campo del encabezado del PDF"""
    # Normalizar saltos de línea
    texto_normalizado = texto.replace('\r\n', '\n').replace('\r', '\n')
    
    # Buscar el campo
    patron = re.compile(re.escape(campo) + r'[:\s]*\n?([^\n]+)', re.IGNORECASE)
    match = patron.search(texto_normalizado)
    
    if match:
        valor = match.group(1).strip()
        # Si hay un siguiente campo, limitar hasta ahí
        if siguiente_campo:
            idx = valor.lower().find(siguiente_campo.lower())
            if idx > 0:
                valor = valor[:idx].strip()
        return valor
    return None

def extraer_metadatos_encabezado(texto: str) -> Dict:
    """Extrae los metadatos del encabezado del PDF"""
    metadatos = {}
    
    # Tarea Número
    match = re.search(r'Tarea\s*N[úu]mero[:\s]*(\d+)', texto, re.IGNORECASE)
    if match:
        metadatos['tarea_numero'] = match.group(1)
    
    # Fecha de inicio
    match = re.search(r'Fecha\s*de\s*inicio[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
    if match:
        fecha_str = match.group(1).strip()
        metadatos['fecha_inicio_str'] = fecha_str
        metadatos['fecha_inicio'] = parsear_fecha(fecha_str)
    
    # Nombre del cliente
    match = re.search(r'Nombre\s*del\s*cliente[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
    if match:
        cliente = match.group(1).strip()
        # Limpiar texto extra que pueda venir después del nombre del cliente
        # Buscar palabras clave que indican fin del nombre
        stop_words = ['categoría', 'categoria', 'teléfono', 'telefono', 'estado', 'número del cliente']
        cliente_lower = cliente.lower()
        for stop_word in stop_words:
            idx = cliente_lower.find(stop_word)
            if idx > 0:
                cliente = cliente[:idx].strip()
                break
        metadatos['cliente_nombre'] = cliente
    
    # Categoría de tarea
    match = re.search(r'Categor[ií]a\s*de\s*tarea[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
    if match:
        metadatos['categoria'] = match.group(1).strip()
    
    # Estado
    match = re.search(r'Estado[:\s]*\n?(Ejecutado|Pendiente)', texto, re.IGNORECASE)
    if match:
        estado_str = match.group(1).capitalize()
        metadatos['estado'] = EstadoEnum.EJECUTADO if estado_str == "Ejecutado" else EstadoEnum.PENDIENTE
    
    return metadatos

def extraer_tabla_entradas(pdf: pdfplumber.PDF) -> List[Dict]:
    """Extrae las filas de la tabla 'Entradas' del PDF"""
    filas = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Detectar si es la tabla de Entradas
            header_row = None
            for i, row in enumerate(table):
                if row and any('Entradas' in str(cell) for cell in row if cell):
                    continue
                if row and any('Empleado' in str(cell) for cell in row if cell):
                    header_row = i
                    break
            
            if header_row is None:
                continue
            
            # Encontrar índices de columnas relevantes
            header = table[header_row]
            col_empleado = None
            col_tipo_entrada = None
            col_fecha = None
            col_hora = None
            
            for i, cell in enumerate(header):
                if cell:
                    cell_str = str(cell).lower()
                    if 'empleado' in cell_str:
                        col_empleado = i
                    elif 'tipo' in cell_str and 'entrada' in cell_str:
                        col_tipo_entrada = i
                    elif 'fecha' in cell_str and 'fecha de' not in cell_str:
                        col_fecha = i
            
            # Si no encontramos columnas específicas, intentar inferir
            if col_empleado is None:
                continue
            
            # Extraer filas
            for row in table[header_row + 1:]:
                if not row or len(row) <= col_empleado:
                    continue
                
                empleado_cell = row[col_empleado] if col_empleado < len(row) else None
                
                # El empleado puede estar en múltiples celdas o con saltos de línea
                empleado_texto = str(empleado_cell) if empleado_cell else ""
                
                # Buscar tipo de entrada en la fila
                tipo_entrada = ""
                if col_tipo_entrada is not None and col_tipo_entrada < len(row):
                    tipo_entrada = str(row[col_tipo_entrada]) if row[col_tipo_entrada] else ""
                
                # Buscar fecha/hora en la fila
                fecha_hora = ""
                for cell in row:
                    if cell and re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', str(cell)):
                        fecha_hora = str(cell)
                        break
                
                filas.append({
                    'empleado': empleado_texto,
                    'tipo_entrada': tipo_entrada,
                    'fecha_hora': fecha_hora
                })
    
    return filas

def extraer_entradas_de_texto(texto: str) -> List[Dict]:
    """Extrae entradas del texto plano cuando las tablas no se parsean bien"""
    filas = []
    
    # Buscar patrones de empleado con MSI Z08SO
    lineas = texto.split('\n')
    
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        
        # Detectar inicio de entrada con MSI Z08SO
        if 'MSI Z08SO' in linea:
            empleado_lineas = [linea]
            j = i + 1
            
            # Acumular líneas siguientes que puedan ser parte del empleado
            while j < len(lineas) and j < i + 5:
                siguiente = lineas[j].strip()
                # Si la línea parece ser parte del nombre del empleado
                if siguiente and not re.match(r'\d{1,2}[/-]\d{1,2}', siguiente):
                    if 'Team' in siguiente or 'Rondon' in siguiente or '(ECC)' in siguiente:
                        empleado_lineas.append(siguiente)
                        j += 1
                    else:
                        break
                else:
                    break
            
            empleado_texto = ' '.join(empleado_lineas)
            
            # Buscar tipo de entrada en las siguientes líneas
            tipo_entrada = ""
            fecha_hora = ""
            
            for k in range(j, min(j + 10, len(lineas))):
                linea_k = lineas[k].strip()
                
                # Detectar tipo de entrada
                if 'Confirmar' in linea_k or 'Ejecutar' in linea_k or 'En ruta' in linea_k or 'Llegó' in linea_k:
                    tipo_entrada = linea_k
                
                # Detectar fecha/hora
                if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', linea_k):
                    fecha_hora = linea_k
            
            filas.append({
                'empleado': empleado_texto,
                'tipo_entrada': tipo_entrada,
                'fecha_hora': fecha_hora
            })
            
            i = j
        else:
            i += 1
    
    return filas

def calcular_hash_archivo(file_path: str) -> str:
    """Calcula el hash SHA-256 de un archivo"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def parsear_pdf(file_path: str, nombre_original: str) -> ExtraccionPreview:
    """Parsea un archivo PDF y extrae los datos relevantes"""
    
    # Calcular hash del archivo
    file_hash = calcular_hash_archivo(file_path)
    
    preview = ExtraccionPreview(
        fuente_archivo_nombre=nombre_original,
        fuente_archivo_tipo="PDF",
        fuente_archivo_hash=file_hash,
        empleado_objetivo=EMPLEADO_OBJETIVO,
        incompleto=True,
        extraccion_confiable=False
    )
    
    try:
        with pdfplumber.open(file_path) as pdf:
            # Extraer todo el texto
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += page.extract_text() or ""
                texto_completo += "\n"
            
            preview.raw_text = texto_completo[:5000]  # Guardar primeros 5000 chars para debug
            
            # Extraer metadatos del encabezado
            metadatos = extraer_metadatos_encabezado(texto_completo)
            
            if 'tarea_numero' in metadatos:
                preview.tarea_numero = metadatos['tarea_numero']
            if 'fecha_inicio' in metadatos:
                preview.fecha_inicio = metadatos['fecha_inicio']
            if 'cliente_nombre' in metadatos:
                preview.cliente_nombre = metadatos['cliente_nombre']
            if 'categoria' in metadatos:
                preview.categoria = metadatos['categoria']
            if 'estado' in metadatos:
                preview.estado = metadatos['estado']
            
            # Extraer tabla de entradas
            filas = extraer_tabla_entradas(pdf)
            
            # Si no se encontraron filas en tablas, intentar con texto
            if not filas:
                filas = extraer_entradas_de_texto(texto_completo)
            
            # Buscar hora_inicio (Confirmar tarea del empleado objetivo)
            horas_inicio = []
            horas_final = []
            
            for fila in filas:
                empleado = fila.get('empleado', '')
                tipo = normalizar_texto(fila.get('tipo_entrada', ''))
                fecha_hora = fila.get('fecha_hora', '')
                
                if empleado_matchea_objetivo(empleado):
                    hora = parsear_hora(fecha_hora)
                    
                    if hora:
                        # Confirmar tarea -> hora_inicio
                        if 'confirmar' in tipo and 'tarea' in tipo:
                            horas_inicio.append(hora)
                        
                        # Ejecutar tarea -> hora_finalizada
                        elif 'ejecutar' in tipo and 'tarea' in tipo:
                            horas_final.append(hora)
            
            # Asignar horas (mínima para inicio, máxima para final)
            if horas_inicio:
                preview.hora_inicio = min(horas_inicio)
            
            if horas_final:
                preview.hora_finalizada = max(horas_final)
            
            # Determinar si la extracción es confiable
            preview.extraccion_confiable = (
                preview.tarea_numero is not None and
                preview.fecha_inicio is not None and
                preview.cliente_nombre is not None and
                preview.estado is not None
            )
            
            # Marcar como incompleto si faltan horas
            preview.incompleto = (
                preview.hora_inicio is None or
                preview.hora_finalizada is None
            )
            
    except Exception as e:
        preview.raw_text = f"Error al parsear PDF: {str(e)}"
        preview.extraccion_confiable = False
        preview.incompleto = True
    
    return preview
