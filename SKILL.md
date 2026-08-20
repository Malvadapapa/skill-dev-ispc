---
name: "ispc-dev"
description: "Skill de trabajo integrado para el ISPC. Gestiona el ciclo de vida completo de desarrollo: planificación de módulos con explicaciones pedagógicas, ejecución de tickets con Kanban de GitHub, commits progresivos, PRs y auditoría."
---

# ISPC Dev - Skill de Trabajo Integrado

Esta skill guía al asistente para gestionar de manera integral el ciclo de vida de desarrollo de cualquier tarea en el repositorio, conectándose con el Kanban de GitHub mediante `kanban_helper.py`. Incluye un flujo de planificación pedagógica para que el desarrollador pueda estudiar y aprender mientras la IA ejecuta el trabajo.

---

## ⚠️ Reglas Obligatorias (se aplican SIEMPRE)

### R1. Plan obligatorio antes de tocar código

**PROHIBIDO modificar código sin un plan aprobado.** Antes de escribir o editar cualquier archivo del proyecto, la IA DEBE:

1. Crear un plan de implementación (artifact `implementation_plan.md`) que detalle:
   - Qué archivos se van a crear/modificar/eliminar
   - Qué cambios concretos se van a hacer en cada archivo
   - Secuencia de commits propuesta
   - Cómo se va a verificar que funciona (tests, lint, etc.)
2. Presentar el plan al usuario y **esperar aprobación explícita** antes de ejecutar.
3. Si durante la ejecución surgen cambios significativos respecto al plan, **pausar y re-planificar** antes de continuar.

> Esto aplica a tickets, features, bugfixes, refactors — cualquier modificación de código fuente del proyecto.

### R2. Idioma: Español Latinoamericano (obligatorio)

**TODO el razonamiento, planificación, explicaciones, comentarios de PR, descripciones de commits y comunicación con el usuario DEBE ser en español latinoamericano.** Esto incluye:

- Planes de implementación
- Descripciones de cambios
- Comentarios en el chat
- Mensajes de commit (excepto el prefijo convencional: `feat:`, `fix:`, etc.)
- Comentarios en PRs y tarjetas del Kanban
- Explicaciones pedagógicas

> La única excepción es el código fuente en sí (nombres de variables, funciones, clases, docstrings técnicos) que pueden estar en inglés según la convención del proyecto.

---

## 🅰️ Bloque A — Configuración y Setup Inicial

### A.1 Verificación y Onboarding de Desarrollador Guiado por IA

**OBLIGATORIO AL ACTIVAR LA SKILL:** Antes de ejecutar cualquier otra acción, la IA DEBE ejecutar:

```bash
py .agents/skills/ispc-dev/scripts/kanban_helper.py --check-user
```

Si la salida muestra que **todo está configurado** (rama, GitHub token y Google OAuth con ✅), continuar directamente al Bloque B.

Si **falta cualquier configuración**, la IA DEBE guiar al usuario paso a paso en el chat (sin requerir que entre a la consola de desarrolladores ni edite archivos manualmente):

1. **Si falta `DEV_BRANCH_NAME` (rama personal):**
   - Preguntarle al usuario en el chat: *"¿Cuál es tu nombre o rama personal en el proyecto? (ej: 'cristian-vargas', 'karina-quinteros')"*
   - Con la respuesta, ejecutar:
     ```bash
     py .agents/skills/ispc-dev/scripts/kanban_helper.py --config-dev --dev-branch "<nombre-rama>"
     ```

2. **Si falta `GITHUB_TOKEN`:**
   - Explicarle al usuario que necesita un token de GitHub con permisos `repo` y `project`.
   - Pedírselo en el chat y ejecutar:
     ```bash
     py .agents/skills/ispc-dev/scripts/kanban_helper.py --config-dev --github-token "<token>"
     ```

3. **Si falta la sesión de Google OAuth (`google_tokens.json`):**
   - Informar al usuario que se va a abrir el navegador para iniciar sesión con Google.
   - Ejecutar:
     ```bash
     py .agents/skills/ispc-dev/scripts/kanban_helper.py --google-login
     ```
   - *(Si la sesión ya existe, el comando la reutiliza sin abrir el navegador).*

