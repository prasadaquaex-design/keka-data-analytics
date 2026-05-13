import requests
import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Secrets from GitHub
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')
SUBDOMAIN = os.environ.get('KEKA_SUBDOMAIN')
GCP_JSON = os.environ.get('GCP_SERVICE_ACCOUNT_JSON')

def get_token():
    url = "https://login.keka.com/connect/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials',
        'scope': 'kekaapi'
    }
    headers = {
        'apiKey': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    try:
        print(f"DEBUG: Sending Request to {url}...")
        # timeout pettadam valla request hang avvakunda telisipothundi
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        print(f"DEBUG: Connection Successful. Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"DEBUG: Keka Rejected Request. Body: {response.text}")
            return None
            
        return response.json().get('access_token')
        
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: NETWORK ERROR! Could not reach Keka. Reason: {e}")
        return None
def fetch_keka_employees(token):
    # Nuvvu ichina URL logic ikkada undi
    url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
    headers = {
        'Authorization': f'Bearer {token}', 
        'apiKey': API_KEY
    }
    
    params = {
        'pageNumber': 1,
        'pageSize': 200,
        'employmentStatus': 'Working'
    }
    
    print(f"DEBUG: Fetching employees from {url}")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json().get('data', [])
        print(f"Successfully fetched {len(data)} employees!")
        return data
    else:
        print(f"FETCH FAILED: {response.status_code} - {response.text}")
        return []

def upload_to_bigquery(data):
    if not data:
        print("No data found to upload.")
        return
        
    info = json.loads(GCP_JSON)
    credentials = service_account.Credentials.from_service_account_info(info)
    client = bigquery.Client(credentials=credentials, project=info['project_id'])
    
    # Table ID
    table_id = "generated-wharf-496208-t5.keka_reports.employees"
    df = pd.json_normalize(data)
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        create_disposition="CREATE_IF_NEEDED",
        autodetect=True
    )
    
    try:
        print("Uploading to BigQuery...")
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        print(f"SUCCESS: Table created/updated at {table_id}")
    except Exception as e:
        print(f"BigQuery Error: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        emp_data = fetch_keka_employees(token)
        upload_to_bigquery(emp_data)
