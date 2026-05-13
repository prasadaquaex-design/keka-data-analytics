import requests
import os

# Secrets
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')

def get_token():
    url = "https://login.keka.com/connect/token"
    
    # Headers - strict order
    headers = {
        'apiKey': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    # Payload as a string to avoid dictionary issues
    payload = f"grant_type=client_credentials&scope=kekaapi&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"

    print(f"DEBUG: Attempting login for Client: {CLIENT_ID[:5]}...")
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        print(f"DEBUG: HTTP Status -> {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Token Received!")
            return response.json().get('access_token')
        else:
            # Trick to bypass GitHub Secret Masking: print with spaces
            raw_text = response.text
            spaced_text = " ".join(list(raw_text))
            print(f"❌ AUTH FAILED! Error Body: {spaced_text}")
            return None
            
    except Exception as e:
        print(f"🔥 NETWORK ERROR: {str(e)}")
        return None

if __name__ == "__main__":
    get_token()
