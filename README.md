# ISPC Dev Skill - Kanban & Project Helper

Este repositorio contiene una "Skill" (habilidad) diseñada para asistentes de IA y agentes de desarrollo (como Antigravity) y también utilizable manualmente mediante su CLI.

Su objetivo principal es **automatizar y centralizar el flujo de trabajo del equipo**, integrando GitHub Projects (Kanban), Google Sheets (Backlog), Documentación (Wiki) y Diseño (Figma) en una única herramienta modular.

## 🚀 Características Principales

La skill está dividida en **4 dominios de trabajo independientes** para optimizar el contexto y los recursos de la IA:

1. 🏷️ **Gestión de Kanban y Tareas (GitHub):** Creación de issues, PRs, movimiento de tarjetas, comentarios, actualización de descripciones.
2. 📖 **Wiki y Documentación:** Búsqueda, lectura y actualización de documentos del proyecto (`.md`, `.txt`, `.docx`).
3. 📊 **Google Sheets y Docs:** Sincronización bidireccional del Backlog y trazabilidad (Google Drive API).
4. 🎨 **Figma Desktop Bridge:** Plugin MCP integrado para leer tokens de diseño y componentes directamente desde prototipos.

---

## 🛠️ Instalación

1. Clona este repositorio dentro de la carpeta `.agents/skills/ispc-dev/` de tu proyecto principal:
   ```bash
   git clone https://github.com/Malvadapapa/skill-dev-ispc.git .agents/skills/ispc-dev/
   ```

2. Instala las dependencias necesarias de Python:
   ```bash
   pip install requests python-dotenv google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-docx
   ```

---

## ⚙️ Configuración Inicial

1. Duplica el archivo de ejemplo de variables de entorno:
   ```bash
   cp .agents/skills/ispc-dev/.env.example .agents/skills/ispc-dev/.env
   ```
2. Edita `.env` con tus datos (Tokens de GitHub, Figma, etc.).
3. **No te preocupes por perder secretos:** El archivo `.gitignore` ya está configurado para evitar que subas `.env` o tokens temporales por error.

---

## 🔑 Autenticación (Onboarding)

Para verificar que todo está correctamente configurado o para iniciar sesión en los servicios, utiliza el CLI:

```bash
# 1. Verificar el estado de la configuración (GitHub y Google)
py .agents/skills/ispc-dev/scripts/kanban_helper.py --check-user

# 2. Iniciar sesión con Google (abrirá el navegador)
py .agents/skills/ispc-dev/scripts/kanban_helper.py --google-login
```

---

## 💻 Uso de la CLI

El punto de entrada es `scripts/kanban_helper.py`. Puedes utilizarlo de forma interactiva (menú) o pasando banderas específicas.

### Modo Interactivo
Ejecuta el script sin argumentos para abrir el menú principal:
```bash
py .agents/skills/ispc-dev/scripts/kanban_helper.py
```

### Comandos Rápidos
```bash
# Ver el estado del Kanban
py .agents/skills/ispc-dev/scripts/kanban_helper.py --list

# Iniciar la tarea TK032 (la mueve a In Progress, la asigna y crea la rama)
py .agents/skills/ispc-dev/scripts/kanban_helper.py --task TK032 --start

# Auditar y Sincronizar Google Sheets
py .agents/skills/ispc-dev/scripts/kanban_helper.py --sync-backlog "URL_DEL_SHEET"
```
> 👉 *Consulta la lista completa de comandos en `references/kanban_commands.md`.*

---

## 🧩 Figma Desktop Bridge
El plugin de Figma integrado permite exportar e inspeccionar tokens sin cuenta Enterprise.
1. Abre **Figma Desktop**.
2. Ve a **Plugins** ➔ **Development** ➔ **Import plugin from manifest**.
3. Selecciona el archivo `.agents/skills/ispc-dev/figma-plugin/manifest.json`.

---

## 🤖 Uso para Agentes de IA
La IA consultará automáticamente el archivo `SKILL.md` en la raíz de este proyecto. Allí se establecen las reglas estrictas de planificación previa, uso de español latino, y qué módulo interno de `scripts/` debe leer según el dominio del problema, ahorrando valiosos tokens de contexto.
