import requests
import json
import sys

def test_orchestration():
    url = "http://127.0.0.1:8000/token"
    data = {
        "username": "admin",
        "password": "password123"
    }
    
    print("Logging in...")
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token = response.json()["access_token"]
    except Exception as e:
        print(f"Login failed: {e}")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # query = {"question": "What are the top 5 high risk vulnerabilities currently in our database?"}
    query = {"indicator": "8.8.8.8", "indicator_type": "ip"}
    
    print(f"Starting orchestration for: {query}")
    url = "http://127.0.0.1:8000/api/orchestrate"
    
    try:
        response = requests.post(url, headers=headers, json=query, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(decoded_line)
    except Exception as e:
        print(f"Orchestration failed: {e}")

if __name__ == "__main__":
    test_orchestration()
