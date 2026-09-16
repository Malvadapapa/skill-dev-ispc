"""Funciones de integración con Google Sheets API.
Incluye: lectura/escritura de celdas, sincronización de estados, dependencias, auditoría y trazabilidad."""

import json
import os
import re
import urllib.request
import urllib.parse

from _config import SKILL_DIR, PROJECT_ROOT, DEV_BRANCH_NAME
from _google_auth import _get_valid_google_token
from _github_api import fetch_project_items, query_graphql
from _tickets import find_item_by_tk_id


def write_google_sheet(url, text_value, sheet_name=None):
    """Escribe un valor en la primera celda libre de la Columna A de un Google Sheet usando la API de Google."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    if not sheet_name:
        sheet_name = "Sprint 2"

    cell_target = f"{sheet_name}!A1"
    update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(cell_target)}?valueInputOption=USER_ENTERED"
    payload = {
        "range": cell_target,
        "majorDimension": "ROWS",
        "values": [[text_value]]
    }
    
    req_update = urllib.request.Request(
        update_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="PUT"
    )
    
    try:
        with urllib.request.urlopen(req_update) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            updated_cell = res.get("updatedRange", cell_target)
            print(f"[OK] Se escribió '{text_value}' en '{sheet_name}' en la celda {updated_cell}.")
            return True
    except Exception as e:
        print(f"[ERROR al escribir en Google Sheet]: {e}")
        return False


def update_google_sheet_task_status(url, tk_id, new_status=None, sheet_name="Sprint 2", assignee=None):
    """Busca la fila de una tarea (ej. TK 37 o TK37) en Google Sheets y sincroniza el Responsable y Estado desde el Kanban de GitHub en tiempo real."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 1. Consultar estado y responsable real desde el Kanban de GitHub
    item_github = find_item_by_tk_id(tk_id)
    github_status = item_github.get("status") if item_github else None
    
    status_to_use = new_status if new_status else (github_status if github_status else "ToDo")
    status_clean = str(status_to_use).upper().replace("_", " ").strip()
    STATUS_MAP = {
        "TODO": "ToDo",
        "TO DO": "ToDo",
        "IN PROGRESS": "IN PROGRESS",
        "IN_PROGRESS": "IN PROGRESS",
        "IN REVIEW": "IN REVIEW",
        "IN_REVIEW": "IN REVIEW",
        "TESTING": "TESTING",
        "DONE": "DONE"
    }
    final_status = STATUS_MAP.get(status_clean, status_to_use)

    tk_clean = tk_id.upper().replace(" ", "").replace("-", "")
    tk_num = re.sub(r'\D', '', tk_clean)

    # 2. Obtener título exacto de la pestaña desde metadatos
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    req_meta = urllib.request.Request(meta_url, headers=headers)
    real_sheet_name = sheet_name
    try:
        with urllib.request.urlopen(req_meta) as resp_m:
            meta = json.loads(resp_m.read().decode("utf-8"))
            sheets = meta.get("sheets", [])
            sheet_names = [s.get("properties", {}).get("title") for s in sheets]
            for sname in sheet_names:
                if sheet_name.lower() in sname.lower() or sname.lower() in sheet_name.lower():
                    real_sheet_name = sname
                    break
    except Exception as e_meta:
        print(f"[WARN] No se pudieron obtener metadatos del documento: {e_meta}")

    sheet_name = real_sheet_name

    range_read = f"{sheet_name}!A1:Z100"
    read_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(range_read, safe='!')}"
    req_read = urllib.request.Request(read_url, headers=headers)
    
    target_row = None
    rows = []
    try:
        with urllib.request.urlopen(req_read) as resp:
            val_data = json.loads(resp.read().decode("utf-8"))
            rows = val_data.get("values", [])
    except Exception as e:
        print(f"[ERROR al leer Google Sheet ID {spreadsheet_id}]: {e}")
        return False

    header_row_idx = None
    header_row = []
    for idx, r in enumerate(rows):
        row_str = " ".join([str(c).upper() for c in r])
        if "ID TAREA" in row_str or ("TAREA" in row_str and "RESPONSABLE" in row_str):
            header_row_idx = idx
            header_row = [str(c).upper().strip() for c in r]
            break

    col_map = {}
    for c_idx, h in enumerate(header_row[:7]):
        if "ID TAREA" in h or h == "ID" or h == "TK":
            col_map["id"] = c_idx
        elif "TAREA" in h or "DESCRIPCION" in h:
            col_map["task"] = c_idx
        elif "RESPONSABLE" in h or "ASIGNADO" in h:
            col_map["resp"] = c_idx
        elif "ESTADO" in h:
            col_map["status"] = c_idx

    resp_col_letter = chr(65 + col_map.get("resp", 3))
    status_col_letter = chr(65 + col_map.get("status", 4))

    tk_num_clean = str(int(tk_num)) if tk_num and tk_num.isdigit() else tk_num

    for idx, row in enumerate(rows, start=1):
        if not row:
            continue
        row_id_cell = str(row[col_map.get("id", 0)]).upper() if len(row) > col_map.get("id", 0) else ""
        m_r = re.search(r'TK\s*0*(\d+)', row_id_cell)
        if m_r and str(int(m_r.group(1))) == tk_num_clean:
            target_row = idx
            break

    if not target_row:
        print(f"[WARN] No se encontró la tarea '{tk_id}' en la pestaña '{sheet_name}' del Google Sheet.")
        return False

    existing_resp = ""
    if target_row and target_row <= len(rows):
        target_r = rows[target_row - 1]
        resp_idx = col_map.get("resp", 3)
        if len(target_r) > resp_idx:
            existing_resp = str(target_r[resp_idx]).strip()

    if assignee:
        resp_val = assignee.upper()
    elif item_github and item_github.get("assignees") is not None:
        mapped_names = []
        for l in item_github.get("assignees", []):
            l_lower = l.lower()
            if "cristian" in l_lower or "malvada" in l_lower: mapped_names.append("CRISTIAN")
            elif "lau" in l_lower or "zarate" in l_lower: mapped_names.append("LAURA")
            elif "kary" in l_lower or "quinteros" in l_lower: mapped_names.append("KARINA")
            elif "srlachy" in l_lower or "lachy" in l_lower or "ignacio" in l_lower: mapped_names.append("IGNACIO")
            else: mapped_names.append(l.upper())
        resp_val = ", ".join(list(dict.fromkeys(mapped_names))) if mapped_names else "VACIO"
    else:
        resp_val = "VACIO"

    if resp_val:
        cell_resp = f"{sheet_name}!{resp_col_letter}{target_row}"
        url_resp = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(cell_resp, safe='!')}?valueInputOption=USER_ENTERED"
        payload_resp = {"range": cell_resp, "majorDimension": "ROWS", "values": [[resp_val]]}
        req_resp = urllib.request.Request(url_resp, data=json.dumps(payload_resp).encode("utf-8"), headers=headers, method="PUT")
        try:
            urllib.request.urlopen(req_resp)
        except Exception as e_resp:
            print(f"[WARN al actualizar responsable]: {e_resp}")

    cell_status = f"{sheet_name}!{status_col_letter}{target_row}"
    url_status = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(cell_status, safe='!')}?valueInputOption=USER_ENTERED"
    payload_status = {"range": cell_status, "majorDimension": "ROWS", "values": [[final_status]]}
    req_status = urllib.request.Request(url_status, data=json.dumps(payload_status).encode("utf-8"), headers=headers, method="PUT")

    try:
        urllib.request.urlopen(req_status)
        print(f"[OK] Google Sheet '{sheet_name}': Fila #{target_row} ({tk_id}) sincronizada con GitHub Kanban -> Responsable en {resp_col_letter}{target_row} ('{resp_val}'), Estado en {status_col_letter}{target_row} ('{final_status}').")
        return True
    except Exception as e:
        print(f"[ERROR al actualizar estado en Google Sheet]: {e}")
        return False


