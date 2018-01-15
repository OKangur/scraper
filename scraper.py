import json
import requests
from bs4 import BeautifulSoup
import time
import re
import os
import datetime
import pickle


def get_starting_values(file_path):
    """
    Looks if file exists if yes load the file of not returns empty dictionary
    :param file_path:
    :return:
    """
    data = {}

    if os.path.exists(file_path):
        with open(file_path) as json_data:
            data = json.load(json_data)

    return data


def create_soup(url):
    """
    Creates beautifulsoup object from url
    :param url:
    :return:
    """

    html = requests.get(url)

    return BeautifulSoup(html.content, 'lxml')


def get_countries():
    """
    Updates countries list
    :return:
    """

    # finds starting values already saved to file if file exists
    countries = {}
    if os.path.exists('data/countries.json'):
        countries = get_starting_values('data/countries.json')

    soup = create_soup('https://int.soccerway.com/competitions/club-domestic/')

    count = 0
    # iterates over all countries in html
    for div in soup.findAll("div", {"class": "row"}):

        for a in div.findAll('a'):

            url = a['href']
            name = url.split('/')[-3]

            if name not in countries:
                countries[name] = url
                count += 1

    # saves countries to a json file
    with open('data/countries.json', 'w') as fp:
        json.dump(countries, fp)

    print('Countries updated : ', count, ' countries added\n')
    time.sleep(3)


def get_competitions(fltr = ['all']):
    """
    Updates the list of all competitions by default or just one countries if fltr is not ['all']

    :param fltr:
    :return:
    """


    # loads information of existing countries
    countries = get_starting_values('data/countries.json')

    # udpates countires filter if needed
    if fltr == ['all']:
        fltr = sorted(list(countries.keys()))

    # loads information of existing competitions in all countiries
    competitions = get_starting_values('data/competitions.json')

    count_countries = 0
    count_competitions = 0

    # iterates over countires
    for country in fltr:

        if country not in competitions:
            competitions[country] = {}

        soup = create_soup('https://int.soccerway.com' + countries[country])

        # iterates over competitions to find new competitions
        for div in soup.findAll("div", {'class':'content plain '}):
            for a in div.findAll('a', {"class": re.compile('flag.*')}):

                url = a['href']
                name = url.split('/')[-3]

                if name not in competitions[country]:
                    competitions[country][name] = url
                    count_competitions += 1

        # saves file prints result
        with open('data/competitions.json', 'w') as fp:
            json.dump(competitions, fp, ensure_ascii=False)

        count_countries += 1

    print(count_competitions, 'competitions from', country, 'added\n')
    time.sleep(3)


def get_seasons(my_countries=['all'], my_leagues=['all']):
    """
    Updates seasons in all competitions or one competition
    :param my_countries:
    :param my_leagues:
    :return:
    """

    # gets starting values as dict
    competitions = get_starting_values('data/competitions.json')
    leagues = get_starting_values('data/seasons.json')

    if my_countries == ['all']:
        my_countries = sorted(list(competitions.keys()))

    # iterates over countries and adds a country if not in leagues
    for country in my_countries:

        count_seasons = 0

        if country not in leagues:

            leagues[country] = {}

        # iterates over competitions looks if league in my_leageues(filter) and adds a league if not in leagues
        for league in competitions[country]:

            if league in my_leagues:

                if league not in leagues[country]:

                    leagues[country][league] = {}

                soup = create_soup('https://int.soccerway.com' + competitions[country][league])

                # finds seasons from html and adds to leagues if not in leagues
                for element in soup.findAll("select", {'id':'season_id_selector'}):
                    for item in element.findAll('option'):

                        season = item.getText().replace('/', '').replace('-', '')
                        url = item['value']

                        if season not in leagues[country][league]:

                            leagues[country][league][season] = {}

                            leagues[country][league][season]['url'] = url
                            leagues[country][league][season]['game_urls'] = []
                            leagues[country][league][season]['game_ids'] = []

                            count_seasons += 1

                # saves result, printes result, spleeps
                with open('data/seasons.json', 'w') as fp:
                    json.dump(leagues, fp, ensure_ascii=False)

                print(country, league,  count_seasons, 'seasons added')

                time.sleep(3)


