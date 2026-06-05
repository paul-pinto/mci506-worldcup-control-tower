import os
from pathlib import Path
from typing import Iterable

from google.cloud import storage

from scripts.config import (
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
    GOOGLE_APPLICATION_CREDENTIALS,
)


LOCAL_DIRS_TO_UPLOAD = [
    "data/raw",
    "data/processed",
    "data/eda",
]


def validate_gcp_config() -> None:
    """Validate GCP environment variables and service account key path."""
    missing = []

    if not GCP_PROJECT_ID:
        missing.append("GCP_PROJECT_ID")

    if not GCS_BUCKET_NAME:
        missing.append("GCS_BUCKET_NAME")

    if not GOOGLE_APPLICATION_CREDENTIALS:
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")

    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

    if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        raise FileNotFoundError(
            f"Service account key not found: {GOOGLE_APPLICATION_CREDENTIALS}"
        )


def iter_files(base_dirs: Iterable[str]) -> Iterable[Path]:
    """Yield files recursively from selected local directories."""
    for base_dir in base_dirs:
        base_path = Path(base_dir)

        if not base_path.exists():
            print(f"[!] Skipping missing directory: {base_dir}")
            continue

        for path in base_path.rglob("*"):
            if path.is_file():
                yield path


def build_blob_name(local_path: Path) -> str:
    """
    Map local data folders to GCS Bronze prefixes.

    Examples:
        data/raw/...       -> bronze/raw/...
        data/processed/... -> bronze/processed/...
        data/eda/...       -> bronze/eda/...
    """
    normalized = local_path.as_posix()

    if normalized.startswith("data/raw/"):
        return normalized.replace("data/raw/", "bronze/raw/", 1)

    if normalized.startswith("data/processed/"):
        return normalized.replace("data/processed/", "bronze/processed/", 1)

    if normalized.startswith("data/eda/"):
        return normalized.replace("data/eda/", "bronze/eda/", 1)

    return f"bronze/misc/{local_path.name}"


def upload_file(bucket: storage.Bucket, local_path: Path) -> str:
    """Upload one local file to GCS and return its gs:// URI."""
    blob_name = build_blob_name(local_path)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    return f"gs://{bucket.name}/{blob_name}"


def main() -> None:
    """Upload local Bronze artifacts to Google Cloud Storage."""
    validate_gcp_config()

    print("[+] GCP config OK")
    print(f"[+] Bucket: {GCS_BUCKET_NAME}")

    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET_NAME)

    uploaded = []

    for local_file in iter_files(LOCAL_DIRS_TO_UPLOAD):
        gcs_uri = upload_file(bucket, local_file)
        uploaded.append(gcs_uri)
        print(f"[+] Uploaded {local_file} -> {gcs_uri}")

    print(f"[+] Upload completed. Files uploaded: {len(uploaded)}")


if __name__ == "__main__":
    main()