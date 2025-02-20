'''
Contains classes storing and processing game, match, and tournament statistics.
'''

import numpy as np
from dataclasses import dataclass
import time
from c4utils.c4_types import Board, Move, Player

from ..utils import TournamentPlayer, tournament_player_from_dict, tournament_player_from_str
from ..params import MINI_MATCH_GAMES

TIMESTAMP_FORMAT = '%Y-%m-%d-%H:%M:%S'

@dataclass
class GameStats:
    game_id: str
    match_id: str
    tournament_id: str
    timestamp: str
    player1: TournamentPlayer
    player2: TournamentPlayer
    initial_board: Board
    moves: list[Move]
    winner: TournamentPlayer | None
    reason: str
    traceback: str | None

    def generate_json(self) -> dict:
        return {
            'game_id': self.game_id,
            'match_id': self.match_id,
            'tournament_id': self.tournament_id,
            'timestamp': self.timestamp,
            'player1': str(self.player1),
            'player2': str(self.player2),
            'initial_board': self.initial_board.tolist(),
            'moves': [int(move) for move in self.moves],
            'winner': str(self.winner) if self.winner is not None else None,
            'reason': self.reason,
            'traceback': self.traceback,
        }

def game_stats_from_json(json_data: dict) -> 'GameStats':
    raw_data = json_data
    raw_data['initial_board'] = np.array(json_data['initial_board'], dtype=Player)
    raw_data['moves'] = [Move(move) for move in json_data['moves']]
    raw_data['player1'] = tournament_player_from_str(json_data['player1'])
    raw_data['player2'] = tournament_player_from_str(json_data['player2'])
    raw_data['winner'] = tournament_player_from_str(json_data['winner']) if json_data['winner'] is not None else None
    return GameStats(**raw_data)

@dataclass
class MatchStats:
    match_id: str
    game_ids: list[str]
    tournament_id: str
    timestamp: str
    players: list[TournamentPlayer]
    result: dict[TournamentPlayer, float]

    def generate_json(self) -> dict:
        return {
            'match_id': self.match_id,
            'game_ids': self.game_ids,
            'tournament_id': self.tournament_id,
            'timestamp': self.timestamp,
            'players': [str(player) for player in self.players],
            'result': {str(player): score for player, score in self.result.items()}
        }
    
def match_stats_from_json(json_data: dict) -> 'MatchStats':
    raw_data = json_data.copy()
    raw_data['players'] = [tournament_player_from_str(player) for player in json_data['players']]
    raw_data['result'] = {tournament_player_from_str(player): score for player, score in json_data['result'].items()}
    return MatchStats(**raw_data)

@dataclass
class TournamentStats:
    tournament_id: str
    timestamp: str
    match_ids: list[str]
    players: list[TournamentPlayer]
    table: list[tuple[TournamentPlayer, float]]

    def generate_json(self) -> dict:
        return {
            'tournament_id': self.tournament_id,
            'timestamp': self.timestamp,
            'match_ids': self.match_ids,
            'players': [str(player) for player in self.players],
            'table': [(str(player), score) for player, score in self.table]
        }

def tournament_stats_from_json(json_data: dict) -> 'TournamentStats':
    raw_data = json_data.copy()
    raw_data['players'] = [tournament_player_from_str(player) for player in json_data['players']]
    raw_data['table'] = [(tournament_player_from_str(player), score) for player, score in json_data['table']]
    return TournamentStats(**raw_data)

def generate_match_stats_from_game_stats(games: list[GameStats]) -> MatchStats:
    games_ok = check_games(games)
    if not games_ok:
        raise ValueError("Invalid games provided")
    game_ids = [game.game_id for game in games]
    match_timestamp = time.strftime(TIMESTAMP_FORMAT, min(time.strptime(game.timestamp, TIMESTAMP_FORMAT) for game in games))

    # Get all players in the match
    players = [games[0].player1, games[0].player2]
    
    # Get the result of the match
    result = {}
    for player in players:
        result[player] = sum(game.winner == player for game in games if game.winner is not None) + 0.5 * sum(game.winner is None for game in games)
    
    return MatchStats(
        match_id=games[0].match_id,
        game_ids=game_ids,
        tournament_id=games[0].tournament_id,
        timestamp=match_timestamp,
        players=players,
        result=result
    )

def check_games(games: list[GameStats]) -> bool:
    try:
        assert len(games) > 0, "No games provided"
        assert len(games) == MINI_MATCH_GAMES, f"Expected {MINI_MATCH_GAMES} games per mini-match"
        assert np.unique(np.array([game.game_id for game in games])).size == len(games), "Expected unique game ids"
        p1_players = set([game.player1 for game in games])
        p2_players = set([game.player2 for game in games])
        unique_players = list(set(p1_players) | set(p2_players))
        assert len(unique_players) == 2, "Expected two players per match"
        assert len(p1_players) == 2, "Expected each player to play first twice"
        assert len(p2_players) == 2, "Expected each player to play second twice"
        for game in games:
            assert game.player1 != game.player2, "Player 1 and player 2 are the same"
        assert all(game.match_id == games[0].match_id for game in games), "Expected all games to be in the same match"
        assert all(game.tournament_id == games[0].tournament_id for game in games), "Expected all games to be in the same tournament"
    except AssertionError as e:
        print(f"Invalid games provided: {e}")
        return False
    return True

def generate_tournament_stats_from_match_stats(matches: list[MatchStats]) -> TournamentStats:
    matches_ok = check_matches(matches)
    if not matches_ok:
        raise ValueError("Invalid matches provided")
    match_ids = [match.match_id for match in matches]
    tournament_timestamp = time.strftime(TIMESTAMP_FORMAT, min(time.strptime(match.timestamp, TIMESTAMP_FORMAT) for match in matches))
    
    players = list(set(player for match in matches for player in match.players))

    scores = generate_tournament_scores(matches)
    table = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return TournamentStats(
        tournament_id=matches[0].tournament_id,
        timestamp=tournament_timestamp,
        match_ids=match_ids,
        players=players,
        table=table
    )
 
def check_matches(matches: list[MatchStats]) -> bool:
    try:
        assert len(matches) > 0, "No matches provided"
        assert all(match.tournament_id == matches[0].tournament_id for match in matches), "Expected all matches to be in the same tournament"
    except AssertionError as e:
        print(f"Invalid matches provided: {e}")
        return False
    return True

def get_players_from_matches(matches: list[MatchStats]) -> list[TournamentPlayer]:
    return list(set(player for match in matches for player in match.players))

def generate_tournament_scores(matches: list[MatchStats]) -> dict[TournamentPlayer, float]:
    players = get_players_from_matches(matches)
    scores = {player: 0. for player in players}
    for match in matches:
        for player, score in match.result.items():
            scores[player] += score
    return scores
