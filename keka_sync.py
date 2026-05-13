import requests
import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# GitHub Secrets
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')
SUBDOMAIN = os.environ.get('KEKA_SUBDOMAIN')
GCP_JSON = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')

def get_token():
    # FIX: Keka Token URL eppudu login.keka.com lo untundi, subdomain lo kadu
    url = "https://login.keka.com/connect/token"
    
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials',
        'scope': 'kekaapi'
    }
    # Headers lo API Key kooda avasaram
    headers = {
        'api_key': API_KEY, 
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    print(f"Attempting to get token for Client ID: {CLIENT_ID[:5]}...")
    response = requests.post(url, data=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"Auth Failed: {response.status_code} - {response.text}")
        return None
    
    print("Token generated successfully!")
    return response.json().get('access_token')

def fetch_keka_employees(token):
    url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
    headers = {
        'Authorization': f'Bearer {token}', 
        'apiKey': API_KEY
    }
    all_data = []
    page = 1
    
    while True:
        print(f"Fetching page {page}...")
        resp_raw = requests.get(url, headers=headers, params={'pageNumber': page, 'pageSize': 200})
        
        if resp_raw.status_code != 200:
            print(f"API Error at page {page}: {resp_raw.text}")
            break
            
        resp = resp_raw.json()
        if resp.get('succeeded') and resp.get('data'):
            all_data.extend(resp['data'])
            # Total pages logic
            if page >= resp.get('totalPages', 1): 
                break
            page += 1
        else:
            break
            
    print(f"Total employees fetched: {len(all_data)}")
    return all_data

def upload_to_bigquery(data):
    if not data or not GCP_JSON:
        print("No data or GCP JSON found.")
        return
        
    info = json.loads(GCP_JSON)
    credentials = service_account.Credentials.from_service_account_info(info)
    client = bigquery.Client(credentials=credentials, project=info['project_id'])
    
    # Tables details (Corrected as per your GCP info)
    table_id = "generated-wharf-496208-t5.keka_reports.employees"
    
    # Historic tracking kosam oka timestamp add chestunnam
    df = pd.json_normalize(data)
    df['sync_timestamp'] = pd.Timestamp.now()
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        create_disposition="CREATE_IF_NEEDED",
        autodetect=True
    )
    
    try:
        print(f"Uploading {len(df)} rows to BigQuery...")
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result() 
        print(f"SUCCESS: Data live in BigQuery -> {table_id}")
    except Exception as e:
        print(f"BigQuery Error: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        emp_data = fetch_keka_employees(token)
        upload_to_bigquery(emp_data)
    else:
        print("Script stopped due to Auth Failure.")