4. **Verificación final:**
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --info
   ```

### A.2 Wiki del Proyecto

La wiki contiene la documentación del proyecto (modelos de datos, casos de uso, stakeholders, etc.) y es fundamental para planificar correctamente.

1. **Si existe `wiki/` dentro del skill con archivos `.md`** → Usarla como referencia.
2. **Si no existe** → Intentar clonarla:
   ```bash
   git clone https://github.com/<ORG>/<REPO>.wiki.git .agents/skills/ispc-dev/wiki/
   ```
3. **Si no se puede clonar** → Pedir al usuario que proporcione la documentación del proyecto en formato `.txt` y guardarla en la carpeta `wiki/` del skill.
4. **Actualizar la wiki** al inicio de cada módulo nuevo:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --update-wiki
   ```

### A.3 Reglas del Entorno de Desarrollo

- **Uso del Entorno Virtual (Venv) en Windows:** Todas las ejecuciones de Python para el backend (`manage.py`, tests, migraciones) deben utilizar obligatoriamente el intérprete del entorno virtual: `& <REPO>/backend/.venv/Scripts/python.exe`. Queda prohibido usar `python`, `py` o `pip` globales para tareas de desarrollo.
- **Estricta Prohibición de scripts temporales:** Queda totalmente prohibido crear archivos o scripts temporales de un solo uso ("one-off", scratch scripts o utilidades pasajeras) para interactuar con GitHub, Git, Issues o Pull Requests.
- **Extensión directa del Kanban Helper:** Si falta alguna funcionalidad de automatización o interacción con GitHub/Git, se debe editar y extender directamente el submódulo correspondiente dentro de `scripts/`, agregando las opciones necesarias al parser de argumentos en `kanban_helper.py` y actualizando la documentación en `references/kanban_commands.md`.

### A.4 Dominios de la Skill y Ruteo de Módulos

La skill cubre **4 dominios funcionales**. La IA DEBE identificar a qué dominio pertenece la tarea actual y **leer SOLO los módulos de ese dominio**, nunca todos.

#### 🏷️ Dominio 1: Kanban y Gestión de Tareas
**Cuándo:** Mover tarjetas, cambiar estados, crear tickets, asignar, listar el tablero, sincronizar con Google Sheets, auditar backlog.

| Módulo a leer | Qué contiene |
|---|---|
| `_config.py` | Constantes, .env, headers de GitHub |
| `_github_api.py` | GraphQL: estados, comentarios, asignaciones |
| `_tickets.py` | Crear issues, etiquetas, campos de proyecto, buscar por TK ID |
| `_google_sheets.py` | Sincronización de planillas, auditoría, trazabilidad |
| `_pull_requests.py` | CRUD de Pull Requests (crear, inspeccionar, aprobar, fusionar) |
| `kanban_helper.py` | CLI parser (solo para ver/agregar argumentos) |

```bash
# Comandos típicos de este dominio:
py .agents/skills/ispc-dev/scripts/kanban_helper.py --list
py .agents/skills/ispc-dev/scripts/kanban_helper.py --task TK37 --start
py .agents/skills/ispc-dev/scripts/kanban_helper.py --summary
py .agents/skills/ispc-dev/scripts/kanban_helper.py --audit "<URL_SHEET>"
```

---

#### 📖 Dominio 2: Wiki y Documentación del Proyecto
**Cuándo:** Consultar wiki, buscar en documentos, leer/actualizar archivos .md/.txt/.docx del proyecto.

| Módulo a leer | Qué contiene |
|---|---|
| `_docs.py` | Lectura de archivos locales (.md, .txt, .docx), Google Docs, wiki |

```bash
# Comandos típicos de este dominio:
py .agents/skills/ispc-dev/scripts/kanban_helper.py --wiki list
py .agents/skills/ispc-dev/scripts/kanban_helper.py --wiki "Modelo-de-Datos"
py .agents/skills/ispc-dev/scripts/kanban_helper.py --docs-search "serializer"
py .agents/skills/ispc-dev/scripts/kanban_helper.py --update-wiki
```

