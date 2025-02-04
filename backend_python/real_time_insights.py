from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from typing import Dict, List, Optional
from datetime import datetime
from crewai import LLM
from crewai.crews.crew_output import CrewOutput
from GUMBO import *
from dotenv import load_dotenv
import google.generativeai as genai
from historic_insights import BaseballDataProcessor, BaseballStrategyAnalyzer
load_dotenv()
import os,json

# Player Related Models

async def process_gumbo_data(raw_data: dict) -> GumboUtilities:
    """Process raw GUMBO data and return utilities object."""
    print("Processing GUMBO data...")
    gumbo_data = GumboData(**raw_data)
    return GumboUtilities(gumbo_data)


class BaseballAnalysis:
    def __init__(self, gumbo_utilities: GumboUtilities, llm_client: genai.GenerativeModel):
        """
        Initialize the baseball analysis with GUMBO utilities and LLM client.
        
        Args:
            gumbo_utilities: GumboUtilities instance
            llm_client: OpenAI or similar LLM client instance
        """
        print("Initializing BaseballAnalysis...")
        self.gumbo = gumbo_utilities
        self.homeTeam = self.gumbo.get_team_details("home").name
        self.awayTeam = self.gumbo.get_team_details("away").name
        self.league = self.gumbo.get_team_details("home").league.name
        self.llm = llm_client
        
    async def analyze_current_play(self,current_play: Optional[Play],historical_data,past_game_summary,current_game_context) -> Dict[str, str]:
        """Analyze the current play with play-by-play and strategic analysis."""
        print("Analyzing current play...")
        # current_play = self.gumbo.get_current_play()
        if not current_play:
            print("No current play found.")
            return {}

        # Play-by-play analysis prompt
        play_analysis_prompt = dedent(f"""
            As a Play-by-Play Analyst, analyze this baseball play for casual viewers:
            In a Match between two teams {self.homeTeam} and {self.awayTeam} in the {self.league} league, you are analyzing the current play in the game.
            Make use of Past Game Context only for your reference to know what has happened so far.
            Use Historic Data if needed to have some past knowledge .
            If you are specifying something from historic data be precise and specific about mentioning as per historical data.

            Past Game Context:
            {past_game_summary}
            
            Current Game Context:
            {current_game_context}
            
            Historic Data:
            {historical_data}
            
            Play Description: {current_play.result.description}
            Count: {current_play.count.balls}-{current_play.count.strikes}
            Inning: {current_play.about.inning} ({current_play.about.halfInning})
            
            Break down what happened in simple terms that any casual fan can understand.
            Focus on:
            1. The key action and result
            2. Why this play matters in the current game context
            3. Any interesting or unusual aspects
            
            Keep the analysis concise but informative, using everyday language.Keep it short
            """)

        # Strategic analysis prompt
        strategic_analysis_prompt = dedent(f"""
            You are a Baseball Strategy Analyst, tasked with analyzing the strategic implications of the current game situation. Your goal is to understand why teams are making specific decisions, what strategic options are available, and what might happen next, all while focusing on managerial decisions and game strategy.

In a Match between two teams {self.homeTeam} and {self.awayTeam} in the {self.league} league, you are analyzing the current play in the game.
            You will be provided with three types of information:

   **Past Game Context:** A summary of the key events that have happened so far in the current game. Use this to understand the flow of the game up to this point. This information is for context and not to influence strategic options.

   **Current Game Context:** Specific details about the current play, such as runners on base, pitch count, etc. This information is related to what is currently happening.

   **Historical Data:** Information about players, their tendencies, or team strategies based on past games, including specific data points. If you are citing historical data, be precise and specific. Do not take the historical data as data that has occured in this game rather as historical context and past knowledge.



        Strategic Analysis:

        1.  Why the teams are making their current decisions in this specific situation given the current game and past game context
        2.  What strategic options are available for each team given the current game context, based on past experiences and tendencies from the historical data?
        3.  What might be the likely next moves or situations based on the current situation? What is the strategy in the short term?

        Please keep your response concise and short. Focus on managerial decisions and game strategy.
            
        Past Game Context:
        {past_game_summary}
            
        Current Game Context:
        {current_game_context}

        - Inning: {current_play.about.halfInning} of {current_play.about.inning}
        - Score: {current_play.result.awayScore}-{current_play.result.homeScore}
        - Matchup: {current_play.matchup.batter.fullName} vs {current_play.matchup.pitcher.fullName}
                    
        Historical Data: 
        {historical_data}
            """)

        print("Generating play analysis...")
        play_analysis = self.llm.generate_content(play_analysis_prompt).text
        
        print("Generating strategic analysis...")
        strategic_analysis = self.llm.generate_content(strategic_analysis_prompt).text

        # Add pitch analysis if it's a pitch event
        pitch_analysis = {}
        if current_play.playEvents and current_play.playEvents[-1].isPitch:
            last_pitch = current_play.playEvents[-1]
            pitch_analysis_prompt = dedent(f"""
                You are a Pitching Analyst, tasked with analyzing individual pitches in a baseball game for casual fans. You will receive specific details about a pitch, and your job is to explain the strategy behind it, how well it was executed, and its overall effectiveness, all while avoiding technical baseball jargon.

In a Match between two teams {self.homeTeam} and {self.awayTeam} in the {self.league} league, you are analyzing the last pitch thrown in the current game.
Here are the details of the pitch:

-   Type: {last_pitch.details.type.description}
-   Speed: {last_pitch.pitchData.startSpeed} mph
-   Location: Zone {last_pitch.pitchData.zone}
-   Result: {last_pitch.details.description}

Pitch Analysis:

1.  Why was this specific pitch type chosen in *this* situation, considering the batter, count, and game context?
2.  How well was this pitch executed, considering its speed, location (zone), and overall movement?
3.  How effective was this pitch selection given the result of the pitch and the overall context of the at-bat?

Use clear language that casual fans can easily understand while maintaining technical accuracy. Please keep your response concise and short.
                """)
            
            print("Generating pitch analysis...")
            pitch_analysis = self.llm.generate_content(pitch_analysis_prompt).text

        return {
            'play_analysis': play_analysis,
            'strategic_analysis': strategic_analysis,
            'pitch_analysis': pitch_analysis if pitch_analysis else None
        }

    async def analyze_patterns(self, current_game: Optional[Play],historical_data: List[Dict],past_game_summary) -> Dict[str, str]:
        """Analyze patterns and trends in the current matchup."""
        print("Analyzing patterns and trends...")
        current_matchup = current_game.matchup
        if not current_matchup:
            print("No current matchup found.")
            return {}

        pattern_analysis_prompt = dedent(f"""
            You are a Baseball Pattern Recognition Specialist, tasked with analyzing the current matchup between a batter and a pitcher, aiming to identify patterns and predict future outcomes. Your goal is to highlight specific trends that would be valuable for anticipating what might happen next.

In a Match between two teams {self.homeTeam} and {self.awayTeam} in the {self.league} league, you are analyzing the current matchup between the batter and pitcher.
You will be provided with three types of information:

*   **Past Game Context:** A summary of key events that have happened in the current game so far. Use this solely to understand the flow of the game and not for finding specific data points.
*   **Current Matchup:** Details about the current batter and pitcher.
    *   Batter: {current_matchup.batter.fullName}
    *   Pitcher: {current_matchup.pitcher.fullName}
*  **Historical Data:** Information about the batter and pitcher tendencies, including their past performance, habits, strategies and other information. If you are citing specific historical information, be precise and specific.

Pattern Recognition Analysis:

1.  Identify notable patterns in the following areas, based on the current game, past game context and historical data if necessary:
    *   **Pitch sequences**: Does the pitcher tend to throw a specific sequence of pitches? E.g., "fastball, then curveball".
    *   **Batter tendencies**: Does the batter tend to swing at pitches in certain locations? Or does the batter tend to do certain things on certain counts?
    *   **Situational approaches**: Do the players act differently based on the score, the number of outs, runners on base, etc?
2.  Based on the patterns identified in the step above, what are the likely next outcomes for the at-bat, and why?
3.  Highlight any particularly interesting trends that are notable from the patterns you have identified that a spectator might not notice.

Focus on identifying trends that would be valuable for predicting what might happen next. Keep your response concise and short.
        
Past Game Context:
{past_game_summary}
       
Historical Data:
{historical_data}
            
            """)

        print("Generating pattern analysis...")
        pattern_analysis = self.llm.generate_content(pattern_analysis_prompt).text

        return {
            'pattern_analysis': pattern_analysis,
        }

    async def get_strategic_prediction(self,past_game_summary,current_game_context) -> Dict[str, str]:
        """Predict upcoming strategic decisions based on current game situation."""
        print("Predicting strategic decisions...")
        current_situation = self.gumbo.get_current_situation()
        
        prediction_prompt = dedent(f"""
            As a Baseball Strategy Analyst, predict upcoming strategic decisions:
            Make use of Past Game Context only for your reference to know what has happened so far.
            In a Match between two teams {self.homeTeam} and {self.awayTeam} in the {self.league} league, you are predicting the strategic decisions that will be made based on the current game situation.
            If you are specifying something from historic data be precise and specific about mentioning as per historical data.
            
            Past Game Context:
            {past_game_summary}
            
            Current Game Context:
            {current_game_context}
            
            Current Situation:
            - Inning: {current_situation.get('inning')}
            - Game State: {current_situation.get('halfInning')}
            - Runners on Base: {len(current_situation.get('runners', []))}
            
            Predict and explain:
            1. Likely pitching decisions (changes, approach adjustments)
            2. Potential batting strategy adjustments
            3. Possible strategic moves (bunts, steals, defensive alignments)
            4. Manager's likely thought process
            
            Focus on practical, likely decisions based on the game situation.
            Explain the reasoning behind each prediction.
                Keep it concise and short.
            
            """)

        print("Generating strategic prediction...")
        prediction_analysis = self.llm.generate_content(prediction_prompt).text

        return {
            'strategic_prediction': prediction_analysis
        }
    async def generate_current_game_context(self,current_game:Optional[Play]) -> Dict[str, str]:

        def extract_crucial_info(data):
            result = data['result']
            about = data['about']
            count = data['count']
            matchup = data['matchup']
            runners = data['runners']
            play_events = data['playEvents']

            crucial_info = {
                "result": {
                    "type": result['type'],
                    "event": result['event'],
                    "eventType": result['eventType'],
                    "description": result['description'],
                    "rbi": result['rbi'],
                    "awayScore": result['awayScore'],
                    "homeScore": result['homeScore'],
                    "isOut": result['isOut']
                },
                "about": {
                    "atBatIndex": about['atBatIndex'],
                    "halfInning": about['halfInning'],
                    "isTopInning": about['isTopInning'],
                    "inning": about['inning'],
                    "startTime": about['startTime'],
                    "endTime": about['endTime'],
                    "isComplete": about['isComplete'],
                    "isScoringPlay": about['isScoringPlay'],
                    "hasReview": about['hasReview'],
                    "hasOut": about['hasOut']
                },
                "count": {
                    "balls": count['balls'],
                    "strikes": count['strikes'],
                    "outs": count['outs']
                },
                "matchup": {
                    "batter": {
                        "id": matchup['batter']['id'],
                        "fullName": matchup['batter']['fullName']
                    },
                    "batSide": matchup['batSide']['description'],
                    "pitcher": {
                        "id": matchup['pitcher']['id'],
                        "fullName": matchup['pitcher']['fullName']
                    },
                    "pitchHand": matchup['pitchHand']['description'],
                    "splits": matchup['splits']
                },
                "runners": [
                    {
                        "runner": {
                            "id": runner['details']['runner']['id'],
                            "fullName": runner['details']['runner']['fullName']
                        },
                        "outBase": runner['movement']['outBase'],
                        "isOut": runner['movement']['isOut'],
                        "outNumber": runner['movement']['outNumber'],
                        "credits": [
                            {
                                "player": {
                                    "id": credit['player']['id']
                                },
                                "position": credit['position']['abbreviation'],
                                "credit": credit['credit']
                            } for credit in runner['credits']
                        ]
                    } for runner in runners
                ],
                "playEvents": [
                    {
                        "pitchNumber": event['pitchNumber'],
                        "description": event['details']['description'],
                        "type": event['details']['type']['description'],
                        "speed": event['pitchData']['startSpeed'] if 'pitchData' in event else None
                    } for event in play_events if event['isPitch']
                ],
                "hitData": {
                    "launchSpeed": play_events[-1]['hitData']['launchSpeed'],
                    "launchAngle": play_events[-1]['hitData']['launchAngle'],
                    "totalDistance": play_events[-1]['hitData']['totalDistance'],
                    "trajectory": play_events[-1]['hitData']['trajectory'],
                    "hardness": play_events[-1]['hitData']['hardness'],
                    "location": play_events[-1]['hitData']['location']
                } if 'hitData' in play_events[-1] else None
            }

            return crucial_info

        def print_crucial_info_markdown(crucial_info):
            markdown = f"""
        # Crucial Information

        ## Result
        - **Type:** {crucial_info['result']['type']}
        - **Event:** {crucial_info['result']['event']}
        - **Event Type:** {crucial_info['result']['eventType']}
        - **Description:** {crucial_info['result']['description']}
        - **RBI:** {crucial_info['result']['rbi']}
        - **Away Score:** {crucial_info['result']['awayScore']}
        - **Home Score:** {crucial_info['result']['homeScore']}
        - **Is Out:** {crucial_info['result']['isOut']}

        ## About
        - **At Bat Index:** {crucial_info['about']['atBatIndex']}
        - **Half Inning:** {crucial_info['about']['halfInning']}
        - **Is Top Inning:** {crucial_info['about']['isTopInning']}
        - **Inning:** {crucial_info['about']['inning']}
        - **Start Time:** {crucial_info['about']['startTime']}
        - **End Time:** {crucial_info['about']['endTime']}
        - **Is Complete:** {crucial_info['about']['isComplete']}
        - **Is Scoring Play:** {crucial_info['about']['isScoringPlay']}
        - **Has Review:** {crucial_info['about']['hasReview']}
        - **Has Out:** {crucial_info['about']['hasOut']}

        ## Count
        - **Balls:** {crucial_info['count']['balls']}
        - **Strikes:** {crucial_info['count']['strikes']}
        - **Outs:** {crucial_info['count']['outs']}

        ## Matchup
        - **Batter:** {crucial_info['matchup']['batter']['fullName']} (ID: {crucial_info['matchup']['batter']['id']})
        - **Bat Side:** {crucial_info['matchup']['batSide']}
        - **Pitcher:** {crucial_info['matchup']['pitcher']['fullName']} (ID: {crucial_info['matchup']['pitcher']['id']})
        - **Pitch Hand:** {crucial_info['matchup']['pitchHand']}
        - **Splits:** {crucial_info['matchup']['splits']}

        ## Runners
        """
            for runner in crucial_info['runners']:
                markdown += f"""
        - **Runner:** {runner['runner']['fullName']} (ID: {runner['runner']['id']})
        - **Out Base:** {runner['outBase']}
        - **Is Out:** {runner['isOut']}
        - **Out Number:** {runner['outNumber']}
        - **Credits:**
        """
                for credit in runner['credits']:
                    markdown += f"    - **Player ID:** {credit['player']['id']}, **Position:** {credit['position']}, **Credit:** {credit['credit']}\n"

            markdown += "\n## Play Events\n"
            for event in crucial_info['playEvents']:
                markdown += f"""
        - **Pitch Number:** {event['pitchNumber']}
        - **Description:** {event['description']}
        - **Type:** {event['type']}
        - **Speed:** {event['speed']} mph
        """

            if crucial_info['hitData']:
                markdown += f"""
        ## Hit Data
        - **Launch Speed:** {crucial_info['hitData']['launchSpeed']} mph
        - **Launch Angle:** {crucial_info['hitData']['launchAngle']} degrees
        - **Total Distance:** {crucial_info['hitData']['totalDistance']} feet
        - **Trajectory:** {crucial_info['hitData']['trajectory']}
        - **Hardness:** {crucial_info['hitData']['hardness']}
        - **Location:** {crucial_info['hitData']['location']}
        """

            return (markdown)

        # Example usage
        # crucial_info = extract_crucial_info(data)
        details = extract_crucial_info(json.loads(current_game.model_dump_json()))
        info = print_crucial_info_markdown(details)
        # print(info)
        PROMPT = """
        You are an expert baseball commentator, tasked with explaining the key events of a baseball game to a casual viewer. You will receive a structured data dump about a specific play in JSON format, and you must use this data to produce a detailed explanation in markdown format, suitable for a user with little knowledge of baseball. You should avoid complicated baseball jargon, instead using clear and simple language.

        Here's a breakdown of the information you'll receive and what to do with it:

        **Input Data Structure**

        The input will be a JSON-like structured Python dictionary which will include these key sections:

        1.  **`result`**: Details about what happened in the play.
            *   `type`: The general outcome of the play (e.g., "atBat," "pickoff").
            *   `event`: A description of the specific event (e.g., "Single", "Strikeout").
            *   `eventType`: The type of event like "hit" or "out".
            *   `description`: A detailed textual summary of the event.
            *   `rbi`: The number of runs batted in (if applicable).
            *   `awayScore`: The current score of the away team.
            *   `homeScore`: The current score of the home team.
        *    `isOut`: A boolean that says if the play is an out

        2.  **`about`**: Context about the play.
            *   `atBatIndex`: The unique index of the at-bat in the game.
            *   `halfInning`: Whether it's the top or bottom of the inning.
            *    `isTopInning`: Boolean to check is it is the top inning
            *   `inning`: The inning number.
            *   `startTime`: When the play started.
            *   `endTime`: When the play ended.
            *   `isComplete`: Boolean to see if the play is completed.
            *   `isScoringPlay`: Boolean that says if it's a scoring play
            *   `hasReview`: Boolean to see if the play was reviewed.
            *  `hasOut` Boolean to see if the play was an out.

        3.  **`count`**: The count of balls, strikes, and outs during the play.
            *   `balls`: Number of balls.
            *   `strikes`: Number of strikes.
            *   `outs`: Number of outs.

        4.  **`matchup`**: Information about the batter and pitcher.
            *   `batter`: The batter's full name and ID.
            *   `batSide`: The batter's batting side ("L", "R", "S").
            *   `pitcher`: The pitcher's full name and ID.
            *   `pitchHand`: The pitcher's throwing hand ("L", "R").
            *   `splits` (optional): Additional matchup information.

        5.  **`runners`**: Array of information about runners on base.
            *   `runner`: The runner's full name and ID.
            *   `outBase`: (optional) If the runner is out, what base they were out on.
            *   `isOut`: (optional)  If the runner is out.
            *   `outNumber`: (optional) The number out it was for the runner.
            *   `credits`: Array of credits for the play.
                * player ID
                * position
                * credit

        6. **`playEvents`**: Information about the events in the play, such as the pitches thrown
            * `pitchNumber` pitch number in a given atbat
            *  `description` a description of the pitch thrown
            * `type`: the type of the event
            * `speed` the speed of the event

        7. **`hitData`** (optional): Detailed data about the hit.
            * `launchSpeed`: The speed of the ball off the bat.
            * `launchAngle`: The angle at which the ball left the bat.
            * `totalDistance`: The total distance the ball traveled.
            * `trajectory`: The trajectory of the ball (e.g. "fly ball", "ground ball").
            * `hardness`: How hard the ball was hit.
            * `location`: Where the ball was hit on the field (optional, not always available).

        **Instructions**

        1.  **Use Markdown:** Structure your response using clear markdown formatting.
        2.  **Introductory Summary:** Begin with a concise summary of the play. Mention the batter, pitcher, and the primary event that occurred.
        3.  **Context and Count:** Explain the game situation (inning, score) and the count (balls, strikes, outs) when the play began.
        4.  **Matchup Details:** Introduce the batter and pitcher by name, using their side/hand for context.
        5.  **Runner Details:** If runners were on base, explain who they were and what happened to them during the play, be clear if they were out and if so where and their out number.
        6.  **Play Breakdown:** Provide a step by step summary of key events from the `playEvents`, also mention any details about the pitch.
        7.  **Casual Tone:** Use a conversational tone and avoid baseball jargon whenever possible. Explain any terms that a casual viewer may not understand, such as what an rbi means.
        8.  **Concise & Detailed:** Be detailed enough to convey information about play, while being concise.
        9. **Output:** Please return your response in markdown format.
        10.**Hit Data Analysis:** If the data "includes hit information", translate it into plain English. Describe what the launch speed, angle, and distance mean for the play.

        **Example Output**

        The markdown output should look something like this:

        ```markdown
        # [Batter's Name] vs [Pitcher's Name]

        ## Summary
        In this at-bat, [Batter's Name] faced [Pitcher's Name] and [Event description (e.g., hit a single to left field].
        Other crucial details about the play that you think that needs to be considered.

        ## Context
        The game was in the [Inning, Top/Bottom] inning, the score was [Away score] to [Home score]. Before this play, the count was [Balls]-[Strikes] with [Outs] out.

        ## Matchup
        The batter, [Batter's Name], bats from the [Left/Right/Switch] side, while the pitcher, [Pitcher's Name], throws with a [Left/Right] hand.

        ## Runners
        [If Runners were on base, a section like this would appear, otherwise, should skip:]
        - [Runner's name] was on [First/Second/Third] and [Was out/ Advanced etc]...

        ## Play Breakdown
        - On the first pitch the pitcher threw a [pitch description] which reached [pitch speed] mph
        - On the second pitch [pitch description] occurred
        - [and so on for the play events]

        ## Hit Analysis
        [If there was a hit or any data related to hit, this section appears, otherwise, this should be omitted]:
        The ball left the bat at [Launch Speed] mph at a [Launch Angle] degree angle and went for [Total Distance] feet. This was a [Trajectory of ball] hit and the batter hit the ball with [Hardness] force.

        Remember to give the sections only if data is present otherwise just ignore the sections
        Here is the acutal data and follow the above instructions to generate the markdown

        {info}
        """
        response = self.llm.generate_content(PROMPT.format(info=info))
        return {"current_context":(response.text)}



    async def generate_entire_game_summary(self,real_time_insights,past_game_summary) -> Dict[str, str]:
        """Generate a summary of the entire game."""
        print("Generating game summary...")
        game_summary_prompt = dedent(f"""
            You are a Baseball Game Analyst, tasked with providing a detailed and insightful summary of a baseball game. Your goal is to capture the key moments, standout performances, strategic decisions, and overall flow of the game.

In a Match between two teams {self.homeTeam} and {self.awayTeam} in the {self.league} league, 
You will be provided with two types of information:

*   **Past Game Context:** A detailed summary of key events that have happened so far in the current game. Use this to understand the flow of the game and how it has progressed.
*   **Current Game Insights:** Real-time insights, including LLM generated analysis, on specific plays, players, and strategic moves. Use this to provide a more granular view of what has been occurring in the game.

Using the Past Game Context and Current Game Insights, provide a detailed summary of the game so far. Your summary should be comprehensive and include the following points, structured clearly with key points highlighted:

1.  Identify and describe the key moments and turning points in the game.
2.  Highlight any standout performances, including players and significant plays, that have had a major impact on the game's outcome.
3.  Analyze the strategic decisions made by managers or players, and discuss their overall impact on the game.
4.  Provide a clear description of the overall flow and dynamics of the game, including any momentum shifts or changes in pace.

Your summary should be detailed, capturing all crucial information about the game.

Past Game Context:
{past_game_summary}

Current Game Insights:
{real_time_insights}        
            """)

        print("Generating game summary...")
        game_summary = self.llm.generate_content(game_summary_prompt).text

        return {
            'game_summary': game_summary
        }
