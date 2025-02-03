import os
import json
from c4league.storage.cloud_storage import get_submitted_agents, download_agent
from c4league.utils import get_containerized_agents, get_new_agents, TournamentPlayer, containerize_agents
from google.cloud import storage

if __name__ == '__main__':
    print(get_submitted_agents())
    print(get_containerized_agents())
    submitted_agents = [TournamentPlayer(**agent) for agent in get_submitted_agents()]
    new_agents = get_new_agents(submitted_agents, get_containerized_agents())
    print(new_agents)
    containerize_agents([new_agents[0]])
