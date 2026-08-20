# Módulo: <Nombre del Módulo>

## 🎯 Objetivo del Módulo

<Describir qué función cumple este módulo dentro del sistema FCCApp. Explicar en términos claros qué problema resuelve, qué necesidad del negocio atiende y cómo se integra con el resto de la aplicación.>

## 📚 Conceptos Clave para Estudiar

<Para cada concepto técnico que se aplica en este módulo, incluir:>

### <Nombre del Concepto> (ej. Modelos Django con ForeignKey)
- **Qué es:** <Explicación breve del concepto>
- **Por qué se usa aquí:** <Por qué es necesario en este módulo específico>
- **Documentación:** <Link a documentación oficial o wiki del proyecto>

### <Otro Concepto>
- **Qué es:** <...>
- **Por qué se usa aquí:** <...>
- **Documentación:** <...>

## 📋 Tickets del Módulo

| TK ID | Título | Estado Actual | Descripción Breve |
|-------|--------|---------------|-------------------|
| TK00X | ...    | Todo          | ...               |
| TK00Y | ...    | Todo          | ...               |
| TK00Z | ...    | Todo          | ...               |

## 🔄 Plan de Entrega

<Describir el orden de ejecución de los tickets y las dependencias entre ellos. Por ejemplo:>

1. **TK00X** → Se ejecuta primero porque define los modelos base que necesitan los demás tickets.
2. **TK00Y** → Depende de TK00X. Implementa los serializers y vistas sobre los modelos creados.
3. **TK00Z** → Puede ejecutarse en paralelo con TK00Y. Agrega configuración independiente.

## 📝 Mensaje de Pull Request (borrador)

<Texto completo del PR que se creará al finalizar todos los tickets. Debe seguir la guía de estilo: narrativo, primera persona del singular, sin listas con viñetas, estructura de párrafos (contexto, detalle técnico, pruebas).>

```markdown
# Integración de <Funcionalidades Principales> (<IDs de Tickets>)

<Párrafo 1 - Contexto y Objetivos>

<Párrafo 2 - Detalle Técnico de la Implementación>

<Párrafo 3 - Suite de Pruebas y Verificación>

Closes #ID_ISSUE_1, Closes #ID_ISSUE_2, Closes #ID_ISSUE_3
```

## ⚠️ Datos Relevantes

<Información adicional importante para el desarrollo del módulo:>

- **Dependencias entre apps:** <Qué apps de Django interactúan>
- **Migraciones esperadas:** <Cuántas migraciones se anticipan>
- **Riesgos identificados:** <Posibles problemas o conflictos>
- **Decisiones de diseño:** <Elecciones técnicas relevantes y su justificación>
- **Variables de entorno nuevas:** <Si se agregan variables al .env>
