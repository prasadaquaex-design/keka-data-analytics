import requests
import json
import pandas as pd
from google.cloud import bigquery
import os

# 1. Keka API Credentials (GitHub Secrets nundi vasthayi)
CLIENT_ID = os.environ['KEKA_CLIENT_ID']
CLIENT_SECRET = os.environ['KEKA_CLIENT_SECRET']
API_KEY = os.environ['KEKA_API_KEY']
SUBDOMAIN = os.environ['KEKA_SUBDOMAIN']

# 2. Get Access Token
def get_token():
    auth_url = "https://login.keka.com/connect/token"
    payload = {
        'grant_type': 'client_credentials',
        'scope': 'kekaapi',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    response = requests.post(auth_url, data=payload)
    return response.json()['access_token']

# 3. Fetch Data from Keka
def fetch_keka_employees(token):
    url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
    headers = {'Authorization': f'Bearer {token}', 'apiKey': API_KEY}
    all_data = []
    page = 1
    
    while True:
        params = {'pageNumber': page, 'pageSize': 200}
        resp = requests.get(url, headers=headers, params=params).json()
        if resp['succeeded'] and resp['data']:
            all_data.extend(resp['data'])
            if page >= resp['totalPages']: break
            page += 1
        else: break
    return all_data

# 4. Upload to BigQuery (Incremental)
def upload_to_bigquery(data):
    client = bigquery.Client()
    table_id = "your_project.your_dataset.employees_historic"
    
    df = pd.json_normalize(data)
    # Adding a timestamp for historic tracking
    df['updated_at'] = pd.Timestamp.now()
    
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client.load_table_from_dataframe(df, table_id, job_config=job_config)

# Run
token = get_token()
emp_data = fetch_keka_employees(token)
upload_to_bigquery(emp_data)
