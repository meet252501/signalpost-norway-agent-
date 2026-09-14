from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import re

def test_duckduckgo_search(legal_name):
    query = f'site:bytt.no "{legal_name}"'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        html_text = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("Error:", e)
        return
        
    soup = BeautifulSoup(html_text, 'html.parser')
    for a in soup.find_all('a', class_='result__snippet'):
        text = a.text.strip()
        print(text)

test_duckduckgo_search("DNB Bank")
