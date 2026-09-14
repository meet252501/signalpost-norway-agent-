from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import re

def test_bing_glassdoor(legal_name):
    query = f'site:glassdoor.com "{legal_name}"'
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        html_text = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("Error:", e)
        return
        
    soup = BeautifulSoup(html_text, 'html.parser')
    for li in soup.find_all('li', class_='b_algo'):
        title_node = li.find('h2')
        snip_node = li.find('div', class_='b_caption') or li.find('div', class_='b_snippet') or li.find('p')
        if title_node and snip_node:
            text = f"{title_node.text} {snip_node.text}"
            
            m1 = re.search(r'(\d[.,]\d)[/\s]+(?:out of|av|/)\s*5', text)
            if not m1: m1 = re.search(r'(\d[.,]\d)\s*/\s*5', text)
            if not m1: m1 = re.search(r'Vurdering:\s*(\d[.,]\d)', text)
            if not m1: m1 = re.search(r'Rating:\s*(\d[.,]\d)', text)
            if not m1: m1 = re.search(r'Score:\s*(\d[.,]\d)', text)
            
            m2 = re.search(r'([\d,.]+)\s*(?:reviews|anmeldelser|omd|votes)', text, flags=re.IGNORECASE)
            
            clean_text = text[:150].encode('ascii', 'ignore').decode('ascii')
            
            if m1:
                print(f"MATCH: {m1.group(1)} stars -> {clean_text}")
            else:
                print(f"NO MATCH: {clean_text}")

test_bing_glassdoor("DNB")
test_bing_glassdoor("Telenor")
