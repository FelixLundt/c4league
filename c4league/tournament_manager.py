import os
import string
import random
import subprocess
from pathlib import Path
import time
from dotenv import load_dotenv
import itertools
import numpy as np
import json
from c4utils.c4_types import Move, Player, NO_PLAYER
from c4utils.match import GameState

from c4league.container_utils import get_containerized_agents, TournamentPlayer, \
    get_sif_file_path_from_tournament_player, get_sif_file_name_from_tournament_player
from c4league.utils import generate_id
from c4league.params import TIMEOUT
from c4league.storage.stats import GameStats, MatchStats, TournamentStats, \
    game_stats_from_json, match_stats_from_json, tournament_stats_from_json, \
    generate_match_stats_from_game_stats, generate_tournament_stats_from_match_stats

load_dotenv()

MatchData = dict[str, tuple[TournamentPlayer, TournamentPlayer]]
Match = tuple[str, tuple[TournamentPlayer, TournamentPlayer]]

MATCH_CONTAINER_DIR = Path(os.getenv("MATCH_CONTAINER_DIR", "/opt"))

class TournamentManager:
    """
    Manages a tournament.
    """

    id_digits: int = 5
    starting_moves_truncate_prob: float = 0.2   # geometric distribution, mean 5
    starting_moves_truncate_max: int = 10
    root_dir = os.getenv("C4LEAGUE_ROOT_DIR")
    if root_dir is None:
        raise ValueError("C4LEAGUE_ROOT_DIR not set")
    c4league_package_root: Path = Path(root_dir) / 'c4league/'
    move_timeout: float = TIMEOUT

    def __init__(self):
        print('Initializing tournament manager...')
        self.agent_dir = Path(os.getenv("AGENT_CONTAINER_DIRECTORY", "/opt"))
        self.gcs_bucket = os.getenv("GCS_BUCKET_NAME")
        self.jobs: dict[str, dict] = {}

        self.tournament_id = f't{generate_id()}'
        print(f'Assigned tournament id: {self.tournament_id}')

        self.results_dir = Path(os.getenv("TOURNAMENT_RESULTS_DIRECTORY")) / f'{self.tournament_id}/'
        print(f'Creating results directory: {self.results_dir}')
        self.results_dir.mkdir(parents=True, exist_ok=False)

        self.logs_dir = Path(os.getenv("TOURNAMENT_LOGS_DIRECTORY")) / f'{self.tournament_id}'
        print(f'Creating logs directory: {self.logs_dir}')
        self.logs_dir.mkdir(parents=True, exist_ok=False)

        print('Getting participants...')
        self.participants = get_containerized_agents()
        print(f'Tournament will have {len(self.participants)} participants.')

        print('Generating random starting board...')
        self.random_starting_board = self._generate_starting_board()

        print('Creating matches...')
        self.matches = self._create_matches(self.participants)
        print(f'Created {len(self.matches)} matches')

        self.tournament_config_path = Path(os.getenv("TOURNAMENT_CONFIG_DIRECTORY", "/opt/match_results")) / f'{self.tournament_id}.txt'
        print(f'Creating tournament config file: {self.tournament_config_path}')
        self.tournament_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.tournament_config_path.touch()
        self._create_tournament_config_file()

        self.job_script_path = Path(os.getenv("TOURNAMENT_JOB_SCRIPT_DIRECTORY")) / f'{self.tournament_id}.sh'
  

        


        

    def run_tournament(self):
        """Run the tournament"""
        
        # Submit all matches
        tournament_job_id = self.submit_all_matches()

        # Wait for all matches to complete
        self.wait_for_all_jobs(tournament_job_id)

        # Process results
        print('All matches completed.')
        print('Processing results...')
        self.process_results()

        print('Results processed.')
        print('Tournament completed.')


    def _generate_starting_board(self) -> np.ndarray:
        """Generate a random starting board"""
        while True:
            game_state = GameState()
            truncate = False  # Initialize truncate flag
            while not truncate:
                move = np.random.choice(np.flatnonzero(game_state.board[-1, :] == NO_PLAYER))
                game_state.update(Move(move))
                
                if game_state.is_game_over:
                    break
                    
                truncate = (
                    np.random.rand() < self.starting_moves_truncate_prob or 
                    np.count_nonzero(game_state.board == NO_PLAYER) < game_state.board.size - self.starting_moves_truncate_max
                )
            else:
                return game_state.board
    
    def _create_matches(self, participants: list[TournamentPlayer]) -> MatchData:
        """Create matches from participants"""
        pairings = list(itertools.combinations(participants, 2))
        match_ids = [f'{self.tournament_id}_m{generate_id()}' 
                     for _ in range(len(pairings))]
        for match_id in match_ids:
            self._get_match_path(match_id).mkdir(parents=True, exist_ok=True)

        return {
            match_id: (pairing[0], pairing[1])
            for pairing, match_id in zip(pairings, match_ids)
        }

    def _get_match_path(self, match_id: str) -> Path:
        """Get the path to a match"""
        return self.results_dir / f'{match_id}'
    
    def _create_tournament_config_file(self):
        """Create a tournament config file"""
        with open(self.tournament_config_path, 'w') as f:
            for match_id, (player1, player2) in self.matches.items():
                f.write(f'{match_id} {get_sif_file_path_from_tournament_player(player1)} {get_sif_file_path_from_tournament_player(player2)}\n')
        print(f'Tournament config file created at {self.tournament_config_path}')
       
    def submit_all_matches(self) -> str:
        """Submit a single match as a Slurm job"""
        job_script = self._create_job_script()
        if not self._is_run_match_container_built():
            raise ValueError('Run match container not built')
        
        # Submit the job
        result = subprocess.run(
            ["sbatch", job_script], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        # Extract job ID from sbatch output
        job_id = result.stdout.strip().split()[-1]
        
        return job_id
    
    def check_job_progress(self, tournament_job_id: str) -> dict[str, int]:
        """Check if all array tasks have completed"""
        
        result = subprocess.run(
            ["sacct", "-j", tournament_job_id, "--format=JobID,State", "--parsable2"],
            capture_output=True,
            text=True
        )
        
        # Parse output to check array task status
        statuses = []
        for line in result.stdout.splitlines()[1:]:  # Skip header
            array_id, state = line.split('|')
            statuses.append(state)
            
        progress = {
            "completed": sum(state == "COMPLETED" for state in statuses),
            "failed": sum(state == "FAILED" for state in statuses),
            "cancelled": sum(state == "CANCELLED" for state in statuses),
            "pending": sum(state == "PENDING" for state in statuses),
            "running": sum(state == "RUNNING" for state in statuses)
        }
        return progress
    
    def wait_for_all_jobs(self, tournament_job_id: str, check_interval: int = 30) -> dict[str, dict]:
        """Wait for all jobs to complete"""
        while True:
            progress = self.check_job_progress(tournament_job_id)
            print(f"Progress:")
            for key, value in progress.items():
                print(f"{key}: {value}")
            if progress["running"] + progress["pending"] == 0:
                print(f"All matches completed.")
                break
            time.sleep(check_interval)
            
        return self.jobs
    
    def _create_job_script(self) -> str:
        """Create a Slurm job script template, to be submitted as an array job"""
        print(f'Creating job script: {self.job_script_path}')
        self.job_script_path.parent.mkdir(parents=True, exist_ok=True)
        self.job_script_path.touch() 
        
        # Format starting board as a bracketed list
        board_list = self.random_starting_board.flatten().tolist()
        formatted_starting_board = f"'[{','.join(map(str, board_list))}]'"
        
        script_content = f"""#!/bin/bash
#SBATCH --job-name=tournament_{self.tournament_id}
#SBATCH --output={self.logs_dir}/{self.tournament_id}_%a.out
#SBATCH --error={self.logs_dir}/{self.tournament_id}_%a.err
#SBATCH --array=1-{len(self.matches)}
#SBATCH --partition=cpu-5h
#SBATCH --ntasks=1
#SBATCH --time=0:22:00
#SBATCH --mem-per-cpu=20G
#SBATCH --cpus-per-task=3

# Debug info
echo "Debug information:"
echo "Current directory: $(pwd)"
echo "Apptainer version: $(apptainer --version)"
echo "Python version: $(python3 --version)"
echo "Environment variables:"
env | sort

# Read match parameters from config file
match_config=$(sed -n "$SLURM_ARRAY_TASK_ID"p {self.tournament_config_path})
match_id=$(echo $match_config | cut -d' ' -f1)
agent1_path=$(echo $match_config | cut -d' ' -f2)
agent2_path=$(echo $match_config | cut -d' ' -f3)
agent1_name=$(basename $agent1_path)
agent2_name=$(basename $agent2_path)

echo "Match parameters:"
echo "Match ID: $match_id"
echo "Agent 1: $agent1_path -> $agent1_name"
echo "Agent 2: $agent2_path -> $agent2_name"

# Mount only existing paths
apptainer exec \\
    --bind {str(self.c4league_package_root)}:/opt/c4league \\
    --bind {os.getenv("C4UTILS_DIR")}:/opt/c4utils \\
    --bind {os.getenv("C4LEAGUE_ROOT_DIR")}/run_match.py:/opt/run_match.py \\
    --bind {str(self.results_dir)}/$match_id:/opt/match_results/ \\
    --bind $agent1_path:/opt/$agent1_name \\
    --bind $agent2_path:/opt/$agent2_name \\
    --bind /usr/bin/apptainer:/usr/bin/apptainer \\
    --bind /usr/bin/unsquashfs:/usr/bin/unsquashfs \\
    --bind /usr/bin/fusermount:/usr/bin/fusermount \\
    --bind /usr/bin/squashfuse:/usr/bin/squashfuse \\
    --bind /usr/bin/fuse2fs:/usr/bin/fuse2fs \\
    --bind /usr/bin/fusermount3:/usr/bin/fusermount3 \\
    --bind /etc/apptainer:/etc/apptainer \\
    --bind /usr/libexec/apptainer:/usr/libexec/apptainer \\
    --bind /usr/libexec/apptainer/bin/starter:/usr/libexec/apptainer/bin/starter \\
    --bind /usr/libexec/apptainer/bin/squashfuse_ll:/usr/libexec/apptainer/bin/squashfuse_ll \\
    --bind /lib/x86_64-linux-gnu/libseccomp.so.2:/lib/x86_64-linux-gnu/libseccomp.so.2 \\
    --bind /lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu \\
    --bind /usr/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu \\
    --bind /etc/passwd:/etc/passwd \\
    --bind /etc/group:/etc/group \\
    --bind /proc:/proc \\
    --bind /sys:/sys \\
    --bind /dev:/dev \\
    --no-home \\
    --fakeroot \\
    --writable-tmpfs \\
    --net \\
    run_match.sif \\
    python3 /opt/run_match.py \\
        --agent-paths "/opt/$agent1_name" "/opt/$agent2_name" \\
        --starting-board {formatted_starting_board} \\
        --results-dir /opt/match_results/
"""
        print('Writing job script to', self.job_script_path)
        self.job_script_path.write_text(script_content)
        return str(self.job_script_path)

    def _is_run_match_container_built(self) -> bool:
        """Check if the run_match container is built"""
        c4league_root_dir = os.getenv("C4LEAGUE_ROOT_DIR")
        if c4league_root_dir is None:
            raise ValueError('C4LEAGUE_ROOT_DIR not set')
        return os.path.exists(os.path.join(c4league_root_dir, 'run_match.sif'))

    def process_results(self):
        """Process the results of the tournament"""
        match_stats = []
        for match_id, (player1, player2) in self.matches.items():
            match_results_dir = self._get_match_path(match_id)
            print(f'Processing results for match {match_id}...')
            # Check for game result files
            game_result_files = [_file for _file in match_results_dir.iterdir() if _file.name.endswith('.json') and _file.name[-11:9] == '_g']
            if len(game_result_files) != 4:
                print(f'Not all game result files found for match {match_id}')
                continue
            else:
                print(f'Found all {len(game_result_files)} game result files for match {match_id}')
                for game_result_file in game_result_files:
                    game_stats = []
                    print(f'Processing game result file {game_result_file}')
                    with open(game_result_file, 'r') as f:
                        game_stats.append(game_stats_from_json(json.load(f)))
                print('Generating match stats...')
                _match_stats = generate_match_stats_from_game_stats(game_stats)
                with open(match_results_dir / f'{match_id}.json', 'w') as f:
                    json.dump(_match_stats.generate_json(), f, ensure_ascii=False, indent=4)
                match_stats.append(_match_stats)
        print('Generating tournament stats...')
        tournament_stats = generate_tournament_stats_from_match_stats(match_stats)
        with open(self.results_dir / f'{self.tournament_id}.json', 'w') as f:
            json.dump(tournament_stats.generate_json(), f, ensure_ascii=False, indent=4)
        print('Generating stats completed.')
