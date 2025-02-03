"""Storage operations for individual game results."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import numpy as np
from .cloud_storage import TournamentStorage

TeamStats = Dict[str, Any]
GameStats = Dict[str, Any]

class GameStorage:
    def __init__(self, storage: TournamentStorage):
        self.storage = storage
        
    def save_game(self, *, 
                 tournament_path: str,
                 team1: TeamStats,
                 team2: TeamStats,
                 game_number: int,
                 game_stats: GameStats,
                 initial_board: Optional[List[List[int]]] = None,
                 runtime_stats: Optional[Dict[str, Any]] = None) -> str:
        """Save a game result.
        
        Args:
            tournament_path: Base path for tournament
            team1: First team ID
            team2: Second team ID
            game_number: Game number in mini-match (1-4)
            moves: List of column numbers played
            winner: Winning team ID or "draw"
            reason: Win reason (four_in_row, timeout, error, etc.)
            initial_board: Starting board state (None for empty board)
            runtime_stats: Optional performance statistics
            team1_submission: Optional submission ID for team1
            team2_submission: Optional submission ID for team2
            
        Returns:
            Path to saved game file
        """
        game_data = {
            "game_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "player1": {
                "group_id": team1,
                "submission_id": team1_submission,
                "color": "red" if game_number % 2 == 1 else "yellow"
            },
            "player2": {
                "group_id": team2,
                "submission_id": team2_submission,
                "color": "yellow" if game_number % 2 == 1 else "red"
            },
            "initial_board": initial_board,
            "moves": moves,
            "winner": winner,
            "reason": reason,
            "runtime_stats": runtime_stats or {}
        }
        
        # Save to GCS
        mini_match_path = self.storage.get_mini_match_path(tournament_path, team1, team2)
        game_path = f"{mini_match_path}/game{game_number}.json"
        self.storage.save_json(game_path, game_data)
        
        return game_path
        
    def save_mini_match_summary(self,
                              tournament_path: str,
                              team1: str,
                              team2: str,
                              game_paths: List[str],
                              points: Dict[str, float],
                              stats: Dict[str, Any]) -> str:
        """Save mini-match summary.
        
        Args:
            tournament_path: Base path for tournament
            team1: First team ID
            team2: Second team ID
            game_paths: Paths to individual game results
            points: Points earned by each team
            stats: Match statistics
            
        Returns:
            Path to saved summary file
        """
        summary_data = {
            "match_id": str(uuid.uuid4()),
            "teams": [team1, team2],
            "games": game_paths,
            "points": points,
            "stats": stats
        }
        
        # Save to GCS
        mini_match_path = self.storage.get_mini_match_path(tournament_path, team1, team2)
        summary_path = f"{mini_match_path}/summary.json"
        self.storage.save_json(summary_path, summary_data)
        
        return summary_path
        
    def get_team_games(self, group_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent games for a team.
        
        Args:
            group_id: Team identifier
            limit: Maximum number of games to return
            
        Returns:
            List of game results, newest first
        """
        # List all tournament directories
        tournaments = sorted(
            self.storage.list_files("tournament_results/matches/"),
            reverse=True
        )
        
        games = []
        for tournament in tournaments:
            # List mini-matches involving this team
            matches = self.storage.list_files(f"{tournament}/mini_matches/")
            team_matches = [m for m in matches if group_id in m]
            
            for match in team_matches:
                # Load all games from this mini-match
                for i in range(1, 5):
                    game_path = f"{match}/game{i}.json"
                    try:
                        game = self.storage.load_json(game_path)
                        games.append(game)
                        if len(games) >= limit:
                            return games
                    except:
                        continue
                        
        return games 