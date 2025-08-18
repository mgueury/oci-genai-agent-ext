# https://www.scraperapi.com/web-scraping/beautiful-soup/
import requests
from bs4 import BeautifulSoup
import json
  
url = 'https://techcrunch.com/category/startups/'
article_list = []
  
response = requests.get(url)
if response.status_code == 200:
    soup = BeautifulSoup(response.content, "lxml")
  
    links = soup.find_all('a')
  
    for link in links:
        try: 
            title = link.get_text(strip=True)
            print( f"title={title}" )
            url = link['href']
            print( f"url={url}" )
            article_list.append({"title": title, "url": url})
        except:
            print( f"Error parsing={str(link)}" )
            pass
  
with open('startup_articles.json', 'w') as f:
   json.dump(article_list, f, indent=4)

 
print("Data saved to startup_articles.json")        