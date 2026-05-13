import requests
import os

# Secrets
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')
SUBDOMAIN = os.environ.get('KEKA_SUBDOMAIN')

def test_connectivity():
    print("--- STEP 1: TESTING AUTHENTICATION ---")
    auth_url = "https://login.keka.com/connect/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials',
        'scope': 'kekaapi'
    }
    auth_headers = {
        'apiKey': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        auth_res = requests.post(auth_url, data=payload, headers=auth_headers, timeout=20)
        print(f"Auth Status: {auth_res.status_code}")
        
        if auth_res.status_code == 200:
            token = auth_res.json().get('access_token')
            print("✅ Auth Success! Token received.")
            
            print("\n--- STEP 2: TESTING DATA FETCH ---")
            data_url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
            data_headers = {
                'Authorization': f'Bearer {token}',
                'apiKey': API_KEY
            }
            # Just 1 record test cheddam
            data_res = requests.get(data_url, headers=data_headers, params={'pageSize': 1}, timeout=20)
            print(f"Data API Status: {data_res.status_code}")
            
            if data_res.status_code == 200:
                print("✅ Data Fetch Success! Keka nundi response vachindi.")
            else:
                print(f"❌ Data Fetch Failed: {data_res.text}")
        else:
            print(f"❌ Auth Failed: {auth_res.text}")
            
    except Exception as e:
        print(f"🔥 NETWORK ERROR: Could not reach Keka. Error: {e}")

if __name__ == "__main__":
    test_connectivity()
