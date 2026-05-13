import base64
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from google.cloud import bigquery
from google.oauth2 import service_account


TOKEN_URL = os.environ.get("KEKA_TOKEN_URL")
KEKA_SUBDOMAIN = os.environ.get("KEKA_SUBDOMAIN")
KEKA_ENVIRONMENT = os.environ.get("KEKA_ENVIRONMENT", "keka")
KEKA_BASE_URL = os.environ.get("KEKA_BASE_URL")

CLIENT_ID = os.environ.get("KEKA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("KEKA_CLIENT_SECRET")
API_KEY = os.environ.get("KEKA_API_KEY")

BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", "keka_reports")
BIGQUERY_PROJECT = os.environ.get("GCP_PROJECT_ID")
GCP_SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")

DEFAULT_ENDPOINTS = {
    "employees": "/api/v1/hris/employees",
}


def require_env(name, value):
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")


def parse_endpoints():
    configured = os.environ.get("KEKA_ENDPOINTS")
    if not configured:
        return DEFAULT_ENDPOINTS

    configured = configured.strip()
    if configured.startswith("{"):
        endpoints = json.loads(configured)
        return {str(name): str(path) for name, path in endpoints.items()}

    endpoints = {}
    for item in configured.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(
                "KEKA_ENDPOINTS entries must use name:/api/path format"
            )
        name, path = item.split(":", 1)
        endpoints[name.strip()] = path.strip()
    return endpoints


def get_token_urls():
    if TOKEN_URL:
        return [TOKEN_URL]

    return [
        "https://login.keka.com/connect/token",
        "https://login.kekad.com/connect/token",
    ]


def get_base_urls():
    if KEKA_BASE_URL:
        return [KEKA_BASE_URL.rstrip("/")]

    require_env("KEKA_SUBDOMAIN", KEKA_SUBDOMAIN)
    urls = [f"https://{KEKA_SUBDOMAIN}.{KEKA_ENVIRONMENT}.com"]
    if KEKA_ENVIRONMENT == "keka":
        urls.append(f"https://{KEKA_SUBDOMAIN}.kekad.com")
    return urls


def get_token():
    require_env("KEKA_CLIENT_ID", CLIENT_ID)
    require_env("KEKA_CLIENT_SECRET", CLIENT_SECRET)
    require_env("KEKA_API_KEY", API_KEY)

    payload = {
        "grant_type": "kekaapi",
        "scope": "kekaapi",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "api_key": API_KEY,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "keka-data-analytics/1.0",
    }

    print("Requesting Keka access token")
    failures = []
    for token_url in get_token_urls():
        response = requests.post(token_url, headers=headers, data=payload, timeout=30)
        if response.status_code == 200:
            token = response.json().get("access_token")
            if not token:
                raise RuntimeError("Keka auth response did not include access_token")
            print(f"Keka access token received from {token_url}")
            return token

        failures.append(
            f"{token_url} -> HTTP {response.status_code}: {response.text[:300]}"
        )

    raise RuntimeError("Keka auth failed. Attempts: " + " | ".join(failures))


def request_json(session, url, params=None):
    for attempt in range(4):
        response = session.get(url, params=params, timeout=60)
        if response.status_code == 429 and attempt < 3:
            wait_seconds = 65
            print(f"Rate limited by Keka; waiting {wait_seconds}s before retry")
            time.sleep(wait_seconds)
            continue
        if response.status_code >= 400:
            raise RuntimeError(
                f"Keka fetch failed for {url} with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        return response.json()
    raise RuntimeError(f"Keka fetch failed for {url} after retries")


def extract_records(payload):
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, list):
        return data
    if data is None:
        return []
    return [data]


def next_page_url(payload):
    if not isinstance(payload, dict):
        return None

    for key in ("nextPage", "next", "nextPageLink", "nextPageUrl"):
        value = payload.get(key)
        if value:
            return value

    return None


def fetch_all_records_for_base(session, endpoint_path, base_url):
    url = (
        endpoint_path
        if endpoint_path.startswith("http")
        else urljoin(base_url, endpoint_path)
    )
    records = []
    page_number = 1
    params = {"pageNumber": page_number, "pageSize": 100}

    while url:
        payload = request_json(session, url, params=params)
        page_records = extract_records(payload)
        records.extend(page_records)
        print(f"Fetched {len(page_records)} records from page {page_number}")

        next_url = next_page_url(payload)
        if next_url:
            url = (
                next_url
                if next_url.startswith("http")
                else urljoin(base_url, next_url)
            )
            params = None
            page_number += 1
            continue

        total_pages = payload.get("totalPages") if isinstance(payload, dict) else None
        if total_pages and page_number < int(total_pages):
            page_number += 1
            params = {"pageNumber": page_number, "pageSize": 100}
            continue

        break

    return records


def fetch_all_records(session, endpoint_path):
    if endpoint_path.startswith("http"):
        return fetch_all_records_for_base(session, endpoint_path, "")

    failures = []
    for base_url in get_base_urls():
        try:
            print(f"Using Keka API base URL: {base_url}")
            return fetch_all_records_for_base(session, endpoint_path, base_url)
        except RuntimeError as exc:
            failures.append(f"{base_url} -> {exc}")

    raise RuntimeError("Keka endpoint fetch failed. Attempts: " + " | ".join(failures))


def build_bigquery_client():
    require_env("GCP_SERVICE_ACCOUNT_JSON", GCP_SERVICE_ACCOUNT_JSON)

    try:
        service_account_info = json.loads(GCP_SERVICE_ACCOUNT_JSON)
    except json.JSONDecodeError:
        decoded = base64.b64decode(GCP_SERVICE_ACCOUNT_JSON).decode("utf-8")
        service_account_info = json.loads(decoded)

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    project_id = BIGQUERY_PROJECT or service_account_info.get("project_id")
    if not project_id:
        raise RuntimeError(
            "Set GCP_PROJECT_ID or include project_id in GCP_SERVICE_ACCOUNT_JSON"
        )
    return bigquery.Client(project=project_id, credentials=credentials)


def ensure_dataset(client):
    dataset_ref = bigquery.Dataset(f"{client.project}.{BIGQUERY_DATASET}")
    dataset_ref.location = os.environ.get("BIGQUERY_LOCATION", "US")
    client.create_dataset(dataset_ref, exists_ok=True)
    return dataset_ref.dataset_id


def to_bigquery_rows(records):
    synced_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for record in records:
        rows.append(
            {
                "synced_at": synced_at,
                "record": json.dumps(record, ensure_ascii=False, default=str),
            }
        )
    return rows


def load_records(client, dataset_id, table_name, records):
    table_id = f"{client.project}.{dataset_id}.{table_name}"
    rows = to_bigquery_rows(records)

    schema = [
        bigquery.SchemaField("synced_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("record", "JSON", mode="NULLABLE"),
    ]
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    load_job = client.load_table_from_json(rows, table_id, job_config=job_config)
    load_job.result()
    print(f"Loaded {len(rows)} rows into {table_id}")


def main():
    token = get_token()
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
    )

    endpoints = parse_endpoints()
    client = build_bigquery_client()
    dataset_id = ensure_dataset(client)

    for name, path in endpoints.items():
        print(f"Syncing Keka endpoint: {name}")
        records = fetch_all_records(session, path)
        load_records(client, dataset_id, f"keka_{name}", records)

    print("Keka to BigQuery sync completed")


if __name__ == "__main__":
    main()
