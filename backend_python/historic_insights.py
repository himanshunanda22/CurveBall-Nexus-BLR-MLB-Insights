from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import google.generativeai as genai
import requests
import os
load_dotenv()
class BaseballDataProcessor:
    def __init__(self):
        self.batters_df = None
        self.pitchers_df = None
        
    def load_data(self, batters_file, pitchers_file):
        self.batters_df = pd.read_csv(batters_file)
        self.pitchers_df = pd.read_csv(pitchers_file)
        
        # Convert date columns
        self.batters_df['game_date'] = pd.to_datetime(self.batters_df['game_date'])
        self.pitchers_df['game_date'] = pd.to_datetime(self.pitchers_df['game_date'])
        
        # Add derived metrics for batters with safe division
        self.batters_df['AVG'] = np.where(
            self.batters_df['AB'] > 0,
            self.batters_df['H'] / self.batters_df['AB'],
            0
        )
        
        denominator = (self.batters_df['AB'] + self.batters_df['BB'] +
                      self.batters_df['HBP'] + self.batters_df['SF'])
        self.batters_df['OBP'] = np.where(
            denominator > 0,
            (self.batters_df['H'] + self.batters_df['BB'] + self.batters_df['HBP']) / denominator,
            0
        )
        
        self.batters_df['SLG'] = np.where(
            self.batters_df['AB'] > 0,
            self.batters_df['TB'] / self.batters_df['AB'],
            0
        )
        
        self.batters_df['OPS'] = self.batters_df['OBP'] + self.batters_df['SLG']
        
        # Add derived metrics for pitchers with safe division
        self.pitchers_df['ERA'] = np.where(
            self.pitchers_df['IP'] > 0,
            (self.pitchers_df['ER'] * 9) / self.pitchers_df['IP'],
            0
        )
        
        self.pitchers_df['WHIP'] = np.where(
            self.pitchers_df['IP'] > 0,
            (self.pitchers_df['BB'] + self.pitchers_df['H']) / self.pitchers_df['IP'],
            0
        )
        
        self.pitchers_df['K9'] = np.where(
            self.pitchers_df['IP'] > 0,
            (self.pitchers_df['SO'] * 9) / self.pitchers_df['IP'],
            0
        )
        
        self.pitchers_df['BB9'] = np.where(
            self.pitchers_df['IP'] > 0,
            (self.pitchers_df['BB'] * 9) / self.pitchers_df['IP'],
            0
        )
 
    def get_recent_performance(self, player_id: str, days: int = 30, player_type: str = 'batter') -> pd.DataFrame:
        """Get player's recent performance data"""
        df = self.batters_df if player_type == 'batter' else self.pitchers_df
        end_date = df['game_date'].max()
        start_date = end_date - timedelta(days=days)
        
        return df[
            (df['player_id'] == player_id) &
            (df['game_date'] >= start_date)
        ].copy()
 
    def get_matchup_history(self, batter_id: str, pitcher_id: str) -> Dict:
        """Get historical matchup statistics between batter and pitcher"""
        batter_games = self.batters_df[self.batters_df['player_id'] == batter_id]
        pitcher_games = self.pitchers_df[self.pitchers_df['player_id'] == pitcher_id]
        
        # Find common games
        common_games = pd.merge(
            batter_games,
            pitcher_games[['game_id', 'player_id', 'player_full_name']], # Only merge on necessary pitcher columns
            on='game_id'
        )
        
        if len(common_games) == 0:
            return {
                'plate_appearances': 0,
                'total_at_bats': 0,
                'hits': 0,
                'walks': 0,
                'strikeouts': 0,
                'home_runs': 0,
                'batting_avg': 0.0
            }
        
        return {
            'plate_appearances': common_games['PA'].sum(),
            'total_at_bats': common_games['AB'].sum(),
            'hits': common_games['H'].sum(),
            'walks': common_games['BB'].sum(),
            'strikeouts': common_games['SO'].sum(),
            'home_runs': common_games['HR'].sum(),
            'batting_avg': (common_games['H'].sum() / common_games['AB'].sum())
                        if common_games['AB'].sum() > 0 else 0.0
        }
 
    def get_player_splits(self, player_id: str, player_type: str = 'batter') -> Dict:
        """Get various performance splits for a player"""
        df = self.batters_df if player_type == 'batter' else self.pitchers_df
        player_data = df[df['player_id'] == player_id]
        
        if len(player_data) == 0:
            return {}
            
        seasons = sorted(player_data['season'].unique())
        # print(seasons)
        splits = {
            'seasonal': {},
            'last_30_days': {},
            'trends': {}
        }
        
        # Seasonal splits
        for season in seasons:
            season_data = player_data[player_data['season'] == season]
            if player_type == 'batter':
                splits['seasonal'][season] = {
                    'games': len(season_data),
                    'avg': season_data['H'].sum() / season_data['AB'].sum() if season_data['AB'].sum() > 0 else 0,
                    'ops': season_data['OPS'].mean(),
                    'hr': season_data['HR'].sum(),
                    'rbi': season_data['RBI'].sum(),
                    'so_rate': season_data['SO'].sum() / season_data['PA'].sum() if season_data['PA'].sum() > 0 else 0
                }
            else:
                splits['seasonal'][season] = {
                    'games': len(season_data),
                    'era': (season_data['ER'].sum() * 9) / season_data['IP'].sum() if season_data['IP'].sum() > 0 else 0,
                    'whip': (season_data['BB'].sum() + season_data['H'].sum()) / season_data['IP'].sum()
                            if season_data['IP'].sum() > 0 else 0,
                    'k9': (season_data['SO'].sum() * 9) / season_data['IP'].sum() if season_data['IP'].sum() > 0 else 0
                }
        
        # Last 30 days performance
        recent_data = self.get_recent_performance(player_id, 30, player_type)
        if player_type == 'batter':
            splits['last_30_days'] = {
                'games': len(recent_data),
                'avg': recent_data['AVG'].mean(),
                'ops': recent_data['OPS'].mean(),
                'hr': recent_data['HR'].sum(),
                'so_rate': recent_data['SO'].sum() / recent_data['PA'].sum() if recent_data['PA'].sum() > 0 else 0
            }
        else:
            splits['last_30_days'] = {
                'games': len(recent_data),
                'era': recent_data['ERA'].mean(),
                'whip': recent_data['WHIP'].mean(),
                'k9': recent_data['K9'].mean()
            }
        # print(splits)
        return splits
    
    def get_player_information(self,player_id: str) -> Dict:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/"
        response = requests.get(url)
        player_info = response.json()
        valuable_info = {
            'player_id': player_info['people'][0]['id'],
            'full_name': player_info['people'][0]['fullName'],
            'birth_date': player_info['people'][0]['birthDate'],
            'height': player_info['people'][0]['height'],
            'weight': player_info['people'][0]['weight'],
            'primary_position': player_info['people'][0]['primaryPosition']['name'],
            'bat_side': player_info['people'][0]['batSide']['description'],
            'pitch_hand': player_info['people'][0]['pitchHand']['description'],
            'mlb_debut_date': player_info['people'][0]['mlbDebutDate'],
            # 'current_team': player_info['people'][0]['currentTeam']['name']
        }
        return valuable_info
        
        
 
    def generate_matchup_analysis(self, batter_id: str, pitcher_id: str) -> Dict:
        """Generate comprehensive matchup analysis"""
        batter_recent = self.get_recent_performance(batter_id, 30, 'batter')
        pitcher_recent = self.get_recent_performance(pitcher_id, 30, 'pitcher')
        historical_matchup = self.get_matchup_history(batter_id, pitcher_id)
        
        batter_splits = self.get_player_splits(batter_id, 'batter')
        pitcher_splits = self.get_player_splits(pitcher_id, 'pitcher')
        
        batter_information = self.get_player_information(batter_id)
        pitcher_information = self.get_player_information(pitcher_id)
        return {
            'batter_info': batter_information,
            'pitcher_info': pitcher_information,
            'batter_current_form': {
                'avg': batter_recent['AVG'].mean(),
                'ops': batter_recent['OPS'].mean(),
                'strikeout_rate': (batter_recent['SO'].sum() / batter_recent['PA'].sum())
                                 if batter_recent['PA'].sum() > 0 else 0
            },
            'pitcher_current_form': {
                'era': pitcher_recent['ERA'].mean(),
                'whip': pitcher_recent['WHIP'].mean(),
                'k9': pitcher_recent['K9'].mean()
            },
            'historical_matchup': historical_matchup,
            'batter_splits': batter_splits,
            'pitcher_splits': pitcher_splits
        }
 