---

#### 📊 Dominio 3: Google Docs y Sheets
**Cuándo:** Leer/escribir planillas de Google Sheets, sincronizar estados con el Kanban, actualizar trazabilidad, auditar matrices.

| Módulo a leer | Qué contiene |
|---|---|
| `_google_auth.py` | OAuth2, refresh de tokens, login |
| `_google_sheets.py` | Todas las operaciones de Sheets API |

```bash
# Comandos típicos de este dominio:
py .agents/skills/ispc-dev/scripts/kanban_helper.py --update-sheet "<URL>" --task TK37
py .agents/skills/ispc-dev/scripts/kanban_helper.py --sync-dependencies "<URL>"
py .agents/skills/ispc-dev/scripts/kanban_helper.py --sync-backlog "<URL>"
py .agents/skills/ispc-dev/scripts/kanban_helper.py --list-sheets
```

---

#### 🎨 Dominio 4: Figma (Diseño, Prototipado y Tokens)
**Cuándo:** Consultar diseños, extraer tokens de diseño (colores, tipografías), leer componentes/frames, generar vistas maquetadas a partir del prototipo.

| Recurso a consultar | Qué contiene |
|---|---|
| `figma-plugin/` | Plugin **Figma Desktop Bridge** integrado (`manifest.json`, `code.js`, `ui.html`) |
| `references/mcp_setup.md` | Instrucciones de conexión MCP y setup |
| `wiki/Maquetado.md` | Guía de maquetado del proyecto y enlaces a prototipos |

**Instalación del plugin integrado en Figma Desktop:**
1. En Figma Desktop: Menú ➔ **Plugins** ➔ **Development** ➔ **Import plugin from manifest...**
2. Seleccionar el archivo: `.agents/skills/ispc-dev/figma-plugin/manifest.json`.
3. El plugin permite conectar en tiempo real vía WebSocket (puertos 9223–9232) con clientes MCP locales para extraer variables y componentes sin plan Enterprise.

**Configuración del MCP Server de Figma en el IDE (`.vscode/mcp.json`):**
```json
{
  "mcpServers": {
    "figma": {
      "url": "https://mcp.figma.com/mcp",
      "headers": {
        "Authorization": "Bearer <FIGMA_ACCESS_TOKEN>"
      }
    }
  }
}
```

**URL del prototipo oficial del proyecto:**
```
https://www.figma.com/design/KZhmDCMHAtuj1d77pXdygB/FCC_App?node-id=0-1
```

**Uso por la IA:** Cuando se requiera consultar diseño de vistas o componentes, la IA debe consultar el MCP de Figma o las referencias en `wiki/Maquetado.md` sin cargar scripts de backend ni módulos innecesarios.

---

#### 🔧 Módulos transversales (solo si se necesitan)

| Módulo | Dominio | Cuándo leerlo |
|---|---|---|
| `_config.py` | Configuración | Setup inicial, cambios de .env |
| `_google_auth.py` | Autenticación | Login, onboarding, refresh de tokens |
| `_git_utils.py` | Git | Commits progresivos, creación de ramas |
| `_menu.py` | CLI interactivo | Casi nunca (uso manual por terminal) |

### A.5 Referencia de Comandos

Consultar `references/kanban_commands.md` para la lista completa de comandos disponibles en `kanban_helper.py`.

---

## 🅱️ Bloque B — Flujo de Módulo (Planificación Global)

Cuando el usuario indica que quiere trabajar un módulo (conjunto de tickets relacionados), se sigue este flujo:

### Paso M1 — Sincronización del Kanban

1. Ejecutar el script para obtener el estado actual del tablero:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --list
   ```
2. Actualizar la wiki si es necesario:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --update-wiki
   ```

### Paso M2 — Plan del Módulo

Crear un archivo `MODULO_<nombre>.md` en la **raíz del proyecto** usando el template de `references/module_plan_template.md`. El archivo debe contener:

1. **Nombre y objetivo del módulo**: Qué función cumple en el sistema y por qué es necesario.
2. **Conceptos clave para estudiar**: Lista de conceptos técnicos que se van a aplicar. Para cada uno:
   - Qué es el concepto.
   - Por qué se usa en este contexto específico.
   - Link a documentación oficial o wiki cuando sea relevante.
