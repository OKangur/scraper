import scraper
import os
import time
import random
import json

def print_options(options):
    """
    print out to console list of optsions to choose from
    :param options: list of countries, competitions, seasons, etc
    :return:
    """

    # adds 'Exit' to options so we could end the program
    if options[-1] != 'Exit':
        options.append('Exit')

    print('')
    print('What do you want to do? Enter the number\n')

    # print out options to console
    for i in range(len(options)):
        if options[i] == 'Exit':
            print(i, options[i])
        else:
            print(i, 'Update ' + options[i])
    print('\n')

    option_id = input('Enter the number')

    # parses string to int or asks new input if not possible
    try:
        if int(option_id) in range(len(options)):
            if int(option_id) == len(options) - 1:
                exit()
            return int(option_id)
        else:
            print_options(options)
    except:
        return print_options(options)


def update_competitions():
    """
    adds new competitions if there are some
    :return:
    """

    # get countries
    if not os.path.exists('data/countries.json'):
        scraper.get_countries()
    countries = scraper.get_starting_values('data/countries.json')

    # list of countries
    options = sorted(list(countries.keys()))

    selection = print_options(options)

    # country to update
    country_name = options[selection].replace('Update ', '')

    # update
    scraper.get_competitions([country_name])

    return country_name


def update_seasons():

    # get country
    country_name = update_competitions()

    # get competition
    competitions = scraper.get_starting_values('data/competitions.json')

    # this country competitions list
    competition_names = sorted(list(competitions[country_name].keys()))

    # get competition to update
    selection = print_options(competition_names)

    competition_name = competition_names[selection]

    # update
    scraper.get_seasons([country_name], [competition_name])

    return country_name, competition_name


def update_games():
    """
    downloads html, parses info from html, saves results, saves done games urls and ids to list
    :return:
    """

    # get country name, competition name
    country_name, competition_name = update_seasons()
    seasons = scraper.get_starting_values('data/seasons.json')
    season_names = sorted(list(seasons[country_name][competition_name].keys()))

    # select season and get it's urls
    selection = print_options(season_names)
    season = season_names[selection]
    season_url = seasons[country_name][competition_name][season]['url']

    # find game urls for this season
    game_urls_list = scraper.get_game_urls(season_url)

    game_count = 0

    # iterate over game urls
    for url in game_urls_list:

        game_id = url.split('/')[-2]

        # if game not saved, get game info save it and the fact that it's saved to seasons list
        if game_id not in seasons[country_name][competition_name][season]['game_ids']:

            scraper.get_games(url)

            seasons[country_name][competition_name][season]['game_urls'].append(url)
            seasons[country_name][competition_name][season]['game_ids'].append(game_id)

            with open('data/seasons.json', 'w') as fp:
                json.dump(seasons, fp, ensure_ascii=False)

            game_count += 1

            # sleep before next html download
            time.sleep(random.randint(sleep_min, sleep_max))

    print(country_name, competition_name, season, game_count, 'games added')


def what_to_do(sleep_min, sleep_max):
    """
    function to interact with user and give orders
    :param sleep_min:min time to sleep in seconds between downloads
    :param sleep_max: max time to sleep in seconds between downloads
    :return:
    """

    # options to choose from
    options = ['Update countries', 'Update competitions', 'Update seasons', 'Update games']

    selection = print_options(options)

    # get_countries
    if selection == 0:
        scraper.get_countries()

    # update competitions list
    elif selection == 1:
        _ = update_competitions()

    # update seasons list
    elif selection == 2:
        _, _ = update_seasons()

    # update games
    elif selection == 3:
        update_games()

    what_to_do(sleep_min, sleep_max)


dir = os.path.dirname(__file__)
os.makedirs(dir + '/data', exist_ok=True)
os.makedirs(dir + '/data/games', exist_ok=True)
os.makedirs(dir + '/data/raw_soup', exist_ok=True)

sleep_min, sleep_max = 2, 5

what_to_do(sleep_min, sleep_max)