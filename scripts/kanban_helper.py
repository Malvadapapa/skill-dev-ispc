"""FCCApp Kanban Helper CLI - Punto de entrada principal.
Importa submódulos por dominio y expone el parser de argumentos CLI.

Módulos internos:
  _config.py         - Configuración (.env, constantes, headers)
  _github_api.py     - API GraphQL de GitHub (estados, comentarios)
  _git_utils.py      - Utilidades Git (ramas, commits)
  _google_auth.py    - OAuth2 de Google y configuración del desarrollador
  _google_sheets.py  - Integración con Google Sheets API
  _docs.py           - Documentos locales, Google Docs y wiki
  _pull_requests.py  - CRUD de Pull Requests
  _tickets.py        - Issues, etiquetas, campos de proyecto
  _menu.py           - Menú interactivo
"""

import os
import sys
import argparse
import subprocess

# Agregar el directorio de scripts al path para imports de submódulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _config import (
    _check_token, TOKEN, ORG, PROJECT_NUMBER, DEV_BRANCH_NAME,
    GITHUB_REPO, DEFAULT_GOOGLE_SHEET_URL, SKILL_DIR, PROJECT_ROOT,
    REPO_DIR, PROJECT_ID, STATUS_OPTIONS, STATUS_BY_ID
)
from _github_api import (
    query_graphql, fetch_project_items, update_item_status,
    update_item_single_select_field, add_comment_to_task,
    get_viewer_id, assign_user_to_issue, update_issue_body,
    fix_body_architecture, show_summary
)
from _git_utils import (
    run_git, get_current_branch, get_branch_name_from_title,
    create_and_checkout_branch, commit_and_push_changes
)
from _google_auth import (
    _get_valid_google_token, check_user_status,
    update_dev_config, login_google_oauth
)
from _google_sheets import (
    write_google_sheet, update_google_sheet_task_status,
    sync_google_sheet_dependencies, sync_backlog_stories_with_kanban,
    add_team_reference_table_to_sheet, update_batch_tasks_traceability,
    audit_sheets_vs_kanban, list_google_drive_sheets,
    sync_testing_matrix_modulo5
)
from _docs import (
    read_docx_text, list_project_docs, search_project_docs,
    fetch_google_doc, read_doc_file, update_wiki
)
from _pull_requests import (
    create_pull_request, list_pull_requests, inspect_pull_request,
    approve_pull_request, request_changes_pull_request,
    dismiss_pull_request_review, merge_pull_request
)
from _tickets import (
    find_item_by_tk_id, get_repository_id, create_github_issue,
    add_issue_to_project, get_repo_labels, add_labels_to_issue,
    apply_labels_by_names, create_and_add_ticket,
    list_project_fields, update_item_field_by_names
)
from _menu import menu_main


