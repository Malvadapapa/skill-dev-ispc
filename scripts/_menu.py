"""Menú interactivo CLI para el Kanban Helper."""

from _config import STATUS_OPTIONS, GITHUB_REPO
from _github_api import fetch_project_items, update_item_status, add_comment_to_task, get_viewer_id, assign_user_to_issue, show_summary
from _git_utils import get_branch_name_from_title, create_and_checkout_branch, commit_and_push_changes


def menu_main():
    while True:
        print("\n==================================")
        print("   FCCApp Kanban Helper CLI       ")
        print("==================================")
        print("1. Ver resumen del tablero")
        print("2. Listar tareas pendientes ('Todo') e iniciar una")
        print("3. Ver tareas en curso ('In Progress') y gestionarlas")
        print("4. Salir")
        print("==================================")
        
        choice = input("Selecciona una opción: ").strip()
        
        if choice == '1':
            items = fetch_project_items()
            show_summary(items)
        elif choice == '2':
            items = fetch_project_items()
            todo_items = [i for i in items if i["status"] == "Todo"]
            
            if not todo_items:
                print("\nNo hay tareas en la columna 'Todo'.")
                continue
                
            print("\nTareas pendientes ('Todo'):")
            for idx, item in enumerate(todo_items, start=1):
                print(f"  {idx}. {item['title']} (Issue #{item['number']})")
                
            task_choice = input("\nSelecciona el número de la tarea para iniciar (o Enter para cancelar): ").strip()
            if not task_choice.isdigit():
                continue
                
            task_idx = int(task_choice) - 1
            if 0 <= task_idx < len(todo_items):
                selected_item = todo_items[task_idx]
                print(f"\nHas seleccionado: {selected_item['title']}")
                
                success = update_item_status(selected_item["id"], "In Progress")
                if success:
                    if selected_item.get("content_type") == "Issue":
                        viewer_id = get_viewer_id()
                        if viewer_id:
                            assign_user_to_issue(selected_item["content_id"], viewer_id)
                    branch_name = get_branch_name_from_title(selected_item["title"])
                    create_and_checkout_branch(branch_name)
                    print(f"\n¡Listo! Estás en la rama '{branch_name}' en el repositorio {GITHUB_REPO}.")
            else:
                print("Selección inválida.")
                
        elif choice == '3':
            items = fetch_project_items()
            in_progress_items = [i for i in items if i["status"] == "In Progress"]
            
            if not in_progress_items:
                print("\nNo hay tareas activas en 'In Progress'.")
                continue
                
            print("\nTareas en curso ('In Progress'):")
            for idx, item in enumerate(in_progress_items, start=1):
                print(f"  {idx}. {item['title']} (Issue #{item['number']})")
                
            task_choice = input("\nSelecciona el número de la tarea para gestionar (o Enter para cancelar): ").strip()
            if not task_choice.isdigit():
                continue
                
            task_idx = int(task_choice) - 1
            if 0 <= task_idx < len(in_progress_items):
                selected_item = in_progress_items[task_idx]
                print(f"\nGestionando: {selected_item['title']}")
                print("1. Mover a 'In Review' (para revisión)")
                print("2. Mover a 'Testing'")
                print("3. Mover a 'Done' (finalizada)")
                print("4. Agregar comentario / descripción de avances (sin cambiar de columna)")
                print("5. Volver al menú")
                
                action_choice = input("Selecciona una acción: ").strip()
                target_status = None
                
                if action_choice == '1':
                    target_status = "In Review"
                elif action_choice == '2':
                    target_status = "Testing"
                elif action_choice == '3':
                    target_status = "Done"
                elif action_choice == '4':
                    comment = input("\nIngresa el comentario o descripción detallada de lo que hiciste:\n").strip()
                    if comment:
                        add_comment_to_task(selected_item["content_id"], selected_item["content_type"], comment, selected_item["id"])
                    else:
                        print("Comentario vacío. No se envió nada.")
                    continue
                    
                if target_status:
                    add_comm = input(f"¿Deseas agregar un comentario/descripción de avances a la tarea en GitHub antes de moverla a '{target_status}'? (s/n): ").strip().lower()
                    if add_comm == 's':
                        comment = input("\nIngresa el comentario o descripción detallada de lo que hiciste:\n").strip()
                        if comment:
                            add_comment_to_task(selected_item["content_id"], selected_item["content_type"], comment, selected_item["id"])
                            
                    commit_success = commit_and_push_changes(selected_item["title"])
                    update_item_status(selected_item["id"], target_status)
            else:
                print("Selección inválida.")
                
        elif choice == '4':
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida.")
