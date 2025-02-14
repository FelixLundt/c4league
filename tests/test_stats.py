import pytest
import numpy as np
from c4league.utils import TournamentPlayer, tournament_player_from_dict
from c4league.storage.stats import GameStats, MatchStats, TournamentStats, generate_match_stats_from_game_stats, \
    generate_tournament_stats_from_match_stats
from c4utils.c4_types import Board, Move, Player

@pytest.fixture
def players():
    players = [
        {'team_name': 'Team 1', 'agent_name': 'agent1', 'version': '1'},
        {'team_name': 'Team 2', 'agent_name': 'agent2', 'version': '2'},
        {'team_name': 'Team 3', 'agent_name': 'agent3', 'version': '3'}
    ]
    return [tournament_player_from_dict(player) for player in players]

@pytest.fixture
def empty_board():
    return np.zeros((6, 7), dtype=Player)


@pytest.fixture
def game_stats_1(players, empty_board):
    return GameStats(
        game_id="1",
        player1=players[0],
        player2=players[1],
        winner=players[0],
        timestamp="2024-01-01",
        match_id="2",
        tournament_id="12",
        initial_board=empty_board,
        moves=[Move(0), Move(5), Move(3)],
        reason="Connect 4",
        traceback=None
    )

@pytest.fixture
def game_stats_2(players, empty_board):
    return GameStats(
        game_id="2",
        player1=players[1],
        player2=players[0],
        winner=players[1],
        timestamp="2024-01-21",
        match_id="2",
        tournament_id="12",
        initial_board=empty_board,
        moves=[Move(6)],
        reason="Connect 4",
        traceback=None
    )

@pytest.fixture
def game_stats_3(players, empty_board):
    return GameStats(
        game_id="3",
        player1=players[0],
        player2=players[1],
        winner=players[0],
        timestamp="2024-04-01",
        match_id="2",
        tournament_id="12",
        initial_board=empty_board,
        moves=[Move(0), Move(1)],
        reason="timeout",
        traceback=None
    )

@pytest.fixture
def game_stats_4(players, empty_board):
    return GameStats(
        game_id="4",
        player1=players[1],
        player2=players[0],
        winner=None,
        timestamp="2022-01-01",
        match_id="2",
        tournament_id="12",
        initial_board=empty_board,
        moves=[Move(0), Move(4)],
        reason="Draw",
        traceback=None
    )    

@pytest.fixture
def game_stats_dict(game_stats_1):
    dicct = {
        'game_id': '1',
        'match_id': '2',
        'tournament_id': '12',
        'timestamp': '2024-01-01',
        'player1': game_stats_1.player1.get_dict(),
        'player2': game_stats_1.player2.get_dict(),
        'initial_board': game_stats_1.initial_board.tolist(),
        'moves': [int(move) for move in game_stats_1.moves],
        'winner': game_stats_1.winner.get_dict(),
        'reason': 'Connect 4',
        'traceback': None
    }
    return dicct


@pytest.fixture
def match_stats(players):
    match1 = MatchStats(
        match_id="1",
        tournament_id="12",
        timestamp="2024-02-01",
        players=[players[0], players[1]],
        result={players[0]: 2.5, players[1]: 1.5},
        game_ids=["1", "2", "3", "4"]
    )
    match2 = MatchStats(
        match_id="2",
        tournament_id="12",
        timestamp="2024-01-02",
        players=[players[0], players[2]],
        result={players[0]: 1., players[2]: 3.},
        game_ids=["5", "6", "7", "8"]
        )
    return [match1, match2]


def test_game_stat_json_conversion(game_stats_1, game_stats_dict):
    game_stat_json = game_stats_1.generate_json()
    assert game_stat_json == game_stats_dict

def test_match_stats_from_game_stats(game_stats_1, game_stats_2, game_stats_3, game_stats_4):
    games_for_match = [game_stats_1, game_stats_2, game_stats_3, game_stats_4]
    match_stats = generate_match_stats_from_game_stats(games_for_match, '2024-01-01')
    assert match_stats.match_id == games_for_match[-1].match_id
    assert match_stats.tournament_id == games_for_match[-2].tournament_id
    assert match_stats.timestamp == '2024-01-01'
    assert match_stats.result == {game_stats_1.player1: 2.5, game_stats_1.player2: 1.5}

def test_tournament_stats_from_match_stats(match_stats):
    tournament_stats = generate_tournament_stats_from_match_stats(match_stats, '2024-01-01')
    assert tournament_stats.tournament_id == match_stats[0].tournament_id
    assert tournament_stats.timestamp == '2024-01-01'
    assert tournament_stats.match_ids == ['1', '2']
    assert set(tournament_stats.players) == set([match_stats[0].players[0], match_stats[0].players[1], match_stats[1].players[1]])