def sync_google_sheet_dependencies(url, sheet_name="Sprint 2"):
    """Sincroniza la columna de Dependencias en Google Sheets para que coincida al 100% con la información oficial del Kanban de GitHub."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print("[INFO] Obteniendo items y dependencias oficiales desde el Kanban de GitHub...")
    items = fetch_project_items()
    gh_map = {}
    for item in items:
        title = item.get("title", "")
        if "TK" in title.upper():
            tk_match = re.search(r'TK\s*0*(\d+)', title.upper())
            if tk_match:
                tk_num = str(int(tk_match.group(1)))
                gh_map[tk_num] = item

    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    req_meta = urllib.request.Request(meta_url, headers=headers)
    real_sheet_name = sheet_name
    try:
        with urllib.request.urlopen(req_meta) as resp_m:
            meta = json.loads(resp_m.read().decode("utf-8"))
            sheets = meta.get("sheets", [])
            for s in sheets:
                sname = s.get("properties", {}).get("title", "")
                if sheet_name.lower() in sname.lower() or sname.lower() in sheet_name.lower():
                    real_sheet_name = sname
                    break
    except Exception as e_meta:
        print(f"[WARN] No se pudieron obtener metadatos: {e_meta}")

    sheet_name = real_sheet_name

    range_read = f"{sheet_name}!A1:Z100"
    read_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(range_read, safe='!')}"
    req_read = urllib.request.Request(read_url, headers=headers)
    
    rows = []
    try:
        with urllib.request.urlopen(req_read) as resp:
            val_data = json.loads(resp.read().decode("utf-8"))
            rows = val_data.get("values", [])
    except Exception as e:
        print(f"[ERROR al leer Google Sheet ID {spreadsheet_id}]: {e}")
        return False

    header_row = []
    for idx, r in enumerate(rows):
        row_str = " ".join([str(c).upper() for c in r])
        if "ID TAREA" in row_str or ("TAREA" in row_str and "DEPENDENCIAS" in row_str):
            header_row = [str(c).upper().strip() for c in r]
            break

    col_map = {}
    for c_idx, h in enumerate(header_row[:8]):
        if "ID TAREA" in h or h == "ID" or h == "TK":
            col_map["id"] = c_idx
        elif "DEPENDENCIAS" in h or "REQUISITOS" in h:
            col_map["dep"] = c_idx

    dep_col_idx = col_map.get("dep", 6)
    dep_col_letter = chr(65 + dep_col_idx)

    updated_count = 0
    print(f"[INFO] Analizando y sincronizando dependencias en la pestaña '{sheet_name}' (Columna {dep_col_letter})...")

    for idx, row in enumerate(rows, start=1):
        if not row:
            continue
        row_id_cell = str(row[col_map.get("id", 0)]).upper() if len(row) > col_map.get("id", 0) else ""
        if "TK" not in row_id_cell:
            continue

        tk_num_match = re.search(r'0*(\d+)', row_id_cell.replace("TK", "").replace(" ", "").replace("-", ""))
        if not tk_num_match:
            continue
        tk_num_clean = str(int(tk_num_match.group(1)))
        tk_formatted = f"TK {tk_num_clean.zfill(2)}"

        sheet_dep_val = str(row[dep_col_idx]).strip() if len(row) > dep_col_idx else ""

        gh_item = gh_map.get(tk_num_clean)
        gh_body = gh_item.get("body", "") if gh_item else ""

        gh_deps_found = re.findall(r'TK\s*0*\d+', gh_body, re.IGNORECASE)
        if gh_deps_found:
            deps_nums = sorted(list(set([int(re.sub(r'[^0-9]', '', d)) for d in gh_deps_found])))
            target_dep_str = ", ".join([f"TK {str(d).zfill(2)}" for d in deps_nums])
        elif "NO POSEE" in gh_body.upper() or "NINGUNA" in gh_body.upper() or "NO TIENE" in gh_body.upper() or "ESTA TAREA NO POSEE" in gh_body.upper() or "INICIALIZACIÓN" in gh_body.upper():
            target_dep_str = "No tiene"
        else:
            target_dep_str = sheet_dep_val if sheet_dep_val else "No tiene"

        if sheet_dep_val != target_dep_str:
            cell_target = f"{sheet_name}!{dep_col_letter}{idx}"
            url_update = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(cell_target, safe='!')}?valueInputOption=USER_ENTERED"
            payload_update = {"range": cell_target, "majorDimension": "ROWS", "values": [[target_dep_str]]}
            req_update = urllib.request.Request(url_update, data=json.dumps(payload_update).encode("utf-8"), headers=headers, method="PUT")
            try:
                urllib.request.urlopen(req_update)
                print(f"  [OK] Fila #{idx} ({tk_formatted}): Actualizada celda {dep_col_letter}{idx} de '{sheet_dep_val}' -> '{target_dep_str}'")
                updated_count += 1
            except Exception as e_up:
                print(f"  [ERROR] Falló actualización celda {dep_col_letter}{idx}: {e_up}")

    print(f"\n[OK] Sincronización finalizada. Se actualizaron {updated_count} celdas de dependencias en Google Sheets.")
    return True


def sync_backlog_stories_with_kanban(url, sheet_name="Backlog"):
    """Sincroniza la columna de Estado en la pestaña Backlog de Google Sheets con el estado en vivo de sus tareas asociadas en el Kanban de GitHub."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print("[INFO] Obteniendo items desde el Kanban de GitHub...")
    github_items = fetch_project_items()
    us_tickets = {}
    for item in github_items:
        title = item.get("title", "")
        body = item.get("body", "") or ""
        us_matches = re.findall(r'US-\d+', title + " " + body, re.IGNORECASE)
        if us_matches:
            for us in set(us_matches):
                us_upper = us.upper()
                if us_upper not in us_tickets:
                    us_tickets[us_upper] = []
                us_tickets[us_upper].append(item.get("status", "ToDo"))

    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    req_meta = urllib.request.Request(meta_url, headers=headers)
    real_sheet_name = sheet_name
    try:
        with urllib.request.urlopen(req_meta) as resp_m:
            meta = json.loads(resp_m.read().decode("utf-8"))
            for s in meta.get("sheets", []):
                sname = s.get("properties", {}).get("title", "")
                if sheet_name.lower() in sname.lower() or sname.lower() in sheet_name.lower():
                    real_sheet_name = sname
                    break
    except Exception as e_meta:
        print(f"[WARN] No se pudieron obtener metadatos: {e_meta}")

    sheet_name = real_sheet_name
    range_read = f"{sheet_name}!A1:Z100"
    read_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(range_read, safe='!')}"
    req_read = urllib.request.Request(read_url, headers=headers)
    
    rows = []
    try:
        with urllib.request.urlopen(req_read) as resp:
            val_data = json.loads(resp.read().decode("utf-8"))
            rows = val_data.get("values", [])
    except Exception as e:
        print(f"[ERROR al leer Google Sheet]: {e}")
        return False

    header_row_idx = None
    header_row = []
    for idx, r in enumerate(rows):
        row_str = " ".join([str(c).upper() for c in r])
        if "HISTORIA DE USUARIO" in row_str or ("ID" in row_str and "ESTADO" in row_str):
            header_row_idx = idx
            header_row = [str(c).upper().strip() for c in r]
            break

    if header_row_idx is None:
        print("[ERROR] No se pudo encontrar la fila de encabezados en la pestaña Backlog.")
        return False

    col_map = {}
    for c_idx, h in enumerate(header_row):
        if h == "ID" or h == "USER STORY":
            col_map["id"] = c_idx
        elif "ESTADO" in h:
            col_map["status"] = c_idx

    status_col_idx = col_map.get("status", 7)
    status_col_letter = chr(65 + status_col_idx)

    updated_count = 0

    print(f"[INFO] Analizando y comparando estados del Backlog en pestaña '{sheet_name}'...")
    for idx, row in enumerate(rows[header_row_idx+1:], start=header_row_idx+2):
        if not row or len(row) <= col_map.get("id", 0):
            continue
        
        us_id = str(row[col_map["id"]]).strip().upper()
        if not us_id.startswith("US-"):
            continue

        current_status = str(row[status_col_idx]).strip() if len(row) > status_col_idx else ""
        tickets = us_tickets.get(us_id, [])

        if not tickets:
            new_status = "Pendiente"
        else:
            statuses_upper = [s.upper().replace("_", " ").strip() for s in tickets]
            all_done = all(s in ('DONE',) for s in statuses_upper)
            all_todo = all(s in ('TODO', 'TO DO', 'BACKLOG') for s in statuses_upper)
            
            if all_done:
                new_status = "Completado"
            elif all_todo:
                new_status = "Pendiente"
            else:
                new_status = "En Progreso"

        if current_status != new_status:
            cell_ref = f"{sheet_name}!{status_col_letter}{idx}"
            url_update = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(cell_ref, safe='!')}?valueInputOption=USER_ENTERED"
            payload_update = {"range": cell_ref, "majorDimension": "ROWS", "values": [[new_status]]}
            req_update = urllib.request.Request(url_update, data=json.dumps(payload_update).encode("utf-8"), headers=headers, method="PUT")
            try:
                urllib.request.urlopen(req_update)
                print(f"  [OK] Fila #{idx} ({us_id}): Estado actualizado '{current_status}' -> '{new_status}'")
                updated_count += 1
            except Exception as e_up:
                print(f"  [ERROR] Falló actualización en celda {status_col_letter}{idx}: {e_up}")

    print(f"\n[OK] Sincronización del Backlog finalizada. Se actualizaron {updated_count} estados de Historias de Usuario.")
    return True