class BaseballStrategyAnalyzer:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.llm_client = genai.GenerativeModel('gemini-1.5-flash')
        
        
    def generate_matchup_prompt(self, matchup_data: Dict) -> str:
        """Generate a detailed prompt for the LLM based on matchup data"""
        recent_season = max(
            list(matchup_data['batter_splits']['seasonal'].keys()) +
            list(matchup_data['pitcher_splits']['seasonal'].keys())
        )
        
        prompt = f"""
        Analyze this baseball matchup based on the following data:
        Batter information:
        {json.dumps(matchup_data['batter_info'], indent=2)}
        Pitcher information:
        {json.dumps(matchup_data['pitcher_info'], indent=2)}
        CURRENT FORM (Last 30 days):
        Batter:
        - Batting Average: {matchup_data['batter_current_form']['avg']:.3f}
        - OPS: {matchup_data['batter_current_form']['ops']:.3f}
        - Strikeout Rate: {matchup_data['batter_current_form']['strikeout_rate']:.3f}
 
        Pitcher:
        - ERA: {matchup_data['pitcher_current_form']['era']:.2f}
        - WHIP: {matchup_data['pitcher_current_form']['whip']:.2f}
        - K/9: {matchup_data['pitcher_current_form']['k9']:.2f}
 
        SEASONAL PERFORMANCE ({recent_season}):
        Batter:
        - Games: {matchup_data['batter_splits']['seasonal'][recent_season]['games']}
        - AVG: {matchup_data['batter_splits']['seasonal'][recent_season]['avg']:.3f}
        - OPS: {matchup_data['batter_splits']['seasonal'][recent_season]['ops']:.3f}
        - HR: {matchup_data['batter_splits']['seasonal'][recent_season]['hr']}
 
        Pitcher:
        - Games: {matchup_data['pitcher_splits']['seasonal'][recent_season]['games']}
        - ERA: {matchup_data['pitcher_splits']['seasonal'][recent_season]['era']:.2f}
        - WHIP: {matchup_data['pitcher_splits']['seasonal'][recent_season]['whip']:.2f}
        - K/9: {matchup_data['pitcher_splits']['seasonal'][recent_season]['k9']:.2f}
 
        HEAD-TO-HEAD HISTORY:
        - Total At-Bats: {matchup_data['historical_matchup']['total_at_bats']}
        - Batting Average: {matchup_data['historical_matchup']['batting_avg']:.3f}
        - Hits: {matchup_data['historical_matchup']['hits']}
        - Walks: {matchup_data['historical_matchup']['walks']}
        - Strikeouts: {matchup_data['historical_matchup']['strikeouts']}
        - Home Runs: {matchup_data['historical_matchup']['home_runs']}
 
        Please provide:
        1. A detailed analysis of the matchup considering recent form and historical performance
        2. Idea is to get Historical Insights about both player as they are playing against each other based on the data provided
        3. Give a organized report and should be in a structured format, go from the basics to the advanced analysis based on your past data and the data provided create a organized analysis
        """
        # print(prompt)
        return prompt
 
    def get_strategic_analysis(self, matchup_data: Dict) -> Dict:
        """Implementation depends on your chosen LLM API"""
        # Example using a generic LLM client
        prompt = self.generate_matchup_prompt(matchup_data)
        
        # Replace this with your actual LLM API call
        try:
            response = self.llm_client.generate_content(prompt)
            analysis = response.text
        except Exception as e:
            analysis = f"Error generating analysis: {str(e)}"
        
        return {
            'analysis': analysis,
            'matchup_data': matchup_data
        }
 
    def generate_game_plan(self, player_id: str, opponent_id: str,
                          data_processor: BaseballDataProcessor) -> Dict:
        """Generate a complete game plan for a matchup"""
        matchup_data = data_processor.generate_matchup_analysis(player_id, opponent_id)
        strategic_analysis = self.get_strategic_analysis(matchup_data)
        
        return {
            'matchup_analysis': strategic_analysis['analysis'],
            'statistical_data': matchup_data,
            'timestamp': datetime.now().isoformat()
        }