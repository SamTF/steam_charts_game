import requests
from bs4 import BeautifulSoup
import json
from enum import Enum

SEARCH_URL = 'https://store.steampowered.com/search/results'
POPULAR_URL = 'https://store.steampowered.com/search/?as-reviews-score=70-&as-reviews-count=10000-&category1=998&ndl=1'
BEST_URL = 'https://store.steampowered.com/search/?sort_by=Reviews_DESC&as-reviews-count=1000-&category1=998&as-reviews-score=80-'
POPULAR_NEW_URL = 'https://store.steampowered.com/search/?sort_by=Released_DESC&filter=popularnew&ndl=1'
link = 'https://store.steampowered.com/search/results'
search_term = ''
head = {'cookie': 'sessionid=cd46137aee87759ca68f1347'}

# Enum to contain all possible search filters
class SearchFilter(str, Enum):
    '''
    Enum with string values that contains all possible search filter when scraping steam games
    '''
    BASE        = 'https://store.steampowered.com/search/results',
    POPULAR     = 'https://store.steampowered.com/search/?as-reviews-score=70-&as-reviews-count=10000-&category1=998&ndl=1'
    BEST        = 'https://store.steampowered.com/search/?sort_by=Reviews_DESC&as-reviews-count=1000-&category1=998&as-reviews-score=80-'
    POPULAR_NEW = 'https://store.steampowered.com/search/?sort_by=Released_DESC&filter=popularnew&ndl=1'


def get_pagination():
    param = {
        'term': search_term,
        'page': 1,
    }

    req = requests.get(link, headers=head, params=param)
    soup = BeautifulSoup(req.text, 'html.parser')
    page_item = soup.find('div', 'search_pagination_right').find_all('a')

    return 1 + int(page_item[-2].text)


# Gets a list of games from steam
# scraping code from: https://medium.com/@senchooo/scraping-all-game-in-steam-using-python-e9f0ad206add
def get_games_list(filter: SearchFilter) -> list[dict]:
    '''
    Fetches a list of 50 pages from the Steam Store page using the given search link and parameters.

    filter: Enum representing with search filters to use when fetching games.

    Returns a list of dictionaries with keys: { id, name, price, release, url }
    '''
    count = 0
    games = []

    # for j in range(1, get_pagination()):
    for page in range(1, 8):
        param = {
            'term': search_term,
            'page': page,
        }
        search_url = filter.value
        req = requests.get(search_url, params=param, headers=head)
        soup = BeautifulSoup(req.text, 'lxml')

        results = soup.find('div', {'id': 'search_resultsRows'}).find_all('a')
        for item in results:
            url = item['href']
            title = item.find('div', 'col search_name ellipsis').text.strip().replace('\n', ' ')
            id = item['data-ds-appid']

            try:
                price = item.find('div', 'col search_price responsive_secondrow').text.strip()
            except Exception:
                price = 'discount from ' + item.find('span', {'style': 'color: #888888;'}).text.replace(' ', '.') + ' to ' + item.find('div', 'col search_price discounted responsive_secondrow').find('br').next_sibling.strip() + f" ({item.find('div', 'col search_discount responsive_secondrow').text.replace('-', '').strip()})"
            if price == '':
                price = 'none'

            release = item.find('div', 'col search_released responsive_secondrow').text
            if release == '':
                release = 'none'

            data = {
                'id'        : id,
                'title'     : title,
                'price'     : price,
                'release'   : release,
                'url'      : url
            }
            games.append(data)

            count += 1
            # print(f'{count}. {title}\nID: {id}\nReleased Date: {release}\nPrice: {price}\nURL: {url}\n----')
    
    # return the scraped list of games
    return games


    

###### MAIN #################################################
if __name__ == "__main__":
    games = get_games_list(SearchFilter.BASE)
    print(len(games))