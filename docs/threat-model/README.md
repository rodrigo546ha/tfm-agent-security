# Modelo de amenazas

Este directorio contiene el modelado de amenazas del sistema objetivo (capítulo 4 de la memoria).
Metodología: **PASTA** para el proceso y **STRIDE** para la clasificación, con la matriz de amenazas
mapeada a **MITRE ATLAS** y **OWASP Agentic Security Initiative (ASI) Top 10 2026**.

## Sistema objetivo

Un agente LLM interno ("AsistenteLab") que ayuda a un analista y dispone de herramientas:
CRM (SQLite), lectura de contratos, `http_fetch`, `enviar_email`, broker de credenciales y utilidades.

## Diagrama de flujo de datos (DFD)

Ver [`dfd.mmd`](dfd.mmd). El límite de confianza clave separa:

- **Zona de confianza**: system prompt, motor de políticas, herramientas internas, base de datos.
- **Zona no confiable**: mensaje del usuario, contenido de documentos y páginas web, descripciones de
  herramientas de terceros (MCP). Todo lo que cruza hacia el modelo desde aquí es *dato*, nunca instrucción.

## Matriz de amenazas (extracto priorizado)

| ID | Amenaza | STRIDE | ATLAS | ASI | Escenario | Control principal |
|---|---|---|---|---|---|---|
| T1 | Inyección directa de instrucciones | Tampering / EoP | AML.T0051 | ASI01 | S1 | Guardrail de entrada |
| T2 | Inyección indirecta vía documento/web | Tampering | AML.T0051 | ASI01/ASI06 | S2 | Guardrail sobre resultados de herramientas |
| T3 | Descripción de herramienta envenenada | Tampering / Spoofing | AML.T0099 | ASI04 | S3 | Pinning de manifiesto |
| T4 | Robo de credenciales | Info. disclosure | AML.T0055 | ASI03 | S4 | Broker + mínimo privilegio |
| T5 | Exfiltración por egress | Info. disclosure | AML.T0055 | ASI03 | S2/S4 | Allowlist de egress + filtro de salida |
| T6 | Abuso de herramienta / acción no autorizada | EoP | AML.T0053 | ASI02 | S3/S4 | Confirmación humana (HITL) |
| T7 | Fuga de PII de clientes | Info. disclosure | — | ASI05 | benignas | Minimización de datos (máscara) |

La matriz completa y su justificación van en el capítulo 4 de la memoria.
