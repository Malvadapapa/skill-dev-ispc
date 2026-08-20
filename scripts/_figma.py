"""Módulo para la manipulación e integración con Figma.
Permite validar el manifest local, mostrar URLs del prototipo, y detectar el estado de Figma Desktop y el MCP.
"""

import os
import json
import subprocess
import socket
from _config import PROJECT_ROOT

FIGMA_PLUGIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figma-plugin")

def is_figma_installed():
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data:
        figma_path = os.path.join(local_app_data, "Figma", "Figma.exe")
        return os.path.exists(figma_path)
    return False

def is_figma_running():
    try:
        # Check tasklist for Figma.exe
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq Figma.exe" /NH', shell=True).decode('utf-8', errors='ignore')
        return 'Figma.exe' in output
    except Exception:
        return False

def check_mcp_ports():
    # El plugin intenta conectar en puertos 9223 a 9232
    active_ports = []
    for port in range(9223, 9233):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            result = s.connect_ex(('localhost', port))
            if result == 0:
                active_ports.append(port)
    return active_ports

def show_figma_status():
    print("\n=== ESTADO DEL MÓDULO DE FIGMA ===")
    
    # 1. Validar manifest
    manifest_path = os.path.join(FIGMA_PLUGIN_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                print(f"[OK] Plugin local encontrado: '{manifest.get('name', 'Desconocido')}' (ID: {manifest.get('id')})")
        except Exception as e:
            print(f"[WARN] No se pudo parsear manifest.json: {e}")
    else:
        print("[WARN] No se encontró el plugin de Figma local en .agents/skills/ispc-dev/figma-plugin/")

    # 2. Instrucciones de prototipo
    print("\n🔗 Prototipo del Proyecto:")
    print("  URL Oficial: https://www.figma.com/design/KZhmDCMHAtuj1d77pXdygB/FCC_App?node-id=0-1")
    
    # 3. Estado de Figma Desktop
    print("\n🖥️  Estado de Figma Desktop (Windows):")
    installed = is_figma_installed()
    running = is_figma_running()
    
    if installed:
        print("  [OK] Figma Desktop está instalado.")
    else:
        print("  [WARN] No se detectó Figma Desktop instalado en %LOCALAPPDATA%\\Figma\\Figma.exe.")
        
    if running:
        print("  [OK] Figma Desktop está actualmente en ejecución.")
    else:
        if installed:
            print("  [!] Figma Desktop NO está en ejecución. Por favor, ábrelo para poder usar el MCP local.")
        else:
            print("  [!] Figma Desktop no está corriendo.")

    # 4. Estado del Servidor MCP
    print("\n⚡ Conexión con Servidor MCP:")
    if running:
        ports = check_mcp_ports()
        if ports:
            print(f"  [OK] Conexión MCP detectada en el/los puerto(s): {', '.join(map(str, ports))}")
            print("  ¡El puente Figma Desktop Bridge está activo y listo para usarse!")
        else:
            print("  [WARN] No se detectó el plugin MCP corriendo en los puertos esperados (9223-9232).")
            print("  -> Asegúrate de ir a Plugins -> Development -> Import plugin from manifest... y ejecutarlo.")
    else:
        print("  [WARN] Figma debe estar abierto para ejecutar el puente MCP.")
        print("  Pasos para activar el puente:")
        print("  1. Abre Figma Desktop.")
        print("  2. Ve a Plugins -> Development -> Import plugin from manifest...")
        print("  3. Selecciona: .agents/skills/ispc-dev/figma-plugin/manifest.json")
        print("  4. Ejecuta el plugin (quedará a la espera de la IA).")

    print("==================================\n")
