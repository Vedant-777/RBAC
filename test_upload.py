import requests
import json

resp = requests.post("http://127.0.0.1:8000/api/v1/auth/login", json={"username": "admin", "password": "password"})
print("login", resp.status_code, resp.text)
if resp.status_code == 200:
    token = resp.json()["access_token"]
    with open("test.txt", "w") as f:
        f.write("test document content")
    with open("test.txt", "rb") as f:
        resp = requests.post("http://127.0.0.1:8000/api/v1/admin/documents", headers={"Authorization": f"Bearer {token}"}, files={"file": f})
    print("upload", resp.status_code, resp.text)
