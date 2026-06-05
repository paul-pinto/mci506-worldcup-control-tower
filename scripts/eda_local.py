import glob
import json
import os
from typing import Any, Dict, List

import pandas as pd

from scripts.config import EDA_DIR
from scripts.utils import ensure_dir


def latest_file(pattern: str) -> str:
    """
    Return most recent file matching a glob pattern.
    """
    files = glob.glob(pattern, recursive=True)

    if not files:
        raise FileNotFoundError(f"No files found for pattern: {pattern}")

    return max(files, key=os.path.getmtime)


def load_api_response(path: str) -> Dict[str, Any]:
    """
    Load API-Football JSON response.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_fixtures(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Flatten fixtures response into tabular format.
    """
    rows: List[Dict[str, Any]] = []

    for item in payload.get("response", []):
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        score = item.get("score", {})

        venue = fixture.get("venue", {})
        status = fixture.get("status", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        rows.append(
            {
                "fixture_id": fixture.get("id"),
                "referee": fixture.get("referee"),
                "timezone": fixture.get("timezone"),
                "match_date": fixture.get("date"),
                "timestamp": fixture.get("timestamp"),
                "period_first": fixture.get("periods", {}).get("first"),
                "period_second": fixture.get("periods", {}).get("second"),
                "venue_id": venue.get("id"),
                "venue_name": venue.get("name"),
                "venue_city": venue.get("city"),
                "status_long": status.get("long"),
                "status_short": status.get("short"),
                "elapsed": status.get("elapsed"),
                "league_id": league.get("id"),
                "league_name": league.get("name"),
                "country": league.get("country"),
                "season": league.get("season"),
                "round": league.get("round"),
                "home_team_id": home.get("id"),
                "home_team_name": home.get("name"),
                "home_team_winner": home.get("winner"),
                "away_team_id": away.get("id"),
                "away_team_name": away.get("name"),
                "away_team_winner": away.get("winner"),
                "goals_home": goals.get("home"),
                "goals_away": goals.get("away"),
                "halftime_home": score.get("halftime", {}).get("home"),
                "halftime_away": score.get("halftime", {}).get("away"),
                "fulltime_home": score.get("fulltime", {}).get("home"),
                "fulltime_away": score.get("fulltime", {}).get("away"),
                "extratime_home": score.get("extratime", {}).get("home"),
                "extratime_away": score.get("extratime", {}).get("away"),
                "penalty_home": score.get("penalty", {}).get("home"),
                "penalty_away": score.get("penalty", {}).get("away"),
            }
        )

    return pd.DataFrame(rows)


def flatten_teams(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Flatten teams response into tabular format.
    """
    rows: List[Dict[str, Any]] = []

    for item in payload.get("response", []):
        team = item.get("team", {})
        venue = item.get("venue", {})

        rows.append(
            {
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "team_code": team.get("code"),
                "team_country": team.get("country"),
                "team_founded": team.get("founded"),
                "team_national": team.get("national"),
                "team_logo": team.get("logo"),
                "venue_id": venue.get("id"),
                "venue_name": venue.get("name"),
                "venue_address": venue.get("address"),
                "venue_city": venue.get("city"),
                "venue_capacity": venue.get("capacity"),
                "venue_surface": venue.get("surface"),
                "venue_image": venue.get("image"),
            }
        )

    return pd.DataFrame(rows)


def flatten_standings(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Flatten standings response into tabular format.
    """
    rows: List[Dict[str, Any]] = []

    for league_block in payload.get("response", []):
        league = league_block.get("league", {})
        standings_groups = league.get("standings", [])

        for group_table in standings_groups:
            for row in group_table:
                team = row.get("team", {})
                all_stats = row.get("all", {})
                goals = all_stats.get("goals", {})

                rows.append(
                    {
                        "league_id": league.get("id"),
                        "league_name": league.get("name"),
                        "country": league.get("country"),
                        "season": league.get("season"),
                        "group": row.get("group"),
                        "rank": row.get("rank"),
                        "team_id": team.get("id"),
                        "team_name": team.get("name"),
                        "points": row.get("points"),
                        "goals_diff": row.get("goalsDiff"),
                        "form": row.get("form"),
                        "status": row.get("status"),
                        "description": row.get("description"),
                        "played": all_stats.get("played"),
                        "win": all_stats.get("win"),
                        "draw": all_stats.get("draw"),
                        "lose": all_stats.get("lose"),
                        "goals_for": goals.get("for"),
                        "goals_against": goals.get("against"),
                        "update": row.get("update"),
                    }
                )

    return pd.DataFrame(rows)


def basic_profile(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """
    Build a compact data quality profile for a dataframe.
    """
    if df.empty:
        return pd.DataFrame(
            [
                {
                    "table_name": name,
                    "column": "__empty_table__",
                    "dtype": "none",
                    "rows": 0,
                    "nulls": 0,
                    "null_pct": 0.0,
                    "distinct": 0,
                }
            ]
        )

    profile = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(df[col].dtype) for col in df.columns],
            "rows": len(df),
            "nulls": [int(df[col].isna().sum()) for col in df.columns],
            "null_pct": [round(float(df[col].isna().mean() * 100), 2) for col in df.columns],
            "distinct": [int(df[col].nunique(dropna=True)) for col in df.columns],
        }
    )

    profile.insert(0, "table_name", name)
    return profile