3. **Tabla de tickets**: Todos los tickets que componen el módulo con TK ID, título, estado actual y descripción breve.
4. **Plan de entrega**: Orden de ejecución de los tickets y dependencias entre ellos.
5. **Mensaje de PR borrador**: El texto completo del Pull Request que se creará al finalizar todos los tickets, en formato narrativo según la guía de estilo (Bloque E).
6. **Datos relevantes**: Dependencias entre apps, migraciones esperadas, riesgos, decisiones de diseño.

> **📚 Propósito pedagógico:** Este archivo sirve como material de estudio. El desarrollador puede leerlo para entender qué va a construir, por qué, y qué conceptos técnicos están involucrados, ANTES de que la IA empiece a codificar.

### Paso M3 — Aprobación del Usuario

Presentar el plan y **esperar OK explícito** antes de continuar. No avanzar a ningún ticket sin aprobación del usuario.

### Paso M4 — Ejecución Ticket por Ticket

Una vez aprobado el plan del módulo, iterar sobre cada ticket en el orden definido usando el **Bloque C** (flujo por ticket). Cada ticket se planifica individualmente, se aprueba, y se ejecuta.

### Paso M5 — Pull Request del Módulo

Al finalizar TODOS los tickets del módulo:

1. Hacer `git push` de la rama del desarrollador:
   ```bash
   git push origin <DEV_BRANCH_NAME>
   ```
2. Crear el PR hacia `develop` usando el kanban helper:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --create-pr --head <DEV_BRANCH_NAME> --base develop --pr-title "<titulo_del_pr>" --pr-body-file <archivo_con_body>
   ```
3. El cuerpo del PR es el borrador aprobado en el Paso M2 (puede ajustarse si hubo cambios durante la ejecución).

---

## 🅲 Bloque C — Flujo por Ticket (Planificación Individual + Ejecución)

Para cada ticket del módulo, seguir estrictamente este protocolo:

### Paso T0 — Aseguramiento de Rama Personal

1. Verificar que estamos en la rama del desarrollador (leída del `.env`):
   ```bash
   git checkout <DEV_BRANCH_NAME>
   ```
2. Si la rama no existe, crearla a partir de `main`:
   ```bash
   git checkout main && git pull
   git checkout -b <DEV_BRANCH_NAME>
   ```
3. **Verificación visual:** Ejecutar `git status` y confirmar la rama actual.

> **⚠️ Estrategia de ramas:** Cada desarrollador trabaja en **una sola rama personal** (no se crea una rama por ticket). Todos los commits van a la misma rama. Al finalizar, la rama se mergea a `develop` vía PR.

### Paso T1 — Lectura Completa del Ticket

1. Leer el ticket completo desde GitHub:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --task <TK_ID>
   ```
2. **Lectura exhaustiva:** Leer en profundidad toda la descripción, flujo de trabajo, especificaciones técnicas y criterios de aceptación. Queda estrictamente prohibido resumir o dar por sentado requerimientos sin contrastar la descripción completa.

### Paso T2 — Inicio en el Kanban

