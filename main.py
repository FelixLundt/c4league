import os
import json
from c4league.storage.cloud_storage import get_submitted_agents, download_agent
from c4league.container_utils import get_containerized_agents, get_new_agents, get_updated_agents, \
    TournamentPlayer, containerize_agents
from google.cloud import storage
import numpy as np
import subprocess
if __name__ == '__main__':
    # print(get_submitted_agents())
    # print(get_containerized_agents())
    # submitted_agents = [TournamentPlayer(**agent) for agent in get_submitted_agents()]
    # new_agents = get_new_agents(submitted_agents, get_containerized_agents())
    # updated_agents = get_updated_agents(submitted_agents, get_containerized_agents())
    # print('New agents: ', new_agents)
    # print('Updated agents: ', updated_agents)
    # containerize_agents(new_agents) 
    # from c4utils.match import play_match
    # from c4utils.agent_sandbox.agent_runner import SandboxedAgent, get_generate_move_func_from_container
    # from pathlib import Path
    
    # player1 = Path('/c4league/agents/team1_cool-agent_7.sif')
    # player2 = Path('/c4league/agents/home-team_random-agent_1.sif')
    # player3 = Path('/c4league/agents/home-team_silly-agent_1.sif')
    
    # try:
    #     winner, moves, error = play_match(player2, player2)
    #     print(f'Winner: {winner}, Moves: {moves}, Error: {error}')
    # except Exception as e:
    #     print(f"Error running agent: {str(e)}")
    #     import traceback
    #     traceback.print_exc()

    from pathlib import Path
    from run_match import run_match, EMPTY_BOARD

    starting_board = EMPTY_BOARD.copy()
    starting_board[0, 0] = 1
    starting_board[0, 1] = 2
    starting_board[0, 4] = 1
    starting_board[0, 6] = 2
    run_match(agent_paths=[Path('/c4league/agents/team1_cool-agent_7.sif'), Path('/c4league/agents/team1_cool-agent_7.sif')],
              starting_board=starting_board,
              results_dir=Path('/c4league/results/test/tabcde_m12345'))

    # from c4league.tournament_manager import TournamentManager
    # tournament_manager = TournamentManager()
    # print(tournament_manager.tournament_id)
    # print(tournament_manager.c4league_package_root)
    # print(tournament_manager.results_dir)
    # print(tournament_manager.logs_dir)
    # print(tournament_manager.job_script_path)
    # print(tournament_manager.tournament_config_path)
    # print(tournament_manager.participants)
    # print(tournament_manager.random_starting_board)
    # tournament_manager._create_job_script()