def main() -> None:
    ensure_dir(EDA_DIR)
    ensure_dir("data/processed")

    fixtures_path = latest_file("data/raw/fixtures/run_id=*/fixtures_*.json")
    teams_path = latest_file("data/raw/teams/run_id=*/teams_*.json")
    standings_path = latest_file("data/raw/standings/run_id=*/standings_*.json")

    print(f"[+] Fixtures file: {fixtures_path}")
    print(f"[+] Teams file: {teams_path}")
    print(f"[+] Standings file: {standings_path}")

    fixtures_payload = load_api_response(fixtures_path)
    teams_payload = load_api_response(teams_path)
    standings_payload = load_api_response(standings_path)

    fixtures_df = flatten_fixtures(fixtures_payload)
    teams_df = flatten_teams(teams_payload)
    standings_df = flatten_standings(standings_payload)

    print("\n[+] Shapes")
    print(f"fixtures: {fixtures_df.shape}")
    print(f"teams: {teams_df.shape}")
    print(f"standings: {standings_df.shape}")

    fixtures_df.to_csv("data/processed/fixtures_flat.csv", index=False)
    teams_df.to_csv("data/processed/teams_flat.csv", index=False)
    standings_df.to_csv("data/processed/standings_flat.csv", index=False)

    fixtures_df.to_parquet("data/processed/fixtures_flat.parquet", index=False)
    teams_df.to_parquet("data/processed/teams_flat.parquet", index=False)
    standings_df.to_parquet("data/processed/standings_flat.parquet", index=False)

    profiles = pd.concat(
        [
            basic_profile(fixtures_df, "fixtures"),
            basic_profile(teams_df, "teams"),
            basic_profile(standings_df, "standings"),
        ],
        ignore_index=True,
    )

    profiles.to_csv("data/eda/data_quality_profile.csv", index=False)

    print("\n[+] Fixtures sample")
    print(fixtures_df.head(10).to_string())

    print("\n[+] Teams sample")
    print(teams_df.head(10).to_string())

    print("\n[+] Standings sample")
    print(standings_df.head(10).to_string())

    print("\n[+] EDA outputs saved:")
    print("    - data/processed/fixtures_flat.csv")
    print("    - data/processed/teams_flat.csv")
    print("    - data/processed/standings_flat.csv")
    print("    - data/processed/fixtures_flat.parquet")
    print("    - data/processed/teams_flat.parquet")
    print("    - data/processed/standings_flat.parquet")
    print("    - data/eda/data_quality_profile.csv")


if __name__ == "__main__":
    main()