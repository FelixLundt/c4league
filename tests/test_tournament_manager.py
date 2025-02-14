import pytest
from c4league.tournament_manager import TournamentManager
from c4league.utils import TournamentPlayer

def test_tournament_manager():
    manager = TournamentManager()
    print(manager.participants)
    print(manager.tournament_id)
    print(manager.matches)
    print(manager.random_starting_board)


    manager._create_job_script(list(manager.matches.items())[0], starting_board=manager.random_starting_board)
    raise ValueError('test')
