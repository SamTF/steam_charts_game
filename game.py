### IMPORTS        ############################################################
from bs4 import BeautifulSoup
import requests
import re

###### CONSTANTS        #######################################################
RANDOM_URL = 'https://whatshouldisteam.com/showresults/none/0/random/1/0/0'
RANDOM_GOOD_URL = 'https://whatshouldisteam.com/showresults/none/0/random/1/0/0/sfw_domestic_ach_pop_high_'
STEAM_URL = 'https://store.steampowered.com/app'
HEADER_URL = 'https://steamcdn-a.akamaihd.net/steam/apps/{}/header.jpg'
STEAMDB_URL = 'https://steamdb.info/app/charts'
STEAMSPY_URL = 'https://steamspy.com/app'
STEAMCHARTS_URL = 'https://steamcharts.com/app'


###### CLASSES        #########################################################
class Game:
    '''
    A class containing all relevant info about a Steam game! Give it a Steam App ID and it will fetch all this info automcatically

    Parameters:
        id (int): Steam ppp ID\n
        name (str): Name of the game 
    '''
    id:             str = None
    title:          str = None
    thumbnail:      str = None
    description:    str = None
    game_url:       str = None
    price_text:     str = None
    price:          float = None
    reviews:        str = None
    owners:         int = None
    players_peak:   int = None
    players_current:     int = None
    player_stats:   dict = {'rn' : 0, '24h' : 0, 'peak' : 0}

    def __init__(self, id:str|int, name:str) -> None:
        # Given / pre-determind Info
        self.id = id
        self.name = name
        self.thumbnail = HEADER_URL.format(id)
        self.game_url = f'{STEAM_URL}/{id}'

        # General info - commebted out because rn only the Steam Charts data is used
        # data = steam_spy(id)
        # self.description = data['description']
        # self.price_text = data['price']
        # self.price = float(data['price'].replace('$', ''))
        # self.reviews = data['reviews']
        # self.owners = int(data['owners'].replace(',', ''))

        # Player stats
        stats = steam_charts(id)
        self.player_stats = { 'current' : stats[0], '24h' : stats[1], 'peak' : stats[2] }
        self.players_peak = stats[2]
        self.players_current = stats[1]

    def __repr__(self) -> str:
        return f'''\
            {self.id} - {self.name.upper()}
            ---------------------

            GENERAL INFO
            Name: {self.name}
            ID: {self.id}
            Thumbnail: {self.thumbnail}
            Store URL: {self.game_url}
            ---------------------

            STORE PAGE
            Price: {self.price_text}
            Owners: {self.owners:,}
            Reviews: {self.reviews}
            ---------------------

            PLAYER STATS
            Current players >>> {self.player_stats['current']:,}
            24h peak >>> {self.player_stats['24h']:,}
            All-time peak >>> {self.player_stats['peak']:,}
        '''.strip('\n')

###### WEB SCRAPING     #######################################################
def fetch_random_game() -> dict[str, str]:
    '''
    Fetches a completely random game from the Steam store.

    Returns its Steam App ID & Game title as a dict -> { id, title }
    '''
    # getting the website source code
    source = requests.get(RANDOM_GOOD_URL).text
    
    # creating html parser object
    soup = BeautifulSoup(source, 'lxml')

    # fetching the wanted HTML elements
    title = soup.find('div', { 'id' : 'GameTitle'}).find('span').text
    thumbnail = soup.find('div', { 'id' : 'InfoBox' }).find('img',  class_='game-image')['data-full']

    # extracting game ID from thumbnail URL LOL
    game_id = re.findall('\d+', thumbnail)[0]
    game_url = f'{STEAM_URL}/{game_id}'

    return { 'id' : game_id, 'title' : title }

    # extracting data from steam page
    head = {'cookie': 'sessionid=7f9a0c8f6d980b3276e4b639'}
    req = requests.get(game_url, headers=head)
    soup = BeautifulSoup(req.text, 'lxml')
    price_text = soup.find('div', class_='game_purchase_price').text.lstrip()
    price_num = int(soup.find('div', class_='price')['data-price-final']) / 100
    # test = soup.find('div', { 'id' : 'appHubAppName' })

    # debug prints
    print(title)
    print(thumbnail)
    print(game_id)
    print(game_url)
    print(price_text)
    print(price_num)
    # print(test)


# STEAM DB
def steam_spy(id:str) -> dict[str, str]:
    '''
    Fetches general info about a Steam Game: store description, current price, review score, and number of owners

    Parameters:
        id (int): Steam App ID of the game
    
    Returns:
        Dictionary with the values -> { owners, price, reviews, description }
    '''
    source = requests.get(f'{STEAMSPY_URL}/{id}').text
    soup = BeautifulSoup(source, 'lxml')

    # fetching all wanted elements (what a clusterfuck, all this info is in a SINGLE <P> tag... fucking madness)
    owners = soup.find("strong", string="Owners").next_sibling.split('..')[1].lstrip()
    reviews = soup.find("strong", string="Old userscore:").next_sibling.lstrip()
    description = soup.find_all('p')[1].find('img').next_sibling.lstrip()

    # fail-safe in case it's a free-to-play game
    try:
        price = soup.find("strong", string="Price:").next_sibling.lstrip()
    except AttributeError:
        price = '0'

    # return data
    return {'owners' : owners, 'price' : price, 'reviews' : reviews, 'description' : description}


# STEAM CHARTS
def steam_charts(id:str) -> list[int]:
    '''
    Fetches info about the player count of the given game: current, 24 hour peak, and all-time peak

    Parameters:
        id (int): Steam App ID of the game
    
    Returns:
        List with the values -> [current, 24h, peak]
    '''
    source = requests.get(f'{STEAMCHARTS_URL}/{id}').text
    soup = BeautifulSoup(source, 'lxml')
    stats = [int(x.find('span').text) for x in soup.find_all('div', class_='app-stat')]
    # player_stats = { 'rn' : stats[0], '24h' : stats[1], 'peak' : stats[2] }

    if len(stats) < 3:
        raise ValueError(f'No Stats found for game with ID {id}')

    return stats


def steam_db(id:str):
    headers = {
        "Accept-Language":"en-EN,en;q=0.9", "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 OPR/81.0.4196.61",
        "cookie" : "__cf_bm=GwbO6QvXO9Va99_CoicezEwxVz9uHGNu.nwTIg2Oouc-1683641384-0-AVav/F2SbLs2FG1QYDzqfqq3241ezT9LPQlhQraj5aIlSXvgLWYm6qdh3TldK3ceSlSGg2NcW7Bz2FhSjWob+TAwr8ZE2SxZogUmH7uObtztCdWNZVlCronPMZaQ6+j+UU3Q9MX0n+ygQIeaxzFAPhc="
    }
    source = requests.get(f'{STEAMDB_URL}/{id}', headers=headers).text
    soup = BeautifulSoup(source, 'lxml')
    print(soup.find('h1'))




###### MAIN #################################################
if __name__ == "__main__":
    # fetch_random_game()
    # print(steam_spy('440'))
    # print(steam_charts('312530'))
    # tf2 = Game('440', 'Team Fortress 2')
    # duck = (Game('312530', 'Duck Game'))

    # print(duck.players_current < tf2.players_current)

    r = fetch_random_game()
    random_game = Game(r['id'], r['title'])
    print(random_game)

    # r2 = Game()
    # print(r2)
