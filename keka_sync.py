import requests
import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Credentials from GitHub Secrets
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')
SUBDOMAIN = os.environ.get('KEKA_SUBDOMAIN')
GCP_JSON = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')

def get_token():
    url = f"https://{SUBDOMAIN}.keka.com/connect/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials',
        'scope': 'kekaapi'
    }
    headers = {'api_key': API_KEY, 'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code != 200:
        print(f"Auth Failed: {response.text}")
        return None
    return response.json().get('access_token')

def fetch_keka_employees(token):
    url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
    headers = {'Authorization': f'Bearer {token}', 'apiKey': API_KEY}
    all_data = []
    page = 1
    while True:
        resp = requests.get(url, headers=headers, params={'pageNumber': page, 'pageSize': 200}).json()
        if resp.get('succeeded') and resp.get('data'):
            all_data.extend(resp['data'])
            if page >= resp.get('totalPages', 1): break
            page += 1
        else: break
    return all_data

def upload_to_bigquery(data):
    if not data or not GCP_JSON: return
    info = json.loads(GCP_JSON)
    credentials = service_account.Credentials.from_service_account_info(info)
    client = bigquery.Client(credentials=credentials, project=info['project_id'])
    
    # Tables details
    table_id = "generated-wharf-496208-t5.keka_reports.employees"
    df = pd.json_normalize(data)
    df['updated_at'] = pd.Timestamp.now()
    
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    try:
        client.load_table_from_dataframe(df, table_id, job_config=job_config)
        print("Success: Data uploaded to BigQuery!")
    except Exception as e:
        print(f"BigQuery Error: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        data = fetch_keka_employees(token)
        upload_to_bigquery(data)
