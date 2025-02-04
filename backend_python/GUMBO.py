from typing import Optional, List, Dict, Any
from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from typing import Dict, List, Optional
import asyncio
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from crewai import LLM
from crewai.crews.crew_output import CrewOutput

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Position(BaseModel):
    code: str = None
    name: str = None
    type: str = None
    abbreviation: str = None

class PlayerStats(BaseModel):
    batting: Optional[Dict[str, Any]] = None
    pitching: Optional[Dict[str, Any]] = None
    fielding: Optional[Dict[str, Any]] = None

class HandSide(BaseModel):
    code: str = None
    description: str = None

class Player(BaseModel):
    id: int
    fullName: str = None
    link: str = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    primaryNumber: Optional[str] = None
    birthDate: Optional[str] = None
    currentAge: Optional[int] = None
    height: Optional[str] = None
    weight: Optional[int] = None
    active: Optional[bool] = None
    primaryPosition: Optional[Position] = None
    batSide: Optional[Dict[str, str]] = None
    pitchHand: Optional[Dict[str, str]] = None
    stats: Optional[PlayerStats] = None

# Team Related Models
class League(BaseModel):
    id: int = None
    name: str = None
    link: str = None

class Division(BaseModel):
    id: int = None
    name: str = None
    link: str = None

class Sport(BaseModel):
    id: int = None
    name: str = None
    link: str = None

class SpringLeague(BaseModel):
    id: int = None
    name: str = None
    link: str = None
    abbreviation: str = None

class SpringVenue(BaseModel):
    id: int
    link: str = None

class LeagueRecord(BaseModel):
    wins: int = None
    losses: int = None
    ties: int = None
    pct: str = None

class TeamRecord(BaseModel):
    gamesPlayed: int = None
    wildCardGamesBack: str = None
    leagueGamesBack: str = None
    springLeagueGamesBack: str = None
    sportGamesBack: str = None
    divisionGamesBack: str = None
    conferenceGamesBack: str = None
    leagueRecord: LeagueRecord = None
    records: Dict[str, Any] = {}
    divisionLeader: bool = None
    wins: int = None
    losses: int = None
    winningPercentage: str = None

class TeamVenue(BaseModel):
    id: int  = None
    name: str = None
    link: str = None

class Team(BaseModel):
    springLeague: Optional[SpringLeague] = None
    allStarStatus: str = None
    id: int = None
    name: str = None
    link: str = None
    season: int = None
    venue: TeamVenue = None
    springVenue: Optional[SpringVenue] = None
    teamCode: str = None
    fileCode: str = None
    abbreviation: str = None
    teamName: str = None
    locationName: str = None
    firstYearOfPlay: str = None
    league: League = None
    division: Division = None
    sport: Sport = None
    shortName: str = None
    record: Optional[TeamRecord] = None
    franchiseName: str = None
    clubName: str = None
    active: bool = None

# Game Status Models
class GameStatus(BaseModel):
    abstractGameState: str = None
    codedGameState: str = None
    detailedState: str = None
    statusCode: str = None
    startTimeTBD: bool = None

# Play Event Models
class PitchCoordinates(BaseModel):
    aY: float = None
    aZ: float = None
    pfxX: float = None
    pfxZ: float = None
    pX: float = None
    pZ: float = None
    vX0: float = None
    vY0: float = None
    vZ0: float = None
    x: float = None
    y: float = None
    x0: float = None
    y0: float = None
    z0: float = None
    aX: float = None

class PitchBreaks(BaseModel):
    breakAngle: float = None
    breakLength: float = None
    breakY: float = None
    breakVertical: float = None
    breakVerticalInduced: float = None
    breakHorizontal: float = None
    spinRate: int = None
    spinDirection: int = None

class PitchType(BaseModel):
    code: str = None
    description: str = None

class PitchCall(BaseModel):
    code: str = None
    description: str = None

class PitchDetails(BaseModel):
    call: PitchCall = None
    description: str = None
    code: str = None
    ballColor: str = None
    trailColor: str = None
    isInPlay: bool = None
    isStrike: bool = None
    isBall: bool = None
    type: PitchType = None
    isOut: bool = None
    hasReview: bool = None

class PitchData(BaseModel):
    startSpeed: float = None
    endSpeed: float = None
    strikeZoneTop: float = None
    strikeZoneBottom: float = None
    coordinates: PitchCoordinates = None
    breaks: PitchBreaks = None
    zone: int = None
    typeConfidence: float = None
    plateTime: float = None
    extension: float = None

class Count(BaseModel):
    balls: int = None
    strikes: int = None
    outs: int = None

class BatterPitcher(BaseModel):
    id: int = None
    fullName: str = None
    link: str = None

class Splits(BaseModel):
    batter: str = None
    pitcher: str = None
    menOnBase: str = None

class Matchup(BaseModel):
    batter: BatterPitcher = None
    batSide: HandSide = None
    pitcher: BatterPitcher = None
    pitchHand: HandSide = None
    batterHotColdZones: List[Any] = []
    pitcherHotColdZones: List[Any] = []
    splits: Splits = None

class Movement(BaseModel):
    originBase: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    outBase: Optional[str] = None
    isOut: Optional[bool] = None
    outNumber: Optional[int] = None

class RunnerDetails(BaseModel):
    event: str = None
    eventType: str = None
    movementReason: Optional[str] = None
    runner: Player = None
    responsiblePitcher: Optional[Player] = None
    isScoringEvent: bool = None
    rbi: bool = None
    earned: bool = None
    teamUnearned: bool = None
    playIndex: int = None

