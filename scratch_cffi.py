from curl_cffi import requests
import re

def test_trustpilot_curl_cffi():
    url = "https://www.trustpilot.com/review/dnb.no"
    try:
        resp = requests.get(url, impersonate="chrome120")
        html = resp.text
        print("Length:", len(html))
        if "ratingValue" in html:
            print("Found rating!")
            m = re.search(r'"ratingValue":"([\d.]+)"', html)
            if m: print("Rating:", m.group(1))
        else:
            print("No rating found")
            print(html[:500])
    except Exception as e:
        print("Error:", e)

test_trustpilot_curl_cffi()
