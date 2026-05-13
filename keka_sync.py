import requests
import json
import pandas as pd
from google.cloud import bigquery
import os

# 1. Keka API Credentials (GitHub Secrets)
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')
SUBDOMAIN = os.environ.get('KEKA_SUBDOMAIN')

# 2. Get Access Token
def get_token():
    # Ikkada variables anni CAPITAL lone undali
    url = f"https://{SUBDOMAIN}.keka.com/connect/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials',
        'scope': 'kekaapi'
    }
    headers = {
        'api_key': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    print(f"Connecting to: {url}")
    response = requests.post(url, data=payload, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error Response: {response.text}")
        return None
        
    return response.json().get('access_token')

# 3. Fetch Data from Keka
def fetch_keka_employees(token):
    if not token:
        print("No token found. Skipping fetch.")
        return []
        
    url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
    headers = {'Authorization': f'Bearer {token}', 'apiKey': API_KEY}
    all_data = []
    page = 1
    
    while True:
        params = {'pageNumber': page, 'pageSize': 200}
        resp_raw = requests.get(url, headers=headers, params=params)
        resp = resp_raw.json()
        
        if resp.get('succeeded') and resp.get('data'):
            all_data.extend(resp['data'])
            if page >= resp.get('totalPages', 1): break
            page += 1
        else: 
            break
    return all_data

# 4. Upload to BigQuery
def upload_to_bigquery(data):
    if not data:
        print("No data to upload.")
        return
        
    client = bigquery.Client()
    # MEE PROJECT ID & DATASET PERU IKKADA MARCHANDI
    table_id = "your_project.your_dataset.employees_historic"
    
    df = pd.json_normalize(data)
    df['updated_at'] = pd.Timestamp.now()
    
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    try:
        client.load_table_from_dataframe(df, table_id, job_config=job_config)
        print("Data successfully uploaded to BigQuery!")
    except Exception as e:
        print(f"BigQuery Error: {e}")

# Main Execution
token = get_token()
if token:
    emp_data = fetch_keka_employees(token)
    upload_to_bigquery(emp_data)
else:
    print("Failed to authenticate with Keka.")
