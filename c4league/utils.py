import random
import string
from dataclasses import dataclass

ID_DIGITS = 5

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

def generate_id() -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=ID_DIGITS))

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

def get_tournament_player_from_sif(file: str) -> TournamentPlayer:
    team_name, agent_name, version = file.rstrip(".sif").split("_")
    return TournamentPlayer(team_name, agent_name, version)

def get_sif_file_name_from_tournament_player(tournament_player: TournamentPlayer) -> str:
    return f"{tournament_player.team_name}_{tournament_player.agent_name}_{tournament_player.version}.sif"