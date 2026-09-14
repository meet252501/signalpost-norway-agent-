from googlesearch import search
import time

def test_google():
    query = 'site:trustpilot.com "DNB Bank"'
    try:
        # googlesearch-python >= 1.0.0 uses num_results
        results = search(query, num_results=3, advanced=True)
        for r in results:
            print("TITLE:", r.title)
            print("DESC:", r.description)
            print("URL:", r.url)
    except Exception as e:
        print("Error:", e)

test_google()
