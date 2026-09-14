from google_play_scraper import search
import pprint

results = search("RID AS", lang='no', country='no')
pprint.pprint(results[:2])
