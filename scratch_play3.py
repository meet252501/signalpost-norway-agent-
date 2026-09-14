from google_play_scraper import app
import pprint

details = app('no.dnb.bmpuls', lang='no', country='no')
print("Keys:", details.keys())
print("Score:", details.get('score'))
print("Ratings:", details.get('ratings'))
print("Reviews:", details.get('reviews'))
