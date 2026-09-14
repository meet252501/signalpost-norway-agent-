import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

def test_gulesider(company):
    url = f"https://www.gulesider.no/{urllib.parse.quote(company)}/bedrifter"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        print("Success!", len(html))
        # look for reviews
        if 'rating' in html.lower():
            print("Contains rating!")
    except Exception as e:
        print("Error:", e)

test_gulesider("dnb")
test_gulesider("rørlegger")
