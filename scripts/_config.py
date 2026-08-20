"""Configuración centralizada del skill ISPC Dev.
Carga .env, define constantes de GitHub, rutas y headers."""

import os
import sys
import json
import urllib.request
import urllib.parse

# === Carga de configuración desde .env ===
def _load_env():
    """Carga las variables de configuración desde el archivo .env del skill.
    Busca el .env en el directorio padre del script (raíz del skill).
    No requiere dependencias externas (sin python-dotenv)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    config = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

_ENV = _load_env()

# Configuración parametrizada desde .env
TOKEN = _ENV.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
ORG = _ENV.get("GITHUB_ORG", os.environ.get("GITHUB_ORG", "TeamYear3"))
PROJECT_NUMBER = int(_ENV.get("PROJECT_NUMBER", os.environ.get("PROJECT_NUMBER", "2")))
DEV_BRANCH_NAME = _ENV.get("DEV_BRANCH_NAME", os.environ.get("DEV_BRANCH_NAME", ""))
GITHUB_REPO = _ENV.get("GITHUB_REPO", os.environ.get("GITHUB_REPO", "FCC_APP"))
DEFAULT_GOOGLE_SHEET_URL = _ENV.get("GOOGLE_SHEET_URL", os.environ.get("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/18bk6mBoyyrO_kGhaLSdjyv0_2jlCSm4rkookrUoueS8/edit"))

# Directorios calculados desde la ubicación del script
SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
REPO_DIR = os.path.join(PROJECT_ROOT, GITHUB_REPO)

# IDs del Proyecto GitHub recuperados por la API
PROJECT_ID = "PVT_kwDOEPmQ984BcSS-"
STATUS_FIELD_ID = "PVTSSF_lADOEPmQ984BcSS-zhW8PjY"

STATUS_OPTIONS = {
    "Backlog": "5fc49f58",
    "Todo": "f75ad846",
    "In Progress": "47fc9ee4",
    "In Review": "ab17b7c2",
    "Testing": "0b2955ab",
    "Done": "98236657"
}

STATUS_BY_ID = {v: k for k, v in STATUS_OPTIONS.items()}

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json',
    'User-Agent': 'KanbanHelperApp'
}

def _check_token():
    """Verifica que el token de GitHub esté configurado."""
    if not TOKEN or TOKEN == "ghp_tu_token_aqui":
        print("[ERROR] No se encontró un token de GitHub válido.")
        print("        Configurá tu token en el archivo .env del skill:")
        print(f"        {os.path.join(SKILL_DIR, '.env')}")
        print("        Podés copiar .env.example como base.")
        sys.exit(1)
