from dataclasses import dataclass
import os
import shutil
import tempfile
from dotenv import load_dotenv
from c4league.storage.cloud_storage import download_agent
import subprocess
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
    team_name, agent_name, version = file.split("_")
    return TournamentPlayer(team_name, agent_name, version)

def get_sif_file_name_from_tournament_player(tournament_player: TournamentPlayer) -> str:
    return f"{tournament_player.team_name}_{tournament_player.agent_name}_{tournament_player.version}.sif"

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
    # for each agent:
    # - create temporary directory
    # - copy agent code to temporary directory
    # - create def file
    # - build container
    # - move container to containerized_agents directory
    # - delete temporary directory
    for agent in agents:

        temp_dir = os.getenv("C4LEAGUE_ROOT_DIR") + '/tmp/' 
        try:
            # temp_dir = tempfile.mkdtemp()
            download_agent(agent.get_dict(), temp_dir)
            # unzip agent code and delete zip file
            print(os.listdir(temp_dir))
            filename = os.listdir(temp_dir)[0]
            print(filename)
            shutil.unpack_archive(temp_dir + '/' +  filename, temp_dir)
            for item in os.listdir(temp_dir):
                full_path = f'{temp_dir}' + '/' + f'{item}'
                if os.path.isfile(full_path) and item != 'requirements.txt':
                    os.remove(full_path)
                elif os.path.isdir(full_path) and item != 'agent':
                    shutil.rmtree(full_path)
            
            # Copy c4utils package temporarily
            shutil.copytree(os.getenv("C4UTILS_DIR"), f'{temp_dir}/c4utils')
            
            # Copy def file
            def_file_path = os.path.join(os.getenv("C4LEAGUE_ROOT_DIR"), 'build_agent.def')
            shutil.copy(def_file_path, temp_dir)
            
            # Build container
            print(f'Building in {temp_dir}')
            print(f'Files in {temp_dir}: {os.listdir(temp_dir)}')
            subprocess.run([
                "apptainer", 
                "build", 
                f"{os.getenv('AGENT_CONTAINER_DIRECTORY')}/{get_sif_file_name_from_tournament_player(agent)}", 
                "build_agent.def"
                ], check=True, cwd = temp_dir)
            
            # Clean up temp directory including c4utils
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error building container for {agent.team_name} {agent.agent_name}: {e}")
            shutil.rmtree(temp_dir)

#         shutil.copytree(os.getenv("AGENT_CODE_DIRECTORY") + "/" + agent.team_name + "/" + agent.agent_name, temp_dir)
#         with open(temp_dir + "/def", "w") as f:
#             f.write(f"Bootstrap: docker\nFrom: {os.getenv('AGENT_DOCKER_IMAGE')}")
#         os.system(f"singularity build {os.getenv('AGENT_CONTAINER_DIRECTORY')}/{get_sif_file_name_from_tournament_player(agent)} {temp_dir}/def")
#         shutil.move(os.getenv('AGENT_CONTAINER_DIRECTORY') + "/" + get_sif_file_name_from_tournament_player(agent), os.getenv('AGENT_CONTAINER_DIRECTORY') + "/" + agent.team_name + "/" + agent.agent_name + ".sif")
#         shutil.rmtree(temp_dir)

# def make_def_file(temp_dir: str, agent: TournamentPlayer) -> None: