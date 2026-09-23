import os
import requests

url = os.environ["CANVAS_ICS_URL"]

print("URL length:", len(url))
print("URL prefix:", url[:60])

response = requests.get(
    url,
    allow_redirects=True
)

print("STATUS:", response.status_code)
print("FINAL URL:", response.url)
print("HEADERS:", dict(response.headers))
print("TEXT:", response.text[:300])
