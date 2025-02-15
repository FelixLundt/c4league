"""
This script runs a single match between two agents inside a container.

(Tentative) Container directory structure:
- /opt/
    - /c4league
        - /storage/
            - ...
        - utils.py
    - /c4utils/
        - c4types.py
        - match.py
        - ...
    - /results/
        - match_id/
    - agent1.sif
    - agent2.sif
    - run_match.py

Arguments passed to the script:
- --match-id: Match id
- --starting-board: Initial board state as a flattened list of 42 integers
- --results-dir: Directory to store match results

Important:
- Get agent names from .sif files
- Mount necessary code from c4league and c4utils
- Mount results directory 
"""
import argparse
import numpy as np
from pathlib import Path
import time
import json
import traceback

from c4utils.match import play_match
from c4utils.c4_types import Player, PLAYER1, PLAYER2, BOARD_SIZE

from c4league.utils import get_tournament_player_from_sif
from c4league.storage.stats import GameStats, TIMESTAMP_FORMAT
from c4league.tournament_manager import generate_id
from c4league.params import TIMEOUT

EMPTY_BOARD = np.zeros(BOARD_SIZE, dtype=Player)

def parse_board(value):
    numbers = [int(x.strip()) for x in value.strip('[]').split(',')]
    if len(numbers) != 42:
        raise argparse.ArgumentTypeError('Board must contain exactly 42 numbers')
    return np.array(numbers).reshape(6, 7)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match-id', type=str, required=True)
    parser.add_argument('--agent-paths', type=str, nargs=2, required=True,
                       help='Paths to two agent containers')
    parser.add_argument('--starting-board', type=parse_board, required=True)
    return parser.parse_args()

def run_match(agent_paths: list[Path], starting_board: np.ndarray, results_dir: Path):
    agent_names = [str(file_path.name) for file_path in agent_paths]
    players = [get_tournament_player_from_sif(agent_name) for agent_name in agent_names]

    match_id = str(results_dir.name)

    print(f'Setting up match {match_id}...')
    tournament_id = match_id.split('_')[0]
    id_digits = (len(match_id) - 3) // 2  # underscore as well as 't' and 'm' prefixes

    # Run two normal games
    for _starting_board in [EMPTY_BOARD, starting_board]:
        print(f'Running match with starting board:\n {_starting_board}')
        for play_first in [1, -1]:
            _agent_paths = agent_paths[::play_first]
            _players = players[::play_first]
            print(f'Playing first: {_players[0]}')
            winner, moves, error = play_match(_agent_paths[0], _agent_paths[1], move_timeout=0.02*TIMEOUT, initial_board=_starting_board)

            print(f'Winner: {winner}, Moves: {[int(move) for move in moves]}, Error: {error}')
            
            game_id = f'{match_id}_g{generate_id()}'

            if winner == PLAYER1:
                winning_player = _players[0]
            elif winner == PLAYER2:
                winning_player = _players[1]
            else:
                winning_player = None
            
            if error is None:
                reason = 'Connect 4' if winning_player is not None else 'Draw'
                _traceback = None
            else:
                _traceback = ''.join(traceback.format_exception(error))
                if 'AgentRuntimeError' in _traceback:
                    reason = 'AgentRuntimeError (crash or timeout)'
                elif 'Invalid move:' in _traceback:
                    reason = 'Invalid move'
                else:
                    reason = 'Unknown Error'
            print(f'Writing results to {results_dir}/{game_id}.json')
            game_stats = GameStats(
                game_id=game_id,
                match_id=match_id,
                tournament_id=tournament_id,
                timestamp=time.strftime(TIMESTAMP_FORMAT),
                player1=_players[0],
                player2=_players[1],
                initial_board=_starting_board,
                moves=moves,
                winner=winning_player,
                reason=reason,
                traceback=_traceback
            )
            with open(f'{str(results_dir)}/{game_id}.json', 'w', encoding='utf-8') as f:
                json.dump(game_stats.generate_json(), f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    args = parse_args()
    agent_paths = [Path(agent_path) for agent_path in args.agent_paths]
    run_match(agent_paths, args.starting_board, args.results_dir)
