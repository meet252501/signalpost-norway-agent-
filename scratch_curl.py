import subprocess
import re

def test_curl_trustpilot():
    url = "https://www.trustpilot.com/review/dnb.no"
    cmd = [
        "curl", "-s", "-L",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.5",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        html = result.stdout
        print("Length:", len(html))
        if "Just a moment" in html or "Cloudflare" in html:
            print("Blocked by Cloudflare")
        elif "ratingValue" in html:
            print("Found rating!")
            m = re.search(r'"ratingValue":"([\d.]+)"', html)
            if m: print("Rating:", m.group(1))
        else:
            print("No rating found")
            print(html[:500])
    except Exception as e:
        print("Error:", e)

test_curl_trustpilot()
