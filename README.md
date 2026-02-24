HEAD
# Control-de-HHEE
Una aplicación web para registrar, gestionar y visualizar las horas extra trabajadas durante la jornada laboral.  El objetivo es simplificar el control de horas extra, garantizar trazabilidad. 

# Work Tracker - Control de Trabajos

Aplicación web para llevar el control de trabajos realizados por días, semanas y meses. Permite cargar archivos PDF o imágenes, extraer campos clave automáticamente, guardarlos en una base de datos y exportar los datos.

## Características

- **Carga de archivos**: Soporta PDF e imágenes (JPG, JPEG, PNG, BMP, GIF)
- **Extracción automática**: Extrae datos de encabezado y tabla de entradas
- **OCR integrado**: Reconocimiento de texto en imágenes
- **Previsualización editable**: Permite revisar y editar datos antes de guardar
- **Deduplicación**: Evita duplicados por hash + tarea + fecha + empleado
- **Dashboard completo**: Filtros por día/semana/mes, estado, cliente, categoría
- **Exportación**: CSV, Excel (XLSX) y JSON

## Stack Tecnológico

### Backend
- **FastAPI** (Python) - Framework web
- **SQLAlchemy** - ORM para base de datos
- **SQLite** - Base de datos
- **pdfplumber** - Parsing de PDFs
- **pytesseract** - OCR para imágenes
- **pandas** - Exportación a Excel/CSV

### Frontend
- **React** + **TypeScript**
- **Tailwind CSS** - Estilos
- **shadcn/ui** - Componentes UI
- **react-dropzone** - Drag & drop de archivos

## Estructura del Proyecto

```
work-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Endpoints API
│   │   ├── models.py            # Modelos SQLAlchemy
│   │   ├── schemas.py           # Schemas Pydantic
│   │   ├── database.py          # Configuración DB
│   │   ├── pdf_parser.py        # Parser de PDFs
│   │   └── ocr_parser.py        # Parser de imágenes (OCR)
│   ├── uploads/                 # Archivos subidos
│   ├── data/                    # Base de datos SQLite
│   ├── requirements.txt
│   └── run.py                   # Script de ejecución
├── frontend/
│   ├── src/
│   │   ├── components/ui/       # Componentes shadcn/ui
│   │   ├── sections/            # Secciones principales
│   │   │   ├── FileUpload.tsx
│   │   │   ├── PreviewForm.tsx
│   │   │   └── Dashboard.tsx
│   │   ├── hooks/               # Custom hooks
│   │   ├── types/               # Tipos TypeScript
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
└── README.md
```

## Instalación y Ejecución

### Requisitos Previos

- Python 3.9+
- Node.js 18+
- Tesseract OCR (para procesamiento de imágenes)

### Instalar Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-spa
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
Descargar e instalar desde: https://github.com/UB-Mannheim/tesseract/wiki

### Backend

1. Navegar al directorio del backend:
```bash
cd backend
```

2. Crear entorno virtual (opcional pero recomendado):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecutar el servidor:
```bash
python run.py
```

El servidor estará disponible en: http://localhost:8000

Documentación API: http://localhost:8000/docs

### Frontend

1. Navegar al directorio del frontend:
```bash
cd frontend
```

2. Instalar dependencias:
```bash
npm install
```

3. Ejecutar en modo desarrollo:
```bash
npm run dev
```

La aplicación estará disponible en: http://localhost:5173

4. Para producción:
```bash
npm run build
```

Los archivos compilados estarán en `dist/`.

## Uso

### Flujo de Trabajo

1. **Cargar Archivo**: Arrastre o seleccione un archivo PDF o imagen
2. **Previsualizar**: Revise los datos extraídos automáticamente
3. **Editar (opcional)**: Modifique los campos si es necesario
4. **Confirmar**: Guarde el trabajo en la base de datos
5. **Dashboard**: Visualice, filtre y exporte los trabajos

### Campos Extraídos

- **Tarea Número**: Identificador de la tarea
- **Fecha Inicio**: Fecha de inicio del trabajo
- **Cliente**: Nombre del cliente
- **Estado**: Ejecutado o Pendiente
- **Categoría**: Tipo de mantenimiento/tarea
- **Hora Inicio**: Primera hora de "Confirmar tarea" del empleado objetivo
- **Hora Finalizada**: Última hora de "Ejecutar tarea" del empleado objetivo

### Empleado Objetivo

Por defecto, el sistema busca al empleado: **MSI Z08SO Team 3 1 Abrahan Rondon (ECC)**

Este valor puede modificarse en el código si es necesario.

## API Endpoints

### Upload y Procesamiento
- `POST /api/upload` - Subir y procesar archivo
- `POST /api/confirmar` - Confirmar y guardar trabajo

### Gestión de Trabajos
- `GET /api/trabajos` - Listar trabajos (con filtros)
- `GET /api/trabajos/{id}` - Obtener trabajo específico
- `PUT /api/trabajos/{id}` - Actualizar trabajo
- `DELETE /api/trabajos/{id}` - Eliminar trabajo

### Estadísticas y Exportación
- `GET /api/estadisticas` - Estadísticas de trabajos
- `GET /api/export/csv` - Exportar a CSV
- `GET /api/export/xlsx` - Exportar a Excel
- `GET /api/export/json` - Exportar a JSON

### Datos de Referencia
- `GET /api/clientes` - Listar clientes únicos
- `GET /api/categorias` - Listar categorías únicas

## Pruebas del Parser

El parser de PDF incluye pruebas para verificar:

1. **Extracción de metadatos del encabezado**
   - Tarea Número
   - Fecha de inicio
   - Nombre del cliente
   - Categoría
   - Estado

2. **Extracción de la tabla "Entradas"**
   - Detección de filas
   - Identificación del empleado objetivo
   - Normalización de nombres con saltos de línea

3. **Cálculo de horas**
   - Hora inicio: mínima de "Confirmar tarea"
   - Hora finalizada: máxima de "Ejecutar tarea"

4. **Normalización de fechas y horas**
   - Fechas DD/MM/YYYY → ISO YYYY-MM-DD
   - Horas a.m./p.m. → formato 24h HH:MM

## Notas Importantes

- **NO** se usa el campo "Recurso" del encabezado para inferir el empleado
- El empleado se determina **solo** desde la tabla "Entradas"
- La deduplicación se basa en: hash del archivo + tarea + fecha + empleado
- Los archivos se almacenan con nombre basado en su hash SHA-256

## Licencia

MIT
>>>>>>> cb09903 (Add project files)
