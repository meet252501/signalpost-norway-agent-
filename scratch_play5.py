from google_play_scraper import search
import pprint
try:
    results = search("DNB Bank")
    print("Default:", len(results))
except Exception as e:
    print("Default error:", e)

try:
    results = search("DNB Bank", lang='en', country='us')
    print("EN/US:", len(results))
except Exception as e:
    print("EN/US error:", e)

try:
    results = search("DNB Bank", lang='no', country='no')
    print("NO/NO:", len(results))
except Exception as e:
    print("NO/NO error:", e)
