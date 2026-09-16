# Referencia Rápida - Comandos del Kanban Helper

Script: `.agents/skills/ispc-dev/scripts/kanban_helper.py`

## Consultas

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--list` | Lista todas las tareas del tablero agrupadas por columna | `py scripts/kanban_helper.py --list` |
| `--summary` | Muestra resumen cuantitativo de cada columna | `py scripts/kanban_helper.py --summary` |
| `--task <TK_ID>` | Muestra el detalle completo de un ticket | `py scripts/kanban_helper.py --task TK001` |
| `--list-fields` | Lista campos personalizados y opciones del proyecto V2 | `py scripts/kanban_helper.py --list-fields` |
| `--info` | Muestra la configuración actual del skill | `py scripts/kanban_helper.py --info` |

## Gestión de Tareas

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--task <ID> --start` | Mueve tarea a "In Progress", asigna al usuario y crea rama | `py scripts/kanban_helper.py --task TK001 --start` |
| `--task <ID> --assign` | Asigna la tarea al usuario autenticado en GitHub | `py scripts/kanban_helper.py --task TK037 --assign` |
| `--task <ID> --status <ESTADO>` | Mueve tarea a un estado específico | `py scripts/kanban_helper.py --task TK001 --status "In Review"` |
| `--task <ID> --message <TEXTO>` | Agrega comentario a la tarea | `py scripts/kanban_helper.py --task TK001 --message "Implementado"` |
| `--task <ID> --message-file <PATH>` | Agrega comentario desde archivo | `py scripts/kanban_helper.py --task TK001 --message-file comment.md` |
| `--task <ID> --add-labels <LISTA>` | Agrega etiquetas separadas por comas | `py scripts/kanban_helper.py --task TK001 --add-labels "backend,high priority"` |
| `--task <ID> --set-field <CAMPO> --value <VALOR>` | Actualiza campo de selección única | `py scripts/kanban_helper.py --task TK001 --set-field "Sprint" --value "Sprint 3"` |
| `--task <ID> --update-body <TEXTO>` | Actualiza la descripción del ticket | `py scripts/kanban_helper.py --task TK001 --update-body "Nueva descripción"` |
| `--task <ID> --update-body-file <PATH>` | Actualiza descripción desde archivo | `py scripts/kanban_helper.py --task TK001 --update-body-file body.md` |

## Pull Requests

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--list-prs` | Lista todos los Pull Requests abiertos en el repositorio | `py scripts/kanban_helper.py --list-prs` |
| `--pr <ID>` | Analiza en detalle un Pull Request especifico (conflictos, archivos, commits) | `py scripts/kanban_helper.py --pr 84` |
| `--approve-pr <ID>` | Aprueba un PR dejando un comentario de revisión con --comment | `py scripts/kanban_helper.py --approve-pr 84 --comment "Revisé..."` |
| `--request-changes-pr <ID>` | Solicita cambios en un PR dejando un comentario con --comment | `py scripts/kanban_helper.py --request-changes-pr 85 --comment "Revisé..."` |
| `--dismiss-review-pr <ID>` | Desestima una revisión previa del PR especificando --review-id | `py scripts/kanban_helper.py --dismiss-review-pr 85 --review-id 123456 --comment "Desestimando..."` |
| `--merge-pr <ID>` | Realiza el merge/fusión de un Pull Request aprobado a la rama base | `py scripts/kanban_helper.py --merge-pr 84` |
| `--create-pr` | Crea un Pull Request en GitHub | `py scripts/kanban_helper.py --create-pr --pr-title "feat: módulo X" --head cristian-vargas --base develop --pr-body "Descripción"` |
| `--create-pr` con archivo | Igual pero lee el body de un archivo | `py scripts/kanban_helper.py --create-pr --pr-title "feat: módulo X" --pr-body-file pr_body.md` |

## Documentación del Proyecto

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--docs` | Lista todos los documentos del proyecto (.md, .txt, .docx) | `py scripts/kanban_helper.py --docs` |
| `--docs-search "<query>"` | Busca un término en todos los documentos del proyecto | `py scripts/kanban_helper.py --docs-search "PostgreSQL"` |
| `--docs-read "<path_or_url>"` | Lee un documento local (.md, .txt, .docx) o descarga/lee Google Docs/Sheets | `py scripts/kanban_helper.py --docs-read "https://docs.google.com/spreadsheets/d/<ID>/edit"` |
| `--update-sheet "<url>"` | Actualiza la celda de Estado en Google Sheets para la tarea dada por `--task` | `py scripts/kanban_helper.py --update-sheet "<url>" --task "TK 37" --status "In Review"` |
| `--list-sheets` | Lista las planillas de Google Sheets accesibles en la cuenta de Google | `py scripts/kanban_helper.py --list-sheets` |
| `--sync-dependencies "<url>"` | Sincroniza la columna de dependencias de Google Sheets con el Kanban oficial de GitHub | `py scripts/kanban_helper.py --sync-dependencies "<url>"` |
| `--sync-backlog "<url>"` | Sincroniza la columna de estado en la pestaña Backlog con el Kanban de GitHub | `py scripts/kanban_helper.py --sync-backlog "<url>"` |
| `--sync-testing-matrix` | Sube las 5 evidencias a Google Drive y registra los casos de prueba del Módulo 5 en Google Sheets | `py scripts/kanban_helper.py --sync-testing-matrix` |
| `--docs-update "<path>"` | Crea o actualiza un documento usando `--body` o `--body-file` | `py scripts/kanban_helper.py --docs-update "doc.md" --body "Texto"` |

## Wiki

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--wiki list` | Lista las páginas disponibles en la wiki | `py scripts/kanban_helper.py --wiki list` |
| `--wiki <PAGINA>` | Muestra el contenido de una página de la wiki | `py scripts/kanban_helper.py --wiki "Modelo-de-Datos"` |
| `--wiki pull` | Actualiza la wiki local con `git pull` | `py scripts/kanban_helper.py --wiki pull` |
| `--update-wiki` | Actualiza la wiki local (equivalente a `--wiki pull`) | `py scripts/kanban_helper.py --update-wiki` |

## Autenticación y Configuración de Desarrollador

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--check-user` | Muestra el estado del desarrollador activo (rama git, token GitHub y sesión Google OAuth) | `py scripts/kanban_helper.py --check-user` |
| `--google-login` | Inicia sesión con Google OAuth solo si no hay una sesión activa en `google_tokens.json` | `py scripts/kanban_helper.py --google-login` |
| `--force-login` | Fuerza la apertura del navegador para re-autenticarse con Google OAuth | `py scripts/kanban_helper.py --google-login --force-login` |
| `--config-dev` | Actualiza los datos del desarrollador en `.env` (`--dev-branch`, `--github-token`) | `py scripts/kanban_helper.py --config-dev --dev-branch "nombre-rama"` |

## Mantenimiento

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `--fix-architecture` | Corrige referencias de arquitectura hexagonal a Django tradicional en todos los tickets | `py scripts/kanban_helper.py --fix-architecture` |

## Estados Válidos

- `Backlog` - Tareas futuras no priorizadas
- `Todo` - Tareas priorizadas para el sprint actual
- `In Progress` - Tareas en desarrollo activo
- `In Review` - Tareas completadas pendientes de revisión
- `Testing` - Tareas en fase de pruebas
- `Done` - Tareas completadas y verificadas
