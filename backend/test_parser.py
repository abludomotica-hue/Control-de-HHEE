#!/usr/bin/env python3
"""
Script de pruebas para el parser de PDF y OCR
"""
import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pdf_parser import (
    normalizar_texto, empleado_matchea_objetivo, parsear_fecha, 
    parsear_hora, extraer_metadatos_encabezado, extraer_entradas_de_texto,
    EMPLEADO_OBJETIVO
)

def test_normalizar_texto():
    """Test de normalización de texto"""
    print("\n=== Test: normalizar_texto ===")
    
    casos = [
        ("MSI Z08SO\nTeam 3 1.\nAbrahan\nRondon (ECC)", "msi z08so team 3 1 abrahan rondon (ecc)"),
        ("  MSI   Z08SO   ", "msi z08so"),
        ("Team 3 1., Abrahan", "team 3 1 abrahan"),
    ]
    
    for entrada, esperado in casos:
        resultado = normalizar_texto(entrada)
        status = "✓" if resultado == esperado else "✗"
        print(f"  {status} '{entrada[:30]}...' -> '{resultado[:40]}'")
        if resultado != esperado:
            print(f"     Esperado: '{esperado}'")

def test_empleado_matchea_objetivo():
    """Test de matching de empleado objetivo"""
    print("\n=== Test: empleado_matchea_objetivo ===")
    
    casos_positivos = [
        "MSI Z08SO Team 3 1. Abrahan Rondon (ECC)",
        "MSI Z08SO\nTeam 3 1.\nAbrahan\nRondon (ECC)",
        "MSI Z08SO Team 3 1 Abrahan Rondon (ECC)",
    ]
    
    casos_negativos = [
        "MSI Z08SO Team 4 2. William Cerda (ECC)",
        "Otro Empleado Cualquiera",
        "",
    ]
    
    print("  Casos que deben hacer match:")
    for caso in casos_positivos:
        resultado = empleado_matchea_objetivo(caso)
        status = "✓" if resultado else "✗"
        print(f"    {status} '{caso[:40]}...' -> {resultado}")
    
    print("  Casos que NO deben hacer match:")
    for caso in casos_negativos:
        resultado = empleado_matchea_objetivo(caso)
        status = "✓" if not resultado else "✗"
        print(f"    {status} '{caso[:40]}...' -> {resultado}")

def test_parsear_fecha():
    """Test de parsing de fechas"""
    print("\n=== Test: parsear_fecha ===")
    
    casos = [
        ("21/02/2026", "2026-02-21"),
        ("21-02-2026", "2026-02-21"),
        ("Fecha de inicio: 21/02/2026 6:00 p. m.", "2026-02-21"),
    ]
    
    for entrada, esperado in casos:
        resultado = parsear_fecha(entrada)
        resultado_str = resultado.isoformat() if resultado else None
        status = "✓" if resultado_str == esperado else "✗"
        print(f"  {status} '{entrada[:40]}...' -> {resultado_str}")

def test_parsear_hora():
    """Test de parsing de horas"""
    print("\n=== Test: parsear_hora ===")
    
    casos = [
        ("5:39 p. m.", "17:39"),
        ("5:39 p.m.", "17:39"),
        ("5:39 pm", "17:39"),
        ("12:00 a. m.", "00:00"),
        ("12:00 p. m.", "12:00"),
        ("6:00 a.m.", "06:00"),
    ]
    
    for entrada, esperado in casos:
        resultado = parsear_hora(entrada)
        resultado_str = resultado.strftime("%H:%M") if resultado else None
        status = "✓" if resultado_str == esperado else "✗"
        print(f"  {status} '{entrada}' -> {resultado_str}")

def test_extraer_metadatos():
    """Test de extracción de metadatos"""
    print("\n=== Test: extraer_metadatos_encabezado ===")
    
    texto_prueba = """
Entradas detalladas de la tarea
Tarea Número: 45776410
Fecha de inicio
21/02/2026 6:00 p. m.
Nombre del cliente
MAS084
Categoría de tarea
Mantenimiento Correctivo RAN
Estado
Ejecutado
    """
    
    metadatos = extraer_metadatos_encabezado(texto_prueba)
    
    campos_esperados = ['tarea_numero', 'fecha_inicio', 'cliente_nombre', 'categoria', 'estado']
    
    for campo in campos_esperados:
        if campo in metadatos:
            print(f"  ✓ {campo}: {metadatos[campo]}")
        else:
            print(f"  ✗ {campo}: NO ENCONTRADO")

def test_extraer_entradas():
    """Test de extracción de entradas de tabla"""
    print("\n=== Test: extraer_entradas_de_texto ===")
    
    texto_prueba = """
Entradas
Fecha
Empleado
MSI Z08SO
Team 3 1.
Abrahan
Rondon (ECC)
21/02/2026
5:39 p. m.
Confirmar tarea
MSI Z08SO
Team 3 1.
Abrahan
Rondon (ECC)
21/02/2026
7:25 p. m.
Ejecutar tarea
    """
    
    filas = extraer_entradas_de_texto(texto_prueba)
    
    print(f"  Entradas encontradas: {len(filas)}")
    
    for i, fila in enumerate(filas):
        es_objetivo = empleado_matchea_objetivo(fila.get('empleado', ''))
        print(f"  [{i+1}] Empleado: {fila.get('empleado', '')[:50]}...")
        print(f"       Tipo: {fila.get('tipo_entrada', '-')}")
        print(f"       Fecha/Hora: {fila.get('fecha_hora', '-')}")
        print(f"       Es objetivo: {es_objetivo}")

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("="*60)
    print("  PRUEBAS DEL PARSER DE PDF")
    print("="*60)
    
    test_normalizar_texto()
    test_empleado_matchea_objetivo()
    test_parsear_fecha()
    test_parsear_hora()
    test_extraer_metadatos()
    test_extraer_entradas()
    
    print("\n" + "="*60)
    print("  PRUEBAS COMPLETADAS")
    print("="*60)

if __name__ == "__main__":
    run_all_tests()