1. Mover la tarea a "In Progress" (sincroniza automáticamente la tarjeta en GitHub Kanban y en la planilla de Google Sheets):
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --task <TK_ID> --start
   ```
2. **Retorno inmediato a la rama del desarrollador** (el comando `--start` crea una rama temporal por ticket, ignorarla):
   ```bash
   git checkout <DEV_BRANCH_NAME>
   ```
3. Confirmar con `git status`.

### Paso T3 — Plan del Ticket con Explicación Pedagógica

**Este es el paso clave para el aprendizaje.** Presentar un plan detallado que sirva como material de estudio:

#### 🎯 Qué se va a hacer
Resumen técnico claro de la funcionalidad a implementar. Descripción concreta de los archivos que se van a crear o modificar y qué hace cada uno.

#### 📚 Por qué se hace esto
- **Contexto dentro del sistema:** Qué problema resuelve esta funcionalidad, cómo se conecta con otros módulos ya implementados o futuros.
- **Concepto técnico que se aplica:** Explicar el concepto de fondo. Por ejemplo:
  - *"Usamos un `ModelSerializer` de DRF porque nos permite validar automáticamente los campos del modelo Django y exponer solo los datos que queremos a la API, sin escribir validaciones manuales para cada campo."*
  - *"Definimos una `ForeignKey` en el modelo Orden hacia Cliente porque cada orden pertenece a un cliente, y esta relación nos permite consultar todas las órdenes de un cliente usando el ORM de Django con `cliente.ordenes.all()`."*
- **Referencia a documentación:** Links a docs oficiales de Django, DRF, Angular, o a la wiki del proyecto cuando sea relevante.

#### 🔍 Datos relevantes para estudiar
- **Patrones de diseño utilizados:** Ej. "Este endpoint sigue el patrón REST: GET lista recursos, POST crea, PUT/PATCH actualiza, DELETE elimina".
- **Relación entre archivos:** Ej. "El modelo define la estructura → el serializer la valida y transforma → la vista la expone como endpoint → la URL la enruta".
- **Tips o gotchas comunes:** Ej. "Si usás `unique=True` en un campo, el serializer de DRF valida automáticamente unicidad. No hace falta agregar una validación manual".

#### Plan de Commits
Lista detallada de commits usando *Conventional Commits simplificado* (ej. `feat(backend): agregar modelo de cliente`).
- **Cantidad dinámica:** La cantidad de commits debe ser **adaptable y dinámica** según los componentes atómicos a implementar (pueden ser 2, 4, 5+ commits). Queda prohibido forzar una cifra fija o patrón rígido.
- Encabezado (Conventional Commit).
- Descripción sobria y corta del contenido.


#### Migraciones
Declarar explícitamente si la tarea requiere `makemigrations` y `migrate`.

#### Consideraciones de Seguridad (si aplica)
Permisos del endpoint (`permission_classes`), validaciones en el serializer, datos sensibles.

#### Dependencias Nuevas
Si se agrega alguna librería, incluir la actualización de `requirements.txt`.

#### Plan de Pruebas Unitarias
Detalle de las pruebas a escribir (casos felices, límites, excepciones).

#### Propuesta de Comentario Final
Borrador del comentario que se dejará en la tarjeta de GitHub al finalizar.

### Paso T4 — Aprobación del Plan del Ticket

**No comenzar a codificar hasta que el usuario apruebe este plan.**

### Paso T5 — Implementación y Pruebas

1. **Aplicar migraciones si corresponde** (usando el venv):
   ```bash
   & <REPO>/backend/.venv/Scripts/python.exe <REPO>/backend/manage.py makemigrations
   & <REPO>/backend/.venv/Scripts/python.exe <REPO>/backend/manage.py migrate
   ```
2. **Escribir la funcionalidad** según el plan aprobado.
3. **Pruebas unitarias obligatorias** para toda funcionalidad con lógica de aplicación (modelos, endpoints, vistas, serializers). Si es 100% configuración, solo verificar la suite existente.
4. **Correr la suite completa de tests** (no solo las nuevas):
   ```bash
   & <REPO>/backend/.venv/Scripts/python.exe <REPO>/backend/manage.py test
   ```
5. **Lint/formato:** Correr herramientas de formateo/linting configuradas en el proyecto.

### Paso T6 — Manejo de Fallos

Si una prueba falla, hay conflicto de migraciones, o el linting reporta errores:
- **Detener el flujo inmediatamente.**
- Informar al usuario detalladamente sobre el error.
- No avanzar hasta que esté resuelto.

### Paso T7 — Commits Progresivos y Secuenciales

1. **Un commit a la vez**, nunca todos de golpe. Simular ritmo de trabajo humano.
2. **Secuencia obligatoria por cada commit:**
   1. Escribir únicamente el código correspondiente a ese commit.
   2. Ejecutar tests y lint.
   3. Si pasa, hacer `git add` y `git commit`.
   4. Verificar con `git status` y `git log -1`.
   5. Recién entonces avanzar al siguiente commit.
3. Formato de commit:
   ```
   <tipo>(<alcance>): <título corto>

   <descripción corta en una o dos líneas>
   ```
4. Si un test o lint falla después de un commit, detener e informar (ver Paso T6).

### Paso T8 — Cierre del Ticket

1. **Verificar Definition of Done (DoD):**
   - [ ] Migraciones aplicadas y probadas (si aplica)
   - [ ] Tests nuevos + suite completa en verde
   - [ ] Lint sin errores o advertencias críticas
   - [ ] `requirements.txt` actualizado (si aplica)
   - [ ] Sin datos sensibles hardcodeados
   - [ ] Variables de entorno nuevas documentadas (si aplica)
2. Solicitar confirmación del usuario.
3. Dejar comentario en GitHub y mover a "In Review":
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --task <TK_ID> --status "In Review" --message "<comentario_aprobado>"
   ```
