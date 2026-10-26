# Costos — Spookython 2026 Track B

Región: **us-east-1**. Estimado de un mes de evento, no de un servicio siempre encendido.
No hay EC2, NAT Gateway, RDS ni balanceadores. Todo es pago por uso.

## Qué queda prendido

| Pieza | Uso previsto en el evento | Estimado mensual |
| --- | --- | --- |
| Lambda orquestador | Demo en vivo y ensayos. ~2.000 invocaciones de 2 s a 1,7 GB | < 1 USD |
| Lambda simulador + agregador | Solo si se dispara el mapa. Tope de 20 en paralelo | < 2 USD si se usa con moderación |
| Step Functions Distributed Map | Nivel Pro. Cada corrida son pocos estados. Concurrencia 20 | < 3 USD bajo el tope de 400 corridas por trabajo |
| API Gateway REST | Las mismas ~2.000 llamadas | < 1 USD |
| CloudFront + S3 frontend | Tráfico del jurado y del equipo | < 1 USD |
| S3 resultados | JSON de trabajos. Se borra a los 14 días | < 1 USD |
| DynamoDB on-demand | Un ítem por trabajo | < 1 USD |
| CloudWatch Logs | Retención 7 días | 1–2 USD |
| AWS Budgets | Dos notificaciones (50% real, 100% previsto). Los dos primeros presupuestos con acción suelen entrar en el tramo gratuito; si no, unos céntimos al día | < 2 USD |
| **Total de referencia** | | **5 a 15 USD** |

El tope de la plantilla es **20 USD** (`MonthlyBudgetUsd`). La alerta sale al 50% del gasto real y cuando el pronóstico llega al 100%.

## Qué haría subir la cuenta

- Subir `BATCH_MAX_RUNS` y lanzar miles de mapas sin el tope de concurrencia.
- Dejar la retención de logs en “nunca expira”.
- Crear un NAT Gateway o una instancia “para probar”. No hace falta para este diseño.
- Pedir intermediación (`betweenness`) en poblaciones grandes dentro de un bucle de ensayos: es más lento, no más caro por sí solo, pero alarga el tiempo de Lambda.

## Gasto real del evento

Completar el día del despliegue y el día de la entrega.

| Concepto | Valor |
| --- | --- |
| Fecha de apertura de la cuenta / del stack | |
| Gasto acumulado al cierre (consola de Billing, us-east-1) | |
| Captura del presupuesto | `docs/budget.png` (pendiente de la cuenta del equipo) |

La plantilla crea el presupuesto solo si el deploy recibe `AlertEmail`. Sin ese correo no hay alerta y el criterio de costos del reto queda incompleto.
