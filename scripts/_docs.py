"""Gestión de documentos del proyecto: locales (.md, .txt, .docx), Google Docs, y wiki."""

import os
import re
import subprocess

from _config import SKILL_DIR, PROJECT_ROOT, ORG, GITHUB_REPO


def read_docx_text(docx_path):
    """Extrae el texto plano de un archivo .docx sin necesidad de librerías externas pesadas."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        paragraphs = []
        for elem in tree.iter():
            if elem.tag.endswith('p'):
                texts = [node.text for node in elem.iter() if node.tag.endswith('t') and node.text]
                if texts:
                    paragraphs.append("".join(texts))
        return "\n".join(paragraphs)
    except Exception as e:
        return f"[ERROR al leer .docx]: {e}"

def list_project_docs():
    """Busca y lista todos los documentos del proyecto (.md, .txt, .docx) sin duplicados."""
    docs = []
    seen = set()
    search_dirs = [PROJECT_ROOT]
    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for root, dirs, files in os.walk(sdir):
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '.venv', '__pycache__', 'dist', 'build']]
            for file in files:
                if file.lower().endswith(('.md', '.txt', '.docx')) and not file.startswith('.'):
                    full_path = os.path.abspath(os.path.join(root, file))
                    if full_path not in seen:
                        seen.add(full_path)
                        rel_path = os.path.relpath(full_path, PROJECT_ROOT)
                        docs.append((file, rel_path, full_path))
    return docs

def search_project_docs(query):
    """Busca un término dentro de todos los documentos del proyecto."""
    docs = list_project_docs()
    results = []
    query_lower = query.lower()
    for fname, rel_path, full_path in docs:
        content = ""
        if fname.lower().endswith('.docx'):
            content = read_docx_text(full_path)
        else:
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue
        if query_lower in content.lower():
            lines = content.split('\n')
            matching_lines = [f"L{idx+1}: {line.strip()}" for idx, line in enumerate(lines) if query_lower in line.lower()]
            results.append((rel_path, matching_lines[:5]))
    return results

def fetch_google_doc(url):
    """Descarga y convierte Google Docs o Google Sheets públicos a texto plano o CSV."""
    import urllib.request
    doc_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
    if doc_match:
        doc_id = doc_match.group(1)
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        try:
            req = urllib.request.Request(export_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                return resp.read().decode('utf-8')
        except Exception as e:
            return f"[ERROR al descargar Google Doc ID {doc_id}]: {e}"

    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if sheet_match:
        sheet_id = sheet_match.group(1)
        gid_match = re.search(r'gid=([0-9]+)', url)
        gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
        try:
            req = urllib.request.Request(export_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                return resp.read().decode('utf-8')
        except Exception as e:
            return f"[ERROR al descargar Google Sheet ID {sheet_id}]: {e}"

    return "[ERROR]: URL no reconocida como Google Docs o Google Sheets."

def read_doc_file(filepath):
    """Lee el contenido de un archivo local (.md, .txt, .docx) o URL de Google Docs/Sheets."""
    if filepath.startswith(('http://', 'https://')):
        return fetch_google_doc(filepath)

    if not os.path.isabs(filepath):
        filepath = os.path.abspath(os.path.join(PROJECT_ROOT, filepath))
    if not os.path.exists(filepath):
        print(f"[ERROR] El archivo '{filepath}' no existe.")
        return None
    if filepath.lower().endswith('.docx'):
        return read_docx_text(filepath)
    else:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"[ERROR] No se pudo leer el archivo '{filepath}': {e}")
            return None

def update_wiki():
    """Actualiza la wiki local haciendo git pull en el directorio wiki/ del skill."""
    wiki_dir = os.path.join(SKILL_DIR, "wiki")
    if not os.path.exists(wiki_dir):
        print(f"[ERROR] No se encontró el directorio de la wiki en '{wiki_dir}'.")
        print("        Para configurar la wiki, cloná el repo wiki dentro del skill:")
        print(f"        git clone https://github.com/{ORG}/{GITHUB_REPO}.wiki.git {wiki_dir}")
        return False
    
    git_dir = os.path.join(wiki_dir, ".git")
    if not os.path.exists(git_dir):
        print("[WARN] El directorio wiki/ no es un repositorio git. No se puede actualizar automáticamente.")
        return False
    
    try:
        res = subprocess.run(
            ["git", "pull"],
            cwd=wiki_dir,
            capture_output=True,
            text=True,
            check=True
        )
        print(res.stdout)
        print("[OK] Wiki actualizada.")
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo actualizar la wiki: {e}")
        return False