4. **Actualizar el Sprint Backlog:** Actualizar obligatoriamente el estado del ticket en el documento local/remoto del Sprint Backlog (`MODULO_<nombre>.md`, `backend_sprint_plan.md` o Google Sheets) para mantener ambos tableros totalmente sincronizados.


---

## 🅳 Bloque D — PRs y Auditoría

### D.1 Integración a Develop

1. Subir commits de la rama del desarrollador:
   ```bash
   git push origin <DEV_BRANCH_NAME>
   ```
2. Crear PR hacia `develop`:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --create-pr --head <DEV_BRANCH_NAME> --base develop --pr-title "<titulo>" --pr-body "<descripcion>"
   ```
3. El título del PR describe brevemente las tareas cubiertas (ej: `feat: autenticación y cierre de sesión - TK007 y TK008`).
4. Si se decide merge local en lugar de PR:
   ```bash
   git checkout develop && git pull
   git merge <DEV_BRANCH_NAME>
   git push origin develop
   git checkout <DEV_BRANCH_NAME>
   ```
5. **No eliminar la rama del desarrollador** después de la integración.

### D.2 PR a Main (Producción)

Al finalizar un sprint o al alcanzar hitos importantes:
```bash
py .agents/skills/ispc-dev/scripts/kanban_helper.py --create-pr --head develop --base main --pr-title "<titulo_release>" --pr-body "<descripcion_release>"
```
El cuerpo debe detallar los tickets integrados con `Closes #ID` para cierre automático.

### D.3 Auditoría y Cierre de Tareas en Review

Al auditar tareas de otros miembros del equipo en estado "In Review":
1. Verificar en el código la existencia e integridad de los cambios.
2. Contrastar con la User Story, Wiki y lineamientos de la cátedra.
3. **Regla de no intervención:** Queda estrictamente prohibido realizar cambios directos en la rama, archivos o commits de otro desarrollador. Si la tarea o PR presenta observaciones, fallas de tests o conflictos de merge con la rama base (`develop`), se debe dejar un comentario explicativo en el ticket o PR detallando la novedad para que el desarrollador asignado realice las correcciones en su propia rama.
4. **Cero Aprobación Prematura:** No existe la aprobación parcial en GitHub. Si una PR tiene conflictos de merge o requiere ajustes, **NUNCA debe ser aprobada (`APPROVE`)**. En su lugar, emitir una revisión con estado `REQUEST_CHANGES` (o comentario solicitando cambios) especificando la necesidad de actualizar la rama y resolver conflictos. La aprobación (`APPROVE`) se otorga únicamente cuando la PR no posee conflictos y está lista para mergear.
5. Si todo está correcto y sin conflictos, cambiar el estado a "Done" con comentario de auditoría y proceder al merge:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --task <TK_ID> --status "Done" --message "<comentario_auditoria>"
   ```

**Estilo de los comentarios de auditoría:**
- **Verbo de inicio:** `"Revisé..."` (para código) o `"Leí y seguí..."` (para documentación).
- **Frase de cierre:** `"...muevo el ticket a Done"` o `"...cierro la tarea"`.
- **Tono:** Narrativo, amigable, conciso, sin adjetivos sensacionalistas.



---

## 🅴 Bloque E — Guía de Estilo para Pull Requests

### E.1 Detección de Tickets

Antes de redactar un PR, verificar qué commits y tickets están involucrados:
```bash
git log origin/develop..HEAD --oneline
```
Identificar todos los TK IDs e issues asociados.

### E.2 Tono y Estilo

- **Narrativa en primera persona:** "implementé", "configuré", "escribí".
- **Directo, sobrio y conciso:** Explicación técnica clara sin prosa robótica, relleno ni cliché de IA.
- **Sin redundancias contextuales:** No repetir nombres de la aplicación, frameworks o tecnologías ("en el sistema FCCApp", "en Django REST Framework", "en PostgreSQL", "consistencia financiera") cuando sean obvios. Usar expresiones breves ("en los serializers", "en los modelos", "en la base de datos").
- **Sin sensacionalismo:** Evitar adjetivos rimbombantes, explicaciones enciclopédicas u obviedades académicas.
- **Prohibición de listas y viñetas en el cuerpo del PR:** Todo en párrafos de texto continuo.


### E.3 Estructura Obligatoria

```markdown
# Integración de [Funcionalidades Principales] ([IDs de Tickets])

