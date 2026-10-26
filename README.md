# Spookython 2026 — Track B · La plaga zombie

Mesa del Comité de Contención para Manta. Simula día a día una gripe de contacto sobre una red de hogares, aulas, buses y mercados, y dice a quién cubrir primero cuando las dosis no alcanzan.

La estrategia se compara siempre contra dos líneas base con la **misma semilla** y la **misma suerte de contagio**: no intervenir, y gastar el mismo presupuesto al azar. El motor es determinista. La nube solo lo orquesta.

![Arquitectura](docs/arquitectura.svg)

## Semilla y parámetros por defecto

| Parámetro | Valor | Qué es |
| --- | --- | --- |
| Semilla | `42` | Fija la ciudad, los pacientes cero y cada tirada |
| Muestra | 480 personas | Un escenario, no el cantón |
| Días | 40 | |
| β | 0,16 | Probabilidad diaria de contagio en un contacto de hogar |
| σ | 0,50 | Mordido → zombie. Media ≈ 2 días |
| γ | 0,25 | Zombie → exorcizado. Media ≈ 4 días |
| K | 40 | Dosis, solo a personas sanas |
| Eficacia | 1 | Protección total. El brote sorpresa puede bajarla |
| Criterio | anillo | Primero el hogar y los contactos del caso; con lo que sobre, el mayor grado |
| Corridas | 8 | Se publican media y percentiles 5 y 95 |

Con esa semilla la vacunación por grado deja menos contagios que el azar y que no hacer nada. La interfaz muestra la huella del resultado: misma configuración y misma semilla → misma huella.

Comprobarlo en local:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m engine
PYTHONPATH=src .venv/bin/pytest
```

## Cómo probar la interfaz

Terminal 1:

```bash
make api
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Abrir `http://127.0.0.1:5173`. Al cargar corre el escenario por defecto. Los botones **Doble contagio**, **Mitad de dosis**, **Brote en el mercado** y **Eficacia 60%** son los giros del brote sorpresa: cambian el escenario actual y vuelven a simular.

`POST /simulate` acepta el mismo JSON que el formulario. `GET /health` y `GET /defaults` describen el servicio.

## Supuestos

La organización no entrega datos. Estos son los nuestros.

**La plaga es de contacto, no de mosquito.** El reto la hace pasar por casa, bus, colegio y mercado, así que el análogo real es una influenza, no el dengue. La incubación media de ~2 días y el periodo infeccioso de ~4 días siguen el orden de magnitud que publica CDC para la influenza estacional. β no sale de una serie de Manta: está elegido para que, sin intervención, el brote en la muestra sea visible y la vacuna todavía pueda cambiar el desenlace. El jurado puede subirlo o bajarlo.

**Estados.** Sano (S), Mordido (E, no contagia), Zombie (I, contagia), Exorcizado (R, inmune). Quien recibe una vacuna de eficacia 1 pasa a R el día 0 y **no cuenta como contagio**. Con eficacia menor sigue sano, pero con susceptibilidad `1 - eficacia`. No se vacuna al paciente cero ni a nadie que ya no esté sano.

**La población es una muestra.** El cantón Manta tenía **271.145 habitantes** en el Censo 2022 (INEC, 271.145; Manabí 1.592.840). El hogar promedio nacional era **3,2 personas** (INEC, presentación del Censo 2022; el portal redondea 3,3). En Manabí, el **25,8%** tenía de 0 a 14 años: en el modelo esa fracción es estudiante. Los resultados son conteos de la muestra. No se multiplican por 271.145: el cantón no es una copia lineal de 480 personas.

**La red.** Hogares con la distribución nacional de tamaños 1 a 6. Parroquias del escenario: Manta, Tarqui, Eloy Alfaro, San Mateo y San Lorenzo, repartidas al azar de la semilla (no hay población parroquial dentro del modelo). Cada estudiante tiene pocos compañeros de aula, no el salón entero conectado. Una arista une aulas del mismo colegio. Parte de los adultos viaja en bus, con pocos contactos por ruta. Todo el mundo compra en uno de tres mercados; nueve comerciantes son los hubs. El contacto de hogar pesa 1. Aula, bus y mercado pesan menos, así que contagian con probabilidad `1 - (1 - β) ^ peso`.

**La estrategia por defecto es vacunación en anillo.** Es la misma idea que se usó contra la viruela y, más cerca, en brotes de Ébola: cubrir primero a quien vive con el caso y a quien tuvo contacto directo, y recién después a los hubs de la ciudad (grado). Con eficacia 1 y un presupuesto que alcanza para ese anillo, el caso índice no tiene a quién contagiar y la incidencia de la muestra queda en 1. No es un truco de una sola semilla: el paciente cero cambia en cada corrida y el anillo se recalcula. Si la eficacia baja o el caso es un comerciante con más contactos que dosis, el brote escapa y el tablero lo muestra. El azar gasta el mismo K sobre sanos, con otro generador, para no tocar la suerte del contagio. También se puede pedir solo grado, solo puentes o intermediación.

La cuarentena no es una vacuna: corta aula, bus, mercado y puentes, y **deja el hogar**. Aislar al anillo no impide que la familia se contagie entre sí.

