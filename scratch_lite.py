import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

def test_lite(company):
    query = f'site:trustpilot.com "{company}"'
    data = urllib.parse.urlencode({'q': query}).encode('utf-8')
    req = urllib.request.Request("https://lite.duckduckgo.com/lite/", data=data, headers={"User-Agent": "Mozilla/5.0"})
    try:
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        for tr in soup.find_all('tr'):
            text = tr.get_text(separator=' ').strip()
            if 'trustpilot' in text.lower():
                print(text[:100])
    except Exception as e:
        print("Error:", e)

test_lite("DNB")
test_lite("Elkjop")
