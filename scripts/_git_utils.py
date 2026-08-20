"""Utilidades de Git: ejecución de comandos, manejo de ramas, commits."""

import os
import re
import subprocess

from _config import REPO_DIR


def run_git(args):
    if not os.path.exists(REPO_DIR):
        print(f"Error: La carpeta del repositorio no existe en {REPO_DIR}")
        return None
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=REPO_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error en Git '{' '.join(args)}': {e.stderr.strip()}")
        return None

def get_current_branch():
    return run_git(["branch", "--show-current"])

def get_branch_name_from_title(title):
    tk_match = re.search(r'(TK\d+)', title, re.IGNORECASE)
    tk_id = tk_match.group(1).lower() if tk_match else ""
    
    type_match = re.search(r'(feat|chore|fix|bugfix|docs|style|refactor|perf|test)\(([^)]+)\)', title, re.IGNORECASE)
    if type_match:
        branch_type = type_match.group(1).lower()
        scope = type_match.group(2).lower()
    else:
        type_match_simple = re.search(r'(feat|chore|fix|bugfix|docs|style|refactor|perf|test):', title, re.IGNORECASE)
        branch_type = type_match_simple.group(1).lower() if type_match_simple else "feature"
        scope = ""
        
    clean_title = title
    if tk_match:
        clean_title = clean_title.replace(tk_match.group(0), "")
    if type_match:
        clean_title = clean_title.replace(type_match.group(0), "")
    elif type_match_simple:
        clean_title = clean_title.replace(type_match_simple.group(0), "")
        
    clean_title = clean_title.lower()
    clean_title = clean_title.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    clean_title = re.sub(r'[^a-z0-9\s-]', '', clean_title)
    clean_title = re.sub(r'[\s-]+', '-', clean_title).strip('-')
    clean_title = clean_title[:30].strip('-')
    
    if tk_id:
        if scope:
            return f"{branch_type}/{tk_id}-{scope}-{clean_title}"
        else:
            return f"{branch_type}/{tk_id}-{clean_title}"
    else:
        return f"{branch_type}/{clean_title}"

def create_and_checkout_branch(branch_name):
    branches = run_git(["branch", "--list", branch_name])
    if branches and branch_name in branches:
        print(f"La rama '{branch_name}' ya existe. Cambiando a ella...")
        run_git(["checkout", branch_name])
    else:
        print(f"Creando y cambiando a la nueva rama '{branch_name}'...")
        run_git(["checkout", "-b", branch_name])

def commit_and_push_changes(task_title):
    print("\n--- Confirmación y subida de cambios ---")
    status = run_git(["status", "--short"])
    if not status:
        print("No hay archivos modificados para confirmar.")
        return False
        
    print("Archivos modificados:")
    print(status)
    
    confirm = input("¿Deseas confirmar (commit) y subir (push) todos estos archivos? (s/n): ").strip().lower()
    if confirm != 's':
        print("Operación cancelada.")
        return False
        
    commit_msg = task_title.strip()
    
    print(f"Ejecutando: git add .")
    run_git(["add", "."])
    
    print(f"Ejecutando: git commit -m \"{commit_msg}\"")
    run_git(["commit", "-m", commit_msg])
    
    current_branch = get_current_branch()
    print(f"Ejecutando: git push origin {current_branch}")
    run_git(["push", "origin", current_branch])
    return True
