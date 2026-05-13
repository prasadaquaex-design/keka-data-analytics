def fetch_keka_employees(token):
    # API URL from your OpenAPI definition
    url = f"https://{SUBDOMAIN}.keka.com/api/v1/hris/employees"
    headers = {
        'Authorization': f'Bearer {token}', 
        'apiKey': API_KEY
    }
    
    all_data = []
    page = 1
    max_page_size = 200 # OpenAPI lo unnattu max 200 pettachu
    
    while True:
        print(f"Fetching page {page}...")
        # Query parameters as per your OpenAPI spec
        params = {
            'pageNumber': page, 
            'pageSize': max_page_size,
            'employmentStatus': 'Working' # Optional: Active employees matrame kavalante
        }
        
        resp_raw = requests.get(url, headers=headers, params=params)
        
        if resp_raw.status_code != 200:
            print(f"DEBUG: API Error -> Status: {resp_raw.status_code}, Body: {resp_raw.text}")
            break
            
        resp = resp_raw.json()
        
        # Checking 'succeeded' flag from the response
        if resp.get('succeeded') and resp.get('data'):
            data_batch = resp['data']
            all_data.extend(data_batch)
            print(f"Successfully fetched {len(data_batch)} records from page {page}.")
            
            # Pagination logic based on totalPages in response
            total_pages = resp.get('totalPages', 1)
            if page >= total_pages:
                break
            page += 1
        else:
            print("DEBUG: No more data or 'succeeded' flag is false.")
            break
            
    print(f"Total employees fetched in this run: {len(all_data)}")
    return all_data
