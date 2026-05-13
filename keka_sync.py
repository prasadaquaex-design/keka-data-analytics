import requests
import json
import os

# Secrets
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')
SUBDOMAIN = os.environ.get('KEKA_SUBDOMAIN')

def get_token():
    url = "https://login.keka.com/connect/token"
    
    # Headers chala strict ga undali
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "apiKey": API_KEY  # Capital 'K' important
    }
    
    # Payload format
    data = {
        'grant_type': 'client_credentials',
        'scope': 'kekaapi',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    try:
        print(f"DEBUG: Attempting login for {CLIENT_ID[:8]}...")
        response = requests.post(url, headers=headers, data=data, timeout=20)
        
        print(f"DEBUG: Status Code -> {response.status_code}")
        
        if response.status_code == 200:
            token = response.json().get('access_token')
            print("✅ Auth Successful!")
            return token
        else:
            # Body empty unte status tho paatu headers ni kuda chuddam
            print(f"❌ Auth Failed! Status: {response.status_code}")
            print(f"❌ Error Detail: {response.text}")
            print(f"❌ Headers: {response.headers}")
            return None
            
    except Exception as e:
        print(f"🔥 Network/Request Error: {str(e)}")
        return None

if __name__ == "__main__":
    token = get_token()
    if token:
        print("Success! Token received. Now you can fetch data.")
    else:
        print("Failed to get token.")