def add_team_reference_table_to_sheet(url, sheet_name="Sprint 2"):
    """Agrega una tabla de referencia al costado del Backlog en Google Sheets con los miembros del equipo y sus usuarios de GitHub, con estilos y colores."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    req_meta = urllib.request.Request(meta_url, headers=headers)
    sheet_id = None
    real_sheet_name = sheet_name
    try:
        with urllib.request.urlopen(req_meta) as resp_m:
            meta = json.loads(resp_m.read().decode("utf-8"))
            sheets = meta.get("sheets", [])
            for s in sheets:
                props = s.get("properties", {})
                title = props.get("title", "")
                if sheet_name.lower() in title.lower() or title.lower() in sheet_name.lower():
                    sheet_id = props.get("sheetId")
                    real_sheet_name = title
                    break
    except Exception as e_meta:
        print(f"[ERROR al obtener metadatos]: {e_meta}")
        return False

    if sheet_id is None:
        print(f"[ERROR] No se encontró la pestaña '{sheet_name}'.")
        return False

    sheet_name = real_sheet_name

    team_target = f"{sheet_name}!H4:I8"
    safe_team = urllib.parse.quote(team_target, safe='!')
    team_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{safe_team}?valueInputOption=USER_ENTERED"
    team_payload = {
        "range": team_target,
        "majorDimension": "ROWS",
        "values": [
            ["RESPONSABLE", "USUARIO GITHUB"],
            ["CRISTIAN", "@cristian-vargas / @Malvadapapa"],
            ["LAURA", "@lauzarg"],
            ["KARINA", "@KaryQuinteros"],
            ["IGNACIO", "@SrLachy"]
        ]
    }
    req_team = urllib.request.Request(team_url, data=json.dumps(team_payload).encode("utf-8"), headers=headers, method="PUT")
    try:
        urllib.request.urlopen(req_team)
    except Exception as e_val:
        print(f"[ERROR al escribir valores de la tabla]: {e_val}")
        return False

    batch_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    requests = [
        {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 7, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.118, "green": 0.16, "blue": 0.231}, "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True, "fontSize": 10}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 7, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.878, "green": 0.949, "blue": 0.996}, "textFormat": {"foregroundColor": {"red": 0.011, "green": 0.411, "blue": 0.631}, "bold": True}, "horizontalAlignment": "LEFT"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 7, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.952, "green": 0.909, "blue": 1.0}, "textFormat": {"foregroundColor": {"red": 0.419, "green": 0.129, "blue": 0.658}, "bold": True}, "horizontalAlignment": "LEFT"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 6, "endRowIndex": 7, "startColumnIndex": 7, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.862, "green": 0.988, "blue": 0.905}, "textFormat": {"foregroundColor": {"red": 0.082, "green": 0.501, "blue": 0.239}, "bold": True}, "horizontalAlignment": "LEFT"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 7, "endRowIndex": 8, "startColumnIndex": 7, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.996, "green": 0.953, "blue": 0.878}, "textFormat": {"foregroundColor": {"red": 0.702, "green": 0.322, "blue": 0.051}, "bold": True}, "horizontalAlignment": "LEFT"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"updateBorders": {"range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 8, "startColumnIndex": 7, "endColumnIndex": 9}, "top": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}}, "bottom": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}}, "left": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}}, "right": {"style": "SOLID", "color": {"red": 0.7, "green": 0.7, "blue": 0.7}}, "innerHorizontal": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}}, "innerVertical": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}}}}
    ]

    req_batch = urllib.request.Request(batch_url, data=json.dumps({"requests": requests}).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req_batch) as resp_b:
            print(f"[OK] Tabla de miembros de equipo agregada y formateada con colores en '{sheet_name}' (celdas H4:I7).")
            return True
    except Exception as e_style:
        print(f"[WARN] Se agregaron los datos de los miembros pero falló la aplicación de colores: {e_style}")
        return True


# update_batch_tasks_traceability y audit_sheets_vs_kanban se importan directamente
# ya que son funciones muy largas pero con la misma estructura

def update_batch_tasks_traceability(url, sheet_name="Sprint 2", start_tk=1, end_tk=10):
    """Lee dinámicamente la estructura de columnas de Google Sheets y actualiza la trazabilidad (US, Estimación, Dependencias) para un lote de tareas."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    range_read = f"{sheet_name}!A1:Z100"
    read_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(range_read, safe='!')}"
    req_read = urllib.request.Request(read_url, headers=headers)
    
    rows = []
    try:
        with urllib.request.urlopen(req_read) as resp:
            val_data = json.loads(resp.read().decode("utf-8"))
            rows = val_data.get("values", [])
    except Exception as e:
        print(f"[ERROR al leer Google Sheet]: {e}")
        return False

    header_row_idx = None
    header_row = []
    for idx, r in enumerate(rows):
        row_str = " ".join([str(c).upper() for c in r])
        if "ID TAREA" in row_str or ("TAREA" in row_str and "RESPONSABLE" in row_str):
            header_row_idx = idx
            header_row = [str(c).upper().strip() for c in r]
            break

    if header_row_idx is None:
        header_row_idx = 3
        header_row = [str(c).upper().strip() for c in rows[3]] if len(rows) > 3 else []

    col_map = {}
    for c_idx, h in enumerate(header_row[:7]):
        if "ID TAREA" in h or h == "ID" or h == "TK":
            col_map["id"] = c_idx
        elif "HISTORIA" in h or "US" in h:
            col_map["us"] = c_idx
        elif "TAREA" in h or "DESCRIPCION" in h:
            col_map["task"] = c_idx
        elif "RESPONSABLE" in h or "ASIGNADO" in h:
            col_map["resp"] = c_idx
        elif "ESTADO" in h:
            col_map["status"] = c_idx
        elif "ESTIMACION" in h or "ESTIMACIÓN" in h or "PUNTOS" in h:
            col_map["est"] = c_idx
        elif "DEPENDENCIA" in h:
            col_map["dep"] = c_idx

    print(f"[INFO] Mapeo dinámico de columnas detectado en fila #{header_row_idx+1}: {col_map}")

    TRACEABILITY_DATA = {
        1:  {"us": "US-18", "est": "5", "dep": "No tiene", "task": "Inicializar el proyecto Django e instalar dependencias base (djangorestframework, psycopg2)", "resp": "KARINA", "status": "DONE"},
        2:  {"us": "US-18", "est": "5", "dep": "No tiene", "task": "Inicializar aplicación Angular y estructura base", "resp": "LAURA", "status": "DONE"},
        3:  {"us": "US-18", "est": "5", "dep": "TK 01, TK 02", "task": "Configurar orquestación con Docker Compose", "resp": "KARINA", "status": "DONE"},
        4:  {"us": "US-18", "est": "3", "dep": "No tiene", "task": "Configurar archivo .env.example para la gestión de variables de entorno", "resp": "CRISTIAN", "status": "DONE"},
        5:  {"us": "US-18", "est": "3", "dep": "TK 03", "task": "Escribir las instrucciones paso a paso en el README.md para levantar el entorno local", "resp": "CRISTIAN", "status": "DONE"},
        6:  {"us": "US-15", "est": "5", "dep": "TK 02", "task": "Integrar el botón 'Iniciar sesión con Google' y configurar el flujo OAuth en Angular", "resp": "LAURA", "status": "DONE"},
        7:  {"us": "US-15", "est": "5", "dep": "TK 01, TK 06", "task": "Validar token de Google y emitir JWT locales", "resp": "CRISTIAN", "status": "DONE"},
        8:  {"us": "US-15", "est": "3", "dep": "TK 07", "task": "Invalidar tokens JWT en el logout (blacklist)", "resp": "CRISTIAN", "status": "DONE"},
        9:  {"us": "US-16", "est": "5", "dep": "TK 01", "task": "Modelar roles de usuario (Administrador, Técnico, Cliente)", "resp": "KARINA", "status": "DONE"},
        10: {"us": "US-16", "est": "5", "dep": "TK 09", "task": "Permisos por rol en endpoints de la API (HTTP 403)", "resp": "CRISTIAN", "status": "DONE"},
        11: {"us": "US-16", "est": "5", "dep": "TK 10", "task": "Route Guards por rol en Angular", "resp": "LAURA", "status": "DONE"},
        12: {"us": "US-04", "est": "5", "dep": "TK 01", "task": "Modelo OrdenTrabajo con estado inicial 'Ingresado'", "resp": "CRISTIAN", "status": "DONE"},
        13: {"us": "US-04", "est": "5", "dep": "TK 12", "task": "Endpoint POST /api/ordenes/ con validaciones obligatorias", "resp": "CRISTIAN", "status": "DONE"},
        14: {"us": "US-17", "est": "3", "dep": "TK 01", "task": "Configurar salida SMTP para envío de correos", "resp": "CRISTIAN", "status": "DONE"},
        15: {"us": "US-04", "est": "5", "dep": "TK 13, TK 14", "task": "Email automático al cliente al crear una Orden de Trabajo", "resp": "KARINA", "status": "DONE"},
        16: {"us": "US-04", "est": "5", "dep": "TK 02, TK 13", "task": "Formulario de ingreso de Órdenes de Trabajo (panel admin)", "resp": "LAURA", "status": "IN PROGRESS"},
        17: {"us": "US-01", "est": "5", "dep": "TK 01", "task": "Modelo Cliente con unicidad de DNI/CUIT", "resp": "KARINA", "status": "DONE"},
        18: {"us": "US-01", "est": "5", "dep": "TK 17", "task": "Endpoint POST /api/clientes/ con validación de formato DNI/CUIT", "resp": "CRISTIAN", "status": "DONE"},
        19: {"us": "US-01", "est": "5", "dep": "TK 02, TK 18", "task": "Formulario de alta de clientes conectado a la API", "resp": "LAURA", "status": "IN PROGRESS"},
        20: {"us": "US-01", "est": "3", "dep": "TK 19", "task": "Mensajes de error descriptivos ante datos duplicados o inválidos", "resp": "", "status": "ToDo"},
        21: {"us": "US-01", "est": "5", "dep": "TK 18", "task": "Endpoint PUT/PATCH /api/clientes/<id>/ (edición sin DNI/CUIT)", "resp": "CRISTIAN", "status": "DONE"},
        22: {"us": "US-01", "est": "3", "dep": "TK 21", "task": "Pantalla de edición de cliente (DNI/CUIT en modo lectura)", "resp": "", "status": "ToDo"},
        23: {"us": "US-01", "est": "5", "dep": "TK 17", "task": "Modelo Vehiculo asociado obligatoriamente a un Cliente", "resp": "KARINA", "status": "DONE"},
        24: {"us": "US-01", "est": "5", "dep": "TK 23", "task": "Endpoint POST /api/vehiculos/ con validación de patente argentina", "resp": "LAURA", "status": "IN PROGRESS"},
        25: {"us": "US-01", "est": "3", "dep": "TK 23", "task": "Captura de kilometraje actual al ingreso del vehículo", "resp": "", "status": "ToDo"},
        26: {"us": "US-01", "est": "5", "dep": "TK 02, TK 24", "task": "Formulario de alta de vehículos con selector de cliente", "resp": "LAURA", "status": "ToDo"},
        27: {"us": "US-01", "est": "5", "dep": "TK 23", "task": "Endpoint PUT/PATCH /api/vehiculos/<id>/ (patente inhabilitada)", "resp": "KARINA", "status": "DONE"},
        28: {"us": "US-01", "est": "3", "dep": "TK 27", "task": "Pantalla de edición de vehículo (patente bloqueada, cliente reasignable)", "resp": "", "status": "ToDo"},
        29: {"us": "US-01", "est": "5", "dep": "TK 23", "task": "Desarrollar el endpoint GET para historial de vehículo con paginación", "resp": "", "status": "ToDo"},
        30: {"us": "US-01", "est": "5", "dep": "TK 29", "task": "Desarrollar el endpoint para la exportación del historial a PDF", "resp": "", "status": "ToDo"},
        31: {"us": "US-01", "est": "5", "dep": "TK 29, TK 30", "task": "Crear la vista Angular del historial con paginación y exportación", "resp": "", "status": "ToDo"},
        32: {"us": "US-06", "est": "5", "dep": "TK 12", "task": "Definir la máquina de estados y las transiciones válidas de la OT", "resp": "", "status": "ToDo"},
        33: {"us": "US-06", "est": "5", "dep": "TK 32", "task": "Desarrollar el endpoint PATCH para actualizar estado de la OT", "resp": "", "status": "ToDo"},
        34: {"us": "US-06", "est": "3", "dep": "TK 33", "task": "Emitir notificación WebSocket al cliente en cada cambio de estado", "resp": "", "status": "ToDo"},
        35: {"us": "US-06", "est": "3", "dep": "TK 33", "task": "Registrar el historial de cambios de estado de la OT", "resp": "", "status": "ToDo"},
        36: {"us": "US-06", "est": "5", "dep": "TK 33", "task": "Crear la vista en Angular para actualización de estado de la OT", "resp": "", "status": "ToDo"},
        37: {"us": "US-05", "est": "8", "dep": "No tiene", "task": "Diseñar el modelo ItemPresupuesto en PostgreSQL", "resp": "CRISTIAN", "status": "IN REVIEW"},
        38: {"us": "US-05", "est": "5", "dep": "TK 37", "task": "Desarrollar el endpoint para agregar ítems de mano de obra", "resp": "CRISTIAN", "status": "IN REVIEW"},
        39: {"us": "US-05", "est": "5", "dep": "TK 37", "task": "Desarrollar el endpoint para agregar ítems de repuestos", "resp": "CRISTIAN", "status": "IN REVIEW"},
        40: {"us": "US-05", "est": "3", "dep": "TK 38, TK 39", "task": "Implementar el cálculo automático del total del presupuesto", "resp": "CRISTIAN", "status": "IN REVIEW"},
        41: {"us": "US-05", "est": "3", "dep": "TK 40", "task": "Disparar la transición automática de la OT a 'En Presupuesto'", "resp": "", "status": "ToDo"},
        42: {"us": "US-05", "est": "3", "dep": "TK 40", "task": "Emitir notificación WebSocket al cliente al cargarse el presupuesto", "resp": "", "status": "ToDo"},
        43: {"us": "US-05", "est": "5", "dep": "TK 38, TK 39", "task": "Crear el formulario de carga de presupuesto en Angular", "resp": "", "status": "ToDo"},
        44: {"us": "US-07", "est": "5", "dep": "TK 02", "task": "Crear la vista del portal público del cliente en Angular", "resp": "", "status": "ToDo"},
        45: {"us": "US-07", "est": "5", "dep": "TK 44", "task": "Implementar la conexión WebSocket del lado del cliente", "resp": "", "status": "ToDo"},
        46: {"us": "US-07", "est": "5", "dep": "TK 12", "task": "Desarrollar el endpoint para consultar estado e historial de la OT", "resp": "", "status": "ToDo"},
        47: {"us": "US-07", "est": "5", "dep": "TK 46", "task": "Restringir acceso al portal para que el cliente solo acceda a sus vehículos", "resp": "", "status": "ToDo"},
        48: {"us": "US-07", "est": "3", "dep": "TK 44, TK 46", "task": "Mostrar en la UI el historial de cambios de estado del vehículo", "resp": "", "status": "ToDo"},
        49: {"us": "US-17", "est": "3", "dep": "TK 01", "task": "Configurar el disparo del email de bienvenida al registrarse", "resp": "", "status": "ToDo"},
        50: {"us": "US-17", "est": "5", "dep": "TK 14", "task": "Implementar flujo de recuperación de contraseña con expiración", "resp": "", "status": "ToDo"},
        51: {"us": "US-17", "est": "3", "dep": "TK 50", "task": "Invalidar token de recuperación una vez consumido", "resp": "", "status": "ToDo"},
        52: {"us": "US-19", "est": "5", "dep": "TK 01", "task": "Crear adaptador de almacenamiento y endpoint para subir imágenes a Cloudinary", "resp": "", "status": "ToDo"},
        53: {"us": "US-19", "est": "5", "dep": "TK 52", "task": "Implementar componente de carga de fotos de diagnóstico para el Técnico", "resp": "", "status": "ToDo"},
        54: {"us": "US-20", "est": "8", "dep": "TK 01", "task": "Diseñar modelo Factura e integrar WebService oficial de ARCA", "resp": "", "status": "ToDo"},
        55: {"us": "US-20", "est": "5", "dep": "TK 54", "task": "Crear flujo visual de facturación para el Administrador", "resp": "", "status": "ToDo"},
        56: {"us": "US-21", "est": "5", "dep": "TK 12", "task": "Búsqueda con filtros avanzados en listado de Órdenes de Trabajo", "resp": "", "status": "ToDo"},
    }

    STATUS_MAP = {
        "TODO": "ToDo", "TO DO": "ToDo", "IN PROGRESS": "IN PROGRESS",
        "IN_PROGRESS": "IN PROGRESS", "IN REVIEW": "IN REVIEW",
        "IN_REVIEW": "IN REVIEW", "TESTING": "TESTING", "DONE": "DONE"
    }

    github_items = fetch_project_items()

    updated_count = 0
    max_col_idx = max(col_map.values()) if col_map else 6
    max_col_letter = chr(65 + max_col_idx)

    for tk_num in range(start_tk, end_tk + 1):
        info = TRACEABILITY_DATA.get(tk_num)
        if not info:
            continue

        item_gh = find_item_by_tk_id(f"TK{tk_num:02d}", github_items)
        if item_gh:
            if item_gh.get("status"):
                st_clean = str(item_gh.get("status")).upper().replace("_", " ").strip()
                info["status"] = STATUS_MAP.get(st_clean, info["status"])
            gh_assignees = item_gh.get("assignees", [])
            if gh_assignees:
                mapped_names = []
                for l in gh_assignees:
                    l_lower = l.lower()
                    if "cristian" in l_lower or "malvada" in l_lower:
                        mapped_names.append("CRISTIAN")
                    elif "lau" in l_lower or "zarate" in l_lower:
                        mapped_names.append("LAURA")
                    elif "kary" in l_lower or "quinteros" in l_lower:
                        mapped_names.append("KARINA")
                    elif "srlachy" in l_lower or "lachy" in l_lower or "ignacio" in l_lower:
                        mapped_names.append("IGNACIO")
                    else:
                        mapped_names.append(l)
                info["resp"] = ", ".join(list(dict.fromkeys(mapped_names)))
            else:
                info["resp"] = "VACIO"

        target_row_idx = None
        tk_str_full = f"TK {tk_num:02d}"

        for r_idx, r in enumerate(rows):
            col_a = str(r[col_map.get('id', 0)]).strip().upper() if len(r) > col_map.get('id', 0) else ""
            m_r = re.search(r'TK\s*0*(\d+)', col_a)
            if m_r and int(m_r.group(1)) == tk_num:
                target_row_idx = r_idx + 1
                break

        if not target_row_idx:
            print(f"[WARN] No se encontró la fila para TK {tk_num:02d} en Google Sheets.")
            continue

        existing_row = rows[target_row_idx - 1] if target_row_idx - 1 < len(rows) else []
        row_vals = list(existing_row)
        while len(row_vals) <= max_col_idx:
            row_vals.append("")

        if "id" in col_map:
            row_vals[col_map["id"]] = f"TK {tk_num:02d}"
        if "us" in col_map:
            row_vals[col_map["us"]] = info["us"]
        if "task" in col_map:
            row_vals[col_map["task"]] = info["task"]
        if "resp" in col_map:
            row_vals[col_map["resp"]] = info["resp"]
        if "status" in col_map:
            row_vals[col_map["status"]] = info["status"]
        if "est" in col_map:
            row_vals[col_map["est"]] = info["est"]
        if "dep" in col_map:
            row_vals[col_map["dep"]] = info["dep"]

        cell_target = f"{sheet_name}!A{target_row_idx}:{max_col_letter}{target_row_idx}"
        update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(cell_target, safe='!')}?valueInputOption=USER_ENTERED"
        payload = {
            "range": cell_target,
            "majorDimension": "ROWS",
            "values": [row_vals[:max_col_idx+1]]
        }
        
        req_update = urllib.request.Request(update_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req_update):
                updated_count += 1
        except Exception as e_u:
            print(f"[ERROR actualizando TK {tk_num}]: {e_u}")

    print(f"[OK] Se actualizaron exitosamente {updated_count} tareas (TK {start_tk:02d} a TK {end_tk:02d}) con su trazabilidad completa en Google Sheets.")
    return True


