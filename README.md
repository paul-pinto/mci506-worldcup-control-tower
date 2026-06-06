# 🏆 World Cup Data Control Tower

Pipeline automatizado de Ingeniería de Datos para extraer, transformar y visualizar datos de la Copa Mundial FIFA usando arquitectura Medallion sobre Google Cloud Platform.

Proyecto final — Módulo MCI506 - Ingeniería de Datos

El proyecto fue desarrollado para el módulo **MCI506 - Ingeniería de Datos** y utiliza el stack solicitado en clase:

- **Python** para extracción y procesamiento inicial.
- **Google Cloud Storage (GCS)** como capa Bronze.
- **BigQuery** para tablas externas, Silver y Gold.
- **GitHub Actions** para orquestación automática.
- **Scheduled Queries de BigQuery** para transformación automática.
- **Looker Studio** para visualización.

---

## Tabla de contenidos

1. [Resumen del proyecto](#resumen-del-proyecto)
2. [Objetivo](#objetivo)
3. [Arquitectura general](#arquitectura-general)
4. [Stack utilizado](#stack-utilizado)
5. [Fuente de datos](#fuente-de-datos)
6. [Limitación de API-Football para season 2026](#limitación-de-api-football-para-season-2026)
7. [Estructura del repositorio](#estructura-del-repositorio)
8. [Flujo del pipeline](#flujo-del-pipeline)
9. [Capas de datos](#capas-de-datos)
10. [Modelo de datos](#modelo-de-datos)
11. [Tablas BigQuery](#tablas-bigquery)
12. [Dashboard Looker Studio](#dashboard-looker-studio)
13. [Automatización](#automatización)
14. [Calidad de datos](#calidad-de-datos)
15. [Cómo ejecutar el proyecto localmente](#cómo-ejecutar-el-proyecto-localmente)
16. [Variables de entorno](#variables-de-entorno)
17. [GitHub Actions](#github-actions)
18. [Scheduled Queries](#scheduled-queries)
19. [Validaciones SQL](#validaciones-sql)
20. [Plan de recuperación ante fallas](#plan-de-recuperación-ante-fallas)
21. [Preguntas clave del proyecto](#preguntas-clave-del-proyecto)
22. [Resultados actuales](#resultados-actuales)
23. [Evolución hacia Mundial 2026](#evolución-hacia-mundial-2026)
24. [Equipo](#equipo)
25. [Links](#links)
26. [Conclusión](#conclusión)
---

# Resumen del proyecto

**World Cup Data Control Tower** es un pipeline automatizado que obtiene datos de la Copa Mundial FIFA desde una API deportiva, los almacena en Google Cloud Storage, los transforma en BigQuery mediante arquitectura medallion y los visualiza en Looker Studio.

El proyecto implementa un flujo completo de Ingeniería de Datos:

```text
API-Football
    ↓
Python extract.py
    ↓
GCS Bronze
    ↓
BigQuery External Tables
    ↓
BigQuery Silver
    ↓
BigQuery Gold
    ↓
Looker Studio Dashboard
```

La arquitectura fue diseñada para operar sobre la temporada objetivo **World Cup 2026**. Sin embargo, durante el desarrollo se identificó que el plan gratuito de API-Football no permite consultar `season=2026`. Por esa razón, la validación funcional del pipeline se realizó usando `season=2022`, que contiene datos reales y completos del Mundial 2022.

El pipeline está parametrizado por variables de entorno, por lo que para operar sobre 2026 solo se debe cambiar:

```env
WORLD_CUP_SEASON=2022
```

siempre que el plan de la API permita el acceso a dicha temporada.

---

# Objetivo

Construir un pipeline automatizado y documentado que permita:

1. Extraer datos deportivos desde una API pública.
2. Guardar los datos crudos en GCS.
3. Crear tablas externas en BigQuery sobre los archivos almacenados.
4. Transformar los datos a una capa Silver limpia y deduplicada.
5. Crear tablas Gold con agregaciones analíticas.
6. Automatizar la extracción mediante GitHub Actions.
7. Automatizar las transformaciones mediante Scheduled Queries.
8. Visualizar los resultados en Looker Studio.
9. Documentar el pipeline para que pueda ser entendido y ejecutado por terceros.

---

# Arquitectura general
## Diagrama de flujo detallado

```
┌──────────────────────────────────────────────────────────────┐
│                    FUENTE DE DATOS                           │
│  API-Football v3  │  /fixtures  │  /teams  │  /standings     │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP GET (Python requests)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  EXTRACCIÓN LOCAL                            │
│  extract.py  →  data/raw/run_id=TIMESTAMP/                   │
│  eda_local.py  →  data/processed/ (.csv + .parquet)          │
│  eda_summary.py  →  data/eda/ (perfiles de calidad)          │
└─────────────────────────┬────────────────────────────────────┘
                          │ google-cloud-storage SDK
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              BRONZE — Google Cloud Storage                   │
│  gs://mci506-worldcup/bronze/raw/        ← JSON crudo        │
│  gs://mci506-worldcup/bronze/processed/  ← CSV + Parquet     │
│  gs://mci506-worldcup/bronze/eda/        ← Perfiles calidad  │
└─────────────────────────┬────────────────────────────────────┘
                          │ BigQuery External Tables
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              SILVER — BigQuery                               │
│  silver_fixtures   ← SAFE_CAST + deduplicación incremental   │
│  silver_teams      ← WHERE NOT EXISTS                        │
│  silver_standings  ← Tipos validados                         │
└─────────────────────────┬────────────────────────────────────┘
                          │ Scheduled Query (06:45 UTC)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              GOLD — BigQuery                                 │
│  gold_tournament_overview  ← Resumen general                 │
│  gold_matches_by_round     ← Partidos por ronda              │
│  gold_venue_load           ← Carga por estadio               │
│  gold_team_performance     ← Rendimiento por equipo          │
│  gold_pipeline_quality     ← Score de calidad                │
└─────────────────────────┬────────────────────────────────────┘
                          │ BigQuery connector
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              VISUALIZACIÓN — Looker Studio                   │
│  4 páginas: Resumen │ Sedes │ Equipos │ Calidad pipeline     │
└──────────────────────────────────────────────────────────────┘

Automatización y Monitoreo:
  GitHub Actions  (06:00 UTC) → extrae y carga a GCS
  Scheduled Query silver (06:30 UTC) → actualiza Silver
  Scheduled Query gold   (06:45 UTC) → actualiza Gold
  Slack Webhooks (on failure) → notifica errores críticos
```
# Stack utilizado

| Componente | Herramienta | Uso |
|---|---|---|
| Lenguaje | Python | Extracción, aplanamiento, EDA y carga a GCS |
| Almacenamiento | Google Cloud Storage | Capa Bronze |
| Data Warehouse | BigQuery | External, Silver y Gold |
| Orquestación | GitHub Actions | Ejecución automática del extractor |
| Transformación programada | BigQuery Scheduled Queries | Silver y Gold automáticos |
| Visualización | Looker Studio | Dashboard final |
| Control de versiones | GitHub | Repositorio público y colaboración |
| Gestión de configuración | `.env` / GitHub Secrets | Variables sensibles y parámetros |
| Notificaciones | Slack Webhooks | Alertas de fallos críticos en el pipeline |

---

# Fuente de datos

La fuente principal del proyecto es **API-Football**, mediante los endpoints de la API v3.

Se utilizan los siguientes recursos:

| Entidad | Endpoint | Descripción |
|---|---|---|
| Fixtures | `/fixtures` | Partidos del torneo |
| Teams | `/teams` | Selecciones participantes |
| Standings | `/standings` | Posiciones por grupo |

Los parámetros principales son:

```env
WORLD_CUP_LEAGUE_ID=1
WORLD_CUP_SEASON=2022
```

Donde:

- `WORLD_CUP_LEAGUE_ID=1` corresponde a la competición World Cup dentro de API-Football.
- `WORLD_CUP_SEASON=2022` se usa para validación funcional con datos completos.
- `WORLD_CUP_SEASON=2026` queda soportado para ejecución futura si la API lo permite.

---

# Limitación de API-Football para season 2026

Durante el desarrollo se intentó consultar la temporada 2026 con el plan gratuito de API-Football. La API respondió:

```text
Free plans do not have access to this season, try from 2022 to 2024.
```

Por este motivo se tomó una decisión de ingeniería:

- Validar el pipeline con `season=2022`, que sí está disponible.
- Mantener el diseño parametrizado para `season=2026`.
- Documentar la restricción de acceso como parte del comportamiento real de la fuente externa.
- Dejar preparada la arquitectura para operar con 2026 si se habilita un plan pago o si se incorpora un dataset fallback oficial.

Esta decisión permite demostrar que el pipeline funciona de extremo a extremo sin depender de una API paga durante el desarrollo académico.

---

# Estructura del repositorio

```text
mci506-worldcup-data-pipeline/
├── .github/
│   └── workflows/
│       └── pipeline.yml
├── scripts/
│   ├── config.py
│   ├── extract.py
│   ├── utils.py
│   ├── eda_local.py
│   ├── eda_summary.py
│   ├── load_gcs.py
│   └── create_bq_dataset.py
├── sql/
│   ├── 01_external_tables.sql
│   ├── 02_silver_transform.sql
│   ├── 03_gold_aggregations.sql
│   └── 04_validation_queries.sql
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Flujo del pipeline

El pipeline se divide en cuatro grandes fases.

## 1. Extracción

Archivo principal:

```text
scripts/extract.py
```

Este script consulta API-Football para obtener:

- Fixtures.
- Teams.
- Standings.

Los datos se guardan como JSON crudo en:

```text
data/raw/
```

Cada ejecución genera un `run_id` basado en timestamp UTC.

Ejemplo:

```text
data/raw/fixtures/run_id=20260601T020746Z/fixtures_league=1_season=2022.json
data/raw/teams/run_id=20260601T020746Z/teams_league=1_season=2022.json
data/raw/standings/run_id=20260601T020746Z/standings_league=1_season=2022.json
```

---

## 2. Aplanamiento y EDA local

Archivo:

```text
scripts/eda_local.py
```

Este script toma los JSON crudos y genera archivos tabulares:

```text
data/processed/fixtures_flat.csv
data/processed/teams_flat.csv
data/processed/standings_flat.csv

data/processed/fixtures_flat.parquet
data/processed/teams_flat.parquet
data/processed/standings_flat.parquet
```

También genera un perfil básico de calidad:

```text
data/eda/data_quality_profile.csv
```

---

## 3. Resúmenes EDA

Archivo:

```text
scripts/eda_summary.py
```

Este script genera archivos analíticos preliminares:

```text
data/eda/overview.csv
data/eda/matches_by_round.csv
data/eda/venue_load.csv
data/eda/team_schedule.csv
data/eda/rest_summary.csv
data/eda/group_summary.csv
data/eda/quality_summary.csv
```

Estos archivos sirvieron como base para diseñar las tablas Gold.

---

## 4. Carga a GCS

Archivo:

```text
scripts/load_gcs.py
```

Este script sube los datos locales a Google Cloud Storage.

Bucket:

```text
gs://mci506-worldcup
```

Estructura en GCS:

```text
gs://mci506-worldcup/bronze/raw/
gs://mci506-worldcup/bronze/processed/
gs://mci506-worldcup/bronze/eda/
```

---

# Capas de datos

El proyecto usa arquitectura medallion.

## Bronze

Capa cruda/semi-cruda almacenada en GCS.

Contiene:

```text
bronze/raw/
bronze/processed/
bronze/eda/
```

Uso:

- Guardar evidencia de cada extracción.
- Mantener archivos versionados por ejecución.
- Servir como fuente de BigQuery External Tables.

---

## External

Tablas externas en BigQuery que leen directamente desde GCS.

Estas tablas no transforman los datos. Funcionan como puente entre Bronze y Silver.

Ejemplos:

```text
ext_fixtures_flat
ext_teams_flat
ext_standings_flat
ext_overview
ext_quality_summary
```

---

## Silver

Capa limpia, tipada y deduplicada.

Características:

- Tablas nativas BigQuery.
- Uso de `SAFE_CAST`.
- Conversión de strings a tipos adecuados.
- Eliminación de registros sin claves.
- Deduplicación incremental con `WHERE NOT EXISTS`.

Ejemplos:

```text
silver_fixtures
silver_teams
silver_standings
```

---

## Gold

Capa analítica final para Looker Studio.

Características:

- Agregaciones de negocio.
- Métricas listas para dashboard.
- Tablas simples de consumir.
- Indicadores de calidad y operación.

Ejemplos:

```text
gold_tournament_overview
gold_matches_by_round
gold_venue_load
gold_team_schedule
gold_group_summary
gold_team_performance
gold_pipeline_quality
```

---

# Modelo de datos

## silver_fixtures

Grano:

```text
1 fila = 1 partido
```

Clave principal:

```text
fixture_id
```

Campos principales:

| Campo | Descripción |
|---|---|
| fixture_id | Identificador único del partido |
| match_date | Fecha y hora del partido |
| season | Temporada |
| round | Ronda del torneo |
| venue_name | Estadio |
| venue_city | Ciudad |
| home_team_name | Equipo local |
| away_team_name | Equipo visitante |
| goals_home | Goles local |
| goals_away | Goles visitante |
| status_short | Estado corto del partido |
| status_long | Estado largo del partido |

---

## silver_teams

Grano:

```text
1 fila = 1 selección
```

Clave principal:

```text
team_id
```

Campos principales:

| Campo | Descripción |
|---|---|
| team_id | Identificador de la selección |
| team_name | Nombre de la selección |
| team_code | Código de selección |
| team_country | País |
| team_national | Indica si es selección nacional |
| team_logo | URL del logo |

---

## silver_standings

Grano:

```text
1 fila = 1 selección dentro de un grupo y temporada
```

Clave natural:

```text
season + group_name + team_id
```

Campos principales:

| Campo | Descripción |
|---|---|
| season | Temporada |
| group_name | Grupo |
| rank | Posición |
| team_id | Identificador de selección |
| team_name | Nombre de selección |
| points | Puntos |
| played | Partidos jugados |
| win | Victorias |
| draw | Empates |
| lose | Derrotas |
| goals_for | Goles a favor |
| goals_against | Goles en contra |
| goals_diff | Diferencia de goles |

---

# Tablas BigQuery

Proyecto GCP:

```text
mci506-paul-pinto
```

Dataset:

```text
mci506_worldcup
```

---

## External tables

| Tabla | Descripción |
|---|---|
| ext_fixtures_flat | Lee fixtures desde GCS |
| ext_teams_flat | Lee teams desde GCS |
| ext_standings_flat | Lee standings desde GCS |
| ext_overview | Lee resumen EDA desde GCS |
| ext_quality_summary | Lee resumen de calidad desde GCS |

---

## Silver tables

| Tabla | Descripción |
|---|---|
| silver_fixtures | Partidos limpios, tipados y deduplicados |
| silver_teams | Selecciones limpias y deduplicadas |
| silver_standings | Posiciones por grupo limpias y deduplicadas |

---

## Gold tables

| Tabla | Descripción |
|---|---|
| gold_tournament_overview | Resumen general del torneo |
| gold_matches_by_round | Partidos por ronda |
| gold_venue_load | Carga de partidos por estadio |
| gold_team_schedule | Calendario y descanso por selección |
| gold_group_summary | Resumen agregado por grupo |
| gold_team_performance | Rendimiento por equipo |
| gold_pipeline_quality | Calidad del pipeline |

---

# Dashboard Looker Studio

El dashboard fue construido en Looker Studio usando únicamente tablas Gold de BigQuery.

Nombre del dashboard:

```text
World Cup Data Control Tower
```

Link del dashboard:

```text
https://datastudio.google.com/reporting/41fa5555-1687-4a2b-918c-0b8321cbea44
```

---

## Páginas del dashboard

### 1. Resumen del torneo

Visualizaciones:

- Total de partidos.
- Total de selecciones.
- Total de sedes.
- Total de ciudades sede.
- Partidos por ronda.
- Resumen general del torneo.

Fuente principal:

```text
gold_tournament_overview
gold_matches_by_round
```

---

### 2. Sedes y rondas

Visualizaciones:

- Carga de partidos por estadio.
- Partidos por ciudad sede.
- Fase de grupos vs eliminatorias por estadio.
- Detalle operativo por estadio.

Fuente principal:

```text
gold_venue_load
```

---

### 3. Equipos y grupos

Visualizaciones:

- Resumen por grupo.
- Tabla de posiciones por grupo.
- Puntos por selección.
- Diferencia de goles por selección.
- Calendario y descanso por selección.

Fuente principal:

```text
gold_group_summary
gold_team_performance
gold_team_schedule
```

---

### 4. Calidad del pipeline

Visualizaciones:

- Score de calidad por tabla Silver.
- Filas cargadas por tabla Silver.
- Claves primarias duplicadas.
- Claves primarias faltantes.
- Detalle de calidad de datos.

Fuente principal:

```text
gold_pipeline_quality
```

---

# Automatización

El proyecto tiene dos niveles de automatización.

## 1. GitHub Actions

Ejecuta diariamente el flujo de extracción y carga a GCS.

Archivo:

```text
.github/workflows/pipeline.yml
```

Frecuencia:

```text
Todos los días a las 06:00 UTC
```

También puede ejecutarse manualmente mediante:

```text
Actions → World Cup Data Pipeline → Run workflow
```

Pasos del workflow:

1. Checkout del repositorio.
2. Configuración de Python.
3. Creación temporal del archivo de credenciales GCP desde GitHub Secrets.
4. Instalación de dependencias.
5. Ejecución de extracción API.
6. Generación de archivos procesados.
7. Generación de resúmenes EDA.
8. Carga a GCS.

---

## 2. BigQuery Scheduled Queries

Se crearon dos consultas programadas:

| Nombre | Frecuencia | Hora UTC | Función |
|---|---:|---:|---|
| silver_transform_daily | Diaria | 06:30 | Actualiza Silver |
| gold_aggregations_daily | Diaria | 06:45 | Actualiza Gold |

La separación horaria permite que primero se actualicen las tablas Silver y luego se recalculen las tablas Gold.

---

## 3. Observabilidad y Alertas (Slack)

El pipeline cuenta con un sistema de observabilidad activa integrado directamente en el flujo de GitHub Actions. Para garantizar la integridad del sistema y una respuesta rápida ante incidentes, se configuró una alerta automatizada mediante Webhooks. 

Si el proceso de extracción o las pruebas unitarias fallan en la capa Bronze (por ejemplo, por indisponibilidad de la API-Football o caducidad de credenciales), el orquestador captura el evento crítico (`if: failure()`) e inmediatamente notifica al equipo de desarrollo a través de un canal de Slack. Esto previene que el pipeline falle en silencio y asegura una rápida ejecución del plan de recuperación.

---

# Calidad de datos

El proyecto implementa controles de calidad en varias etapas.

## Controles locales

El script `eda_local.py` genera un perfil de calidad con:

- Nombre de tabla.
- Columnas.
- Tipo de dato.
- Filas.
- Nulos.
- Porcentaje de nulos.
- Valores distintos.

Archivo generado:

```text
data/eda/data_quality_profile.csv
```

---

## Controles resumidos

El script `eda_summary.py` genera:

```text
data/eda/quality_summary.csv
```

Incluye:

- Filas por tabla.
- Columnas por tabla.
- Celdas totales.
- Celdas nulas.
- Porcentaje de nulos.
- Duplicados por clave principal.

---

## Controles en BigQuery

La tabla Gold:

```text
gold_pipeline_quality
```

contiene métricas de calidad por tabla Silver:

| Métrica | Descripción |
|---|---|
| rows_count | Cantidad de filas |
| distinct_pk_count | Claves primarias distintas |
| duplicate_pk_count | Claves duplicadas |
| missing_pk_count | Claves faltantes |
| missing_critical_dates | Fechas críticas faltantes |
| missing_critical_venues | Sedes críticas faltantes |
| quality_score | Score de calidad calculado |

---

## Resultado de calidad actual

Durante la validación con Mundial 2022 se obtuvieron los siguientes resultados base:

| Tabla | Filas | Columnas | Duplicados |
|---|---:|---:|---:|
| fixtures | 64 | 34 | 0 |
| teams | 32 | 14 | 0 |
| standings | 32 | 20 | 0 |

Principales métricas:

```text
fixtures: 64 partidos
teams: 32 selecciones
standings: 32 registros
venues: 8 estadios
cities: 6 ciudades
duplicados fixture_id: 0
missing fixture_id: 0
missing match_date: 0
missing venue_name: 0
```

---

# Cómo ejecutar el proyecto localmente

## 1. Clonar repositorio

```bash
git clone https://github.com/paul-pinto/mci506-worldcup-data-pipeline.git
cd mci506-worldcup-data-pipeline
```

---

## 2. Crear entorno virtual

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 4. Crear archivo `.env`

Copiar el ejemplo:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
copy .env.example .env
```

Editar `.env` con valores reales.

---

## 5. Ejecutar extracción

```bash
python -m scripts.extract
```

---

## 6. Ejecutar aplanamiento y EDA

```bash
python -m scripts.eda_local
```

---

## 7. Ejecutar resúmenes EDA

```bash
python -m scripts.eda_summary
```

---

## 8. Subir datos a GCS

```bash
python -m scripts.load_gcs
```

---

# Variables de entorno

El archivo `.env.example` contiene:

```env
API_FOOTBALL_KEY=
API_FOOTBALL_HOST=v3.football.api-sports.io
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
WORLD_CUP_LEAGUE_ID=1
WORLD_CUP_SEASON=2022

GCP_PROJECT_ID=
GCS_BUCKET_NAME=
GOOGLE_APPLICATION_CREDENTIALS=
BQ_DATASET=mci506_worldcup
```

---

## Descripción de variables

| Variable | Descripción |
|---|---|
| API_FOOTBALL_KEY | API key de API-Football |
| API_FOOTBALL_HOST | Host de API-Football |
| API_FOOTBALL_BASE_URL | URL base de la API |
| WORLD_CUP_LEAGUE_ID | ID de la competición World Cup |
| WORLD_CUP_SEASON | Temporada a consultar |
| GCP_PROJECT_ID | ID del proyecto GCP |
| GCS_BUCKET_NAME | Nombre del bucket GCS |
| GOOGLE_APPLICATION_CREDENTIALS | Ruta al JSON de service account |
| BQ_DATASET | Dataset BigQuery |

---

# GitHub Actions

El workflow se encuentra en:

```text
.github/workflows/pipeline.yml
```

## Eventos que lo disparan

```yaml
on:
  workflow_dispatch:

  schedule:
    - cron: "0 6 * * *"
```

Esto significa:

- Puede ejecutarse manualmente.
- Corre automáticamente todos los días a las 06:00 UTC.

---

## Secrets requeridos

En GitHub:

```text
Settings → Secrets and variables → Actions
```

Se configuraron los siguientes secrets:

| Secret | Uso |
|---|---|
| API_FOOTBALL_KEY | Autenticación contra API-Football |
| GCP_PROJECT_ID | Proyecto GCP |
| GCS_BUCKET_NAME | Bucket GCS |
| GCP_SA_KEY | JSON completo de service account |

---

## Seguridad

El repositorio no incluye:

- `.env`
- credenciales JSON
- secretos GCP
- datos locales generados
- entorno virtual

Estos archivos están excluidos mediante `.gitignore`.

---

# Scheduled Queries

Las transformaciones se ejecutan mediante consultas programadas en BigQuery.

## silver_transform_daily

Ejecuta:

```text
sql/02_silver_transform.sql
```

Función:

- Crea tablas Silver si no existen.
- Inserta nuevos registros.
- Aplica `SAFE_CAST`.
- Aplica deduplicación incremental con `WHERE NOT EXISTS`.

---

## gold_aggregations_daily

Ejecuta:

```text
sql/03_gold_aggregations.sql
```

Función:

- Regenera tablas Gold.
- Calcula agregaciones para dashboard.
- Calcula métricas de calidad.
- Deja datos listos para Looker Studio.

---

# Validaciones SQL

## Validar cantidad de registros en Silver

```sql
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT fixture_id) AS distinct_fixtures,
  COUNT(*) - COUNT(DISTINCT fixture_id) AS duplicates
FROM `mci506-paul-pinto.mci506_worldcup.silver_fixtures`;
```

Resultado esperado:

```text
total_rows = 64
distinct_fixtures = 64
duplicates = 0
```

---

## Validar equipos

```sql
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT team_id) AS distinct_teams,
  COUNT(*) - COUNT(DISTINCT team_id) AS duplicates
FROM `mci506-paul-pinto.mci506_worldcup.silver_teams`;
```

Resultado esperado:

```text
total_rows = 32
distinct_teams = 32
duplicates = 0
```

---

## Validar calidad Gold

```sql
SELECT *
FROM `mci506-paul-pinto.mci506_worldcup.gold_pipeline_quality`
ORDER BY table_name;
```

---

## Validar resumen del torneo

```sql
SELECT *
FROM `mci506-paul-pinto.mci506_worldcup.gold_tournament_overview`;
```

---

## Validar carga por estadio

```sql
SELECT *
FROM `mci506-paul-pinto.mci506_worldcup.gold_venue_load`
ORDER BY total_matches DESC;
```

---

# Plan de recuperación ante fallas

## 1. Falla la API

Síntomas:

- Error HTTP.
- API key inválida.
- Límite de plan.
- Temporada no disponible.

Acciones:

1. Revisar logs en GitHub Actions.
2. Revisar respuesta de API en consola.
3. Validar variables:

```env
API_FOOTBALL_KEY
WORLD_CUP_LEAGUE_ID
WORLD_CUP_SEASON
```

4. Si la temporada no está disponible, cambiar temporalmente a una temporada soportada:

```env
WORLD_CUP_SEASON=2022
```

5. Documentar la restricción de la fuente.

---

## 2. Falla GitHub Actions

Síntomas:
- El equipo recibe un mensaje de *¡ALERTA EN EL PIPELINE!* a través del webhook de Slack.

Acciones:

1. Al recibir la notificación, ir a:

```text
GitHub → Actions → World Cup Data Pipeline
```

2. Abrir la última ejecución fallida.
3. Revisar el paso con error.
4. Validar secrets:

```text
API_FOOTBALL_KEY
GCP_PROJECT_ID
GCS_BUCKET_NAME
GCP_SA_KEY
```

5. Ejecutar manualmente con `Run workflow`.

---

## 3. Falla la carga a GCS

Posibles causas:

- Service account sin permisos.
- Bucket inexistente.
- JSON inválido.
- Variable `GOOGLE_APPLICATION_CREDENTIALS` incorrecta.

Acciones:

1. Validar existencia del bucket:

```text
gs://mci506-worldcup
```

2. Validar permisos de la service account.
3. Confirmar que el secret `GCP_SA_KEY` contiene el JSON completo.
4. Ejecutar localmente:

```bash
python -m scripts.load_gcs
```

---

## 4. Fallan External Tables

Posibles causas:

- Archivo no existe en GCS.
- Ruta incorrecta.
- Cambió el esquema CSV.
- Permisos insuficientes.

Acciones:

1. Revisar rutas:

```text
gs://mci506-worldcup/bronze/processed/fixtures_flat.csv
gs://mci506-worldcup/bronze/processed/teams_flat.csv
gs://mci506-worldcup/bronze/processed/standings_flat.csv
```

2. Ejecutar:

```sql
SELECT *
FROM `mci506-paul-pinto.mci506_worldcup.ext_fixtures_flat`
LIMIT 10;
```

3. Si no funciona, recrear external tables con:

```text
sql/01_external_tables.sql
```

---

## 5. Fallan tablas Silver

Acciones:

1. Revisar si existen tablas externas.
2. Ejecutar manualmente:

```text
sql/02_silver_transform.sql
```

3. Revisar problemas de casteo.
4. Validar claves nulas.

---

## 6. Fallan tablas Gold

Acciones:

1. Revisar que Silver tenga datos.
2. Ejecutar manualmente:

```text
sql/03_gold_aggregations.sql
```

3. Validar que no se haya cambiado el nombre de una columna.
4. Revisar `gold_pipeline_quality`.

---

## 7. Looker Studio no actualiza

Acciones:

1. Revisar que BigQuery Gold tenga datos.
2. En Looker Studio, actualizar la fuente de datos.
3. Revisar permisos del usuario sobre BigQuery.
4. Revisar si el dashboard está conectado a las tablas Gold correctas.

---

# Preguntas clave del proyecto

## 1. ¿Qué datos extrae?

El pipeline extrae datos de Copa Mundial FIFA desde API-Football:

- Partidos.
- Selecciones.
- Posiciones por grupo.

Las entidades principales son:

```text
fixtures
teams
standings
```

El dataset funcional actual contiene:

```text
64 partidos
32 selecciones
32 registros de standings
8 estadios
6 ciudades
```

---

## 2. ¿De dónde los trae?

Los datos provienen de API-Football, usando endpoints REST de la API v3:

```text
/fixtures
/teams
/standings
```

Los parámetros usados son:

```text
league = 1
season = 2022
```

El diseño permite cambiar a:

```text
season = 2026
```

si la API lo habilita.

---

## 3. ¿A dónde los guarda?

Primero se guardan localmente durante la ejecución:

```text
data/raw/
data/processed/
data/eda/
```

Luego se suben a Google Cloud Storage:

```text
gs://mci506-worldcup/bronze/raw/
gs://mci506-worldcup/bronze/processed/
gs://mci506-worldcup/bronze/eda/
```

Después BigQuery consume estos archivos mediante External Tables.

---

## 4. ¿Cuándo se ejecuta?

El pipeline de extracción se ejecuta mediante GitHub Actions:

```text
Todos los días a las 06:00 UTC
```

Las transformaciones se ejecutan mediante BigQuery Scheduled Queries:

```text
silver_transform_daily → 06:30 UTC
gold_aggregations_daily → 06:45 UTC
```

---

## 5. ¿Cómo funciona?

El flujo completo es:

```text
1. GitHub Actions ejecuta scripts Python.
2. Python consulta API-Football.
3. Los JSON crudos se guardan en data/raw.
4. Los datos se aplanan a CSV/Parquet.
5. Se generan perfiles EDA y calidad.
6. Los archivos se suben a GCS.
7. BigQuery External Tables leen GCS.
8. Scheduled Query actualiza Silver.
9. Scheduled Query actualiza Gold.
10. Looker Studio consume Gold.
```

La capa Silver usa lógica incremental:

```sql
WHERE NOT EXISTS (
  SELECT 1
  FROM silver_fixtures s
  WHERE s.fixture_id = ext.fixture_id
)
```

Esto evita duplicados cuando el pipeline se ejecuta repetidamente.

---

## 6. ¿Cuánta calidad tienen los datos?

La calidad se mide en tres niveles:

1. Perfil local con `data_quality_profile.csv`.
2. Resumen EDA con `quality_summary.csv`.
3. Tabla Gold `gold_pipeline_quality`.

Métricas controladas:

- Filas por tabla.
- Nulos.
- Porcentaje de nulos.
- Claves primarias duplicadas.
- Claves primarias faltantes.
- Fechas críticas faltantes.
- Sedes críticas faltantes.
- Score de calidad.

Resultado actual:

```text
Duplicados en fixtures: 0
Duplicados en teams: 0
Duplicados en standings: 0
Fechas faltantes críticas: 0
Sedes faltantes críticas: 0
```

---

## 7. ¿Si falla qué hacer?

El plan de recuperación está documentado por componente:

- Revisar logs de GitHub Actions.
- Validar secrets.
- Verificar permisos GCS.
- Validar existencia de archivos en GCS.
- Ejecutar SQL manualmente en BigQuery.
- Revisar `gold_pipeline_quality`.
- Reejecutar workflow manualmente.

Comando local recomendado para reproducir el pipeline:

```bash
python -m scripts.extract
python -m scripts.eda_local
python -m scripts.eda_summary
python -m scripts.load_gcs
```

---

# Resultados actuales

La validación con Mundial 2022 produjo:

```text
fixtures: 64 filas, 34 columnas
teams: 32 filas, 14 columnas
standings: 32 filas, 20 columnas
```

Resumen:

```text
Total de partidos: 64
Total de selecciones: 32
Total de sedes: 8
Total de ciudades: 6
```

Distribución por ronda:

```text
Group Stage - 1: 16
Group Stage - 2: 16
Group Stage - 3: 16
Round of 16: 8
Quarter-finals: 4
Semi-finals: 2
3rd Place Final: 1
Final: 1
```

Top estadios por carga:

```text
Lusail Iconic Stadium: 10
Al Bayt Stadium: 9
Education City Stadium: 8
Al Thumama Stadium: 8
Khalifa International Stadium: 8
```

---

# Evolución hacia Mundial 2026

El pipeline está preparado para Mundial 2026 porque la temporada está parametrizada.

Para cambiar a 2026:

```env
WORLD_CUP_SEASON=2026
```

En GitHub Actions:

```yaml
WORLD_CUP_SEASON: "2026"
```

Si se habilita el acceso pago a la temporada 2026, el mismo pipeline podrá capturar:

- Fixtures 2026.
- Equipos 2026.
- Standings 2026.
- Estados de partido.
- Resultados cuando el torneo esté en curso.

Frecuencias recomendadas:

| Etapa | Frecuencia |
|---|---|
| Pre-torneo | Diaria |
| Semana previa | Cada 6 horas |
| Días con partidos | Cada 15-60 minutos |
| Live operativo | Cloud Scheduler + Cloud Run cada 1-5 minutos |

Para este proyecto académico se utiliza ejecución diaria, suficiente para demostrar automatización, idempotencia y actualización batch.

## Equipo

| Nombre | Rol |
|--------|-----|
| Jhonny Paul Pinto Phillips | Estructura del proyecto / load_gcs.py |
| Ronald Marcelo Pinto Delgadillo  | Extracción / extract.py |
| Pablo Andrés Linares Ruíz | EDA local / README / SQL validaciones |
| Ana Patricia Abán Monzón | EDA summary / Alertas Slack |

## Links

- Repositorio: https://github.com/paul-pinto/mci506-worldcup-control-tower
- Data Lake (Google Cloud Storage): https://console.cloud.google.com/storage/browser/mci506-worldcup;tab=objects?project=mci506-paul-pinto&prefix=&forceOnObjectsSortingFiltering=false
- Dashboard Looker Studio: https://datastudio.google.com/u/0/reporting/41fa5555-1687-4a2b-918c-0b8321cbea44/page/8vszF
- Proyecto GCP: mci506-paul-pinto
---

# Conclusión

Este proyecto implementa un pipeline completo de Ingeniería de Datos usando una arquitectura medallion sobre Google Cloud.

El sistema demuestra:

- Extracción automatizada desde API.
- Almacenamiento Bronze en GCS.
- Lectura mediante BigQuery External Tables.
- Transformación Silver con limpieza, tipado y deduplicación incremental.
- Agregaciones Gold orientadas a visualización.
- Scheduled Queries para actualización automática.
- GitHub Actions para orquestación diaria.
- Dashboard en Looker Studio.
- Monitoreo de calidad del pipeline.
- Documentación operativa y plan de recuperación.

El valor principal del proyecto no es solo mostrar datos deportivos, sino demostrar un pipeline automatizado, reproducible, idempotente y observable, preparado para operar con datos actualizados del Mundial 2026 cuando la fuente permita el acceso a esa temporada.