class BaseballInsightApp:
    def __init__(self, gumbo_utilities, llm_client:genai.GenerativeModel,index_number:int):
        print("Initializing BaseballInsightApp...")
        os.makedirs("cache",exist_ok=True)
        self.analyzer = BaseballAnalysis(gumbo_utilities, llm_client)
        self.current_inning = 1
        self.last_play_index = -1
        self.index_number = index_number

    async def process_game_update(self, historic_tool:BaseballStrategyAnalyzer,data_processor:BaseballDataProcessor) -> Dict[str, str]:
        """Process updates to the game and generate insights."""
        print("Processing game update...")
        # Get past game summary
        if os.path.exists("cache/past_game_summary.json"):
            with open("cache/past_game_summary.json", "r") as file:
                game_summary = json.load(file)
        else:
            with open("cache/past_game_summary.json", "w") as file:
                json.dump({},file)
            game_summary = {}
        
        if os.path.exists("cache/real_time_analysis.json"):
            with open("cache/real_time_analysis.json", "r") as file:
                real_time_insights = json.load(file)
        else:
            with open("cache/real_time_analysis.json", "w") as file:
                json.dump({},file)
            real_time_insights = {}
        if self.index_number < len(real_time_insights):
            return real_time_insights[str(self.index_number)]
            
            
        # Get Current Play situation if present in the cache
        
        
        current_play = self.analyzer.gumbo.get_all_plays()[self.index_number]
        if not current_play:
            print("No current play found.")
            return None

        # Check if this is a new play
        if current_play.about.atBatIndex <= self.last_play_index:
            print("No new play detected.")
            return None

        self.last_play_index = current_play.about.atBatIndex
        
        past_game_summary = game_summary[str(self.index_number-1)] if self.index_number-1 >= 0  else ""
        # Get historical data for the matchup
        historical_data = historic_tool.generate_game_plan(current_play.matchup.batter.id, current_play.matchup.pitcher.id, data_processor)['matchup_analysis']
        print(historical_data)
        # Get various types of analysis
        print("Getting current game context...")
        current_game_context_task = asyncio.create_task(self.analyzer.generate_current_game_context(current_play))
        current_game_context = await current_game_context_task
        
        print("Getting play analysis...")
        play_analysis_task = asyncio.create_task(self.analyzer.analyze_current_play(current_play,historical_data,past_game_summary,current_game_context))
        print("Getting pattern analysis...")
        pattern_analysis_task = asyncio.create_task(self.analyzer.analyze_patterns(current_play,historical_data,past_game_summary) if historical_data else {})
        print("Getting strategic prediction...")
        strategic_prediction_task = asyncio.create_task(self.analyzer.get_strategic_prediction(past_game_summary,current_game_context))

        play_analysis = await play_analysis_task
        pattern_analysis = await pattern_analysis_task
        strategic_prediction = await strategic_prediction_task
        print("got everything.......")
        current_game_context['batter'] = current_play.matchup.batter.fullName
        current_game_context['pitcher'] = current_play.matchup.pitcher.fullName 
        real_time_insight =  {
            'play_analysis': play_analysis,
            'pattern_analysis': pattern_analysis,
            'strategic_prediction': strategic_prediction,
            'current_game_context': current_game_context
        }
        
        # yield real_time_insight
        # print(len(game_summary))
        current_game_summary = game_summary[str(self.index_number)] if self.index_number >= 0 and self.index_number<len(game_summary) else ""
        print(current_game_summary)
        if current_game_summary == "":
            game_summary_task = asyncio.create_task(self.analyzer.generate_entire_game_summary(real_time_insight,past_game_summary))
            game_summary_task = await game_summary_task
            game_summary[str(self.index_number)] = game_summary_task['game_summary']
            with open("cache/past_game_summary.json", "w") as file:
                json.dump(game_summary, file,indent=4)
        
        real_time_insights[self.index_number] = real_time_insight
        with open("cache/real_time_analysis.json", "w") as file:
            json.dump(real_time_insights, file,indent=4)
                
        
        return real_time_insight
        
        
