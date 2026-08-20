"""Funciones de interacción con la API GraphQL de GitHub.
Incluye: consultas al proyecto V2, actualización de estados, comentarios y asignaciones."""

import json
import re
import urllib.request

from _config import (
    GRAPHQL_URL, HEADERS, ORG, PROJECT_NUMBER, PROJECT_ID,
    STATUS_FIELD_ID, STATUS_OPTIONS, STATUS_BY_ID
)


def query_graphql(query, variables=None):
    payload = {'query': query}
    if variables:
        payload['variables'] = variables
        
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            if "errors" in res:
                print("GraphQL errors:", res["errors"])
                return None
            return res.get("data")
    except Exception as e:
        print("Error al comunicarse con GitHub API:", e)
        return None

def fetch_project_items():
    query = """
    query($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          items(first: 100) {
            nodes {
              id
              fieldValues(first: 20) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field {
                      ... on ProjectV2FieldCommon {
                        id
                        name
                      }
                    }
                  }
                }
              }
              content {
                __typename
                ... on Issue {
                  id
                  title
                  number
                  body
                  labels(first: 10) {
                    nodes {
                      name
                    }
                  }
                  assignees(first: 5) {
                    nodes {
                      login
                    }
                  }
                }
                ... on DraftIssue {
                  id
                  title
                  body
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
        return []
        
    project = data.get("organization", {}).get("projectV2", {})
    items = project.get("items", {}).get("nodes", [])
    
    parsed_items = []
    for item in items:
        content = item.get("content") or {}
        title = content.get("title", "Sin Título").strip()
        number = content.get("number", None)
        content_id = content.get("id", None)
        content_type = content.get("__typename", None)
        body = content.get("body", "").strip()
        labels = [l["name"] for l in content.get("labels", {}).get("nodes", [])] if content_type == "Issue" else []
        assignees = [a["login"] for a in content.get("assignees", {}).get("nodes", [])] if content_type == "Issue" else []
        
        status = "None"
        for fval in item.get("fieldValues", {}).get("nodes", []):
            if fval and fval.get("field", {}).get("name") == "Status":
                status = fval.get("name")
                break
                
        parsed_items.append({
            "id": item["id"],
            "title": title,
            "number": number,
            "status": status,
            "content_id": content_id,
            "content_type": content_type,
            "body": body,
            "labels": labels,
            "assignees": assignees
        })
    return parsed_items


def update_item_status(item_id, target_status_name):
    if target_status_name not in STATUS_OPTIONS:
        print(f"Estado '{target_status_name}' no es válido.")
        return False
        
    option_id = STATUS_OPTIONS[target_status_name]
    
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: {
            singleSelectOptionId: $optionId
          }
        }
      ) {
        projectV2Item {
          id
        }
      }
    }
    """
    
    variables = {
        "projectId": PROJECT_ID,
        "itemId": item_id,
        "fieldId": STATUS_FIELD_ID,
        "optionId": option_id
    }
    
    data = query_graphql(mutation, variables)
    if data:
        print(f"[OK] Tarjeta movida exitosamente a '{target_status_name}' en GitHub.")
        return True
    else:
        print("[ERROR] Error al actualizar el estado en GitHub.")
        return False

def update_item_single_select_field(item_id, field_id, option_id):
    mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(
        input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: {
            singleSelectOptionId: $optionId
          }
        }
      ) {
        projectV2Item {
          id
        }
      }
    }
    """
    variables = {
        "projectId": PROJECT_ID,
        "itemId": item_id,
        "fieldId": field_id,
        "optionId": option_id
    }
    data = query_graphql(mutation, variables)
    return data is not None


def add_comment_to_task(content_id, content_type, comment_body, item_id=None):
    if not content_id:
        print("No se puede comentar: ID de contenido no disponible.")
        return False
        
    if content_type == "Issue":
        mutation = """
        mutation($subjectId: ID!, $body: String!) {
          addComment(input: {subjectId: $subjectId, body: $body}) {
            commentEdge {
              node {
                id
              }
            }
          }
        }
        """
        variables = {
            "subjectId": content_id,
            "body": comment_body
        }
        data = query_graphql(mutation, variables)
        if data:
            print("[OK] Comentario agregado exitosamente al Issue de GitHub.")
            return True
            
    elif content_type == "DraftIssue":
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $body: String!) {
          updateProjectV2DraftIssue(
            input: {
              projectId: $projectId
              itemId: $itemId
              body: $body
            }
          ) {
            projectV2DraftIssue {
              id
            }
          }
        }
        """
        variables = {
            "projectId": PROJECT_ID,
            "itemId": item_id,
            "body": comment_body
        }
        data = query_graphql(mutation, variables)
        if data:
            print("[OK] Descripción de la nota borrador (Draft Issue) actualizada en GitHub.")
            return True
    else:
        print(f"Tipo de contenido '{content_type}' no es compatible con comentarios/notas.")
    return False

def get_viewer_id():
    query = """
    query {
      viewer {
        id
      }
    }
    """
    data = query_graphql(query)
    if data:
        return data.get("viewer", {}).get("id")
    return None

def assign_user_to_issue(issue_id, user_id):
    mutation = """
    mutation($assignableId: ID!, $assigneeIds: [ID!]!) {
      addAssigneesToAssignable(input: {assignableId: $assignableId, assigneeIds: $assigneeIds}) {
        assignable {
          ... on Issue {
            id
          }
        }
      }
    }
    """
    data = query_graphql(mutation, {"assignableId": issue_id, "assigneeIds": [user_id]})
    if data:
        print("[OK] Usuario asignado exitosamente al Issue en GitHub.")
        return True
    return False

def update_issue_body(issue_id, new_body):
    mutation = """
    mutation($id: ID!, $body: String!) {
      updateIssue(input: {id: $id, body: $body}) {
        issue {
          id
        }
      }
    }
    """
    data = query_graphql(mutation, {"id": issue_id, "body": new_body})
    if data:
        return True
    return False

def fix_body_architecture(body):
    body = re.sub(r'apps/(\w+)/infrastructure/models\.py', r'backend/\1/models.py', body)
    body = re.sub(r'apps/(\w+)/infrastructure/', r'backend/\1/', body)
    body = re.sub(r'apps/(\w+)/interfaces/', r'backend/\1/', body)
    body = re.sub(r'apps/(\w+)/application/', r'backend/\1/', body)
    body = re.sub(r'apps/(\w+)/domain/', r'backend/\1/', body)
    body = re.sub(r'apps/(\w+)', r'backend/\1', body)
    body = re.sub(r'Arquitectura Hexagonal', r'Arquitectura Tradicional de Django', body, flags=re.IGNORECASE)
    body = re.sub(r'Capas \(Arquitectura Hexagonal\):[^\n]*', r'Arquitectura: Django tradicional (models, views, serializers)', body, flags=re.IGNORECASE)
    body = re.sub(r'capas \(arquitectura hexagonal\):[^\n]*', r'Arquitectura: Django tradicional (models, views, serializers)', body, flags=re.IGNORECASE)
    return body

def show_summary(items):
    summary = {k: 0 for k in STATUS_OPTIONS.keys()}
    for item in items:
        if item["status"] in summary:
            summary[item["status"]] += 1
            
    print("\n=== RESUMEN DEL KANBAN ===")
    for status, count in summary.items():
        print(f"  [{status}]: {count} tareas")
    print("==========================")
