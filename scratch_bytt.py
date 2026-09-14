import urllib.request
import urllib.parse
import json

def search_bytt(query):
    url = f"https://www.bytt.no/api/search/companies?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        print(resp)
    except Exception as e:
        print("Error:", e)

search_bytt("DNB")
search_bytt("Elkjop")
