from c4league.container_utils import get_updated_agents, get_new_agents, TournamentPlayer

def test_should_return_empty_list_if_agents_unchanged():
    submitted_agents = [TournamentPlayer("team1", "agent1", "2"), TournamentPlayer("team2", "agent2", "1")]
    containerized_agents = [TournamentPlayer("team1", "agent1", "2"), TournamentPlayer("team2", "agent2", "1")]
    assert get_updated_agents(submitted_agents, containerized_agents) == []

def test_should_find_updated_agent():
    submitted_agents = [TournamentPlayer("team1", "agent1", "2"), TournamentPlayer("team2", "agent2", "2")]
    containerized_agents = [TournamentPlayer("team1", "agent1", "2"), TournamentPlayer("team2", "agent2", "1")]
    assert get_updated_agents(submitted_agents, containerized_agents) == [TournamentPlayer("team2", "agent2", "2")]

def test_should_find_new_agent():
    submitted_agents = [TournamentPlayer("team1", "agent1", "2"), TournamentPlayer("team2", "agent2", "1")]
    containerized_agents = [TournamentPlayer("team1", "agent1", "2")]
    assert get_new_agents(submitted_agents, containerized_agents) == [TournamentPlayer("team2", "agent2", "1")]

def test_should_flag_all_agents_as_new_if_none_containerized():
    submitted_agents = [TournamentPlayer("team1", "agent1", "2"), TournamentPlayer("team2", "agent2", "1")]
    containerized_agents = []
    assert get_new_agents(submitted_agents, containerized_agents) == submitted_agents