def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def get_players(soup, match_info, start_sub='playerstats lineups table'):
    """
    Gets info about players in game, goals scored, minutes played, cards etc
    :param soup:
    :param match_info: dict with game info
    :param start_sub: table class from where the info is taken
    :return:
    """

    # to check if home or away team
    count = 0

    # finds right table
    for table in soup.findAll("table", {'class': start_sub}):

        # values for dictionaries used for saving information
        if 'away_players' in match_info:
            if count == 0:
                players_dict, coaches_dict = match_info['home_players'], match_info['home_coach']
            else:
                players_dict, coaches_dict = match_info['away_players'], match_info['away_coach']
        else:
            players_dict, coaches_dict = {}, {}

        # iterates over players in table
        for player in table.findAll("tr"):

            # find coach name, url, id
            for strong in player.findAll("strong"):
                text = strong.getText()
                if 'Coach' in text:
                    for a in player.findAll("a"):
                        coaches_dict['url'] = a['href']
                        coaches_dict['id'] = a['href'].split('/')[-2]
                        coaches_dict['name'] = a.getText()

                        away_coach = coaches_dict
                        if count == 0:
                            home_coach = coaches_dict

            # if player in starting lineup
            player_info = {'starting_lineup': True}
            if 'substitutions' in start_sub:
                player_info = {'starting_lineup': False}

            # if player sidelined
            player_info['sidelined'] = False


            # find player name, url, id
            for a in player.findAll("a"):
                player_id = a['href'].split('/')[-2]
                if player_id not in players_dict:
                    player_info['player_url'] = a['href']
                    player_info['player_name'] = a.getText()
                    player_info['player_id'] = a['href'].split('/')[-2]

            # find actions related to player, yellow, cards, goals, substitutions, etc
            actions = {}
            for td in player.findAll("td"):
                for span in td.findAll('span'):
                    for img in span.findAll('img'):

                        if '/G.png' in img['src']:
                            if 'goals' not in actions:
                                actions['goals'] = []
                            actions['goals'].append(int(span.getText().replace("'", '').replace('+','').strip()))


                        elif '/SI.png' in img['src']:
                            actions['substitution_in'] = 0

                            for p in td.findAll('p', {'class': "substitute substitute-out"}):
                                substitution_time = p.getText().replace("'",'').replace('+','').split(' ')[-1]
                                actions['substitution_in'] = substitution_time

                            for p in td.findAll('p', {'class': "substitute substitute-out"}):
                                for a in p.findAll('a'):
                                    player_out_id = a['href'].split('/')[-2]
                                    players_dict[player_out_id]['actions']['substitution_out'] = substitution_time

                        elif '/SO.png' in img['src']:
                            actions['substitution_out'] = 0

                        elif '/Y2C.png' in img['src']:
                            actions['second_yellow'] = int(span.getText().strip().replace("'", '').replace('+',''))

                        elif '/YC.png' in img['src']:
                            actions['yellow'] = int(span.getText().strip().replace("'", '').replace('+',''))

                        elif '/PM.png' in img['src']:
                            actions['penalty_missed'] = int(span.getText().strip().replace("'", '').replace('+',''))

                        elif '/PG.png' in img['src']:
                            actions['penalty_goal'] = int(span.getText().strip().replace("'", '').replace('+',''))

                        elif '/OG.png' in img['src']:
                            actions['own_goal'] = int(span.getText().strip().replace("'", '').replace('+',''))

                        elif '/RC.png' in img['src']:
                            actions['red'] = int(span.getText().strip().replace("'", '').replace('+',''))

                        elif '.png' in img['src']:
                            print(img['src'])
                            break

            player_info['actions'] = actions

            if 'player_id' in player_info and player_info['player_url'][:8] == '/players':
                players_dict[player_info['player_id']] = player_info

        if count == 0:
            match_info['home_players'] = players_dict
            match_info['home_coach'] = coaches_dict
        else:
            match_info['away_players'] = players_dict
            match_info['away_coach'] = coaches_dict

        count += 1

    return match_info


def get_referees(soup):
    """
    finds referees
    :param soup:
    :return:
    """

    # iterate over referees
    for dl in soup.findAll("dl", {'class':'details'}):

        referees = {}
        positions = []

        # referee positions
        for dt in dl.findAll("dt"):
            positions.append(dt.getText().replace(':','').lower().replace(' ', '_'))

        count = 0
        # find referee name, url, id and lik to position
        for dd in dl.findAll("dd"):
            for a in dd.findAll("a"):
                referee_name = a.getText()
                referee_url = a['href']
                referee_id = a['href'].split('/')[-2]
                referee_position = positions[count]

                referees[referee_id] = {}
                referees[referee_id]['name'] =referee_name
                referees[referee_id]['url'] =referee_url
                referees[referee_id]['position'] =referee_position
            count += 1
    return referees