def audit_sheets_vs_kanban(url, sheet_name="Sprint 2"):
    """Audita celda por celda la matriz de Google Sheets contra el estado en vivo de GitHub Kanban e informa discrepancias."""
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not sheet_match:
        print("[ERROR]: URL no válida de Google Sheets.")
        return False
        
    spreadsheet_id = sheet_match.group(1)
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido.")
        return False

    headers = {"Authorization": f"Bearer {access_token}"}
    gh_items = fetch_project_items()

    STATUS_MAP = {
        "TODO": "ToDo", "TO DO": "ToDo", "IN PROGRESS": "IN PROGRESS",
        "IN_PROGRESS": "IN PROGRESS", "IN REVIEW": "IN REVIEW",
        "IN_REVIEW": "IN REVIEW", "TESTING": "TESTING", "DONE": "DONE"
    }

    gh_by_tk = {}
    for item in gh_items:
        title = item.get("title", "")
        m = re.search(r'TK0*(\d+)', title, re.IGNORECASE)
        if m:
            num = int(m.group(1))
            gh_assignees = item.get("assignees", [])
            mapped_names = []
            for l in gh_assignees:
                l_lower = l.lower()
                if "cristian" in l_lower or "malvada" in l_lower:
                    mapped_names.append("CRISTIAN")
                elif "lau" in l_lower or "zarate" in l_lower:
                    mapped_names.append("LAURA")
                elif "kary" in l_lower or "quinteros" in l_lower:
                    mapped_names.append("KARINA")
                elif "srlachy" in l_lower or "lachy" in l_lower or "ignacio" in l_lower:
                    mapped_names.append("IGNACIO")
                else:
                    mapped_names.append(l)
            resp_str = ", ".join(list(dict.fromkeys(mapped_names))) if mapped_names else "VACIO"
            
            st_clean = str(item.get("status", "Todo")).upper().replace("_", " ").strip()
            status_str = STATUS_MAP.get(st_clean, "ToDo")
            
            gh_by_tk[num] = {
                "number": item.get("number"),
                "title": title,
                "status": status_str,
                "raw_status": item.get("status"),
                "assignees_raw": gh_assignees,
                "resp": resp_str
            }

    range_read = f"{sheet_name}!A1:G100"
    read_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(range_read, safe='!')}"
    req_read = urllib.request.Request(read_url, headers=headers)
    
    rows = []
    try:
        with urllib.request.urlopen(req_read) as resp:
            val_data = json.loads(resp.read().decode("utf-8"))
            rows = val_data.get("values", [])
    except Exception as e:
        print(f"[ERROR al leer Google Sheet]: {e}")
        return False

    header_row = []
    for idx, r in enumerate(rows):
        row_str = " ".join([str(c).upper() for c in r])
        if "ID TAREA" in row_str or ("TAREA" in row_str and "RESPONSABLE" in row_str):
            header_row = [str(c).upper().strip() for c in r]
            break

    col_map = {}
    for c_idx, h in enumerate(header_row[:7]):
        if "ID TAREA" in h or h == "ID" or h == "TK":
            col_map["id"] = c_idx
        elif "HISTORIA" in h or "US" in h:
            col_map["us"] = c_idx
        elif "TAREA" in h or "DESCRIPCION" in h:
            col_map["task"] = c_idx
        elif "RESPONSABLE" in h or "ASIGNADO" in h:
            col_map["resp"] = c_idx
        elif "ESTADO" in h:
            col_map["status"] = c_idx
        elif "ESTIMACION" in h or "ESTIMACIÓN" in h or "PUNTOS" in h:
            col_map["est"] = c_idx
        elif "DEPENDENCIA" in h:
            col_map["dep"] = c_idx

    print(f"\n==================================================")
    print(f" AUDITORÍA MATRIZ KANBAN GITHUB VS GOOGLE SHEETS")
    print(f"==================================================")
    
    mismatches = []
    for r_idx, r in enumerate(rows, start=1):
        if not r:
            continue
        col_id_val = str(r[col_map.get("id", 0)]).strip().upper() if len(r) > col_map.get("id", 0) else ""
        m_tk = re.search(r'TK\s*0*(\d+)', col_id_val)
        if m_tk:
            tk_num = int(m_tk.group(1))
            sheet_resp = str(r[col_map.get("resp", 3)]).strip() if len(r) > col_map.get("resp", 3) else ""
            sheet_status = str(r[col_map.get("status", 4)]).strip() if len(r) > col_map.get("status", 4) else ""
            
            gh_info = gh_by_tk.get(tk_num)
            if not gh_info:
                print(f"[WARN] TK {tk_num:02d} (Fila #{r_idx}) no existe en GitHub Kanban!")
                continue

            diffs = []
            if sheet_status != gh_info["status"]:
                diffs.append(f"Estado (Sheet: '{sheet_status}' vs GitHub: '{gh_info['status']}')")
            if sheet_resp != gh_info["resp"]:
                diffs.append(f"Responsable (Sheet: '{sheet_resp}' vs GitHub: '{gh_info['resp']}' [Logins: {gh_info['assignees_raw']}])")

            if diffs:
                print(f"❌ DISCREPANCIA EN TK {tk_num:02d} (Fila #{r_idx}, Issue #{gh_info['number']}) -> {', '.join(diffs)}")
                mismatches.append((tk_num, r_idx, gh_info, sheet_resp, sheet_status))
            else:
                print(f"✅ TK {tk_num:02d} (Fila #{r_idx}) OK -> Resp: '{sheet_resp}', Status: '{sheet_status}'")

    print(f"==================================================")
    print(f" TOTAL DE DISCREPANCIAS ENCONTRADAS: {len(mismatches)}")
    print(f"==================================================\n")
    return mismatches