**Números aleatorios emparejados.** Cada corrida deriva su semilla de la semilla maestra. Dentro de la corrida, las tres políticas consumen la misma cinta: cada arista y cada persona tiran su dado aunque ese día no haya contagio. La diferencia entre curvas es a quién se protegió, no una racha de suerte distinta.

**Lo que el modelo no hace.** No hay camas de hospital, ni fumigación, ni reposición diaria de dosis, ni mapa de manzanas. La edad no cambia la letalidad: en esta plaga nadie muere, se exorciza y queda inmune. Esas extensiones caben en el nivel Pro sin cambiar la forma del motor.

## Arquitectura

El detalle desplegable está en [`infra/template.yaml`](infra/template.yaml) y el dibujo editable en [`docs/arquitectura.drawio`](docs/arquitectura.drawio).

| Capa | Pieza | Para qué |
| --- | --- | --- |
| Presentación | S3 + CloudFront | SPA React/Vite |
| Borde | API Gateway | `POST /api/simulate`, `GET /api/jobs/{id}` |
| Orquestación | Lambda | Valida, fija semilla, responde en la demo |
| Monte Carlo grande | Step Functions Distributed Map | Hasta 20 corridas a la vez, ítems en S3 |
| Motor | Lambda simulador | El mismo paquete `engine` que corre en local |
| Estado | DynamoDB | Trabajo, semilla, puntero al JSON. TTL 14 días |
| Curvas | S3 | Privado. Los objetos expiran a los 14 días |
| Ojo en la cuenta | CloudWatch (7 días) y AWS Budgets | Alerta desde el deploy |

La demo en vivo usa la ruta **síncrona** (API Gateway corta a los 29 s y el escenario por defecto responde enseguida). El mapa distribuido es para pasar de decenas de corridas a cientos sin reescribir el motor. `src/engine` no importa boto3.

Seguridad del diseño: sin llaves en el código; cada Lambda tiene su rol; el bucket del frontend solo lo lee CloudFront (OAC); el bucket de resultados no es público; CORS de la API limitado a GET, POST y OPTIONS.

## Despliegue en us-east-1

Hace falta una cuenta del equipo, AWS SAM y credenciales locales. El presupuesto de AWS solo se crea en us-east-1.

```bash
cd frontend && npm ci && npm run build && cd ..
sam build -t infra/template.yaml
sam deploy -t infra/template.yaml --guided --region us-east-1 \
  --parameter-overrides AlertEmail=correo-del-equipo@ejemplo.com MonthlyBudgetUsd=20
```

Al terminar, el output `FrontendBucketName` es el bucket privado y `PublicUrl` es la URL del jurado:

```bash
aws s3 sync frontend/dist "s3://NOMBRE-DEL-BUCKET" --delete --region us-east-1
```

Confirmar el correo de Budgets el mismo día. Guardar la captura en `docs/budget.png` y anotar el gasto real en [`docs/costos.md`](docs/costos.md).

La URL pública queda pendiente de esa cuenta. Este repositorio trae el sistema y la plantilla; no despliega solo.

## Decisiones

- El motor vive aparte de AWS para que la prueba de fuego solo cambie parámetros.
- La línea base aleatoria gasta el mismo K. Si no, la comparación no dice nada.
- El criterio por defecto es el anillo del caso y, con las dosis que sobran, el grado. En las semillas 1, 2, 3, 7, 11, 21, 42, 99, 123 y 256 la media le gana a las dos líneas base. Grado, puentes e intermediación siguen en el selector; la intermediación es la más lenta.
- La muestra no se extrapola al cantón. Inventar ese factor restaría rigor.

## Límites

- Sin mapa territorial ni informe para el alcalde (nivel Pro: GeoJSON y, si se quiere, Bedrock).
- El mapa distribuido está en la plantilla y no se ejercitó contra una cuenta real en este repo. La ruta que usa la interfaz es la síncrona, y esa sí tiene pruebas.
- Betweenness en muestras grandes puede acercarse al tope de 29 s de API Gateway. Para ensayar, bajar población o corridas.
- Falta la captura del presupuesto hasta que el equipo despliegue.

## Estructura

```
README.md
docs/arquitectura.svg
docs/arquitectura.drawio
docs/costos.md
src/engine/          motor puro
src/api/             FastAPI local
src/lambdas/         orquestador, simulador, agregador
infra/template.yaml
frontend/            SPA
tests/
```

## Referencias de los números públicos

- INEC, «201.279 personas más viven en Manabí» (4 de octubre de 2023): Manabí 1.592.840; Manta 271.145; 25,8% de 0 a 14 años en la provincia. https://www.ecuadorencifras.gob.ec/institucional/201-279-personas-mas-viven-en-manabi/
- INEC, presentación del VIII Censo de Población y VII de Vivienda 2022: 5.188.827 hogares, promedio 3,2 personas. https://anda.inec.gob.ec/anda5/index.php/catalog/1085
- CDC, signos clínicos de la influenza: incubación de 1 a 4 días, alrededor de 2. El periodo infeccioso usual va de un día antes de los síntomas a unos 5–7 días después; el modelo usa una media de 4 días como simplificación explícita.
