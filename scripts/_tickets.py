"""Gestión de tickets/issues en GitHub: crear, buscar, etiquetar, campos de proyecto."""

import os
import re
import time
import json
import urllib.request

from _config import ORG, GITHUB_REPO, PROJECT_ID, PROJECT_NUMBER
from _github_api import query_graphql, fetch_project_items, update_item_single_select_field, update_issue_body


def find_item_by_tk_id(tk_id, items=None):
    if not items:
        items = fetch_project_items()
    tk_num = re.sub(r'\D', '', tk_id)
    tk_clean = tk_id.strip().lower().replace(" ", "").replace("-", "")
    for item in items:
        title_clean = item["title"].lower().replace(" ", "").replace("-", "")
        if tk_clean in title_clean:
            return item
        if tk_num:
            m = re.search(r'tk0*(\d+)', title_clean)
            if m and int(m.group(1)) == int(tk_num):
                return item
    return None

def get_repository_id():
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
      }
    }
    """
    data = query_graphql(query, {"owner": ORG, "name": GITHUB_REPO})
    if data:
        return data.get("repository", {}).get("id")
    return None

def create_github_issue(title, body):
    repo_id = get_repository_id()
    if not repo_id:
        print("[ERROR] No se pudo obtener el ID del repositorio.")
        return None
        
    mutation = """
    mutation($repositoryId: ID!, $title: String!, $body: String!) {
      createIssue(input: {repositoryId: $repositoryId, title: $title, body: $body}) {
        issue {
          id
          number
        }
      }
    }
    """
    res = query_graphql(mutation, {"repositoryId": repo_id, "title": title, "body": body})
    if res:
        issue = res.get("createIssue", {}).get("issue", {})
        print(f"[OK] Issue #{issue.get('number')} creado en GitHub.")
        return issue.get("id")
    return None

def add_issue_to_project(issue_id):
    mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item {
          id
        }
      }
    }
    """
    res = query_graphql(mutation, {"projectId": PROJECT_ID, "contentId": issue_id})
    if res:
        print("[OK] Issue agregado al tablero Kanban.")
        return True
    return False

def get_repo_labels():
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        labels(first: 50) {
          nodes {
            id
            name
          }
        }
      }
    }
    """
    data = query_graphql(query, {"owner": ORG, "name": GITHUB_REPO})
    if data:
        return {label["name"].lower(): label["id"] for label in data.get("repository", {}).get("labels", {}).get("nodes", [])}
    return {}

def add_labels_to_issue(issue_id, label_ids):
    mutation = """
    mutation($labelableId: ID!, $labelIds: [ID!]!) {
      addLabelsToLabelable(input: {labelableId: $labelableId, labelIds: $labelIds}) {
        labelable {
          ... on Issue {
            id
          }
        }
      }
    }
    """
    res = query_graphql(mutation, {"labelableId": issue_id, "labelIds": label_ids})
    return res is not None

def apply_labels_by_names(issue_id, label_names):
    existing_labels = get_repo_labels()
    ids_to_add = []
    for name in label_names:
        name_clean = name.strip().lower()
        if name_clean in existing_labels:
            ids_to_add.append(existing_labels[name_clean])
        else:
            print(f"[WARN] La etiqueta '{name}' no existe en el repositorio.")
    if ids_to_add:
        add_labels_to_issue(issue_id, ids_to_add)
        print(f"[OK] Etiquetas {label_names} aplicadas al issue.")

def create_and_add_ticket(title, body, labels_list=None):
    issue_id = create_github_issue(title, body)
    if issue_id:
        add_issue_to_project(issue_id)
        if labels_list:
            apply_labels_by_names(issue_id, labels_list)
        return True
    return False

def create_ispc_bug_ticket(tk_id, scope, bug_code, title, severity="Mayor", steps="", expected="", actual="", wcag="", module="", tc_code="", labels_list=None):
    """Crea un issue de bug con la plantilla estandarizada ISPC y lo suma al proyecto."""
    full_title = f"{tk_id} - bug({scope}): {bug_code} - {title}"
    
    wcag_str = f"WCAG 2.2 - {wcag}" if wcag else "N/A"
    tc_str = tc_code if tc_code else "N/A (Exploración / Sprint 4)"
    module_str = module if module else scope.capitalize()
    steps_str = steps if steps else "1. Acceder al sistema.\n2. Ejecutar la acción que dispara el fallo."
    
    body = f"""### 🐛 Descripción del Defecto
{title}

