-- ============================================================
-- VALIDATION QUERIES - World Cup Data Control Tower
-- Proyecto: MCI506 - MCDIA - FIFA World Cup 2026
-- Propósito: Verificar integridad y calidad de datos por capa
-- ============================================================

-- ============================================================
-- 1. VALIDACIONES CAPA SILVER
-- ============================================================

-- 1.1 Contar filas y duplicados en silver_fixtures
SELECT
  COUNT(*)                          AS total_rows,
  COUNT(DISTINCT fixture_id)        AS distinct_fixtures,
  COUNT(*) - COUNT(DISTINCT fixture_id) AS duplicates
FROM `mci506-paul-pinto.mci506_worldcup.silver_fixtures`;
-- Esperado: total_rows = 64, duplicates = 0

-- 1.2 Verificar nulos en columnas críticas de silver_fixtures
SELECT
  COUNTIF(fixture_id IS NULL)     AS null_fixture_id,
  COUNTIF(match_date IS NULL)     AS null_match_date,
  COUNTIF(home_team_name IS NULL) AS null_home_team,
  COUNTIF(away_team_name IS NULL) AS null_away_team,
  COUNTIF(venue_name IS NULL)     AS null_venue
FROM `mci506-paul-pinto.mci506_worldcup.silver_fixtures`;
-- Esperado: todos en 0

-- 1.3 Contar filas y duplicados en silver_teams
SELECT
  COUNT(*)                      AS total_rows,
  COUNT(DISTINCT team_id)       AS distinct_teams,
  COUNT(*) - COUNT(DISTINCT team_id) AS duplicates
FROM `mci506-paul-pinto.mci506_worldcup.silver_teams`;
-- Esperado: total_rows = 32, duplicates = 0

-- 1.4 Contar filas y duplicados en silver_standings
SELECT
  COUNT(*)                      AS total_rows,
  COUNT(DISTINCT CONCAT(
    CAST(season AS STRING), group_name, CAST(team_id AS STRING)
  ))                            AS distinct_keys,
  COUNT(*) - COUNT(DISTINCT CONCAT(
    CAST(season AS STRING), group_name, CAST(team_id AS STRING)
  ))                            AS duplicates
FROM `mci506-paul-pinto.mci506_worldcup.silver_standings`;
-- Esperado: duplicates = 0

-- ============================================================
-- 2. VALIDACIONES CAPA GOLD
-- ============================================================

-- 2.1 Verificar que gold_tournament_overview tiene datos
SELECT
  total_matches,
  total_teams,
  total_venues,
  total_cities
FROM `mci506-paul-pinto.mci506_worldcup.gold_tournament_overview`;
-- Esperado: total_matches = 64, total_teams = 32

-- 2.2 Verificar distribución de partidos por ronda
SELECT
  round,
  total_matches
FROM `mci506-paul-pinto.mci506_worldcup.gold_matches_by_round`
ORDER BY total_matches DESC;
-- Esperado: Group Stage con más partidos (48 en total)

-- 2.3 Verificar que no hay equipos sin puntos en standings
SELECT
  team_name,
  points,
  played
FROM `mci506-paul-pinto.mci506_worldcup.gold_group_summary`
WHERE played > 0 AND points IS NULL
ORDER BY team_name;
-- Esperado: 0 filas

-- 2.4 Score de calidad del pipeline
SELECT
  table_name,
  rows_count,
  duplicate_pk_count,
  missing_pk_count,
  quality_score
FROM `mci506-paul-pinto.mci506_worldcup.gold_pipeline_quality`
ORDER BY quality_score ASC;

-- ============================================================
-- 3. VALIDACIONES CROSS-LAYER
-- ============================================================

-- 3.1 Equipos en standings deben existir en fixtures
SELECT
  s.team_name,
  s.team_id
FROM `mci506-paul-pinto.mci506_worldcup.silver_standings` s
LEFT JOIN `mci506-paul-pinto.mci506_worldcup.silver_fixtures` f
  ON s.team_id = f.home_team_id OR s.team_id = f.away_team_id
WHERE f.fixture_id IS NULL;
-- Esperado: 0 filas

-- 3.2 Todos los partidos deben tener equipos registrados
SELECT
  f.fixture_id,
  f.home_team_name,
  f.away_team_name
FROM `mci506-paul-pinto.mci506_worldcup.silver_fixtures` f
LEFT JOIN `mci506-paul-pinto.mci506_worldcup.silver_teams` t
  ON f.home_team_id = t.team_id
WHERE t.team_id IS NULL;
-- Esperado: 0 filas

-- ============================================================
-- 4. RESUMEN EJECUTIVO DEL PIPELINE
-- ============================================================

SELECT
  (SELECT COUNT(*) FROM `mci506-paul-pinto.mci506_worldcup.silver_fixtures`)  AS fixtures_cargados,
  (SELECT COUNT(*) FROM `mci506-paul-pinto.mci506_worldcup.silver_teams`)     AS equipos_cargados,
  (SELECT COUNT(*) FROM `mci506-paul-pinto.mci506_worldcup.silver_standings`) AS standings_cargados,
  CURRENT_TIMESTAMP() AS verificado_en;