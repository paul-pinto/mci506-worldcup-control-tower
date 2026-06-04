import os

from scripts.config import RAW_DIR, WORLD_CUP_LEAGUE_ID, WORLD_CUP_SEASON
from scripts.utils import api_get, ensure_dir, save_json, save_metadata, utc_now_str


def extract_fixtures(run_id: str) -> str:
    """
    Extract FIFA World Cup 2026 fixtures.

    Returns:
        Output JSON path.
    """
    payload = api_get(
        endpoint="/fixtures",
        params={
            "league": WORLD_CUP_LEAGUE_ID,
            "season": WORLD_CUP_SEASON,
        },
    )

    output_path = (
        f"{RAW_DIR}/fixtures/run_id={run_id}/"
        f"fixtures_league={WORLD_CUP_LEAGUE_ID}_season={WORLD_CUP_SEASON}.json"
    )
    metadata_path = f"{RAW_DIR}/fixtures/run_id={run_id}/_metadata.json"

    save_json(payload, output_path)
    save_metadata("fixtures", payload, metadata_path)

    return output_path


def extract_teams(run_id: str) -> str:
    """
    Extract teams for FIFA World Cup 2026.
    """
    payload = api_get(
        endpoint="/teams",
        params={
            "league": WORLD_CUP_LEAGUE_ID,
            "season": WORLD_CUP_SEASON,
        },
    )

    output_path = (
        f"{RAW_DIR}/teams/run_id={run_id}/"
        f"teams_league={WORLD_CUP_LEAGUE_ID}_season={WORLD_CUP_SEASON}.json"
    )
    metadata_path = f"{RAW_DIR}/teams/run_id={run_id}/_metadata.json"

    save_json(payload, output_path)
    save_metadata("teams", payload, metadata_path)

    return output_path


def extract_standings(run_id: str) -> str:
    """
    Extract standings/groups for FIFA World Cup 2026 if available.
    """
    payload = api_get(
        endpoint="/standings",
        params={
            "league": WORLD_CUP_LEAGUE_ID,
            "season": WORLD_CUP_SEASON,
        },
    )

    output_path = (
        f"{RAW_DIR}/standings/run_id={run_id}/"
        f"standings_league={WORLD_CUP_LEAGUE_ID}_season={WORLD_CUP_SEASON}.json"
    )
    metadata_path = f"{RAW_DIR}/standings/run_id={run_id}/_metadata.json"

    save_json(payload, output_path)
    save_metadata("standings", payload, metadata_path)

    return output_path


def main() -> None:
    """
    Run local extraction for the World Cup 2026 pipeline.
    """
    run_id = utc_now_str()

    ensure_dir(RAW_DIR)

    print(f"[+] Starting extraction run_id={run_id}")

    outputs = []

    print("[+] Extracting fixtures...")
    outputs.append(extract_fixtures(run_id))

    print("[+] Extracting teams...")
    outputs.append(extract_teams(run_id))

    print("[+] Extracting standings...")
    outputs.append(extract_standings(run_id))

    print("[+] Extraction completed.")
    for path in outputs:
        print(f"    - {path}")


if __name__ == "__main__":
    main()