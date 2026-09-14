from google_play_scraper import search
import sys
import pprint

try:
    results = search("DNB Bank")
    pprint.pprint(results[:2])
except Exception as e:
    print("Error:", e)