---

### 📍 Clasificación y Alcance
- **Módulo Afectado:** {module_str}
- **Componente / Scope:** {scope}
- **Tipo de Defecto:** {'Accesibilidad WCAG' if wcag else 'Funcional / Validación'}
- **Severidad:** {severity}
- **Prioridad:** {'Alta' if severity in ['Crítica', 'Mayor'] else 'Media'}
- **Criterio WCAG Afectado:** {wcag_str}
- **Caso de Prueba Vinculado:** {tc_str}

---

### 📋 Precondiciones
1. Entorno local operativo (Backend Django + Frontend Angular).
2. Usuario autenticado con rol correspondiente según el módulo.

---

### 👣 Pasos para Reproducir
{steps_str}

---

### ❌ Comportamiento Obtenido
{actual if actual else 'Comportamiento incorrecto detectado durante las pruebas de verificación.'}

---

### ✅ Comportamiento Esperado
{expected if expected else 'El sistema debe comportarse según la especificación funcional y pautas de calidad.'}

---

### 📷 Evidencias
- **Captura / Log:** `docs/evidencias_bugs/EVIDENCIA_{bug_code}.png`

---

### 💻 Entorno de Prueba
- **Ambiente:** Local / Staging
- **Base de Datos:** PostgreSQL 16
"""
    final_labels = ["bug", scope]
    if wcag:
        final_labels.append("accesibilidad")
    if labels_list:
        for l in labels_list:
            if l not in final_labels:
                final_labels.append(l)

    return create_and_add_ticket(full_title, body, final_labels)


def list_project_fields():
    query = """
    query($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          fields(first: 50) {
            nodes {
              ... on ProjectV2FieldCommon {
                id
                name
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    data = query_graphql(query, {"org": ORG, "number": PROJECT_NUMBER})
    if data:
        fields = data.get("organization", {}).get("projectV2", {}).get("fields", {}).get("nodes", [])
        print("\n=== CONFIGURACIÓN DE CAMPOS DEL PROYECTO ===")
        for f in fields:
            print(f"Campo: {f.get('name')} (ID: {f.get('id')})")
            if "options" in f:
                for opt in f["options"]:
                    print(f"  - Opción: {opt.get('name')} (ID: {opt.get('id')})")
        print("============================================\n")

def update_item_field_by_names(item_id, field_name, value_name):
    query = """
    query($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          fields(first: 50) {
            nodes {
              ... on ProjectV2FieldCommon {
                id
                name
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    data = query_graphql(query, {"org": ORG, "number": PROJECT_NUMBER})
    if not data:
        print("[ERROR] No se pudo consultar la configuración de campos del proyecto.")
        return False
        
    fields = data.get("organization", {}).get("projectV2", {}).get("fields", {}).get("nodes", [])
    
    target_field = None
    for f in fields:
        if f.get("name", "").lower().strip() == field_name.lower().strip():
            target_field = f
            break
            
    if not target_field:
        print(f"[ERROR] No se encontró el campo '{field_name}' en el proyecto.")
        return False
        
    if "options" not in target_field:
        print(f"[ERROR] El campo '{field_name}' no es de selección única.")
        return False
        
    target_option = None
    for opt in target_field["options"]:
        if opt.get("name", "").lower().strip() == value_name.lower().strip():
            target_option = opt
            break
            
    if not target_option:
        print(f"[ERROR] No se encontró el valor '{value_name}' para el campo '{field_name}'.")
        print(f"Opciones válidas: {[opt.get('name') for opt in target_field['options']]}")
        return False
        
    success = update_item_single_select_field(item_id, target_field["id"], target_option["id"])
    if success:
        print(f"[OK] Campo '{target_field['name']}' actualizado a '{target_option['name']}' en GitHub.")
    else:
        print(f"[ERROR] Falló la actualización del campo '{field_name}'.")
    return success


def audit_empty_bodies(items=None):
    """Audita todas las tareas del Kanban y lista las que tienen el cuerpo/descripción vacío."""
    if not items:
        items = fetch_project_items()
    empty_items = []
    for it in items:
        body = (it.get("body") or "").strip()
        if not body:
            empty_items.append(it)
    print(f"\n=== AUDITORÍA DE TICKETS CON CUERPO VACÍO ===")
    print(f"Total encontrados: {len(empty_items)} de {len(items)} tareas.")
    for it in empty_items:
        num = f"#{it['number']}" if it.get("number") else "Draft"
        print(f"  - [{num}] [{it.get('status')}] {it.get('title')}")
    print("=============================================\n")
    return empty_items


def sync_bodies_from_markdown(md_file_path, overwrite=False):
    """Sincroniza los cuerpos de los tickets en GitHub a partir de un archivo Markdown."""
    if not os.path.exists(md_file_path):
        print(f"[ERROR] Archivo no encontrado: {md_file_path}")
        return False
        
    with open(md_file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    pattern = re.compile(r'(?:^|\n)# \*\*TK0*(\d+)[^\n]*\*\*\s*\n(.*?)(?=(?:\n# \*\*TK0*\d+|\Z))', re.DOTALL)
    matches = pattern.findall(content)
    
    if not matches:
        print(f"[WARN] No se encontraron secciones de tickets con formato '# **TKxxx...' en {md_file_path}")
        return False
        
    print(f"\n[INFO] Se encontraron {len(matches)} especificaciones de tickets en '{md_file_path}'.")
    items = fetch_project_items()
    
    updated_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for tk_num_str, body in matches:
        tk_id = f"TK{tk_num_str}"
        item = find_item_by_tk_id(tk_id, items)
        if not item:
            print(f"  [WARN] No se encontró {tk_id} en el tablero Kanban.")
            not_found_count += 1
            continue
            
        current_body = (item.get("body") or "").strip()
        if current_body and not overwrite:
            print(f"  [SKIP] {tk_id} (#{item.get('number')}): Ya tiene cuerpo cargado ({len(current_body)} chars).")
            skipped_count += 1
            continue
            
        clean_body = body.strip()
        clean_body = re.sub(r'\n*---\s*$', '', clean_body).strip()
        
        if item.get("content_type") == "Issue":
            success = update_issue_body(item["content_id"], clean_body)
            if success:
                print(f"  [OK] {tk_id} (Issue #{item.get('number')}): Cuerpo actualizado ({len(clean_body)} chars).")
                updated_count += 1
            else:
                print(f"  [ERROR] Falló la actualización del cuerpo para {tk_id}.")
        elif item.get("content_type") == "DraftIssue":
            mutation = """
            mutation($projectId: ID!, $itemId: ID!, $body: String!) {
              updateProjectV2DraftIssue(
                input: {
                  projectId: $projectId
                  itemId: $itemId
                  body: $body
                }
              ) {
                draftIssue {
                  id
                }
              }
            }
            """
            res = query_graphql(mutation, {"projectId": PROJECT_ID, "itemId": item["id"], "body": clean_body})
            if res:
                print(f"  [OK] {tk_id} (Draft): Cuerpo actualizado ({len(clean_body)} chars).")
                updated_count += 1
            else:
                print(f"  [ERROR] Falló la actualización para {tk_id} (Draft).")
                
        time.sleep(0.5)  # Rate limiting
        
    print(f"\n=== RESUMEN DE SINCRONIZACIÓN ===")
    print(f"  Actualizados: {updated_count}")
    print(f"  Omitidos (ya tenían cuerpo): {skipped_count}")
    print(f"  No encontrados: {not_found_count}")
    print("==================================\n")
    return True


def get_ticket_dependencies(body, self_tk=None):
    """Extrae la lista de tickets de los que depende una tarea a partir de su descripción o campos."""
    if not body:
        return []
    
    dep_match = re.search(r'(?:Dependencias?|Depende de|Requisitos?)[^\n]*\n(.*?)(?=(?:\n\*\*|\n##|\n---|\Z))', body, re.IGNORECASE | re.DOTALL)
    text_to_search = dep_match.group(1) if dep_match else body
    
    upper_text = text_to_search.upper()
    if any(neg in upper_text for neg in ["NO TIENE", "NINGUNA", "NO POSEE", "ESTA TAREA NO POSEE"]):
        return []
        
    raw_deps = re.findall(r'TK\s*0*(\d+)', text_to_search, re.IGNORECASE)
    self_num = re.sub(r'[^0-9]', '', self_tk) if self_tk else ''
    
    clean_deps = []
    for d in raw_deps:
        d_num = str(int(d))
        tk_formatted = f"TK{d_num}"
        if d_num != self_num and tk_formatted not in clean_deps:
            clean_deps.append(tk_formatted)
            
    return clean_deps


def check_ticket_dependencies(item, all_items=None, verbose=True):
    """
    Verifica estrictamente si todas las dependencias de una tarea se encuentran en estado 'Done'.
    Retorna True si todas las dependencias están cumplidas o no tiene dependencias.
    Retorna False si existen dependencias pendientes, bloqueadas o no encontradas.
    """
    if not item:
        return False
        
    title = item.get("title", "")
    tk_match = re.search(r'TK\s*0*(\d+)', title, re.IGNORECASE)
    tk_id = f"TK{int(tk_match.group(1))}" if tk_match else item.get("id", "TASK")
    
    body = item.get("body", "")
    deps = get_ticket_dependencies(body, tk_id)
    
    if not deps:
        if verbose:
            print(f"[INFO] La tarea '{tk_id}' no posee dependencias registradas. Inicio habilitado.")
        return True
        
    if all_items is None:
        all_items = fetch_project_items()
        
    unresolved = []
    satisfied = []
    
    for dep_tk in deps:
        dep_item = find_item_by_tk_id(dep_tk, all_items)
        if not dep_item:
            unresolved.append({
                "tk": dep_tk,
                "number": None,
                "status": "No encontrado",
                "title": "Tarea no localizada en el Kanban"
            })
            continue
            
        status = dep_item.get("status", "Backlog")
        if status.lower().strip() == "done":
            satisfied.append({
                "tk": dep_tk,
                "number": dep_item.get("number"),
                "status": status,
                "title": dep_item.get("title")
            })
        else:
            unresolved.append({
                "tk": dep_tk,
                "number": dep_item.get("number"),
                "status": status,
                "title": dep_item.get("title")
            })
            
    if unresolved:
        print("\n" + "=" * 80)
        print(f"⛔ [BLOQUEO ESTRICTO DE DEPENDENCIAS - PREVENCIÓN DE CONFLICTOS DE RAMAS]")
        print(f"No es posible iniciar la tarea '{tk_id}' ({title}).")
        print(f"Se detectaron dependencias obligatorias sin completar en el Kanban:\n")
        for u in unresolved:
            num_str = f"#{u['number']}" if u['number'] else "Draft"
            print(f"  ❌ {u['tk']} ({num_str}) [{u['status']}]: {u['title']}")
            
        if satisfied:
            print(f"\nDependencias ya cumplidas ('Done'):")
            for s in satisfied:
                num_str = f"#{s['number']}" if s['number'] else "Draft"
                print(f"  ✅ {s['tk']} ({num_str}): {s['title']}")
                
        print("\n⚠️ REGLA DEL PROYECTO:")
        print("Para erradicar conflictos de ramas y divergencias de código en develop,")
        print("toda tarea dependiente exige que sus predecesoras estén en estado 'Done'")
        print("y mergeadas en la rama base antes de comenzar a trabajar en ella.")
        print("\nSi se requiere omitir esta validación de forma justificada y excepcional,")
        print("ejecutá: py scripts/kanban_helper.py --task <TK_ID> --start --force-start")
        print("=" * 80 + "\n")
        return False
        
    if verbose:
        print(f"\n✅ [VALIDACIÓN DE DEPENDENCIAS OK] Todas las dependencias de '{tk_id}' ({', '.join(deps)}) están en estado 'Done'.")
        print("Inicio de tarea autorizado sin riesgo de colisión de ramas.\n")
    return True


