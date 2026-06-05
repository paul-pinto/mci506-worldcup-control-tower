# 🏆 World Cup Data Control Tower

Pipeline automatizado de Ingeniería de Datos para extraer, transformar y visualizar datos de la Copa Mundial FIFA usando arquitectura Medallion sobre Google Cloud Platform.

Proyecto final — Módulo MCI506 - Ingeniería de Datos

---

## Arquitectura

```
API-Football → extract.py → GCS (Bronze) → BigQuery (Silver → Gold) → Looker Studio
```

## Flujo detallado

```
┌──────────────────────────────────────────────────────────────┐
│                    FUENTE DE DATOS                           │
│  API-Football v3  │  /fixtures  │  /teams  │  /standings     │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP GET (Python requests)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  EXTRACCIÓN LOCAL                            │
│  extract.py     →  data/raw/run_id=TIMESTAMP/                │
│  eda_local.py   →  data/processed/ (.csv + .parquet)         │
│  eda_summary.py →  data/eda/ (perfiles de calidad)           │
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

Automatización:
  GitHub Actions         (06:00 UTC) → extrae y carga a GCS
  Scheduled Query silver (06:30 UTC) → actualiza Silver
  Scheduled Query gold   (06:45 UTC) → actualiza Gold
```

## Stack

| Componente | Herramienta |
|---|---|
| Extracción | Python + API-Football |
| Almacenamiento | Google Cloud Storage |
| Data Warehouse | BigQuery |
| Orquestación | GitHub Actions |
| Transformación | BigQuery Scheduled Queries |
| Visualización | Looker Studio |

## Estructura del repositorio

```
mci506-worldcup-control-tower/
├── .github/workflows/pipeline.yml
├── scripts/
│   ├── config.py
│   ├── extract.py
│   ├── utils.py
│   ├── eda_local.py
│   ├── eda_summary.py
│   └── load_gcs.py
├── sql/
│   └── 04_validation_queries.sql
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Fuente de datos

- **API:** API-Football v3
- **Liga:** World Cup (ID=1)
- **Temporada:** 2022 (validación funcional) / 2026 (objetivo)
- **Endpoints:** `/fixtures`, `/teams`, `/standings`

## Cómo ejecutar localmente

```bash
git clone https://github.com/paul-pinto/mci506-worldcup-control-tower.git
cd mci506-worldcup-control-tower
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.extract
python -m scripts.eda_local
python -m scripts.eda_summary
python -m scripts.load_gcs
```

## Equipo

| Nombre | Rol |
|---|---|
| Paul Pinto | Estructura del proyecto / load_gcs.py |
| Ronald | Extracción / extract.py |
| Pablo Linares | EDA local / README / SQL validaciones |
| Patricia | EDA summary / Alertas Slack |

## Links

- Repositorio: https://github.com/paul-pinto/mci506-worldcup-control-tower
- Dashboard Looker Studio: [Agregar enlace]
- Proyecto GCP: mci506-paul-pinto