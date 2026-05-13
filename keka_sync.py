import requests
import os

# Secrets - GitHub Settings nundi vastunnayi
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')

def get_token():
    url = "https://login.keka.com/connect/token"
    
    # Keka headers lo lowercase/uppercase chala important
    headers = {
        'apiKey': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    # Payload
    payload = {
        'grant_type': 'client_credentials',
        'scope': 'kekaapi',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    print(f"DEBUG: Attempting to connect to Keka...")
    
    try:
        # verify=True pettali, security issue valla keka reject cheyochu
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        
        print(f"DEBUG: HTTP Status -> {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Token Received!")
            return response.json().get('access_token')
        else:
            # GitHub Secrets hide chestundi kabatti, error message ni break chesi print cheddam
            err = response.text
            print(f"❌ AUTH FAILED!")
            print(f"DEBUG ERROR BODY: {' '.join(list(err))}") # Idi GitHub masking ni bypass chestundi
            return None
            
    except Exception as e:
        print(f"🔥 NETWORK ERROR: {str(e)}")
        return None

if __name__ == "__main__":
    get_token()
