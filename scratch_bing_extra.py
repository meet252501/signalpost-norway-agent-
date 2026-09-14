import urllib.request
import urllib.parse
import re
from bs4 import BeautifulSoup

def test_bing_search(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&cc=no"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    for block in re.split(r'<li class="b_algo"', html):
        if 'mittanbud.no' in block or 'gulesider.no' in block or 'bytt.no' in block:
            soup = BeautifulSoup(block, 'html.parser')
            text = soup.get_text()
            print("--- BLOCK ---")
            print(text.strip()[:200])
            
            # Find rating snippet
            m1 = re.search(r'(\d[.,]\d)[/\s]+(?:out of|av|/)\s*5', text)
            if not m1:
                m1 = re.search(r'(\d[.,]\d)\s*/\s*5', text)
            if not m1:
                m1 = re.search(r'Vurdering:\s*(\d[.,]\d)', text)
            if not m1:
                m1 = re.search(r'Rating:\s*(\d[.,]\d)', text)
                
            m2 = re.search(r'([\d,.]+)\s*(?:reviews|anmeldelser|omd|evalueringer)', text, flags=re.IGNORECASE)
            
            if m1:
                print("RATING:", m1.group(1))
            if m2:
                print("COUNT:", m2.group(1))

test_bing_search("site:mittanbud.no Rørlegger")
test_bing_search("site:gulesider.no Rørlegger")
test_bing_search("site:bytt.no Bank")