def handle_cli_arguments():
    parser = argparse.ArgumentParser(description="FCCApp Kanban Helper CLI - Automatizador de Tareas (ISPC Dev Skill)")
    parser.add_argument("--list", action="store_true", help="Listar todas las tareas del tablero")
    parser.add_argument("--summary", action="store_true", help="Mostrar resumen cuantitativo de las columnas")
    parser.add_argument("--task", metavar="TK_ID", help="ID de la tarea a gestionar (ej. TK001)")
    parser.add_argument("--start", action="store_true", help="Iniciar la tarea especificada (mover a In Progress y crear rama)")
    parser.add_argument("--status", metavar="ESTADO", help="Mover la tarea especificada a un nuevo estado (ej. 'In Review', 'Done')")
    parser.add_argument("--message", metavar="TEXTO", help="Agregar un comentario o descripción de avances a la tarea especificada")
    parser.add_argument("--message-file", metavar="PATH", help="Agregar un comentario a la tarea leyendo el contenido de un archivo")
    parser.add_argument("--fix-architecture", action="store_true", help="Corregir referencias de arquitectura hexagonal a Django tradicional en todos los tickets")
    parser.add_argument("--wiki", nargs="?", const="list", help="Consultar la wiki del proyecto. Ej: --wiki 'Modelo-de-Datos' o --wiki list para listar páginas o --wiki pull para actualizar.")
    parser.add_argument("--update-wiki", action="store_true", help="Actualizar la wiki local haciendo git pull")
    parser.add_argument("--create-ticket", metavar="TITULO", help="Crear un nuevo ticket e incorporarlo al proyecto")
    parser.add_argument("--body", metavar="TEXTO", help="Cuerpo o descripción del nuevo ticket")
    parser.add_argument("--labels", metavar="LIST", help="Etiquetas separadas por comas a aplicar al nuevo ticket")
    parser.add_argument("--add-labels", metavar="LIST", help="Etiquetas separadas por comas a aplicar al ticket especificado por --task")
    parser.add_argument("--list-fields", action="store_true", help="Listar todos los campos personalizados y opciones del proyecto V2")
    parser.add_argument("--set-field", metavar="FIELD_NAME", help="Nombre del campo a actualizar en la tarea especificada por --task")
    parser.add_argument("--value", metavar="VALUE", help="Valor a asignar al campo de la tarea especificada por --task")
    parser.add_argument("--update-body", metavar="TEXTO", help="Actualizar la descripción/cuerpo del ticket especificado por --task")
    parser.add_argument("--update-body-file", metavar="PATH", help="Actualizar la descripción/cuerpo del ticket especificado por --task usando el contenido de un archivo")
    parser.add_argument("--create-pr", action="store_true", help="Crear un Pull Request en GitHub")
    parser.add_argument("--list-prs", action="store_true", help="Listar todos los Pull Requests abiertos en el repositorio")
    parser.add_argument("--pr", metavar="PR_NUMBER", type=int, help="Analizar e inspeccionar un Pull Request específico por su número")
    parser.add_argument("--approve-pr", metavar="PR_NUMBER", type=int, help="Aprobar un Pull Request y dejar un comentario de revisión")
    parser.add_argument("--request-changes-pr", metavar="PR_NUMBER", type=int, help="Solicitar cambios (REQUEST_CHANGES) en un Pull Request")
    parser.add_argument("--dismiss-review-pr", metavar="PR_NUMBER", type=int, help="Desestimar (dismiss) una revisión previa de un Pull Request")
    parser.add_argument("--review-id", metavar="REVIEW_ID", help="ID de la revisión a desestimar en --dismiss-review-pr")
    parser.add_argument("--merge-pr", metavar="PR_NUMBER", type=int, help="Realizar el merge/fusión de un Pull Request aprobado")
    parser.add_argument("--comment", metavar="TEXTO", help="Comentario o cuerpo para la aprobación/solicitud del Pull Request")
    parser.add_argument("--head", metavar="BRANCH", help="Rama origen para el Pull Request")
    parser.add_argument("--base", metavar="BRANCH", default="develop", help="Rama destino para el Pull Request (default: develop)")
    parser.add_argument("--pr-title", metavar="TITULO", help="Título del Pull Request")
    parser.add_argument("--pr-body", metavar="TEXTO", help="Cuerpo o descripción del Pull Request")
    parser.add_argument("--pr-body-file", metavar="PATH", help="Cuerpo o descripción del Pull Request leyendo el contenido de un archivo")
    parser.add_argument("--assign", action="store_true", help="Asignar la tarea especificada por --task al usuario autenticado en GitHub")
    parser.add_argument("--docs", nargs="?", const="list", help="Gestión de documentos del proyecto. Usá --docs list para listar o --docs search '<query>'")
    parser.add_argument("--docs-search", metavar="QUERY", help="Buscar un término o concepto en todos los documentos del proyecto (.md, .txt, .docx)")
    parser.add_argument("--docs-read", metavar="PATH", help="Leer el contenido completo de un documento (.md, .txt, .docx)")
    parser.add_argument("--docs-update", metavar="PATH", help="Crear o actualizar un documento del proyecto usando el contenido de --body o --body-file")
    parser.add_argument("--update-sheet", metavar="URL", help="Actualizar el estado de una tarea especificada por --task en una planilla de Google Sheets")
    parser.add_argument("--sheet-name", metavar="NAME", default="Sprint 2", help="Nombre de la pestaña del Google Sheet a actualizar (default: 'Sprint 2')")
    parser.add_argument("--assignee", metavar="NAME", default=None, help="Nombre del responsable para la tarea en Google Sheets (ej: 'CRISTIAN')")
    parser.add_argument("--add-team-table", metavar="URL", help="Agregar la tabla de referencia de miembros de equipo al costado del Backlog en Google Sheets")
    parser.add_argument("--update-batch-traceability", metavar="URL", help="Actualizar la trazabilidad completa (US, Estimación, Dependencias) en Google Sheets para un lote de tareas")
    parser.add_argument("--start-tk", type=int, default=1, help="Número de inicio para la actualización por lotes (default: 1)")
    parser.add_argument("--end-tk", type=int, default=10, help="Número de fin para la actualización por lotes (default: 10)")
    parser.add_argument("--audit", metavar="URL", help="Auditar celda por celda la matriz de Google Sheets contra el estado en vivo del Kanban de GitHub")
    parser.add_argument("--list-sheets", action="store_true", help="Listar las planillas de Google Sheets disponibles en la cuenta autenticada")
    parser.add_argument("--sync-dependencies", metavar="URL", help="Sincronizar la columna de Dependencias en Google Sheets con las dependencias oficiales del Kanban de GitHub")
    parser.add_argument("--sync-backlog", metavar="URL", help="Sincronizar la columna de Estado en la pestaña Backlog de Google Sheets con el estado de las tareas en el Kanban de GitHub")
    parser.add_argument("--sync-testing-matrix", action="store_true", help="Sube las 5 evidencias a Google Drive y registra los casos de prueba del Módulo 5 en Google Sheets")
    parser.add_argument("--figma-status", action="store_true", help="Mostrar el estado del módulo de Figma y sus configuraciones")
    parser.add_argument("--info", action="store_true", help="Mostrar información de configuración actual del skill")
    parser.add_argument("--check-user", action="store_true", help="Verificar el estado del usuario activo (rama, github token y sesión Google OAuth)")
    parser.add_argument("--google-login", "--login-google", action="store_true", help="Inicia sesión con Google OAuth solo si no hay un usuario activo")
    parser.add_argument("--force-login", action="store_true", help="Fuerza la re-autenticación abriendo el navegador aunque ya exista una sesión activa")
    parser.add_argument("--config-dev", action="store_true", help="Actualiza la configuración del desarrollador (.env)")
    parser.add_argument("--dev-branch", metavar="BRANCH_NAME", help="Nombre de la rama personal de desarrollo a guardar en .env")
    parser.add_argument("--github-token", metavar="TOKEN", help="Token de acceso personal de GitHub a guardar en .env")
    
    args = parser.parse_args()
    
    if not (args.list or args.summary or args.task or args.start or args.status or args.message or args.message_file or args.fix_architecture or args.wiki or args.update_wiki or args.create_ticket or args.add_labels or args.list_fields or args.set_field or args.update_body or args.update_body_file or args.create_pr or args.list_prs or args.pr or args.approve_pr or args.request_changes_pr or args.dismiss_review_pr or args.merge_pr or args.info or args.docs or args.docs_search or args.docs_read or args.docs_update or args.assign or args.update_sheet or args.list_sheets or args.add_team_table or args.update_batch_traceability or args.audit or args.sync_dependencies or args.sync_backlog or args.check_user or args.google_login or args.force_login or args.config_dev or args.dev_branch or args.github_token or args.figma_status or args.sync_testing_matrix):
        return False

    if args.sync_testing_matrix:
        sync_testing_matrix_modulo5()
        return True

    if args.figma_status:
        from _figma import show_figma_status
        show_figma_status()
        return True

    if args.check_user:
        check_user_status()
        return True

    if args.config_dev or args.dev_branch or args.github_token:
        update_dev_config(branch_name=args.dev_branch, github_token=args.github_token)
        return True

    if args.google_login or args.force_login:
        login_google_oauth(force=args.force_login)
        return True

    if args.sync_backlog:
        sync_backlog_stories_with_kanban(args.sync_backlog, args.sheet_name)
        return True

    if args.sync_dependencies:
        sync_google_sheet_dependencies(args.sync_dependencies, args.sheet_name)
        return True

    if args.audit:
        audit_sheets_vs_kanban(args.audit, args.sheet_name)
        return True

    if args.list_prs:
        list_pull_requests()
        return True

    if args.pr:
        inspect_pull_request(args.pr)
        return True

    if args.approve_pr:
        comm_text = args.comment if args.comment else ""
        if args.message_file and os.path.exists(args.message_file):
            with open(args.message_file, "r", encoding="utf-8") as f_in:
                comm_text = f_in.read()
        approve_pull_request(args.approve_pr, comm_text)
        return True

    if args.request_changes_pr:
        comm_text = args.comment if args.comment else ""
        if args.message_file and os.path.exists(args.message_file):
            with open(args.message_file, "r", encoding="utf-8") as f_in:
                comm_text = f_in.read()
        request_changes_pull_request(args.request_changes_pr, comm_text)
        return True

    if args.dismiss_review_pr:
        if not args.review_id:
            print("[ERROR] Debes especificar el ID de la revisión usando --review-id <ID>.")
            return True
        comm_text = args.comment if args.comment else "Desestimando aprobación errónea previa."
        dismiss_pull_request_review(args.dismiss_review_pr, args.review_id, comm_text)
        return True

    if args.merge_pr:
        merge_pull_request(args.merge_pr)
        return True

    if args.list_sheets:
        list_google_drive_sheets()
        return True

    if args.add_team_table:
        add_team_reference_table_to_sheet(args.add_team_table, args.sheet_name)
        return True

    if args.update_batch_traceability:
        update_batch_tasks_traceability(args.update_batch_traceability, args.sheet_name, args.start_tk, args.end_tk)
        return True

    if args.update_sheet:
        if not args.task:
            print("[ERROR] Debes especificar la tarea usando --task <TK_ID>.")
            return True
        update_google_sheet_task_status(args.update_sheet, args.task, args.status, args.sheet_name, args.assignee)
        return True

    if args.docs or args.docs_search or args.docs_read or args.docs_update:
        if args.docs_search:
            results = search_project_docs(args.docs_search)
            print(f"\n=== RESULTADOS DE BÚSQUEDA PARA: '{args.docs_search}' ===")
            if not results:
                print("No se encontraron coincidencias en los documentos.")
            else:
                for rel_path, snippets in results:
                    print(f"\n📄 Archivo: {rel_path}")
                    for snip in snippets:
                        print(f"   {snip}")
            print("========================================================\n")
            return True

        if args.docs_read:
            content = read_doc_file(args.docs_read)
            if content is not None:
                print(f"\n=== CONTENIDO DE: {args.docs_read} ===")
                print(content)
                print("========================================================\n")
            return True

        if args.docs_update:
            filepath = args.docs_update
            if not os.path.isabs(filepath):
                filepath = os.path.abspath(os.path.join(PROJECT_ROOT, filepath))
            body_text = args.body if args.body else ""
            if args.update_body_file and os.path.exists(args.update_body_file):
                with open(args.update_body_file, "r", encoding="utf-8") as f_in:
                    body_text = f_in.read()
            if not body_text:
                print("[ERROR] Debes especificar el contenido mediante --body '<texto>' o --update-body-file <path>.")
                return True
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f_out:
                f_out.write(body_text)
            print(f"[OK] Documento '{filepath}' guardado/actualizado exitosamente.")
            return True

        docs = list_project_docs()
        print("\n=== DOCUMENTOS DEL PROYECTO ENCONTRADOS ===")
        for fname, rel_path, full_path in sorted(docs, key=lambda x: x[1]):
            print(f"  - [{fname}] ({rel_path})")
        print("===========================================\n")
        return True

    if args.info:
        print("\n=== CONFIGURACIÓN DEL SKILL ISPC DEV ===")
        print(f"  Directorio del skill: {SKILL_DIR}")
        print(f"  Raíz del proyecto:    {PROJECT_ROOT}")
        print(f"  Directorio del repo:  {REPO_DIR}")
        print(f"  Organización GitHub:  {ORG}")
        print(f"  Repositorio:          {GITHUB_REPO}")
        print(f"  Proyecto #:           {PROJECT_NUMBER}")
        print(f"  Rama del dev:         {DEV_BRANCH_NAME or '(no configurada)'}")
        print(f"  Token configurado:    {'Sí' if TOKEN and TOKEN != 'ghp_tu_token_aqui' else 'No'}")
        wiki_dir = os.path.join(SKILL_DIR, "wiki")
        print(f"  Wiki disponible:      {'Sí' if os.path.exists(wiki_dir) and os.listdir(wiki_dir) else 'No'}")
        print("========================================\n")
        return True
        
    if args.list_fields:
        list_project_fields()
        return True

    if args.update_wiki:
        update_wiki()
        return True

    if args.create_pr:
        title = args.pr_title
        if not title:
            print("[ERROR] Debes especificar un título usando --pr-title '<titulo>'.")
            return True
        
        head = args.head
        if not head:
            if DEV_BRANCH_NAME:
                head = DEV_BRANCH_NAME
            else:
                try:
                    res = subprocess.run(["git", "branch", "--show-current"], cwd=REPO_DIR, capture_output=True, text=True, check=True)
                    head = res.stdout.strip()
                except Exception:
                    print("[ERROR] No se pudo determinar la rama origen. Usá --head <rama> o configurá DEV_BRANCH_NAME en .env.")
                    return True
        
        body = args.pr_body if args.pr_body else ""
        if args.pr_body_file:
            if os.path.exists(args.pr_body_file):
                with open(args.pr_body_file, "r", encoding="utf-8") as f_in:
                    body = f_in.read().strip()
            else:
                print(f"[ERROR] El archivo de cuerpo de PR '{args.pr_body_file}' no existe.")
                return True
                
        create_pull_request(title=title, head=head, base=args.base, body=body)
        return True

    if args.create_ticket:
        body = args.body if args.body else ""
        labels = [l.strip() for l in args.labels.split(",")] if args.labels else []
        create_and_add_ticket(args.create_ticket, body, labels)
        return True

    if args.summary:
        items = fetch_project_items()
        show_summary(items)
        return True
        
    if args.wiki:
        wiki_dir = os.path.join(SKILL_DIR, "wiki")
        if not os.path.exists(wiki_dir):
            print(f"[ERROR] No se encontró el directorio de la wiki en '{wiki_dir}'.")
            print("        Para configurar la wiki, cloná el repo wiki dentro del skill:")
            print(f"        git clone https://github.com/{ORG}/{GITHUB_REPO}.wiki.git {wiki_dir}")
            return True
            
        action = args.wiki.strip().lower()
        if action in ("pull", "update"):
            update_wiki()
            return True
            
        files = [f for f in os.listdir(wiki_dir) if f.endswith(".md") and not f.startswith("_")]
        if action == "list":
            print("\n=== PÁGINAS DE LA WIKI DISPONIBLES ===")
            for f in sorted(files):
                print(f"  - {f[:-3]}")
            print("======================================\n")
            return True
            
        target_file = None
        for f in files:
            name_no_ext = f[:-3].lower()
            if name_no_ext == action or name_no_ext.replace("-", " ") == action.replace("-", " ") or name_no_ext.replace("_", " ") == action.replace("_", " "):
                target_file = f
                break
        
        if not target_file:
            for f in files:
                if action in f.lower():
                    target_file = f
                    break
                    
        if target_file:
            path = os.path.join(wiki_dir, target_file)
            print(f"\n=== WIKI: {target_file[:-3]} ===")
            with open(path, "r", encoding="utf-8") as f_in:
                print(f_in.read())
            print("======================================\n")
        else:
            print(f"[ERROR] No se encontró la página '{args.wiki}' en la wiki.")
            print("Páginas disponibles:")
            for f in sorted(files):
                print(f"  - {f[:-3]}")
        return True
        
    if args.fix_architecture:
        print("Buscando y corrigiendo referencias arquitectónicas en los tickets...")
        items = fetch_project_items()
        fixed_count = 0
        for item in items:
            if item.get("content_type") == "Issue" and item.get("body"):
                original_body = item["body"]
                fixed_body = fix_body_architecture(original_body)
                if original_body != fixed_body:
                    print(f"Modificando Tarea: {item['title']} (Issue #{item['number']})")
                    if update_issue_body(item["content_id"], fixed_body):
                        print(f"  [OK] Ticket #{item['number']} actualizado.")
                        fixed_count += 1
                    else:
                        print(f"  [ERROR] Falló actualización del ticket #{item['number']}.")
        print(f"\n[OK] Proceso terminado. Se actualizaron {fixed_count} tickets.")
        return True
        
    if args.list:
        items = fetch_project_items()
        columns = {}
        for item in items:
            stat = item["status"]
            if stat not in columns:
                columns[stat] = []
            columns[stat].append(item)
            
        print("\n=== DETALLE DE TAREAS EN EL TABLERO ===")
        for col_name in STATUS_OPTIONS.keys():
            col_items = columns.get(col_name, [])
            print(f"\n* {col_name.upper()} ({len(col_items)} tareas):")
            for item in col_items:
                num_str = f"#{item['number']}" if item['number'] else "Draft"
                print(f"  - [{num_str}] {item['title']}")
        return True
        
    if args.task:
        item = find_item_by_tk_id(args.task)
        if not item:
            print(f"[ERROR] No se encontró ninguna tarea con el ID '{args.task}'.")
            return True
            
        print(f"\n==================================================")
        print(f" TAREA: {item['title']}")
        print(f" Estado actual: {item['status']}")
        print(f" Issue: #{item['number']}" if item['number'] else " Nota Borrador")
        print(f"==================================================")
        if item.get("body"):
            print("\n--- DESCRIPCIÓN / CRITERIOS DE ACEPTACIÓN ---")
            print(item["body"])
            print("==================================================\n")

        if args.add_labels:
            labels = [l.strip() for l in args.add_labels.split(",")]
            apply_labels_by_names(item["content_id"], labels)

        if args.assign:
            if item.get("content_type") == "Issue":
                viewer_id = get_viewer_id()
                if viewer_id:
                    assign_user_to_issue(item["content_id"], viewer_id)
            else:
                print("[WARN] Solo se pueden asignar usuarios a tarjetas de tipo Issue.")

        if args.set_field:
            if not args.value:
                print("[ERROR] Debes especificar un valor usando --value '<valor>' para actualizar el campo.")
            else:
                update_item_field_by_names(item["id"], args.set_field, args.value)
        
        if args.message:
            add_comment_to_task(item["content_id"], item["content_type"], args.message, item["id"])
            
        if args.message_file:
            if not os.path.exists(args.message_file):
                print(f"[ERROR] El archivo '{args.message_file}' no existe.")
            else:
                with open(args.message_file, "r", encoding="utf-8") as f_in:
                    message_content = f_in.read().strip()
                add_comment_to_task(item["content_id"], item["content_type"], message_content, item["id"])
            
        if args.update_body:
            if item.get("content_type") == "Issue":
                if update_issue_body(item["content_id"], args.update_body):
                    print(f"[OK] Body del ticket #{item['number']} actualizado exitosamente en GitHub.")
                else:
                    print(f"[ERROR] Error al actualizar el body del ticket #{item['number']}.")
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
                    projectV2DraftIssue {
                      id
                    }
                  }
                }
                """
                variables = {
                    "projectId": PROJECT_ID,
                    "itemId": item["id"],
                    "body": args.update_body
                }
                data = query_graphql(mutation, variables)
                if data:
                    print("[OK] Descripción de la nota borrador actualizada en GitHub.")
                else:
                    print("[ERROR] Error al actualizar nota borrador.")
            
        if args.update_body_file:
            if not os.path.exists(args.update_body_file):
                print(f"[ERROR] El archivo '{args.update_body_file}' no existe.")
            else:
                with open(args.update_body_file, "r", encoding="utf-8") as f_in:
                    body_content = f_in.read().strip()
                if item.get("content_type") == "Issue":
                    if update_issue_body(item["content_id"], body_content):
                        print(f"[OK] Body del ticket #{item['number']} actualizado exitosamente en GitHub desde archivo.")
                    else:
                        print(f"[ERROR] Error al actualizar el body del ticket #{item['number']}.")
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
                        projectV2DraftIssue {
                          id
                        }
                      }
                    }
                    """
                    variables = {
                        "projectId": PROJECT_ID,
                        "itemId": item["id"],
                        "body": body_content
                    }
                    data = query_graphql(mutation, variables)
                    if data:
                        print("[OK] Descripción de la nota borrador actualizada en GitHub desde archivo.")
                    else:
                        print("[ERROR] Error al actualizar nota borrador.")

        if args.start:
            success = update_item_status(item["id"], "In Progress")
            if success:
                update_google_sheet_task_status(DEFAULT_GOOGLE_SHEET_URL, args.task, "IN PROGRESS", assignee="CRISTIAN")
                if item.get("content_type") == "Issue":
                    viewer_id = get_viewer_id()
                    if viewer_id:
                        assign_user_to_issue(item["content_id"], viewer_id)
                branch_name = get_branch_name_from_title(item["title"])
                create_and_checkout_branch(branch_name)
                print(f"[OK] Tarea '{args.task}' iniciada con éxito.")
                
        elif args.status:
            target_status = None
            for key in STATUS_OPTIONS.keys():
                if key.lower() == args.status.lower().strip():
                    target_status = key
                    break
            if not target_status:
                print(f"[ERROR] Estado '{args.status}' no válido. Opciones válidas: {list(STATUS_OPTIONS.keys())}")
            else:
                success = update_item_status(item["id"], target_status)
                if success:
                    update_google_sheet_task_status(DEFAULT_GOOGLE_SHEET_URL, args.task, target_status)
        return True
    else:
        if args.start or args.status or args.message:
            print("[ERROR] Debes especificar el ID de la tarea con --task <TK_ID> para realizar esta acción.")
        return True

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    _check_token()
    if not handle_cli_arguments():
        menu_main()
