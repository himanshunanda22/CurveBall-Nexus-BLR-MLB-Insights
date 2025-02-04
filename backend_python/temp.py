import json
import os
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_player_id(player_name):
    url = f'https://statsapi.mlb.com/api/v1/people/search?names={player_name}'
    data = fetch_data(url)
    if 'people' in data and data['people']:
        return data['people'][0]['id']
    return None


def get_game_pks(date):
    url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}'
    data = fetch_data(url)
    return [
        game['gamePk']
        for date_info in data.get('dates', [])
        for game in date_info.get('games', [])
    ]


def get_team_ids(sport_id=1):
    url = f'https://statsapi.mlb.com/api/v1/teams?sportId={sport_id}'
    data = fetch_data(url)
    return [team['id'] for team in data['teams']]


def get_mlbDebutDate(player_id, year, retries=3):
    single_player_url = f'https://statsapi.mlb.com/api/v1/people/{player_id}'
    for attempt in range(retries):
        try:
            response = requests.get(single_player_url, timeout=15)
            response.raise_for_status()
            player_info = response.json().get('people', [{}])[0]

            exclude_fields = [
                'fullName', 'link', 'firstName', 'lastName', 'primaryNumber',
                'nameFirstLast', 'nameSlug', 'firstLastName', 'lastFirstName',
                'lastInitName', 'initLastName', 'fullFMLName', 'fullLFMName'
            ]

            player_info_filtered = {k: v for k, v in player_info.items() if k not in exclude_fields}

            if 'mlbDebutDate' not in player_info_filtered:
                player_info_filtered['mlbDebutDate'] = '9999-12-31'

            flg = None
            if 'mlbDebutDate' in player_info_filtered:
                debut_year = int(player_info_filtered['mlbDebutDate'].split('-')[0])
                if debut_year == year + 1:
                    flg = 'Y'
                elif debut_year == 9999:
                    flg = 'N'
                else:
                    return None, None
            else:
                return None, None

            return player_info_filtered, flg
        except requests.exceptions.RequestException as e:
            print(f"Error fetching player data for ID {player_id}: {e}")
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return None, None


def get_roster(team_id, year):
    url = f'https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?season={year}'
    data = fetch_data(url)
    return [(player['person']['id'], player['person']['fullName']) for player in data.get('roster', [])]


def get_minor_league_person_ids_and_names(year):
    sport_ids = [11, 12, 13, 14, 15]
    all_person_data = []

    for sport_id in tqdm(sport_ids, desc="Fetching team rosters"):
        team_ids = get_team_ids(sport_id)
        for team_id in tqdm(team_ids, desc=f"Fetching roster for sport ID {sport_id}", leave=False):
            try:
                person_data = get_roster(team_id, year)
                for pid, name in person_data:
                    player_details, flg = get_mlbDebutDate(pid, year)
                    if player_details is not None:
                        player_details.update({'Year': year, 'ID': pid, 'Name': name, 'Sport_id': sport_id, 'Flg': flg})
                        all_person_data.append(player_details)
                time.sleep(0.5)
            except Exception as e:
                print(f"Error fetching roster for team {team_id} in year {year}: {e}")

    return all_person_data


def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f'Data saved to {filename}')


def construct_schedule_url(season, level):
    sport_ids = {"aaa": 11, "aa": 12, "a+": 13, "a": 14, "a-": 15}
    sport_id = sport_ids.get(level.lower(), 11)
    return (
        f"https://statsapi.mlb.com/api/v1/schedule?lang=en&sportId={sport_id}"
        "&hydrate=team(venue(timezone)),venue(timezone),"
        "game(seriesStatus,seriesSummary,tickets,promotions,sponsorships,"
        "content(summary,media(epg))),seriesStatus,seriesSummary,"
        f"linescore&season={season}&eventTypes=primary&scheduleTypes=games,events,xref"
    )


def parse_schedule_data(json_data):
    schedule_df = pd.DataFrame()
    for d in tqdm(json_data["dates"], desc="Parsing schedule data"):
        for game in d["games"]:
            row_df = pd.DataFrame({
                "game_pk": game["gamePk"],
                "link": game["link"],
            }, index=[0])
            schedule_df = pd.concat([schedule_df, row_df], ignore_index=True)
    return schedule_df


