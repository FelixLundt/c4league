"""
This script is used to run a tournament.
"""
from pathlib import Path
from c4league.tournament_manager import TournamentManager
from c4league.storage.cloud_storage import get_submitted_agents
from c4league.utils import TournamentPlayer, get_new_agents, get_updated_agents
from c4league.container_utils import containerize_agents, get_containerized_agents


def run_tournament():
    # Make sure everything is set up correctly
    print('Checking if everything is set up correctly...')
    # Check if the directory containing this script contains a .env file
    if not Path('.env').exists():
        print('Error: .env file not found in the directory containing this script.')
        exit(1)
    # Check if the directory contains a run_match.sif file
    if not Path('run_match.sif').exists():
        print('Error: run_match.sif file not found in the directory containing this script.')
        exit(1)

    # Check if the directory contains a c4league-c67e7716e473.json file
    if not Path('c4league-c67e7716e473.json').exists():
        print('Error: c4league-c67e7716e473.json file not found in the directory containing this script.')
        exit(1)

    # Check if directory contains /agents directory
    Path('agents').mkdir(parents=True, exist_ok=True)

    # Get participants
    print('Gathering tournament participants...')

    print('Getting submitted agents from cloud storage...')
    submitted_agents = [TournamentPlayer(**agent) for agent in get_submitted_agents()]
    print('Checking for new agents...')
    new_agents = get_new_agents(submitted_agents, get_containerized_agents())
    print('Checking for updated agents...')
    updated_agents = get_updated_agents(submitted_agents, get_containerized_agents())
    print(f'Found {len(new_agents)} new agents and {len(updated_agents)} updated agents.')

    # Build new/updated agents
    print('Building new/updated agents...')
    try:
        containerize_agents(new_agents + updated_agents)
    except Exception as e:
        print(f'Error building agents: {e}')
        exit(1)

    # Set up tournament manager
    # Needs to:
    # - Initialize tournament (get new id, localize results dir, ..)
    # - Generate pairings (sets of TournamentPlayers/paths to agents with match ids)
    # - Submit all matches
    # - Wait for all matches to complete
    # - Process results

    # Each match is a Slurm job
    # - We need to set up a script to run the match
    # - The match needs to run several games and store the results (game results, match results)

    # Run tournament
    print('Running tournament...')
    manager = TournamentManager()

    manager.run_tournament()

if __name__ == "__main__":
    run_tournament()
