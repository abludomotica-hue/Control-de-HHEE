import pytesseract
from PIL import Image
import re
from datetime import date, time
from typing import Optional, Dict, List
from app.schemas import ExtraccionPreview, EstadoEnum
from app.pdf_parser import (
    normalizar_texto, empleado_matchea_objetivo, parsear_fecha, 
    parsear_hora, EMPLEADO_OBJETIVO, calcular_hash_archivo
)

def parsear_imagen(file_path: str, nombre_original: str) -> ExtraccionPreview:
    """Parsea una imagen usando OCR y extrae los datos relevantes"""
    
    # Calcular hash del archivo
    file_hash = calcular_hash_archivo(file_path)
    
    preview = ExtraccionPreview(
        fuente_archivo_nombre=nombre_original,
        fuente_archivo_tipo="IMAGEN",
        fuente_archivo_hash=file_hash,
        empleado_objetivo=EMPLEADO_OBJETIVO,
        incompleto=True,
        extraccion_confiable=False
    )
    
    try:
        # Abrir imagen y ejecutar OCR en español
        image = Image.open(file_path)
        texto_completo = pytesseract.image_to_string(image, lang='spa')
        
        preview.raw_text = texto_completo[:5000]
        
        # Extraer metadatos usando los mismos patrones que PDF
        metadatos = extraer_metadatos_ocr(texto_completo)
        
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
        
        # Extraer entradas de la tabla
        filas = extraer_entradas_ocr(texto_completo)
        
        # Buscar horas
        horas_inicio = []
        horas_final = []
        
        for fila in filas:
            empleado = fila.get('empleado', '')
            tipo = normalizar_texto(fila.get('tipo_entrada', ''))
            fecha_hora = fila.get('fecha_hora', '')
            
            if empleado_matchea_objetivo(empleado):
                hora = parsear_hora(fecha_hora)
                
                if hora:
                    if 'confirmar' in tipo and 'tarea' in tipo:
                        horas_inicio.append(hora)
                    elif 'ejecutar' in tipo and 'tarea' in tipo:
                        horas_final.append(hora)
        
        if horas_inicio:
            preview.hora_inicio = min(horas_inicio)
        
        if horas_final:
            preview.hora_finalizada = max(horas_final)
        
        # Determinar confiabilidad (OCR es menos confiable que PDF)
        preview.extraccion_confiable = (
            preview.tarea_numero is not None and
            preview.fecha_inicio is not None and
            preview.cliente_nombre is not None
        )
        
        preview.incompleto = (
            preview.hora_inicio is None or
            preview.hora_finalizada is None
        )
        
    except Exception as e:
        preview.raw_text = f"Error en OCR: {str(e)}"
        preview.extraccion_confiable = False
        preview.incompleto = True
    
    return preview

def extraer_metadatos_ocr(texto: str) -> Dict:
    """Extrae metadatos del texto OCR"""
    metadatos = {}
    
    # Tarea Número - varios patrones
    patrones_tarea = [
        r'N[úu]mero\s*de\s*tarea[:\s]*(\d+)',
        r'Tarea\s*N[úu]mero[:\s]*(\d+)',
        r'Tarea[:\s]*(\d+)',
    ]
    for patron in patrones_tarea:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            metadatos['tarea_numero'] = match.group(1)
            break
    
    # Fecha de inicio
    match = re.search(r'Fecha\s*de\s*inicio[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
    if match:
        fecha_str = match.group(1).strip()
        metadatos['fecha_inicio'] = parsear_fecha(fecha_str)
    
    # Si no se encontró, buscar fechas en formato común
    if 'fecha_inicio' not in metadatos:
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', texto)
        if match:
            metadatos['fecha_inicio'] = parsear_fecha(match.group(0))
    
    # Cliente
    patrones_cliente = [
        r'Cliente[:\s]*\n?([^\n]+)',
        r'Nombre\s*del\s*cliente[:\s]*\n?([^\n]+)',
    ]
    for patron in patrones_cliente:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            metadatos['cliente_nombre'] = match.group(1).strip()
            break
    
    # Categoría
    match = re.search(r'Categor[ií]a[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
    if match:
        metadatos['categoria'] = match.group(1).strip()
    
    # Tipo de tarea (alternativa a categoría)
    if 'categoria' not in metadatos:
        match = re.search(r'Tipo\s*de\s*tarea[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
        if match:
            metadatos['categoria'] = match.group(1).strip()
    
    # Estado
    match = re.search(r'Estado[:\s]*\n?(Ejecutado|Pendiente)', texto, re.IGNORECASE)
    if match:
        estado_str = match.group(1).capitalize()
        metadatos['estado'] = EstadoEnum.EJECUTADO if estado_str == "Ejecutado" else EstadoEnum.PENDIENTE
    
    # Empleado objetivo en el texto
    match = re.search(r'Nombre\s*de\s*empleado[:\s]*\n?([^\n]+)', texto, re.IGNORECASE)
    if match:
        empleado_extraido = match.group(1).strip()
        # Verificar si coincide con nuestro objetivo
        if empleado_matchea_objetivo(empleado_extraido):
            metadatos['empleado_confirmado'] = True
    
    return metadatos

def extraer_entradas_ocr(texto: str) -> List[Dict]:
    """Extrae entradas del texto OCR"""
    filas = []
    lineas = texto.split('\n')
    
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        
        # Buscar líneas que contengan MSI Z08SO
        if 'MSI Z08SO' in linea:
            empleado_lineas = [linea]
            j = i + 1
            
            # Acumular líneas del empleado
            while j < len(lineas) and j < i + 5:
                siguiente = lineas[j].strip()
                if siguiente and (any(x in siguiente for x in ['Team', 'Rondon', '(ECC)', 'Abrahan'])):
                    empleado_lineas.append(siguiente)
                    j += 1
                else:
                    break
            
            empleado_texto = ' '.join(empleado_lineas)
            
            # Buscar tipo de entrada y fecha/hora en líneas siguientes
            tipo_entrada = ""
            fecha_hora = ""
            
            for k in range(j, min(j + 15, len(lineas))):
                linea_k = lineas[k].strip()
                
                # Detectar tipo de entrada
                if any(x in linea_k for x in ['Confirmar', 'Ejecutar', 'En ruta', 'Llegó', 'Iniciar']):
                    tipo_entrada = linea_k
                
                # Detectar fecha/hora
                if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', linea_k) or re.search(r'\d{1,2}:\d{2}', linea_k):
                    if not fecha_hora:
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
