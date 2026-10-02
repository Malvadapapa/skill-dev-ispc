# Plantilla Estandarizada para Reporte de Defectos (Bugs) — ISPC

Esta plantilla define el formato obligatorio para reportar incidentes, regresiones y fallos de accesibilidad en el proyecto, conforme a las directivas de la cátedra de Verificación y Validación de Programas.

---

## Formato del Título

```
TK<ID> - bug(<scope>): <CODIGO-BUG> - <Título descriptivo del defecto>
```

**Ejemplos:**
- `TK114 - bug(backend): BUG-01 - Error 400 al registrar cliente con guiones en CUIT/DNI`
- `TK237 - bug(frontend): ACC-BUG-01 - Contraste de color insuficiente en badge de estados del taller (WCAG 1.4.3)`

---

## Cuerpo del Issue (Markdown)

```markdown
### 🐛 Descripción del Defecto
[Descripción concisa y técnica del comportamiento anómalo detectado en el sistema.]

---

### 📍 Clasificación y Alcance
- **Módulo Afectado:** [Ej. Clientes / Facturación / Taller / Turnos / Autenticación]
- **Componente / Ruta:** [Ej. `src/app/modules/taller/components/orden-card.component.html` o `/api/clientes/`]
- **Tipo de Defecto:** [Funcional / Validación / Rendimiento / Visual / Accesibilidad WCAG]
- **Severidad:** [Crítica (Bloqueante) | Mayor | Menor | Trivial]
- **Prioridad:** [Alta | Media | Baja]
- **Criterio WCAG Afectado:** [Ej. WCAG 2.2 - 1.4.3 Contraste Mínimo (Nivel AA) - Si no aplica colocar N/A]
- **Caso de Prueba Vinculado:** [Ej. `TEST-D-001`, `ACC-01` o `N/A (Detectado en exploración)`]

---

### 📋 Precondiciones
1. [Ej. Usuario autenticado con rol de Administrador o Técnico.]
2. [Ej. Existencia de una orden de trabajo en estado "En Diagnóstico".]

---

### 👣 Pasos para Reproducir
1. [Navegar a la ruta / pantalla ...]
2. [Hacer clic en el botón / elemento ...]
3. [Ingresar el valor '...' en el campo ...]
4. [Enviar el formulario o presionar Guardar.]

---

### ❌ Comportamiento Obtenido
[Describir exactamente qué sucede actualmente, incluyendo mensajes de error, códigos HTTP anómalos o comportamientos visuales incorrectos.]

---

### ✅ Comportamiento Esperado
[Describir cómo debería comportarse el sistema según la especificación funcional o la pauta de diseño/accesibilidad.]

---

### 📷 Evidencias
- **Captura / Grabación:** `docs/evidencias_bugs/EVIDENCIA_<CODIGO_BUG>.png`
- **Logs / Consola de Red:** 
```json
{
  "status": 400,
  "error": "..."
}
```

---

### 💻 Entorno de Prueba
- **Ambiente:** Local / Staging
- **Sistema Operativo:** Windows 11 / Linux
- **Navegador:** Chrome / Firefox / Edge (versión ...)
- **Resolución:** Desktop 1920x1080 / Mobile 375x667
- **Base de Datos:** PostgreSQL 16
```
