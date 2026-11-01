# Modelo de amenazas

Este directorio contiene el modelado de amenazas del sistema objetivo (capítulo 4 de la memoria).
Metodología: **PASTA** para el proceso y **STRIDE** para la clasificación, con la matriz de amenazas
mapeada a **MITRE ATLAS 2026.10** y al **OWASP Top 10 for Agentic Applications for 2026** (ASI01-ASI10).
IDs y nombres comprobados el 1 nov 2026 en `mitre-atlas/atlas-data` (`dist/v6/ATLAS-2026.10.yaml`) y en el
PDF oficial de OWASP.

## Sistema objetivo

Un agente LLM interno ("AsistenteLab") que ayuda a un analista y dispone de herramientas:
CRM (SQLite), lectura de contratos, `http_fetch`, `enviar_email`, broker de credenciales y utilidades.

## Diagrama de flujo de datos (DFD)

Ver [`dfd.mmd`](dfd.mmd). El límite de confianza clave separa:

- **Zona de confianza**: system prompt, motor de políticas, herramientas internas, base de datos.
- **Zona no confiable**: mensaje del usuario, contenido de documentos y páginas web, descripciones de
  herramientas de terceros (MCP). Todo lo que cruza hacia el modelo desde aquí es *dato*, nunca instrucción.

## Matriz de amenazas priorizada

P = probabilidad, I = impacto (A alta, M media), estimadas a priori. Prioridad: crítica si A/A, alta si A/M,
media si M/M.

| ID | Amenaza | STRIDE | ATLAS | ASI | P/I | Prioridad | Escenario | Control principal |
|---|---|---|---|---|---|---|---|---|
| T1 | Inyección directa (E1) | T, E | AML.T0051.000, AML.T0069.002 | ASI01 | A/M | Alta | S1 | Guardrail de entrada |
| T2 | Inyección indirecta vía documento o web (E2) | T, E | AML.T0051.001, AML.T0099 | ASI01 | A/A | Crítica | S2 | Guardrail sobre resultados |
| T3 | Descripción de herramienta envenenada (E3) | S, T | AML.T0110, AML.T0010.005 | ASI04 | M/A | Alta | S3 | Pinning por hash |
| T4 | Robo de credenciales | I, E | AML.T0098 | ASI03 | M/A | Alta | S4 | Broker `cred://` + mínimo privilegio |
| T5 | Exfiltración por egress (E4) | I | AML.T0086 | ASI02 | M/A | Alta | S2-S4 | Allowlist de egress + DLP |
| T6 | Acción no autorizada con herramienta legítima | E | AML.T0053 | ASI02 | M/M | Media | S2-S4 | Confirmación humana (HITL) |
| T7 | Fuga de datos personales en la respuesta (E4) | I | AML.T0136 | — | M/M | Media | benignas | Máscara de campos + DLP |

Correcciones del 1 nov 2026 respecto a la versión anterior: S3 es AML.T0110 (*AI Agent Tool Poisoning*, la
definición visible de la herramienta), no AML.T0099 (*AI Agent Tool Data Poisoning*, datos que el agente lee
con una herramienta, que encaja con S2); ASI06 no aplica porque el agente no tiene memoria persistente; ASI05
es *Unexpected Code Execution* y no cubre la fuga de PII, que no tiene categoría propia en el Top 10.

Fuera de alcance: ASI05 (sin herramientas que ejecuten código), ASI06 (sin memoria), ASI07/ASI08/ASI10 (un
solo agente), ASI09 (aprobador automático en campañas) y los ataques al propio modelo.

La justificación completa está en el capítulo 4 de la memoria.
