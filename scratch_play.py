from google_play_scraper import search, app
import sys

def test_play_store(company_name):
    print(f"\n--- Searching for: {company_name} ---")
    try:
        results = search(company_name, lang='no', country='no')
        for res in results[:5]:
            # print(f"Found: {res['title']} by {res['developer']}")
            if company_name.lower().replace(' as', '').strip() in res['developer'].lower() or company_name.lower().replace(' as', '').strip() in res['title'].lower():
                print(f"MATCH! {res['title']} by {res['developer']}")
                details = app(res['appId'], lang='no', country='no')
                print(f"Rating: {details['score']}, Reviews: {details['ratings']}")
                return
    except Exception as e:
        print("Error:", e)

test_play_store("DNB Bank")
test_play_store("Vipps")
test_play_store("KLP")
