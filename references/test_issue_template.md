# Plantilla Estandarizada para Tickets de Testing (QA) — ISPC

Esta plantilla define el formato obligatorio para los tickets de pruebas automatizadas y aseguramiento de calidad del Sprint 4, conforme a la pirámide de pruebas de la cátedra de Verificación y Validación de Programas.

---

## Formato del Título

```
TK<ID> - testing(<scope>): <CODIGO-TEST> - <Título descriptivo de la prueba>
```

**Prefijos normativos por capa:**
- `AUT-BE-XX`: Pruebas de Backend (Django REST Framework / pytest-django)
- `AUT-API-XX`: Pruebas de API de Caja Negra (Postman / Newman)
- `AUT-E2E-XX`: Pruebas End-to-End de Frontend (Playwright / POM)
- `ACC-XX`: Auditorías y Evaluaciones de Accesibilidad Web (WCAG 2.2 Nivel AA)
- `DOC-QA-XX`: Documentación, Planes de Prueba y Matrices de Trazabilidad

**Ejemplos:**
- `TK218 - testing(backend): AUT-BE-02 - Validación de verbos HTTP no permitidos (405) y endpoints inexistentes (404)`
- `TK224 - testing(api): AUT-API-03 - Verificación de tiempos de respuesta (< 500 ms) y estabilidad en endpoints críticos`
- `TK229 - testing(frontend): AUT-E2E-02 - Automatización de flujo E2E: Autenticación completa (login válido, inválido y logout)`
- `TK233 - testing(frontend): ACC-02 - Auditoría con Google Lighthouse en vistas principales (Puntuación ≥ 90)`

---

## Cuerpo del Issue (Markdown)

```markdown
### 🎯 Objetivo de la Prueba
[Descripción concisa del escenario o suite a implementar y el riesgo que mitiga.]

---

### 📊 Clasificación de QA
- **Capa de la Pirámide:** [Unitaria / Integración Backend | API Caja Negra | E2E Frontend | Accesibilidad WCAG]
- **Tipo de Testing:** [Funcional | Negativa | Regresión | Contrato | Seguridad | Accesibilidad | Rendimiento]
- **Historia de Usuario Vinculada:** [Ej. `HU-01`, `HU-03`, `HU-05`]
- **Caso de Prueba Manual Relacionado:** [Ej. `TEST-D-001`, `TEST-L-001` o `Nuevo (Sprint 4)`]
- **Herramienta Principal:** [pytest-django / coverage.py | Postman / Newman | Playwright | axe-core / Lighthouse]

---

### 📋 Precondiciones y Datos de Prueba
1. [Ej. Servidor de backend y frontend levantados en entorno local.]
2. [Ej. Base de datos PostgreSQL inicializada con migraciones y fixtures de usuarios/roles.]
3. [Ej. Credenciales válidas para tokens JWT o variables de entorno Postman.]

---

### 🔬 Escenarios a Evaluar y Aserciones
- [ ] **Escenario 1 (Caso Feliz / Positivo):**
  - Acción: [Ej. Envío de payload válido vía POST /api/clientes/]
  - Aserción: [Ej. Status code 201 Created, estructura JSON según contrato, campo id generado]
- [ ] **Escenario 2 (Casos Borde / Negativos):**
  - Acción: [Ej. Envío sin token Authorization o con datos inválidos]
  - Aserción: [Ej. Status 401 Unauthorized / 400 Bad Request con mensaje de error específico por campo]
- [ ] **Escenario 3 (Regresión / Tiempos / Accesibilidad):**
  - Aserción: [Ej. Tiempo de respuesta menor a 500 ms / 0 violaciones graves en axe-core]

---

### 💻 Ubicación del Código y Comandos de Ejecución
- **Archivo de Implementación:** `[ruta/al/archivo/test.py o e2e/tests/flujo.spec.ts]`
- **Comando de Ejecución Local:**
```bash
[Comando exacto para reproducir la prueba localmente]
```

---

### 🏁 Criterios de Aceptación (Definition of Done)
- [ ] Código del test implementado bajo el estándar correspondiente (AAA en backend / POM en Playwright / Carpetas en Postman).
- [ ] Suite completa en verde (sin fallos ni skips injustificados).
- [ ] Reporte o artefacto de evidencia generado (`htmlcov/`, `report_newman.html`, captura o trace).
- [ ] Fila registrada en la [Matriz de Trazabilidad](file:///c:/Users/av-cr/OneDrive/Escritorio/Integrador-fullstack/.agents/skills/ispc-dev/wiki/Matriz-de-Trazabilidad.md).
```