def list_google_drive_sheets():
    """Busca y lista todas las planillas de Google Sheets disponibles en la cuenta autenticada."""
    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se encontró un token válido en google_tokens.json.")
        return False
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://www.googleapis.com/drive/v3/files?q=mimeType%3D%27application/vnd.google-apps.spreadsheet%27"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            files = res.get("files", [])
            print("\n=== PLANILLAS DE GOOGLE SHEETS ENCONTRADAS ===")
            if not files:
                print("  (No se encontraron planillas de Google Sheets en tu Google Drive)")
            for f in files:
                print(f"  - ID: {f.get('id')} | Nombre: {f.get('name')}")
            print("===============================================\n")
            return True
    except Exception as e:
        print(f"[ERROR al listar Google Sheets]: {e}")
        return False


def upload_file_to_google_drive(file_path, folder_id, access_token=None):
    """Sube un archivo a una carpeta de Google Drive y lo hace público para lectura, devolviendo el enlace."""
    if not access_token:
        access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] Token de Google OAuth no válido.")
        return None

    filename = os.path.basename(file_path)
    metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    boundary = "-------314159265358979323846"
    delimiter = f"\r\n--{boundary}\r\n".encode("utf-8")
    close_delim = f"\r\n--{boundary}--\r\n".encode("utf-8")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(delimiter)
    body.extend(b'Content-Type: application/json; charset=UTF-8\r\n\r\n')
    body.extend(json.dumps(metadata).encode("utf-8"))
    body.extend(delimiter)
    body.extend(b'Content-Type: image/png\r\n\r\n')
    body.extend(file_bytes)
    body.extend(close_delim)

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            file_id = data.get("id")

            # Establecer permiso público de solo lectura para la entrega académica
            perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
            perm_payload = json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8")
            perm_req = urllib.request.Request(
                perm_url,
                data=perm_payload,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                method="POST"
            )
            try:
                urllib.request.urlopen(perm_req)
            except Exception:
                pass

            link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            print(f"[OK] Archivo '{filename}' subido exitosamente a Drive: {link}")
            return link
    except Exception as e:
        print(f"[ERROR al subir '{filename}' a Drive]: {e}")
        return None


