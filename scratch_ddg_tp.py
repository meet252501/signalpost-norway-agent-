from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import re

def test_duckduckgo_trustpilot(legal_name):
    query = f'site:trustpilot.com "{legal_name}"'
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        html_text = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("Error:", e)
        return
        
    soup = BeautifulSoup(html_text, 'html.parser')
    for a in soup.find_all('a', class_='result__snippet'):
        text = a.text.strip()
        
        m1 = re.search(r'(\d[.,]\d)[/\s]+(?:out of|av|/)\s*5', text)
        if not m1: m1 = re.search(r'(\d[.,]\d)\s*/\s*5', text)
        if not m1: m1 = re.search(r'Vurdering:\s*(\d[.,]\d)', text)
        if not m1: m1 = re.search(r'Rating:\s*(\d[.,]\d)', text)
        
        m2 = re.search(r'([\d,.]+)\s*(?:reviews|anmeldelser|omd)', text, flags=re.IGNORECASE)
        
        clean_text = text[:100].encode('ascii', 'ignore').decode('ascii')
        
        if m1 and m2:
            print(f"MATCH: {m1.group(1)} stars, {m2.group(1)} reviews -> {clean_text}")
        else:
            print(f"NO MATCH: {clean_text}")

test_duckduckgo_trustpilot("DNB Bank")
test_duckduckgo_trustpilot("Komplett")
