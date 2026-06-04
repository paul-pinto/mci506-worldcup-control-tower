import os
from dotenv import load_dotenv

load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_HOST = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")
API_FOOTBALL_BASE_URL = os.getenv(
    "API_FOOTBALL_BASE_URL",
    "https://v3.football.api-sports.io"
)

WORLD_CUP_LEAGUE_ID = int(os.getenv("WORLD_CUP_LEAGUE_ID", "1"))
WORLD_CUP_SEASON = int(os.getenv("WORLD_CUP_SEASON", "2022"))

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BQ_DATASET = os.getenv("BQ_DATASET", "mci506_worldcup")

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
EDA_DIR = "data/eda"