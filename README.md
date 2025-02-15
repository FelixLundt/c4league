This repo is used to run a league for students' Connect4 agents.

- It is going to be deployed on the Hydra cluster in a screen session, where 
we'll keep a container running. 

- Every couple of hours, it will check if there are any new agents.

- If there are, it will download the code from the cloud, build the container


### Setup and Running

1. Set up Python environment on the login node:

```bash
# Create virtual environment
python3 -m venv ~/c4league_env

# Activate environment
source ~/c4league_env/bin/activate

# Install requirements
pip install -r requirements.txt

# Install c4utils package
export GITHUB_TOKEN=your_token_here
pip install git+https://${GITHUB_TOKEN}@github.com/FelixLundt/c4utils.git
```

2. Build containers on a compute node:

```bash
# Request an interactive session
srun --partition=cpu-2h --pty bash

# Build containers
apptainer build run_match.sif run_match.def
```

3. Run tournament scheduler on login node:

```bash
# Start new screen session
screen -S c4league

# Inside screen:
source ~/c4league_env/bin/activate
./schedule_tournaments.py
```

Detach from screen: Press Ctrl+A, then D
```bash
To manage the screen session:
    # List sessions
    screen -ls

    # Reattach to session
    screen -r c4league

    # Kill session
    screen -X -S c4league quit
```

Alternatively using tmux:

```bash
    # Start new session
    tmux new -s c4league

    # Inside tmux:
    source ~/c4league_env/bin/activate
    ./schedule_tournaments.py

    # Detach: Press Ctrl+B, then D
    # Reattach: tmux attach -t c4league
    # Kill: tmux kill-session -t c4league
```

The tournament scheduler will:
- Run every 4 hours
- Check for new agents
- Run matches if needed
- Log activity to tournament_scheduler.log


### Ideas




### Questions

- How to run the tournament from a python file? I don't want to block resources, 
so I need to find a way to launch processes at specific times.

- What to run? Games with empty boards (each agent starts once) and games with 
random starting positions?

- We need code to run the league

- What to store from games and how? Maybe it would be useful to have one
database with all the raw info and then have code that reads that out.