def fetch_game_ids(year, sport_id):
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule?lang=en&sportId={sport_id}"
        "&hydrate=team(venue(timezone)),venue(timezone),"
        "game(seriesStatus,seriesSummary,tickets,promotions,sponsorships,"
        "content(summary,media(epg))),seriesStatus,seriesSummary,"
        f"linescore&season={year}&eventTypes=primary&scheduleTypes=games,events,xref"
    )

    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to connect to the API. HTTP Error Code: {response.status_code}")

    json_data = response.json()

    game_ids = []
    for date_info in json_data.get("dates", []):
        for game in date_info.get("games", []):
            game_ids.append(game.get("gamePk"))

    return game_ids


def get_milb_player_game_stats(game_id, locally=False, year=2024):
    if locally:
        with open(f"/home/attcloud/temp/data/{year}/game_{game_id}.json") as f:
            json_data = json.load(f)
            return parse_game_data(json_data, game_id)
    json_data = fetch_data(f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live?")
    if not json_data:
        print(f"Could not get player game stats data for game ID {game_id}")
        return pd.DataFrame(), pd.DataFrame()
    try:
        return parse_game_data(json_data, game_id)
    except KeyError as e:
        print(f"KeyError: {e} - The JSON structure might have changed or the game ID might be invalid.")
        print("JSON data:", json_data)
        return pd.DataFrame(), pd.DataFrame()


def parse_game_data(json_data, game_id):
    game_date_str = json_data.get("gameData", {}).get("datetime", {}).get("officialDate")
    if not game_date_str:
        raise KeyError("officialDate")
    game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
    away_runs = json_data["liveData"]["linescore"]["teams"]["away"]["runs"]
    home_runs = json_data["liveData"]["linescore"]["teams"]["home"]["runs"]
    away_player_stats = json_data["liveData"]["boxscore"]["teams"]["away"]["players"]
    home_player_stats = json_data["liveData"]["boxscore"]["teams"]["home"]["players"]

    batters_df = pd.DataFrame()
    pitchers_df = pd.DataFrame()

    for loc, player_stats in [("A", away_player_stats), ("H", home_player_stats)]:
        for key, value in player_stats.items():
            player_data = value["stats"]
            if player_data.get("batting"):
                row_df = extract_player_data(value, loc, game_date, game_id, away_runs, home_runs, player_data, "batting")
                batters_df = pd.concat([batters_df, row_df], ignore_index=True)
            if player_data.get("pitching"):
                row_df = extract_player_data(value, loc, game_date, game_id, away_runs, home_runs, player_data, "pitching")
                pitchers_df = pd.concat([pitchers_df, row_df], ignore_index=True)

    return batters_df, pitchers_df


def extract_player_data(value, loc, game_date, game_id, away_runs, home_runs, player_data, category):
    final_score_str = calculate_final_score(away_runs, home_runs, loc)
    player_pos = extract_player_positions(value)
    player_id = value["person"]["id"]
    player_jersey_number = value.get("jerseyNumber", None)
    player_full_name = value["person"]["fullName"]
    player_order = value.get("battingOrder", None)

    row_df = pd.DataFrame(
        {
            "season": game_date.year,
            "game_id": game_id,
            "game_date": game_date,
            "team_runs": away_runs if loc == "A" else home_runs,
            "opp_runs": home_runs if loc == "A" else away_runs,
            "score": final_score_str,
            "player_id": player_id,
            "player_jersey_number": player_jersey_number,
            "player_full_name": player_full_name,
            "player_position": player_pos,
        },
        index=[0],
    )

    if category == "batting":
        append_batting_stats(row_df, player_data)
    elif category == "pitching":
        append_pitching_stats(row_df, player_data)

    return row_df


def calculate_final_score(away_runs, home_runs, loc):
    if home_runs == away_runs:
        return f"T {away_runs}-{home_runs}"
    elif (away_runs > home_runs and loc == "A") or (home_runs > away_runs and loc == "H"):
        return f"W {away_runs}-{home_runs}"
    else:
        return f"L {away_runs}-{home_runs}"


def extract_player_positions(value):
    player_pos = ""
    for i, pos in enumerate(value.get("allPositions", [])):
        player_pos += ("/" if i > 0 else "") + pos["abbreviation"]
    return player_pos or None


def append_batting_stats(row_df, player_data):
    row_df["G"] = player_data["batting"]["gamesPlayed"]
    row_df["PA"] = player_data["batting"]["plateAppearances"]
    row_df["AB"] = player_data["batting"]["atBats"]
    row_df["R"] = player_data["batting"]["runs"]
    row_df["H"] = player_data["batting"]["hits"]
    row_df["2B"] = player_data["batting"]["doubles"]
    row_df["3B"] = player_data["batting"]["triples"]
    row_df["HR"] = player_data["batting"]["homeRuns"]
    row_df["RBI"] = player_data["batting"]["rbi"]
    row_df["SB"] = player_data["batting"]["stolenBases"]
    row_df["CS"] = player_data["batting"]["caughtStealing"]
    row_df["BB"] = player_data["batting"]["baseOnBalls"]
    row_df["IBB"] = player_data["batting"]["intentionalWalks"]
    row_df["SO"] = player_data["batting"]["strikeOuts"]
    row_df["TB"] = player_data["batting"]["totalBases"]
    row_df["GiDP"] = player_data["batting"]["groundIntoDoublePlay"]
    row_df["GiTP"] = player_data["batting"]["groundIntoTriplePlay"]
    row_df["HBP"] = player_data["batting"]["hitByPitch"]
    row_df["SH"] = player_data["batting"]["sacBunts"]
    row_df["SF"] = player_data["batting"]["sacFlies"]
    row_df["CI"] = player_data["batting"]["catchersInterference"]
    row_df["FO"] = player_data["batting"]["flyOuts"]
    row_df["GO"] = player_data["batting"]["groundOuts"]
    row_df["LOB"] = player_data["batting"]["leftOnBase"]


def append_pitching_stats(row_df, player_data):
    row_df["G"] = player_data["pitching"]["gamesPitched"]
    row_df["GS"] = player_data["pitching"]["gamesStarted"]
    row_df["GF"] = player_data["pitching"]["gamesFinished"]
    row_df["CG"] = player_data["pitching"]["completeGames"]
    row_df["SHO"] = player_data["pitching"]["shutouts"]
    row_df["W"] = player_data["pitching"]["wins"]
    row_df["L"] = player_data["pitching"]["losses"]
    row_df["SVO"] = player_data["pitching"]["saveOpportunities"]
    row_df["SV"] = player_data["pitching"]["saves"]
    row_df["BS"] = player_data["pitching"]["blownSaves"]
    row_df["HLD"] = player_data["pitching"]["holds"]
    row_df["IP"] = round(player_data["pitching"]["outs"] / 3, 3)
    row_df["IP_str"] = str(player_data["pitching"]["inningsPitched"])
    row_df["R"] = player_data["pitching"]["runs"]
    row_df["ER"] = player_data["pitching"]["earnedRuns"]
    row_df["BF"] = player_data["pitching"]["battersFaced"]
    row_df["AB"] = player_data["pitching"]["atBats"]
    row_df["H"] = player_data["pitching"]["hits"]
    row_df["2B"] = player_data["pitching"]["doubles"]
    row_df["3B"] = player_data["pitching"]["triples"]
    row_df["HR"] = player_data["pitching"]["homeRuns"]
    row_df["RBI"] = player_data["pitching"]["rbi"]
    row_df["BB"] = player_data["pitching"]["baseOnBalls"]
    row_df["IBB"] = player_data["pitching"]["intentionalWalks"]
    row_df["SO"] = player_data["pitching"]["strikeOuts"]
    row_df["HBP"] = player_data["pitching"]["hitByPitch"]
    row_df["BK"] = player_data["pitching"]["balks"]
    row_df["WP"] = player_data["pitching"]["wildPitches"]
    row_df["GO"] = player_data["pitching"]["groundOuts"]
    row_df["AO"] = player_data["pitching"]["airOuts"]
    row_df["SB"] = player_data["pitching"]["stolenBases"]
    row_df["CS"] = player_data["pitching"]["caughtStealing"]
    row_df["SH"] = player_data["pitching"]["sacBunts"]
    row_df["SF"] = player_data["pitching"]["sacFlies"]
    row_df["CI"] = player_data["pitching"]["catchersInterference"]
    row_df["PB"] = player_data["pitching"]["passedBall"]
    row_df["PK"] = player_data["pitching"]["pickoffs"]
    row_df["IR"] = player_data["pitching"]["inheritedRunners"]
    row_df["IRS"] = player_data["pitching"]["inheritedRunnersScored"]
    row_df["PI"] = player_data["pitching"]["numberOfPitches"]
    row_df["PI_strikes"] = player_data["pitching"]["strikes"]
    row_df["PI_balls"] = player_data["pitching"]["balls"]


def calculate_rolling_averages(df, player_id, window=10, metrics=['R', 'H', 'RBI', 'HR']):
    """
    Calculates rolling averages for specified metrics.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing player stats.
    player_id (int): ID of the player for whom to calculate rolling averages.
    window (int): Window size for the rolling average.
    metrics (list): List of metrics to calculate rolling averages for.
    
    Returns:
    pd.DataFrame: DataFrame with rolling averages added as new columns.
    """
    player_df = df[df['player_id'] == player_id].sort_values(by='game_date')
    for metric in metrics:
        if metric in player_df.columns:
            player_df[f'rolling_{metric}'] = player_df[metric].rolling(window=window, min_periods=1).mean()
    return player_df

def calculate_year_over_year_performance(df, player_id, metrics=['R', 'H', 'RBI', 'HR']):
    """
    Calculates year-over-year performance for a player.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing player stats.
    player_id (int): ID of the player for whom to calculate year-over-year performance.
    metrics (list): List of metrics to calculate year-over-year performance for.
    
    Returns:
    pd.DataFrame: DataFrame with yearly stats and year-over-year changes.
    """
    player_df = df[df['player_id'] == player_id]
    yearly_stats = player_df.groupby('season')[metrics].sum().reset_index()
    for metric in metrics:
        yearly_stats[f'yoy_change_{metric}'] = yearly_stats[metric].diff()
    return yearly_stats

def calculate_career_trajectory(df, player_id, metrics=['R', 'H', 'RBI', 'HR']):
    """
    Tracks a player's progression over their career.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing player stats.
    player_id (int): ID of the player for whom to track career progression.
    metrics (list): List of metrics to track over the player's career.
    
    Returns:
    pd.DataFrame: DataFrame with career stats aggregated by season.
    """
    player_df = df[df['player_id'] == player_id].sort_values(by='game_date')
    career_stats = player_df.groupby('season')[metrics].sum().reset_index()
    return career_stats

def calculate_monthly_performance(df, player_id, metrics=['R', 'H', 'RBI', 'HR']):
    """
    Aggregates player stats by month.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing player stats.
    player_id (int): ID of the player for whom to calculate monthly performance.
    metrics (list): List of metrics to aggregate by month.
    
    Returns:
    pd.DataFrame: DataFrame with monthly aggregated stats.
    """
    player_df = df[df['player_id'] == player_id]
    player_df['month'] = player_df['game_date'].dt.month
    monthly_stats = player_df.groupby('month')[metrics].mean().reset_index()
    return monthly_stats

def calculate_matchup_stats(df, batter_id, pitcher_id):
    """
    Calculates matchup stats between a batter and a pitcher.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing player stats.
    batter_id (int): ID of the batter.
    pitcher_id (int): ID of the pitcher.
    
    Returns:
    pd.DataFrame: DataFrame with aggregated matchup stats.
    """
    matchup_df = df[((df['player_id'] == batter_id) | (df['player_id'] == pitcher_id))]

    matchup_stats_batting = matchup_df[matchup_df['player_id'] == batter_id].groupby(by=['player_id', 'game_id', 'player_position']).agg(
        AB=('AB', 'sum'),
        PA=('PA', 'sum'),
        H=('H', 'sum'),
        R=('R', 'sum'),
        RBI=('RBI', 'sum'),
        BB=('BB', 'sum'),
        SO=('SO', 'sum'),
    ).reset_index()

    matchup_stats_pitching = matchup_df[matchup_df['player_id'] == pitcher_id].groupby(by=['player_id', 'game_id', 'player_position']).agg(
        IP=('IP', 'sum'),
        R=('R', 'sum'),
        ER=('ER', 'sum'),
        SO=('SO', 'sum'),
        BB=('BB', 'sum'),
    ).reset_index()

    merge_matchup = pd.merge(matchup_stats_batting, matchup_stats_pitching, on='game_id', suffixes=('_bat', '_pit'), how='outer')

    merge_matchup['BA'] = merge_matchup['H'] / merge_matchup['AB']
    merge_matchup['ERA'] = merge_matchup['ER'] / merge_matchup['IP'] * 9
    merge_matchup['WHIP'] = (merge_matchup['BB'] + merge_matchup['H']) / merge_matchup['IP']
    merge_matchup['SO/9'] = merge_matchup['SO_pit'] / merge_matchup['IP'] * 9
    merge_matchup['BB/9'] = merge_matchup['BB_pit'] / merge_matchup['IP'] * 9

    return merge_matchup

def calculate_handedness_splits(df, batter_id, pitcher_id):
    """
    Calculates handedness splits for a batter and a pitcher.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing player stats.
    batter_id (int): ID of the batter.
    pitcher_id (int): ID of the pitcher.
    
    Returns:
    pd.DataFrame: DataFrame with handedness splits.
    """
    matchup_df = df[((df['player_id'] == batter_id) | (df['player_id'] == pitcher_id))]
    player_info_batter = fetch_data(f'https://statsapi.mlb.com/api/v1/people/{batter_id}')
    player_info_pitcher = fetch_data(f'https://statsapi.mlb.com/api/v1/people/{pitcher_id}')
    if not player_info_batter or not player_info_pitcher:
        return pd.DataFrame()

    player_info_batter = player_info_batter['people'][0]
    player_info_pitcher = player_info_pitcher['people'][0]
    bat_hand = player_info_batter.get('batSide', {}).get('code', 'Unknown')
    pitch_hand = player_info_pitcher.get('pitchHand', {}).get('code', 'Unknown')

    batting_stats_L = matchup_df[(matchup_df['player_id'] == batter_id)].groupby(by=['player_id']).agg(
        AB=('AB', 'sum'),
        PA=('PA', 'sum'),
        H=('H', 'sum'),
        R=('R', 'sum'),
        RBI=('RBI', 'sum'),
        BB=('BB', 'sum'),
        SO=('SO', 'sum'),
    ).reset_index()

    batting_stats_L['BA'] = batting_stats_L['H'] / batting_stats_L['AB']

    if bat_hand != 'Unknown':
        batting_stats_L['bat_hand'] = bat_hand
    if pitch_hand != 'Unknown':
        batting_stats_L['pitch_hand'] = pitch_hand

    return batting_stats_L


if __name__ == "__main__":
    year = 2021
    game_ids = fetch_game_ids(year, 1)
    print(f"Total games in {year}: {len(game_ids)}")
    all_batters_df = pd.DataFrame()
    all_pitchers_df = pd.DataFrame()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_milb_player_game_stats, game_id, True, year): game_id for game_id in game_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching game stats"):
            game_id = futures[future]
            try:
                batters_df, pitchers_df = future.result()
                if not batters_df.empty:
                    all_batters_df = pd.concat([all_batters_df, batters_df], ignore_index=True)
                if not pitchers_df.empty:
                    all_pitchers_df = pd.concat([all_pitchers_df, pitchers_df], ignore_index=True)
            except Exception as e:
                print(f"Could not fetch stats for game ID {game_id}. Reason: {e}")

    all_batters_df.to_csv(f"milb_batters_stats_{year}.csv", index=False)
    all_pitchers_df.to_csv(f"milb_pitchers_stats_{year}.csv", index=False)
    print(f"Batters stats saved to milb_batters_stats_{year}.csv")
    print(f"Pitchers stats saved to milb_pitchers_stats_{year}.csv")
