"""
eda_local.py - Aplanamiento y perfil de calidad de datos extraídos
Proyecto: MCI506 - World Cup Data Control Tower
"""

import json
import os
from pathlib import Path

import pandas as pd

from scripts.config import RAW_DIR, PROCESSED_DIR, EDA_DIR


def find_latest_run(entity: str) -> str:
    """
    Encuentra el run_id más reciente para una entidad.

    Args:
        entity: nombre de la entidad (fixtures, teams, standings)
    Returns:
        ruta al archivo JSON más reciente
    """
    base = Path(RAW_DIR) / entity
    runs = sorted(base.glob("run_id=*"), reverse=True)
    if not runs:
        raise FileNotFoundError(f"No runs found for entity: {entity}")
    files = list(runs[0].glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files in {runs[0]}")
    return str(files[0])


def flatten_fixtures(path: str) -> pd.DataFrame:
    """
    Aplana el JSON de fixtures a un DataFrame tabular.

    Args:
        path: ruta al archivo JSON de fixtures
    Returns:
        DataFrame con una fila por partido
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    response = data.get("response", [])
    print(f"[DEBUG] Total items en response: {len(response)}")
    if response:
        print(f"[DEBUG] Keys del primer item: {list(response[0].keys())}")

    for item in response:
        fixture = item.get("fixture", {})
        league  = item.get("league", {})
        teams   = item.get("teams", {})
        goals   = item.get("goals", {})

        rows.append({
            "fixture_id":     fixture.get("id"),
            "match_date":     fixture.get("date"),
            "season":         league.get("season"),
            "round":          league.get("round"),
            "venue_name":     fixture.get("venue", {}).get("name"),
            "venue_city":     fixture.get("venue", {}).get("city"),
            "home_team_id":   teams.get("home", {}).get("id"),
            "home_team_name": teams.get("home", {}).get("name"),
            "away_team_id":   teams.get("away", {}).get("id"),
            "away_team_name": teams.get("away", {}).get("name"),
            "goals_home":     goals.get("home"),
            "goals_away":     goals.get("away"),
            "status_short":   fixture.get("status", {}).get("short"),
            "status_long":    fixture.get("status", {}).get("long"),
        })

    return pd.DataFrame(rows)

def flatten_teams(path: str) -> pd.DataFrame:
    """
    Aplana el JSON de teams a un DataFrame tabular.

    Args:
        path: ruta al archivo JSON de teams
    Returns:
        DataFrame con una fila por equipo
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for item in data.get("response", []):
        team = item.get("team", {})
        rows.append({
            "team_id":       team.get("id"),
            "team_name":     team.get("name"),
            "team_code":     team.get("code"),
            "team_country":  team.get("country"),
            "team_national": team.get("national"),
            "team_logo":     team.get("logo"),
        })

    return pd.DataFrame(rows)


def flatten_standings(path: str) -> pd.DataFrame:
    """
    Aplana el JSON de standings a un DataFrame tabular.

    Args:
        path: ruta al archivo JSON de standings
    Returns:
        DataFrame con una fila por equipo en su grupo
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    season = data.get("parameters", {}).get("season")
    for league in data.get("response", []):
        for group in league.get("league", {}).get("standings", []):
            for item in group:
                team  = item.get("team", {})
                all_s = item.get("all", {})
                goals = all_s.get("goals", {})
                rows.append({
                    "season":       season,
                    "group_name":   item.get("group"),
                    "rank":         item.get("rank"),
                    "team_id":      team.get("id"),
                    "team_name":    team.get("name"),
                    "points":       item.get("points"),
                    "played":       all_s.get("played"),
                    "win":          all_s.get("win"),
                    "draw":         all_s.get("draw"),
                    "lose":         all_s.get("lose"),
                    "goals_for":    goals.get("for"),
                    "goals_against":goals.get("against"),
                    "goals_diff":   item.get("goalsDiff"),
                })

    return pd.DataFrame(rows)


def save_formats(df: pd.DataFrame, name: str) -> None:
    """
    Guarda un DataFrame en CSV y Parquet.

    Args:
        df: DataFrame a guardar
        name: nombre base del archivo (sin extensión)
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df.to_csv(f"{PROCESSED_DIR}/{name}.csv", index=False)
    df.to_parquet(f"{PROCESSED_DIR}/{name}.parquet", index=False)
    print(f"[eda_local] Guardado: {name} ({len(df)} filas)")


def build_quality_profile(dfs: dict) -> pd.DataFrame:
    """
    Genera un perfil de calidad básico para cada DataFrame.

    Args:
        dfs: diccionario {nombre: DataFrame}
    Returns:
        DataFrame con métricas de calidad por tabla
    """
    rows = []
    for name, df in dfs.items():
        for col in df.columns:
            rows.append({
                "table":    name,
                "column":   col,
                "dtype":    str(df[col].dtype),
                "rows":     len(df),
                "nulls":    df[col].isnull().sum(),
                "pct_null": round(df[col].isnull().mean() * 100, 2),
                "distinct": df[col].nunique(),
            })
    return pd.DataFrame(rows)


def main():
    """Función principal: aplana JSONs y genera perfil de calidad."""
    os.makedirs(EDA_DIR, exist_ok=True)

    fixtures_path  = find_latest_run("fixtures")
    teams_path     = find_latest_run("teams")
    standings_path = find_latest_run("standings")

    df_fixtures  = flatten_fixtures(fixtures_path)
    df_teams     = flatten_teams(teams_path)
    df_standings = flatten_standings(standings_path)

    save_formats(df_fixtures,  "fixtures_flat")
    save_formats(df_teams,     "teams_flat")
    save_formats(df_standings, "standings_flat")

    dfs = {
        "fixtures":  df_fixtures,
        "teams":     df_teams,
        "standings": df_standings,
    }
    df_quality = build_quality_profile(dfs)
    df_quality.to_csv(f"{EDA_DIR}/data_quality_profile.csv", index=False)
    print(f"[eda_local] Perfil de calidad guardado en {EDA_DIR}/data_quality_profile.csv")


if __name__ == "__main__":
    main()