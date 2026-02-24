#!/bin/bash

# Script para iniciar Work Tracker (Backend + Frontend)

echo "========================================"
echo "  Work Tracker - Iniciando Servicios"
echo "========================================"
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: No se encontraron los directorios backend y frontend"
    echo "Por favor, ejecute este script desde el directorio raíz del proyecto"
    exit 1
fi

# Función para limpiar procesos al salir
cleanup() {
    echo ""
    echo "Deteniendo servicios..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Verificar dependencias del backend
echo "[1/3] Verificando dependencias del backend..."
cd backend

if ! python -c "import fastapi" 2>/dev/null; then
    echo "Instalando dependencias del backend..."
    pip install -r requirements.txt
fi

cd ..

# Iniciar backend
echo "[2/3] Iniciando backend en http://localhost:8000..."
cd backend
python run.py &
BACKEND_PID=$!
cd ..

# Esperar a que el backend esté listo
echo "      Esperando que el backend esté listo..."
sleep 4

# Verificar que el backend responde
echo "[3/3] Verificando conexión..."
if curl -s http://localhost:8000/api/trabajos > /dev/null 2>&1; then
    echo "      Backend respondiendo correctamente"
else
    echo "      Advertencia: El backend puede tardar unos segundos más en iniciar"
fi

echo ""
echo "========================================"
echo "  Servicios iniciados correctamente!"
echo "========================================"
echo ""
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  Frontend:    http://localhost:8000 (servido desde backend)"
echo ""
echo "Presione Ctrl+C para detener los servicios"
echo ""

# Esperar a que el proceso termine
wait $BACKEND_PID