class Credit(BaseModel):
    player: Player = None
    position: Position = None
    credit: str = None

class Runner(BaseModel):
    movement: Movement = None
    details: RunnerDetails = None
    credits: Optional[List[Credit]] = None

class PlayEvent(BaseModel):
    details: PitchDetails = None
    count: Count = None
    pitchData: PitchData = None
    index: int = None
    playId: str = None
    pitchNumber: int = None
    startTime: str = None
    endTime: str = None
    isPitch: bool = None
    type: str = None

class PlayResult(BaseModel):
    type: str = None
    event: str = None
    eventType: str = None
    description: str = None
    rbi: int = None
    awayScore: int = None
    homeScore: int = None
    isOut: bool = None

class PlayAbout(BaseModel):
    atBatIndex: int = None
    halfInning: str = None
    isTopInning: bool = None
    inning: int = None
    startTime: str = None
    endTime: str = None
    isComplete: bool = None
    isScoringPlay: bool = None
    hasReview: bool = None
    hasOut: bool = None
    captivatingIndex: int = None

class Play(BaseModel):
    result: PlayResult = None
    about: PlayAbout = None
    count: Count = None
    matchup: Matchup = None
    pitchIndex: List[int] = []
    actionIndex: List[int] = []
    runnerIndex: List[int] = []
    runners: List[Runner] = []
    playEvents: List[PlayEvent] = []
    playEndTime: str = None
    atBatIndex: int = None

# Linescore Models
class InningLine(BaseModel):
    num: int = None
    ordinalNum: str = None
    home: Dict[str, int] = None
    away: Dict[str, int] = None

class Linescore(BaseModel):
    currentInning: int = None
    currentInningOrdinal: str = None
    inningState: str = None
    inningHalf: str = None
    isTopInning: bool = None
    scheduledInnings: int = None
    innings: List[InningLine] = []
    teams: Dict[str, Dict[str, Any]] = None
    defense: Dict[str, Any] = None
    offense: Dict[str, Any] = None

# Root GUMBO Model
class GumboData(BaseModel):
    gamePk: int = None
    link: str = None
    gameData: Dict[str, Any] = None
    liveData: Dict[str, Any] = None

# Utility Functions
class GumboUtilities:
    def __init__(self, gumbo_data: GumboData):
        self.data = gumbo_data

    def get_team_details(self, team_type: str) -> Optional[Team]:
        """Get detailed team information for either 'home' or 'away' team."""
        team_data = self.data.gameData.get("teams", {}).get(team_type, {})
        if team_data:
            return Team(**team_data)
        return None

    def get_player_details(self, player_id: int) -> Optional[Player]:
        """Get detailed player information by player ID."""
        players = self.data.gameData.get("players", {})
        player_key = f"ID{player_id}"
        if player_key in players:
            return Player(**players[player_key])
        return None
    
    def get_all_players(self) -> List[Player]:
        """Get all players in the game."""
        players = self.data.gameData.get("players", {})
        return [Player(**player) for player in players.values()]
    
    def get_current_play(self) -> Optional[Play]:
        """Get the current play details."""
        current_play = self.data.liveData.get("plays", {}).get("currentPlay")
        if current_play:
            return Play(**current_play)
        return None

    def get_all_plays(self) -> List[Play]:
        """Get all plays in the game."""
        plays = self.data.liveData.get("plays", {}).get("allPlays", [])
        return [Play(**play) for play in plays]

    def get_scoring_plays(self) -> List[Play]:
        """Get all scoring plays in the game."""
        plays = self.get_all_plays()
        return [play for play in plays if play.about.isScoringPlay]

    def get_inning_plays(self, inning: int) -> List[Play]:
        """Get all plays for a specific inning."""
        plays = self.get_all_plays()
        return [play for play in plays if play.about.inning == inning]

    def get_current_matchup(self) -> Optional[Matchup]:
        """Get current batter vs pitcher matchup."""
        current_play = self.get_current_play()
        if current_play:
            return current_play.matchup
        return None

    def get_linescore(self) -> Optional[Linescore]:
        """Get the current linescore of the game."""
        linescore_data = self.data.liveData.get("linescore", {})
        if linescore_data:
            return Linescore(**linescore_data)
        return None

    def get_pitcher_stats(self, pitcher_id: int) -> Optional[Dict[str, Any]]:
        """Get current game stats for a pitcher."""
        player = self.get_player_details(pitcher_id)
        if player and player.stats:
            return player.stats.pitching
        return None

    def get_team_batting_order(self, team_type: str) -> List[int]:
        """Get current batting order for specified team."""
        boxscore = self.data.liveData.get("boxscore", {})
        team_data = boxscore.get("teams", {}).get(team_type, {})
        return team_data.get("battingOrder", [])

    def get_current_situation(self,current_play=None) -> Dict[str, Any]:
        """Get current game situation (runners on base, outs, count, etc.)."""
        if not current_play:
            current_play = self.get_current_play()
        if not current_play:
            return {}
        
        return {
            "count": current_play.count.dict(),
            "matchup": current_play.matchup.dict(),
            "runners": [runner.dict() for runner in current_play.runners],
            "inning": current_play.about.inning,
            "halfInning": current_play.about.halfInning,
            "isTopInning": current_play.about.isTopInning
        }
