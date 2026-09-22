import os
import requests

ics_url = os.environ["CANVAS_ICS_URL"]

response = requests.get(ics_url)

print("STATUS:", response.status_code)
print("FIRST 500 CHARS:")
print(response.text[:500])
