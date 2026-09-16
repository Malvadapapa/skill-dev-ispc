"""Autenticación de Google OAuth2 y configuración del desarrollador.
Incluye: login condicional, verificación de usuario, actualización de .env."""

import os
import json
import urllib.request
import urllib.parse

from _config import _load_env, SKILL_DIR, TOKEN, DEV_BRANCH_NAME

_ENV = _load_env()


def _get_valid_google_token():
    """Obtiene un token de acceso válido de Google Sheets, refrescándolo automáticamente si expiró."""
    from _config import PROJECT_ROOT
    token_file = os.path.join(SKILL_DIR, "google_tokens.json")
    if not os.path.exists(token_file):
        scratch_token = os.path.join(PROJECT_ROOT, "..", "google_tokens.json")
        for tpath in [token_file, scratch_token, os.path.join(PROJECT_ROOT, "google_tokens.json")]:
            if os.path.exists(tpath):
                token_file = tpath
                break

    if not os.path.exists(token_file):
        return None

    try:
        with open(token_file, "r", encoding="utf-8") as f:
            tokens = json.load(f)
    except Exception:
        return None

    refresh_token = tokens.get("refresh_token")
    if refresh_token:
        client_id = tokens.get("client_id") or _ENV.get("GOOGLE_CLIENT_ID", "")
        client_secret = tokens.get("client_secret") or _ENV.get("GOOGLE_CLIENT_SECRET", "")
        post_data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }).encode("utf-8")
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=post_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                new_token = res.get("access_token")
                if new_token:
                    tokens["access_token"] = new_token
                    with open(token_file, "w", encoding="utf-8") as f_out:
                        json.dump(tokens, f_out, indent=2)
                    return new_token
        except Exception:
            pass

    return tokens.get("access_token")


def check_user_status():
    """Verifica la configuración actual del usuario (desarrollador y Google OAuth)."""
    token_path = os.path.join(SKILL_DIR, "google_tokens.json")
    has_google_token = False
    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("refresh_token") or data.get("access_token"):
                    has_google_token = True
        except Exception:
            pass

    has_github_token = bool(TOKEN and TOKEN != "ghp_tu_token_aqui")
    has_branch = bool(DEV_BRANCH_NAME)

    print("\n=== ESTADO DEL USUARIO / DESARROLLADOR ===")
    print(f"  Rama personal (DEV_BRANCH_NAME): {DEV_BRANCH_NAME if has_branch else '❌ (no configurada)'}")
    print(f"  GitHub Token:                  {'✅ Configurado' if has_github_token else '❌ (faltante)'}")
    print(f"  Sesión de Google OAuth:        {'✅ Activa (google_tokens.json)' if has_google_token else '❌ (no iniciada)'}")
    print("=========================================\n")

    return {
        "has_branch": has_branch,
        "has_github_token": has_github_token,
        "has_google_token": has_google_token,
        "branch_name": DEV_BRANCH_NAME,
        "is_ready": (has_branch and has_github_token and has_google_token)
    }

def update_dev_config(branch_name=None, github_token=None):
    """Actualiza las variables de desarrollo en el archivo .env del skill."""
    env_path = os.path.join(SKILL_DIR, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_branch = False
    updated_token = False

    new_lines = []
    for line in lines:
        if branch_name and line.strip().startswith("DEV_BRANCH_NAME="):
            new_lines.append(f"DEV_BRANCH_NAME={branch_name.strip()}\n")
            updated_branch = True
        elif github_token and line.strip().startswith("GITHUB_TOKEN="):
            new_lines.append(f"GITHUB_TOKEN={github_token.strip()}\n")
            updated_token = True
        else:
            new_lines.append(line)

    if branch_name and not updated_branch:
        new_lines.append(f"DEV_BRANCH_NAME={branch_name.strip()}\n")
    if github_token and not updated_token:
        new_lines.append(f"GITHUB_TOKEN={github_token.strip()}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"[OK] Configuración en .env actualizada exitosamente.")
    if branch_name:
        print(f"  - Rama asignada: {branch_name}")
    if github_token:
        print(f"  - GitHub token actualizado.")

def login_google_oauth(force=False):
    """Inicia sesión con Google OAuth2 usando el navegador local solo si no hay usuario activo o si se fuerza."""
    token_path = os.path.join(SKILL_DIR, "google_tokens.json")

    if not force and os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("refresh_token") or data.get("access_token"):
                    print("[INFO] Ya existe una sesión de Google activa en 'google_tokens.json'. No es necesario volver a iniciar sesión.")
                    print("       Usá --force-login si querés cambiar de cuenta de Google.")
                    return True
        except Exception:
            pass

    client_id = _ENV.get("GOOGLE_CLIENT_ID", "")
    client_secret = _ENV.get("GOOGLE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("[ERROR] No se encontraron las credenciales de Google OAuth.")
        print("        Configurá GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en el archivo .env del skill.")
        return False

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/", "http://127.0.0.1:8080/"]
            }
        }
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/documents'
        ]
        flow = InstalledAppFlow.from_client_config(client_config, scopes)
        print("\n[OAUTH] Abriendo navegador para iniciar sesión con Google...")
        creds = flow.run_local_server(port=8080, prompt='consent')

        token_data = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "scope": " ".join(scopes),
            "token_type": "Bearer",
            "expires_in": 3599,
            "client_id": client_id
        }

        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

        print(f"[OK] Sesión iniciada con éxito. Token guardado en '{token_path}'.\n")
        return True
    except ImportError:
        import webbrowser
        import http.server

        redirect_uri = "http://localhost:8080/"
        scope = "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
            f"response_type=code&"
            f"scope={urllib.parse.quote(scope)}&"
            f"access_type=offline&"
            f"prompt=consent"
        )

        auth_code = []

        class OAuthHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                if "code" in params:
                    auth_code.append(params["code"][0])
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write("<h1>¡Autenticación Exitosa con Google!</h1><p>Sesión vinculada como Cristian Vargas. Podés cerrar esta pestaña.</p>".encode("utf-8"))
                elif self.path == "/favicon.ico":
                    self.send_response(404)
                    self.end_headers()
                else:
                    self.send_response(400)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        server = http.server.HTTPServer(('localhost', 8080), OAuthHandler)
        print(f"\n[OAUTH] URL de autorización:\n{auth_url}\n")
        print("[OAUTH] Abriendo navegador para iniciar sesión con Google...")
        webbrowser.open(auth_url)
        while not auth_code:
            server.handle_request()

        if not auth_code:
            print("[ERROR] No se pudo obtener el código de autorización de Google.")
            return False

        token_url = "https://oauth2.googleapis.com/token"
        data = urllib.parse.urlencode({
            'code': auth_code[0],
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }).encode('utf-8')

        req = urllib.request.Request(token_url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urllib.request.urlopen(req) as resp:
                token_res = json.loads(resp.read().decode('utf-8'))
                token_res["client_id"] = client_id
                with open(token_path, "w", encoding="utf-8") as f:
                    json.dump(token_res, f, indent=2)
                print(f"[OK] Sesión de Google iniciada exitosamente. Token guardado en '{token_path}'.\n")
                return True
        except Exception as e:
            print(f"[ERROR al intercambiar tokens de Google]: {e}")
            return False
