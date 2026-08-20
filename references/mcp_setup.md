# Guía de Integración con Servidores MCP y Google Docs / Sheets

El **Model Context Protocol (MCP)** y las herramientas integradas del skill permiten conectar, leer, buscar y modificar dinámicamente tanto la documentación local como la alojada en **Google Docs** y **Google Sheets**.

---

## 🌐 1. Soporte Nativo para Google Docs y Google Sheets (Vía URL)

El `kanban_helper.py` cuenta con extracción directa de contenido desde enlaces públicos de **Google Docs** y **Google Sheets**.

### Comandos de Ejemplo:

- **Leer o actualizar una planilla de Google Sheets (ej. Product Backlog):**
  ```bash
  py .agents/skills/ispc-dev/scripts/kanban_helper.py --update-sheet "https://docs.google.com/spreadsheets/d/18bk6mBoyyrO_kGhaLSdjyv0_2jlCSm4rkookrUoueS8/edit" --task "TK 37" --status "In Review"
  ```
- **Leer un documento de Google Docs:**
  ```bash
  py .agents/skills/ispc-dev/scripts/kanban_helper.py --docs-read "https://docs.google.com/document/d/<DOC_ID>/edit"
  ```

---

## 🔌 2. Servidores MCP Recomendados

Para entornos que utilizan **MCP Servers**, se pueden configurar los siguientes conectores para interacción bidireccional:

### 📄 MCP Server de Google Drive / Docs (`@modelcontextprotocol/server-gdrive`)
Permite leer, buscar y modificar archivos directamente en Google Drive, Google Docs y Google Sheets sin exportaciones manuales.

**Configuración lista para tu proyecto:**
```json
{
  "mcpServers": {
    "ispc-gdrive": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gdrive"],
      "env": {
        "GOOGLE_CLIENT_ID": "TU_CLIENT_ID_AQUI.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "GOCSPX-TU_CLIENT_SECRET_AQUI"
      }
    }
  }
}
```

### 📁 MCP Server de Archivos Locales (`@modelcontextprotocol/server-filesystem`)
```json
{
  "mcpServers": {
    "ispc-filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "c:/Users/av-cr/OneDrive/Escritorio/Integrador-fullstack"
      ]
    }
  }
}
```

### 🐙 MCP Server de GitHub (`@modelcontextprotocol/server-github`)
```json
{
  "mcpServers": {
    "ispc-github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<TU_GITHUB_TOKEN>"
      }
    }
  }
}
```

### 🎨 MCP Server y Plugin de Figma (`Figma Desktop Bridge` / `@modelcontextprotocol/server-figma`)

El skill incluye el plugin integrado en `.agents/skills/ispc-dev/figma-plugin/`.

#### Opción A: Figma Desktop Bridge (Local WebSocket)
1. Abrir Figma Desktop.
2. Ir a **Plugins** ➔ **Development** ➔ **Import plugin from manifest...**
3. Seleccionar el archivo `.agents/skills/ispc-dev/figma-plugin/manifest.json`.
4. Ejecutar el plugin en Figma.

#### Opción B: Figma Remote MCP Server (Oficial)
```json
{
  "mcpServers": {
    "figma": {
      "url": "https://mcp.figma.com/mcp",
      "headers": {
        "Authorization": "Bearer <FIGMA_PERSONAL_ACCESS_TOKEN>"
      }
    }
  }
}
```

---

## 🛠️ Resumen de Comandos CLI del Kanban Helper

| Tipo | Comando | Descripción |
|------|---------|-------------|
| **Local** | `py scripts/kanban_helper.py --docs` | Lista documentos `.md`, `.txt`, `.docx` |
| **Local** | `py scripts/kanban_helper.py --docs-search "<query>"` | Busca términos en documentos locales |
| **Local** | `py scripts/kanban_helper.py --docs-read "<path>"` | Lee un documento local |
| **Google** | `py scripts/kanban_helper.py --docs-read "<google_doc_or_sheet_url>"` | Descarga y lee un Google Doc o Sheet |
| **Local** | `py scripts/kanban_helper.py --docs-update "<path>" --body "<texto>"` | Crea o actualiza un documento |
