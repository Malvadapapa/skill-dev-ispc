"""Gestión de Pull Requests en GitHub: crear, listar, inspeccionar, aprobar, solicitar cambios, fusionar."""

import json
import urllib.request
import urllib.error

from _config import ORG, GITHUB_REPO, HEADERS


def create_pull_request(title, head, base="develop", body=""):
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls"
    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            pr_url = res.get("html_url")
            pr_num = res.get("number")
            print(f"[OK] Pull Request #{pr_num} creado exitosamente en GitHub: {pr_url}")
            return res
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"[ERROR] Error al crear Pull Request (HTTP {e.code}): {err_body}")
        return None
    except Exception as e:
        print(f"[ERROR] Error al comunicarse con la API de GitHub: {e}")
        return None

def list_pull_requests(state="open"):
    """Lista todos los Pull Requests del repositorio con su estado y ramas."""
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls?state={state}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            prs = json.loads(resp.read().decode('utf-8'))
            print(f"\n=== PULL REQUESTS EN ESTADO '{state.upper()}' ({len(prs)}) ===")
            if not prs:
                print("No hay Pull Requests en este estado.")
            for pr in prs:
                print(f"  - PR #{pr['number']}: {pr['title']}")
                print(f"    Autor: {pr.get('user', {}).get('login')}")
                print(f"    Ramas: {pr.get('head', {}).get('ref')} ➔ {pr.get('base', {}).get('ref')}")
                print(f"    URL: {pr.get('html_url')}")
            print("===================================================\n")
            return prs
    except Exception as e:
        print(f"[ERROR al listar Pull Requests]: {e}")
        return []

def inspect_pull_request(pr_number):
    """Analiza en detalle un Pull Request especifico, sus archivos, commits y estado de fusion/conflictos."""
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls/{pr_number}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            pr = json.loads(resp.read().decode('utf-8'))
            print(f"\n==================================================")
            print(f" PULL REQUEST #{pr['number']}: {pr['title']}")
            print(f"==================================================")
            print(f" Autor: {pr.get('user', {}).get('login')}")
            print(f" Estado: {pr.get('state')} | Estado de fusión: {pr.get('mergeable_state')} (Mergeable: {pr.get('mergeable')})")
            print(f" Ramas: {pr.get('head', {}).get('ref')} ➔ {pr.get('base', {}).get('ref')}")
            print(f" URL: {pr.get('html_url')}")
            if pr.get("body"):
                print("\n--- DESCRIPCIÓN ---")
                print(pr["body"])

            comp_url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/compare/{pr['base']['ref']}...{pr['head']['ref']}"
            req_comp = urllib.request.Request(comp_url, headers=HEADERS)
            try:
                with urllib.request.urlopen(req_comp) as resp_comp:
                    comp = json.loads(resp_comp.read().decode('utf-8'))
                    print(f"\n--- COMPARACIÓN DE RAMAS ({pr['base']['ref']} vs {pr['head']['ref']}) ---")
                    print(f" Commits de diferencia: {comp.get('ahead_by')} adelante, {comp.get('behind_by')} atrás de {pr['base']['ref']}")
                    print("\n Commits incluidos:")
                    for c in comp.get("commits", []):
                        msg = c.get('commit', {}).get('message', '').splitlines()[0]
                        author = c.get('commit', {}).get('author', {}).get('name')
                        sha = c.get('sha', '')[:7]
                        print(f"   - [{sha}] {msg} ({author})")
                    print("\n Archivos modificados:")
                    for f in comp.get("files", []):
                        status = f.get('status')
                        adds = f.get('additions', 0)
                        dels = f.get('deletions', 0)
                        filename = f.get('filename')
                        print(f"\n   📄 {filename} [{status}] (+{adds}/-{dels})")
                        patch = f.get('patch')
                        if patch:
                            print("   --- Diff de cambios ---")
                            patch_lines = patch.split('\n')
                            for pl in patch_lines[:30]:
                                print(f"     {pl}")
                            if len(patch_lines) > 30:
                                print(f"     ... ({len(patch_lines) - 30} líneas más)")
            except Exception as e_comp:
                print(f"[WARN] No se pudo obtener la comparación detallada de ramas: {e_comp}")

            print("==================================================\n")
            return pr
    except urllib.error.HTTPError as e:
        print(f"[ERROR] No se encontró el PR #{pr_number} (HTTP {e.code}).")
        return None
    except Exception as e:
        print(f"[ERROR al inspeccionar PR #{pr_number}]: {e}")
        return None

def approve_pull_request(pr_number, comment=""):
    """Aprueba un Pull Request y envía un comentario de revisión."""
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls/{pr_number}/reviews"
    payload = {
        "event": "APPROVE",
        "body": comment
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f"[OK] Pull Request #{pr_number} aprobado exitosamente en GitHub.")
            return res
    except Exception as e:
        print(f"[ERROR al aprobar PR #{pr_number}]: {e}")
        return None

def request_changes_pull_request(pr_number, comment=""):
    """Solicita cambios (REQUEST_CHANGES) en un Pull Request con un comentario explicativo."""
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls/{pr_number}/reviews"
    payload = {
        "event": "REQUEST_CHANGES",
        "body": comment
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f"[OK] Solicitud de cambios (REQUEST_CHANGES) enviada al PR #{pr_number} exitosamente.")
            return res
    except Exception as e:
        print(f"[ERROR al solicitar cambios en PR #{pr_number}]: {e}")
        return None

def dismiss_pull_request_review(pr_number, review_id, message=""):
    """Desestima (dismiss) una revisión previa de un Pull Request."""
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls/{pr_number}/reviews/{review_id}/dismissals"
    payload = {
        "message": message
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='PUT'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f"[OK] Revisión #{review_id} del PR #{pr_number} desestimada exitosamente.")
            return res
    except Exception as e:
        print(f"[ERROR al desestimar revisión #{review_id} del PR #{pr_number}]: {e}")
        return None


def merge_pull_request(pr_number, merge_method="merge"):
    """Realiza la fusión (merge) de un Pull Request aprobado."""
    url = f"https://api.github.com/repos/{ORG}/{GITHUB_REPO}/pulls/{pr_number}/merge"
    payload = {
        "merge_method": merge_method
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='PUT'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            if res.get("merged"):
                print(f"[OK] Pull Request #{pr_number} fue fusionado (merged) exitosamente.")
            else:
                print(f"[WARN] Respuesta al fusionar PR #{pr_number}: {res.get('message')}")
            return res
    except Exception as e:
        print(f"[ERROR al fusionar PR #{pr_number}]: {e}")
        return None