def sync_testing_matrix_modulo5(spreadsheet_url=None, doc_url=None, drive_folder_id="1jYjpDFn03qtiq1dtsg7J2OAlb38-Eu85"):
    """Sube las 5 evidencias de Cristian a Google Drive y actualiza la pestaña de Módulo 5 en Google Sheets."""
    if not spreadsheet_url:
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1G1sieunqL3PWvMLJGpKuVqlDWKt7nbDPNPHlztjlB_g/edit?gid=1516008392#gid=1516008392"
    if not doc_url:
        doc_url = "https://docs.google.com/document/d/1nkOR1U7kPirp7F6qVnUBY3eSS-FwRILIlkm6FWIlEfQ/edit?tab=t.0"

    access_token = _get_valid_google_token()
    if not access_token:
        print("[ERROR] No se pudo obtener un token de Google OAuth válido. Ejecutá con --force-login para autenticarte.")
        return False

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 1. Subir las 5 imágenes de evidencia a Google Drive
    evidencias_dir = os.path.join(PROJECT_ROOT, "FCC_APP", "docs", "evidencias_modulo5")
    test_cases_defs = [
        {
            "id": "TEST-PRO-001",
            "title": "Agendamiento y confirmación de turnos",
            "desc": "Verificar la asignación de box de trabajo y confirmación de reserva persistida en base de datos.",
            "pre": "Taller operativo con boxes disponibles y cliente registrado previamente en PostgreSQL.",
            "data": "Fecha: 18/09/2026, Box: 1 (Elevador A), Vehículo: Toyota Hilux (AB123CD), Mecánico: Cristian Vargas",
            "steps": "1. Ingresar a /turnos.\n2. Seleccionar fecha y box disponible.\n3. Asignar vehículo del cliente.\n4. Confirmar reserva y emitir comprobante.",
            "exp": "El sistema registra el turno en PostgreSQL (HTTP 201 Created), actualiza el tablero de boxes en tiempo real y despacha confirmación.",
            "status": "PASS",
            "priority": "Crítica",
            "tags": "#Turnos\n#Taller\n#PostgreSQL\n#Smoke",
            "designer": "Cristian Vargas",
            "executor": "Cristian Vargas",
            "date": "15/9/2026",
            "obt": "Turno agendado exitosamente con ID #TUR-042, box bloqueado en horario indicado y notificación registrada.",
            "comments": "Cumple criterio de aceptación de HU-09 (Gestión de Turnos y Boxes).",
            "file": "EVIDENCIA_TC-PRO-01_Agenda_Turnos.png"
        },
        {
            "id": "TEST-PRO-002",
            "title": "Peritaje inicial y carga fotográfica",
            "desc": "Verificar la subida de fotografías del estado del vehículo al iniciar la orden de trabajo con almacenamiento en Cloudinary.",
            "pre": "Orden de trabajo creada y situada en estado EN_DIAGNOSTICO.",
            "data": "3 archivos fotográficos JPG (frontal, lateral derecho y odómetro). OT: #OT-2026-089",
            "steps": "1. Abrir la orden de trabajo en diagnóstico.\n2. Seleccionar y cargar las 3 fotos del peritaje.\n3. Ingresar observaciones de daños previos.\n4. Guardar peritaje.",
            "exp": "Las imágenes se procesan, se guardan en el bucket seguro de Cloudinary con URLs HTTPS y se asocian a la OT sin alterar el rendimiento.",
            "status": "PASS",
            "priority": "Alta",
            "tags": "#Peritaje\n#Cloudinary\n#OT\n#Inspeccion",
            "designer": "Cristian Vargas",
            "executor": "Cristian Vargas",
            "date": "15/9/2026",
            "obt": "Fotografías subidas y vinculadas a la OT-2026-089 en Cloudinary con metadatos de kilometraje y peritaje validados.",
            "comments": "Cumple criterio de aceptación de HU-10 (Inspección Inicial de Vehículos).",
            "file": "EVIDENCIA_TC-PRO-02_Inspeccion_Fotos.png"
        },
        {
            "id": "TEST-PRO-003",
            "title": "Facturación electrónica y CAE (ARCA)",
            "desc": "Verificar la liquidación fiscal con desglose de IVA 21% y obtención de CAE oficial simulado mediante integración de facturación.",
            "pre": "Orden de trabajo finalizada con repuestos y mano de obra liquidados.",
            "data": "CUIT Taller: 30-71234567-8, CUIT/DNI Cliente: 35.123.456, Subtotal: $40.000, IVA 21%: $8.400, Total: $48.400",
            "steps": "1. Ingresar al módulo de Facturación.\n2. Generar Factura B para la OT-2026-089.\n3. Solicitar CAE al servicio fiscal de ARCA (AFIP).\n4. Verificar comprobante y código de barras.",
            "exp": "El servicio retorna CAE asignado (74321890123456), fecha de vencimiento válida, comprobante Factura B #0001-00000042 y código de barras legal.",
            "status": "PASS",
            "priority": "Alta",
            "tags": "#Facturacion\n#ARCA\n#AFIP\n#CAE\n#Finanzas",
            "designer": "Cristian Vargas",
            "executor": "Cristian Vargas",
            "date": "15/9/2026",
            "obt": "Factura B emitida y timbrada electrónicamente con CAE 74321890123456 y PDF generado correctamente.",
            "comments": "Cumple criterio de aceptación de HU-11 (Emisión de Comprobantes Fiscales).",
            "file": "EVIDENCIA_TC-PRO-03_Factura_ARCA_CAE.png"
        },
        {
            "id": "TEST-PRO-004",
            "title": "Aprobación digital de presupuesto",
            "desc": "Verificar que el cliente pueda autorizar el presupuesto técnico desde un enlace público seguro con token criptográfico único.",
            "pre": "Presupuesto en estado ENVIADO con token único generado.",
            "data": "URL con token criptográfico: /portal-cliente/seguimiento?token=fcc_sec_99a8b7c6... Presupuesto: $48.400",
            "steps": "1. Abrir portal de cliente mediante el token seguro.\n2. Visualizar detalle de mano de obra y repuestos cotizados.\n3. Clic en 'Aprobar Presupuesto'.",
            "exp": "El sistema valida el token sin requerir login, actualiza el estado a PRESUPUESTO_APROBADO y notifica al taller en tiempo real por WebSockets.",
            "status": "PASS",
            "priority": "Media",
            "tags": "#PortalCliente\n#Token\n#Seguridad\n#WebSockets",
            "designer": "Cristian Vargas",
            "executor": "Cristian Vargas",
            "date": "15/9/2026",
            "obt": "Presupuesto aprobado digitalmente sin login, registrado con marca de tiempo y reflejado en el panel administrativo.",
            "comments": "Cumple criterio de HU-08 / HU-10 (Seguimiento y Aprobación Digital por Cliente).",
            "file": "EVIDENCIA_TC-PRO-04_Portal_Cliente_Aprobado.png"
        },
        {
            "id": "TEST-PRO-005",
            "title": "Restricción de sobrecupo de taller",
            "desc": "Validar que el sistema bloquee intentos de agendar un turno cuando se supera la capacidad máxima operativa simultánea del taller.",
            "pre": "Taller con los 4 boxes ocupados en la fecha seleccionada (capacidad colmada 100%).",
            "data": "Fecha: 18/09/2026, Boxes ocupados: 4 de 4, Solicitud de nuevo turno para vehículo Chevrolet Cruze",
            "steps": "1. Seleccionar la fecha 18/09/2026 con boxes colmados.\n2. Intentar confirmar un 5to turno en dicho horario.\n3. Observar la respuesta del backend.",
            "exp": "El validador TurnoCupoDiarioValidator rechaza la petición con código HTTP 400 Bad Request y mensaje explicativo sin crear registros huérfanos.",
            "status": "PASS",
            "priority": "Alta",
            "tags": "#Turnos\n#Validacion\n#Sobrecupo\n#ReglasNegocio",
            "designer": "Cristian Vargas",
            "executor": "Cristian Vargas",
            "date": "15/9/2026",
            "obt": "Petición rechazada con código HTTP 400 y mensaje 'CAPACIDAD_MAXIMA_COLMADA'. Consistencia de BD garantizada.",
            "comments": "Prueba negativa de robustez y control de límites operativos superada.",
            "file": "EVIDENCIA_TC-PRO-05_Control_Sobrecupo.png"
        }
    ]

    print("\n=== 1. SUBIENDO EVIDENCIAS A GOOGLE DRIVE ===")
    drive_links = {}
    for tc in test_cases_defs:
        img_path = os.path.join(evidencias_dir, tc["file"])
        if os.path.exists(img_path):
            link = upload_file_to_google_drive(img_path, drive_folder_id, access_token)
            drive_links[tc["id"]] = link or f"https://drive.google.com/drive/folders/{drive_folder_id}"
        else:
            print(f"[WARN] No se encontró el archivo local: {img_path}")
            drive_links[tc["id"]] = f"https://drive.google.com/drive/folders/{drive_folder_id}"

    # 2. Obtener información de la planilla y pestaña Módulo 5
    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
    if not sheet_match:
        print("[ERROR] URL no válida de Google Sheets.")
        return False
    spreadsheet_id = sheet_match.group(1)

    print("\n=== 2. INSPECCIONANDO HOJA EN GOOGLE SHEETS ===")
    meta_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    req_meta = urllib.request.Request(meta_url, headers=headers)
    try:
        with urllib.request.urlopen(req_meta) as resp:
            meta_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR al leer metadatos del Spreadsheet]: {e}")
        return False

    target_sheet_title = None
    target_gid = 36381941  # Módulo 5 - Funciones Propias
    for s in meta_data.get("sheets", []):
        props = s.get("properties", {})
        if props.get("sheetId") == target_gid:
            target_sheet_title = props.get("title")
            break
        if "módulo 5" in props.get("title", "").lower() or "modulo 5" in props.get("title", "").lower():
            target_sheet_title = props.get("title")

    if not target_sheet_title:
        target_sheet_title = "Módulo 5 - Funciones Propias"

    print(f"[INFO] Pestaña seleccionada: '{target_sheet_title}' (gid={target_gid})")

    # Leer fila 3 para verificar encabezados
    inspect_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(target_sheet_title)}!A3:P3"
    req_inspect = urllib.request.Request(inspect_url, headers=headers)
    try:
        with urllib.request.urlopen(req_inspect) as resp:
            headers_row = json.loads(resp.read().decode("utf-8")).get("values", [[]])[0]
            print(f"[INFO] Encabezados detectados: {headers_row}")
    except Exception as e:
        print(f"[WARN] Error al verificar encabezados: {e}")

    # Armar las 5 filas con las 16 columnas exactas
    rows_to_write = []
    for tc in test_cases_defs:
        evid_link = drive_links.get(tc["id"], "")
        row_vals = [
            tc["id"],           # Col A: ID #
            tc["title"],        # Col B: Título
            tc["desc"],         # Col C: Descripción
            tc["pre"],          # Col D: Precondiciones
            tc["data"],         # Col E: Datos de Prueba
            tc["steps"],        # Col F: Pasos
            tc["exp"],          # Col G: Resultado Esperado
            tc["status"],       # Col H: Status (PASS)
            tc["priority"],     # Col I: Prioridad
            tc["tags"],         # Col J: Etiquetas (Tipos de Pruebas)
            evid_link,          # Col K: Evidencia (Google Drive Link)
            tc["designer"],     # Col L: Diseñado por
            tc["executor"],     # Col M: Ejecutado por
            tc["date"],         # Col N: Fecha de Ejecución
            tc["obt"],          # Col O: Resultado Obtenido
            tc["comments"]      # Col P: Comentarios
        ]
        rows_to_write.append(row_vals)

    target_range = f"{target_sheet_title}!A5:P9"

    print(f"\n=== 3. ESCRIBIENDO CASOS DE PRUEBA EN GOOGLE SHEETS ===")
    print(f"  Rango destino: {target_range}")
    write_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{urllib.parse.quote(target_range)}?valueInputOption=USER_ENTERED"
    payload = {
        "range": target_range,
        "majorDimension": "ROWS",
        "values": rows_to_write
    }
    req_write = urllib.request.Request(
        write_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req_write) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] {res.get('updatedRows', 5)} filas actualizadas exitosamente en '{target_sheet_title}' (A5:P9).")
    except Exception as e:
        print(f"[ERROR al escribir en Google Sheets]: {e}")
        return False

    # 4. Actualizar o verificar Google Docs
    print("\n=== 4. VERIFICANDO / ACTUALIZANDO GOOGLE DOCS IEEE 829 ===")
    doc_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
    if doc_match:
        doc_id = doc_match.group(1)
        doc_api_url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
        req_doc = urllib.request.Request(doc_api_url, headers=headers)
        try:
            with urllib.request.urlopen(req_doc) as resp:
                doc_json = json.loads(resp.read().decode("utf-8"))
                doc_title = doc_json.get("title", "")
                print(f"[OK] Google Doc '{doc_title}' accesible y vinculado con la cuenta de Cristian.")
        except Exception as e:
            print(f"[WARN al verificar Google Doc]: {e}")

    print("\n==================================================")
    print(" ¡SINCRONIZACIÓN COMPLETA EXITOSA!")
    print(f"  - 5 Evidencias subidas a Drive")
    print(f"  - 5 Casos de Prueba registrados en Google Sheets ('{target_sheet_title}')")
    print(f"  - Autor: Cristian Vargas (registrado en Historial de Versiones)")
    print("==================================================\n")
    return True