[Párrafo 1 - Contexto y Objetivos]: Qué necesidad se aborda, motivación, tickets integrados.

[Párrafo 2 - Detalle Técnico]: Componentes creados/modificados, cómo interactúan, criterios de aceptación.

[Párrafo 3 - Pruebas y Verificación]: Tests desarrollados, casos evaluados, resultado de la suite.

Closes #ID_ISSUE_1, Closes #ID_ISSUE_2, Closes #ID_ISSUE_3
```

---

## 🅵 Bloque F — Inspección e Iteración de Documentación (Locales, Google Docs/Sheets y MCP)

Antes de planificar cualquier módulo o ticket, la IA debe contrastar la requerimientos con la documentación del proyecto (tanto local como remota en Google Docs/Sheets):

### F.1 Lectura e Iteración de Documentación
1. **Listar y buscar documentos locales (`.md`, `.txt`, `.docx`):**
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --docs
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --docs-search "<concepto>"
   ```
2. **Consultar documentos de Google Docs o planillas de Google Sheets:**
   Cualquier enlace de Google Docs o Sheets (como el Product Backlog en Google Sheets) se puede leer directamente con:
   ```bash
   py .agents/skills/ispc-dev/scripts/kanban_helper.py --docs-read "<URL_GOOGLE_DOC_O_SHEETS>"
   ```
3. **Uso de Servidores MCP:**
   Si el cliente tiene activos servidores MCP (`@modelcontextprotocol/server-gdrive` o `@modelcontextprotocol/server-filesystem`), la IA puede usarlos directamente para inspeccionar y actualizar la documentación en tiempo real. Consultar `references/mcp_setup.md` para más información.

### F.2 Consolidación con el Kanban
Cualquier actualización en la documentación (ej. nuevas historias de usuario en Google Docs o cambios de alcance en la wiki) debe sincronizarse con el Kanban mediante `kanban_helper.py --create-ticket` o `--update-body`.

### F.3 Inspección Dinámica de Encabezados y Validación en GitHub
1. **Lectura previa obligatoria de la fila de encabezados:** Antes de modificar o actualizar una hoja de cálculo en Google Sheets, la skill/agente debe inspeccionar dinámicamente la fila de encabezados (ej. Row 4) para identificar las columnas reales (`ID TAREA`, `HISTORIA DE USUARIO`, `TAREAS`, `RESPONSABLE`, `ESTADO`, `ESTIMACIÓN`, `DEPENDENCIAS`).
2. **Prohibición de columnas estáticas:** Nunca se deben asumir posiciones estáticas de columnas (ej. letra C o D estáticas) ya que la estructura de la hoja de cálculo puede ser modificada por el usuario.
3. **Validación previa en el tablero de GitHub:** La skill DEBE consultar en tiempo real el Kanban de GitHub (`fetch_project_items()`) antes de volcar cualquier estado o responsable en la hoja de cálculo. Los valores se sincronizan 1:1 desde GitHub y NUNCA se asumen manualmente.


