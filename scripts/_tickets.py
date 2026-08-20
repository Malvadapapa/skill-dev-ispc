"""Gestión de tickets/issues en GitHub: crear, buscar, etiquetar, campos de proyecto."""

import re
import json
import urllib.request

from _config import ORG, GITHUB_REPO, PROJECT_ID, PROJECT_NUMBER
from _github_api import query_graphql, fetch_project_items, update_item_single_select_field


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
