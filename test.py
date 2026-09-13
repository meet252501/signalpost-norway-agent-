
import urllib.parse, urllib.request
query = urllib.parse.quote('"DNB"') + '+(site:dn.no+OR+site:e24.no)'
url = f'https://news.google.com/rss/search?q={query}&hl=no&gl=NO&ceid=NO:no'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
print(urllib.request.urlopen(req).read().decode('utf-8')[:500])

