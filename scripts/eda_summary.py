import pandas as pd
from scripts.utils import ensure_dir


def save_table(df: pd.DataFrame, path: str) -> None:
    """Save dataframe as CSV."""
    ensure_dir(path.rsplit("/", 1)[0])
    df.to_csv(path, index=False)


def main() -> None:
    ensure_dir("data/eda")

    fixtures = pd.read_csv("data/processed/fixtures_flat.csv")
    teams = pd.read_csv("data/processed/teams_flat.csv")
    standings = pd.read_csv("data/processed/standings_flat.csv")

    fixtures["match_date"] = pd.to_datetime(fixtures["match_date"], errors="coerce")

    # 1. resumen general
    overview = pd.DataFrame(
        [
            {
                "metric": "total_fixtures",
                "value": len(fixtures),
            },
            {
                "metric": "total_teams",
                "value": len(teams),
            },
            {
                "metric": "total_standings_rows",
                "value": len(standings),
            },
            {
                "metric": "total_venues",
                "value": fixtures["venue_name"].nunique(dropna=True),
            },
            {
                "metric": "total_cities",
                "value": fixtures["venue_city"].nunique(dropna=True),
            },
            {
                "metric": "start_date",
                "value": fixtures["match_date"].min(),
            },
            {
                "metric": "end_date",
                "value": fixtures["match_date"].max(),
            },
            {
                "metric": "duplicate_fixture_ids",
                "value": fixtures["fixture_id"].duplicated().sum(),
            },
            {
                "metric": "missing_fixture_ids",
                "value": fixtures["fixture_id"].isna().sum(),
            },
            {
                "metric": "missing_match_dates",
                "value": fixtures["match_date"].isna().sum(),
            },
            {
                "metric": "missing_venues",
                "value": fixtures["venue_name"].isna().sum(),
            },
        ]
    )

    # 2. partidos por ronda
    matches_by_round = (
        fixtures.groupby("round", dropna=False)
        .agg(total_matches=("fixture_id", "count"))
        .reset_index()
        .sort_values("total_matches", ascending=False)
    )

    # 3. carga por estadio
    venue_load = (
        fixtures.groupby(["venue_name", "venue_city"], dropna=False)
        .agg(
            total_matches=("fixture_id", "count"),
            first_match_date=("match_date", "min"),
            last_match_date=("match_date", "max"),
            rounds=("round", lambda x: ", ".join(sorted(set(x.dropna().astype(str))))),
        )
        .reset_index()
        .sort_values("total_matches", ascending=False)
    )

    # 4. calendario por equipo
    home_matches = fixtures[
        ["fixture_id", "match_date", "round", "venue_name", "venue_city", "home_team_id", "home_team_name"]
    ].rename(
        columns={
            "home_team_id": "team_id",
            "home_team_name": "team_name",
        }
    )
    home_matches["side"] = "home"

    away_matches = fixtures[
        ["fixture_id", "match_date", "round", "venue_name", "venue_city", "away_team_id", "away_team_name"]
    ].rename(
        columns={
            "away_team_id": "team_id",
            "away_team_name": "team_name",
        }
    )
    away_matches["side"] = "away"

    team_matches = pd.concat([home_matches, away_matches], ignore_index=True)

    team_schedule = (
        team_matches.groupby(["team_id", "team_name"], dropna=False)
        .agg(
            total_matches=("fixture_id", "count"),
            first_match_date=("match_date", "min"),
            last_match_date=("match_date", "max"),
            venues_played=("venue_name", "nunique"),
            cities_played=("venue_city", "nunique"),
        )
        .reset_index()
        .sort_values(["total_matches", "team_name"], ascending=[False, True])
    )

    # 5. descanso entre partidos
    team_matches_sorted = team_matches.sort_values(["team_id", "match_date"])
    team_matches_sorted["previous_match_date"] = team_matches_sorted.groupby("team_id")["match_date"].shift(1)
    team_matches_sorted["rest_days"] = (
        team_matches_sorted["match_date"] - team_matches_sorted["previous_match_date"]
    ).dt.days

    rest_summary = (
        team_matches_sorted.groupby(["team_id", "team_name"], dropna=False)
        .agg(
            min_rest_days=("rest_days", "min"),
            avg_rest_days=("rest_days", "mean"),
            matches_with_short_rest=("rest_days", lambda x: int((x < 4).sum())),
        )
        .reset_index()
        .sort_values(["min_rest_days", "avg_rest_days"], ascending=[True, True])
    )

    # 6. standings por grupo
    group_summary = (
        standings.groupby("group", dropna=False)
        .agg(
            teams=("team_id", "nunique"),
            avg_points=("points", "mean"),
            total_goals_for=("goals_for", "sum"),
            total_goals_against=("goals_against", "sum"),
        )
        .reset_index()
        .sort_values("group")
    )

    # 7. calidad por tabla
    quality = []
    for table_name, df, pk in [
        ("fixtures", fixtures, "fixture_id"),
        ("teams", teams, "team_id"),
        ("standings", standings, "team_id"),
    ]:
        total_cells = df.shape[0] * df.shape[1]
        null_cells = int(df.isna().sum().sum())
        duplicate_pk = int(df[pk].duplicated().sum()) if pk in df.columns else None

        quality.append(
            {
                "table_name": table_name,
                "rows": df.shape[0],
                "columns": df.shape[1],
                "total_cells": total_cells,
                "null_cells": null_cells,
                "null_pct": round((null_cells / total_cells) * 100, 2) if total_cells else 0,
                "duplicate_pk": duplicate_pk,
            }
        )

    quality_df = pd.DataFrame(quality)

    save_table(overview, "data/eda/overview.csv")
    save_table(matches_by_round, "data/eda/matches_by_round.csv")
    save_table(venue_load, "data/eda/venue_load.csv")
    save_table(team_schedule, "data/eda/team_schedule.csv")
    save_table(rest_summary, "data/eda/rest_summary.csv")
    save_table(group_summary, "data/eda/group_summary.csv")
    save_table(quality_df, "data/eda/quality_summary.csv")

    print("[+] EDA summary generated:")
    print("    - data/eda/overview.csv")
    print("    - data/eda/matches_by_round.csv")
    print("    - data/eda/venue_load.csv")
    print("    - data/eda/team_schedule.csv")
    print("    - data/eda/rest_summary.csv")
    print("    - data/eda/group_summary.csv")
    print("    - data/eda/quality_summary.csv")

    print("\n[+] Overview")
    print(overview.to_string(index=False))

    print("\n[+] Matches by round")
    print(matches_by_round.to_string(index=False))

    print("\n[+] Top venue load")
    print(venue_load.head(10).to_string(index=False))

    print("\n[+] Data quality")
    print(quality_df.to_string(index=False))


if __name__ == "__main__":
    main()
