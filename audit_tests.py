import time
import requests
import json
import urllib3
urllib3.disable_warnings()

BASE_URL = "https://cardio-vanta-prod.vercel.app"
canonical_payload = {"age": 60.0,"sex": 1,"cp": 2,"trestbps": 130.0,"chol": 250.0,"fbs": 0,"restecg": 1,"thalach": 150.0,"exang": 0,"oldpeak": 1.5,"slope": 1,"ca": 0,"thal": 2}

def print_header(title):
    print("\n==================================================\n" + title + "\n==================================================")

print_header("1. FRONTEND CHECKS")
routes = ["/", "/assessment"]
for route in routes:
    start = time.time()
    resp = requests.get(f"{BASE_URL}{route}", verify=False)
    print(f"GET {route} -> {resp.status_code} ({((time.time() - start)*1000):.1f}ms)")

print_header("2. BACKEND API CHECKS")
resp = requests.get(f"{BASE_URL}/api/v1/health", verify=False)
print(f"GET /api/v1/health -> {resp.status_code} | Body: {resp.text}")

predict_resp = requests.post(f"{BASE_URL}/api/v1/predict", json=canonical_payload, verify=False)
print(f"POST /api/v1/predict (Warm) -> {predict_resp.status_code} | Body: {predict_resp.text}")

resp = requests.post(f"{BASE_URL}/api/v1/predict", data="not json", headers={"Content-Type": "application/json"}, verify=False)
print(f"Malformed JSON -> {resp.status_code} | Body: {resp.text}")

p2 = canonical_payload.copy()
del p2["age"]
resp = requests.post(f"{BASE_URL}/api/v1/predict", json=p2, verify=False)
print(f"Missing field -> {resp.status_code} | Body: {resp.text}")

p3 = canonical_payload.copy()
p3["extra_field"] = "bad"
resp = requests.post(f"{BASE_URL}/api/v1/predict", json=p3, verify=False)
print(f"Extra field -> {resp.status_code} | Body: {resp.text}")

p4 = canonical_payload.copy()
p4["sex"] = 3
resp = requests.post(f"{BASE_URL}/api/v1/predict", json=p4, verify=False)
print(f"Invalid categorical -> {resp.status_code} | Body: {resp.text}")

p5 = canonical_payload.copy()
p5["age"] = 150.0
resp = requests.post(f"{BASE_URL}/api/v1/predict", json=p5, verify=False)
try:
    warning = resp.json().get("development_range_warning")
except:
    warning = None
print(f"Out of range -> {resp.status_code} | Warning: {warning}")

print_header("3. SECURITY CHECKS")
resp = requests.options(f"{BASE_URL}/api/v1/predict", headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "POST"}, verify=False)
print(f"CORS evil.com -> {resp.status_code} | Allow-Origin: {resp.headers.get('Access-Control-Allow-Origin')}")

for docs in ["/docs", "/redoc", "/api/v1/docs"]:
    resp = requests.get(f"{BASE_URL}{docs}", verify=False)
    print(f"GET {docs} -> {resp.status_code}")

