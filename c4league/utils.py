from dataclasses import dataclass
import os
import shutil
import tempfile
from dotenv import load_dotenv
from c4league.storage.cloud_storage import download_agent
import subprocess
import time

load_dotenv()

@dataclass
class TournamentPlayer:
    team_name: str
    agent_name: str
    version: str
    
    def get_dict(self) -> dict:
        return {
            'team_name': self.team_name,
            'agent_name': self.agent_name,
            'version': self.version
        }
    
    def __eq__(self, other):
        return self.team_name == other.team_name and self.agent_name == other.agent_name and self.version == other.version
    
    def __hash__(self):
        return hash(self.team_name + self.agent_name + self.version)
    
def tournament_player_from_dict(param_dict: dict) -> 'TournamentPlayer':
    return TournamentPlayer(
        team_name=param_dict['team_name'],
        agent_name=param_dict['agent_name'],
        version=param_dict['version']
    )

def get_containerized_agents() -> list[TournamentPlayer]:
    containerized_agents = []
    for file in os.listdir(os.getenv("AGENT_CONTAINER_DIRECTORY")):
        if file.endswith(".sif"):
            containerized_agents.append(get_tournament_player_from_sif(file))
        else:
            print(f"Warning: File {file} is not a .sif file")
    return containerized_agents
                            
def get_tournament_player_from_sif(file: str) -> TournamentPlayer:
    team_name, agent_name, version = file.rstrip(".sif").split("_")
    return TournamentPlayer(team_name, agent_name, version)

def get_sif_file_name_from_tournament_player(tournament_player: TournamentPlayer) -> str:
    return f"{tournament_player.team_name}_{tournament_player.agent_name}_{tournament_player.version}.sif"

def get_sif_file_path_from_tournament_player(tournament_player: TournamentPlayer) -> str:
    return os.path.join(os.getenv("AGENT_CONTAINER_DIRECTORY"), get_sif_file_name_from_tournament_player(tournament_player))

def _get_diff_agents(submitted_agents: list[TournamentPlayer], containerized_agents: list[TournamentPlayer]) -> list[tuple[TournamentPlayer, str]]:
    diff_agents = []
    for submitted_agent in submitted_agents:
        if submitted_agent not in containerized_agents:
            team_agents = [agent for agent in containerized_agents if agent.team_name == submitted_agent.team_name]
            if len(team_agents) == 0:
                diff_agents.append((submitted_agent, 'team_name'))
            else:
                previous_agent = [agent for agent in team_agents if agent.agent_name == submitted_agent.agent_name]
                if len(previous_agent) == 0:
                    diff_agents.append((submitted_agent, 'agent_name'))
                else:
                    diff_agents.append((submitted_agent, 'version'))
    return diff_agents

def get_updated_agents(submitted_agents: list[TournamentPlayer], containerized_agents: list[TournamentPlayer]) -> list[TournamentPlayer]:
    diff_agents = _get_diff_agents(submitted_agents, containerized_agents)
    return [agent[0] for agent in diff_agents if agent[1] == 'version']


def get_new_agents(submitted_agents: list[TournamentPlayer], containerized_agents: list[TournamentPlayer]) -> list[TournamentPlayer]:
    diff_agents = _get_diff_agents(submitted_agents, containerized_agents)
    return [agent[0] for agent in diff_agents if agent[1] != 'version']

def containerize_agents(agents: list[TournamentPlayer]) -> None:
    for agent in agents:
        try:
            temp_dir = tempfile.mkdtemp()
            print(f'Downloading agent {agent.team_name} {agent.agent_name} {agent.version} to {temp_dir}')
            download_agent(agent.get_dict(), temp_dir)
            
            # Unzip agent code and clean up
            print(f'Files in {temp_dir}: {os.listdir(temp_dir)}')
            filename = os.listdir(temp_dir)[0]
            print(f'Found: {filename}. Unzipping...')
            shutil.unpack_archive(temp_dir + '/' +  filename, temp_dir)
            
            # Clean up files except agent code and requirements
            for item in os.listdir(temp_dir):
                full_path = f'{temp_dir}' + '/' + f'{item}'
                if os.path.isfile(full_path) and item != 'requirements.txt':
                    print(f'Removing file {item}')
                    os.remove(full_path)
                elif os.path.isdir(full_path) and item != 'agent':
                    print(f'Removing directory {item}')
                    shutil.rmtree(full_path)
            # Check temp dir contents
            print(f'Files in {temp_dir}: {os.listdir(temp_dir)}')
            
            # Copy c4utils package temporarily
            print(f'Copying c4utils package to {temp_dir}')
            shutil.copytree(os.getenv("C4UTILS_DIR"), f'{temp_dir}/c4utils')
            
            # Copy def file
            print(f'Copying def file to {temp_dir}')
            def_file_path = os.path.join(os.getenv("C4LEAGUE_ROOT_DIR"), 'build_agent.def')
            shutil.copy(def_file_path, temp_dir)
            
            # Create build script
            build_script = f"""#!/bin/bash
#SBATCH --job-name=build_{agent.team_name}_{agent.agent_name}
#SBATCH --output=build_%j.out
#SBATCH --error=build_%j.err
#SBATCH --partition=cpu-2h
#SBATCH --ntasks=1
#SBATCH --time=0:30:00

cd {temp_dir}
apptainer build {os.getenv('AGENT_CONTAINER_DIRECTORY')}/{get_sif_file_name_from_tournament_player(agent)} build_agent.def
"""
            script_path = os.path.join(temp_dir, "build.sh")
            with open(script_path, "w") as f:
                f.write(build_script)
            os.chmod(script_path, 0o755)
            
            # Check temp dir contents
            print(f'Files in {temp_dir}: {os.listdir(temp_dir)}')

            # Submit build job and wait for completion
            print(f'Submitting build job for {agent.team_name} {agent.agent_name}')
            result = subprocess.run(["sbatch", script_path], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to submit job: {result.stderr}")
            
            job_id = result.stdout.strip().split()[-1]
            print(f"Build job submitted with ID: {job_id}")
            
            # Wait for job completion
            job_completed = False
            while not job_completed:
                status_result = subprocess.run(
                    ["sacct", "-j", job_id, "--format=JobID,State", "--parsable2", "--noheader"], 
                    capture_output=True, 
                    text=True
                )
                if status_result.returncode != 0:
                    raise Exception(f"Failed to check job status: {status_result.stderr}")
                
                # Get status of main job (not steps)
                for line in status_result.stdout.strip().split('\n'):
                    if line.strip():
                        job_id_str, status = line.split('|')
                        if job_id_str == str(job_id):  # Main job, not a step
                            print(f"Current status for job {job_id}: {status}")
                            if status in ["COMPLETED", "FAILED", "CANCELLED"]:
                                job_completed = True
                                if status != "COMPLETED":
                                    # Check error file
                                    error_file = f"build_{job_id}.err"
                                    if os.path.exists(error_file):
                                        with open(error_file, 'r') as f:
                                            error_content = f.read()
                                            print(f"Build error output:\n{error_content}")
                                    raise Exception(f"Build job failed with status: {status}")
                                break
                
                if not job_completed:
                    time.sleep(10)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            print(f"Error building container for {agent.team_name} {agent.agent_name}: {e}")
            shutil.rmtree(temp_dir)
