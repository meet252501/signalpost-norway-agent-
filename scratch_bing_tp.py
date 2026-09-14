from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import re

query = "site:trustpilot.com DNB"
url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&cc=no"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")

for block in re.split(r'<li class="b_algo"', html):
    if 'trustpilot.com' in block:
        soup = BeautifulSoup(block, "html.parser")
        text = soup.get_text(separator=' ')
        print("--- BLOCK ---")
        print(text[:300].encode('ascii', 'ignore').decode('ascii'))
