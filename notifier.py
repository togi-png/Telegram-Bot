import os
import requests

url = os.environ["CANVAS_ICS_URL"]

response = requests.get(url)

print("STATUS:", response.status_code)
print(response.text[:300])