def get_goals(soup):
    """
    finds information about goals
    :param soup:
    :return:
    """
    # list of goals to save the values
    goals = []

    # goals table
    for element in soup.findAll("table", {'class':'matches events'}):

        # one individual goal
        goal = {}

        for event in element.findAll("tr", {'class':'event expanded'}):

            count = 0

            # scorer and assist information
            for item in event.findAll("a"):
                if count == 0:
                    goal['scorer'] = item.getText()
                    goal['scorer_url'] = item['href']
                else:
                    goal['assist_by'] = item.getText()
                    goal['assist_by_url'] = item['href']
                count += 1

            # score and goal difference
            for item in event.findAll("td", {'class':'event-icon'}):
                goal['score'] = item.getText()
                home_away_goals = goal['score'].split(' - ')
                goal['home_goals'] = int(home_away_goals[0])
                goal['away_goals'] = int(home_away_goals[1])
                goal['goal_dif'] = goal['home_goals'] - goal['away_goals']

                goal['team'] = 'away'
                if not goals:
                    if goal['home_goals'] == 1:
                        goal['team'] = 'home'
                else:
                    if goal['home_goals'] > goals[-1]['home_goals']:
                        goal['team'] = 'home'


            # goal time
            for item in event.findAll("span", {'class':'minute'}):
                goal['minute'] = item.getText().replace("'", '')
                goal['overtime'] = 0
                if '+' in goal['minute']:
                    goal['overtime'] = goal['minute'].split('+')[1]
                    goal['minute'] = goal['minute'].split('+')[0]


            # add to gaols
            goals.append(goal.copy())

    return goals


def get_match_info(soup, match_info):
    """
    find general match info
    :param soup:
    :param match_info:
    :return:
    """

    # iterate over match details
    for element in soup.findAll("div", {'class':'details clearfix'}):

        info = []

        # detail name
        for item in element.findAll('dt'):
            name = item.getText().strip().lower().replace(' ', '_')
            info.append(name)

        count = 0

        # detail value
        for item in element.findAll('dd'):

            if info[count] == 'competition':
                name = item.getText().strip()
                match_info['competition_name'] = name

                for item_1 in item.findAll('a'):
                    match_info['competition_url'] = item_1['href']

            elif info[count] == 'date':
                date = item.getText().strip()
                match_info['date'] = datetime.datetime.strptime(date, '%d %B %Y').date()

            elif info[count] == 'kick-off':
                t = item.getText().strip()
                match_info['kick-off'] = datetime.datetime.strptime(t, '%H:%M').time()

            elif info[count] == 'half-time':
                match_info['half-time'] = item.getText().strip()

            elif info[count] == 'game_week':
                match_info['game_week'] = item.getText().strip()

            elif info[count] == 'full-time':
                match_info['full-time'] = item.getText().strip()

            elif info[count] == 'on_aggregate':
                match_info['on_aggregate'] = item.getText().strip()

                for item_1 in item.findAll('a'):
                    match_info['link_to_linked_game'] = item_1['href']

            elif info[count] == 'venue':
                match_info['venue'] = item.getText().strip()

                for item_1 in item.findAll('a'):
                    match_info['venue_url'] = item_1['href']

            elif info[count] == 'attendance':
                match_info['attendance'] = item.getText().strip()

            elif info[count] == 'details':
                match_info['details'] = item.getText().strip()

            else:
                print('VALUEMISSING', info[count])

            count += 1

    return match_info


def get_games(url):
    """
    Saves raw html and dictionary with extracted game info
    :param url:
    :return:
    """
    match_info = {}

    key = url.split('/')[-2]

    match_info['match_url'] = url
    match_info['match_id'] = key

    # finds match info if match not done already
    if os.path.exists('data/games/' + str(key) + '.pickle'):

        print('game allready in database')

    else:

        soup = create_soup('https://int.soccerway.com' + url)
        info = []


        # finds team names and ids
        for element in soup.findAll("h3", {'class':'thick'}):
            for item in element.findAll('a'):
                info.append(item['href'])
                info.append(item.getText())

        match_info['home_team_id'] = info[0]
        match_info['home_team_name'] = info[1]
        match_info['away_team_id'] = info[2]
        match_info['away_team_name'] = info[3]

        # Info about score, teams, date, venue etc
        match_info = get_match_info(soup, match_info)

        # Goals info
        match_info['goals'] = get_goals(soup)

        # First 11 and coach
        match_info = get_players(soup, match_info)

        # Add substitutes
        match_info = get_players(soup, match_info, 'playerstats lineups substitutions table')

        # Referees
        match_info['referees'] = get_referees(soup)

        # saves extarcted game info and raw html just in case we need to work with it again
        pickle.dump(match_info, open('data/games/' + str(key) + '.pickle', 'wb'))
        pickle.dump(str(soup.contents), open('data/raw_soup/' + str(key) + '.pickle', 'wb'))

        print('game added home team', match_info['home_team_name'],
              'away team', match_info['away_team_name'],
              'date', match_info['date'],
              'match_id', match_info['match_id'])


def get_game_urls(url):
    """
    Returnsa list of game urls from html
    :param url: league url
    :return: list of game urls
    """
    soup = create_soup('https://int.soccerway.com' + url)

    game_urls_list = []

    # finds urls
    for td in soup.findAll("td", {"class": "form"}):
        for a in td.findAll("a"):
            game_urls_list.append(a['href'])

    return game_urls_list





