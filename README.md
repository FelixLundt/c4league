# Connect4 AI League Manager

This repository contains the tools and scripts to manage and run a Connect4 tournament league for AI agents. It is designed for deployment on a Slurm-managed HPC cluster and automates the process of fetching new agents, building them into secure containers, running tournaments, and processing results.

## Core Features

*   **Automated Tournament Scheduling:** Periodically checks for new agents and initiates tournaments.
*   **Agent Containerization:** Fetches agent code (e.g., from Google Cloud Storage) and builds them into Apptainer (Singularity) SIF containers for sandboxed execution.
*   **Slurm Integration:** Leverages Slurm for distributing and managing match jobs as a job array.
*   **Flexible Match Execution:** Runs matches between pairs of agents, potentially with randomized starting boards.
*   **Results & Statistics:** Collects raw game data and processes it into comprehensive match and tournament statistics.
*   **Logging:** Maintains logs for scheduling, tournament execution, and individual match outcomes.

## Workflow Overview

1.  **Scheduler (`schedule_tournaments.py`):**
    *   Runs as a persistent process (e.g., in a `screen` or `tmux` session on a login node).
    *   Periodically (e.g., every 4 hours) triggers a new tournament run.

2.  **Tournament Initialization (`run_tournament.py` & `c4league.TournamentManager`):**
    *   **Agent Discovery:**
        *   Fetches the list of all submitted agents.
        *   Identifies new or updated agents since the last run.
    *   **Agent Build:**
        *   If new/updated agents are found, they are downloaded.
        *   Each agent is built into an individual Apptainer SIF container (using `build_agent.def` as a base). Old versions of updated agents are removed.
    *   **Tournament Setup:**
        *   A unique tournament ID is generated.
        *   Directories for results (`tournament_results/<tournament_id>/`) and Slurm logs (`tournament_logs/<tournament_id>/`) are created.
        *   All-play-all pairings are generated for the available (and successfully built) agents.
        *   A configuration file (`tournament_configs/<tournament_id>.txt`) is created, mapping each match ID to the SIF files of the participating agents.
        *   A Slurm job script (`tournament_scripts/<tournament_id>.sh`) is generated for the tournament.

3.  **Match Execution (Slurm Job Array):**
    *   The generated Slurm script is submitted as a job array, where each array task corresponds to a single match.
    *   Each Slurm array task:
        *   Reads its assigned match details (match ID, agent SIF paths) from the tournament config file.
        *   Executes `run_match.py` (typically within the `run_match.sif` container environment) to play the games for the match.
        *   `run_match.py` uses the two specified agent SIFs to run multiple games (e.g., one with each agent starting, potentially with a common random board).
        *   Game and match results are saved as JSON files in `tournament_results/<tournament_id>/<match_id>/`.

4.  **Monitoring & Results Processing (`c4league.TournamentManager`):**
    *   The system monitors the Slurm queue (`sacct`) until all matches (job array tasks) are complete.
    *   Upon completion, it retrieves and parses the JSON result files from each match.
    *   Aggregated statistics (`GameStats`, `MatchStats`, `TournamentStats`) are computed and saved.

## Directory Structure

```
.
├── agents/                   # Directory where agent SIF containers are stored
├── c4league/                 # Core Python package for the league manager
│   ├── __init__.py
│   ├── tournament_manager.py # Main logic for managing tournaments
│   ├── container_utils.py    # Utilities for building/managing agent containers
│   ├── utils.py              # General utilities
│   ├── params.py             # Configuration parameters
│   └── storage/              # Modules for handling data (stats, cloud storage)
├── tournament_configs/       # Stores configuration files for each tournament (list of matches)
├── tournament_logs/          # Stores Slurm output (.out) and error (.err) logs for each match
├── tournament_results/       # Stores raw JSON results from games and processed statistics
├── tournament_scripts/       # Stores generated Slurm job scripts for each tournament
├── .env                      # Environment variables (see Configuration section)
├── build_agent.def           # Apptainer definition file template for building agent SIFs
├── run_match.def             # Apptainer definition file for the match execution environment
├── run_match.sif             # Compiled Apptainer container for running matches (built from run_match.def)
├── run_match.py              # Script to run a single match between two agents
├── run_tournament.py         # Script to initiate and run a full tournament
├── schedule_tournaments.py   # Script to periodically schedule and run tournaments
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── ...                       # Other project files (e.g., .gitignore, LICENSE)
```

## Setup and Installation

### 1. Prerequisites
*   Access to a Slurm-managed HPC cluster.
*   Apptainer (Singularity) installed on the cluster nodes.
*   Python 3.x (e.g., 3.10 or as specified in `requirements.txt`).
*   Git.
*   (Optional) Google Cloud SDK if using GCS for agent storage, and appropriate credentials.

### 2. Clone Repository
```bash
git clone <your-repository-url>
cd <repository-name>
```

### 3. Configure Environment (`.env` file)
Create a `.env` file in the root of the project with the following variables (adjust paths and values as needed for your cluster environment):

```env
# --- Core Paths ---
# Root directory of the c4league project on the cluster
C4LEAGUE_ROOT_DIR="/path/to/your/c4league_repository"

# Directory where agent SIF containers are/will be stored
AGENT_CONTAINER_DIRECTORY="${C4LEAGUE_ROOT_DIR}/agents"

# Directory to store tournament result files
TOURNAMENT_RESULTS_DIRECTORY="${C4LEAGUE_ROOT_DIR}/tournament_results"

# Directory to store tournament log files (Slurm logs)
TOURNAMENT_LOGS_DIRECTORY="${C4LEAGUE_ROOT_DIR}/tournament_logs"

# Directory to store tournament configuration files (match lists)
TOURNAMENT_CONFIG_DIRECTORY="${C4LEAGUE_ROOT_DIR}/tournament_configs"

# Directory to store generated Slurm job scripts
TOURNAMENT_JOB_SCRIPT_DIRECTORY="${C4LEAGUE_ROOT_DIR}/tournament_scripts"

# --- Agent Source (Example: Google Cloud Storage) ---
# GCS Bucket Name where agent submissions are stored
GCS_BUCKET_NAME="your-gcs-bucket-name"
# Path to GCS credentials JSON file
GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/gcs-credentials.json"

# --- Match Parameters ---
# Timeout for a single move in seconds
TIMEOUT="10"

# --- GitHub Token (Optional) ---
# Optional: If you have other private GitHub dependencies
# GITHUB_TOKEN="your_github_personal_access_token"
```
**Important:** Ensure all specified directories exist or that the scripts have permission to create them.

### 4. Python Environment (Login Node)
It's recommended to use a virtual environment.
```bash
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install the c4utils package (now public)
# Option 1: From GitHub (if not yet on PyPI)
pip install git+https://github.com/FelixLundt/c4utils.git

# Option 2: From PyPI (once published)
# pip install c4utils

# Option 3: From a local path (if developing c4utils alongside this project)
# pip install /path/to/your/local/c4utils

# (If you have other custom private packages, you might install them here using GITHUB_TOKEN)
```

### 5. Build Match Execution Container (`run_match.sif`)
This container provides the environment in which `run_match.py` (and thus the agent SIFs) will be executed by Slurm.
This step typically needs to be done on a compute node.

```bash
# Request an interactive session on a compute node (if necessary)
# Adjust partition and time as needed
srun --partition=cpu-short --time=00:30:00 --pty bash

# Navigate to your project directory
cd /path/to/your/c4league_repository

# Load Apptainer module (if required on your cluster)
# module load apptainer

# Build the container
apptainer build run_match.sif run_match.def
```
*Ensure `run_match.def` is configured correctly (e.g., Python version, necessary libraries).*

## Running the Tournament System

### 1. Start the Tournament Scheduler
The scheduler runs periodically to check for new agents and start tournaments. Run this on a **login node** within a `screen` or `tmux` session to keep it running after you disconnect.

```bash
# Activate Python environment (if not already active)
source .venv/bin/activate

# Start a new screen session
screen -S c4league

# Inside the screen session, run the scheduler:
./schedule_tournaments.py
```
*   To detach from screen: `Ctrl+A`, then `D`.
*   To reattach: `screen -r c4league`.
*   Scheduler activity is logged to `tournament_scheduler.log`.

### 2. Manual Tournament Run (Optional)
To run a single tournament manually (e.g., for testing):
```bash
# Activate Python environment
source .venv/bin/activate

# Run the tournament script
./run_tournament.py
```

## Checking Results and Logs

*   **Tournament Scheduler Logs:** `tournament_scheduler.log` in the project root.
*   **Slurm Job Logs:** Located in `tournament_logs/<tournament_id>/`. Each match (array task) will have a `.out` and `.err` file.
*   **Match Results:**
    *   Raw JSON files for each game are in `tournament_results/<tournament_id>/<match_id>/`.
    *   Processed match statistics and overall tournament statistics are also stored in the tournament results directory.
*   **Agent Containers:** Built agent SIF files are stored in the directory specified by `AGENT_CONTAINER_DIRECTORY` (e.g., `agents/`).

## Development & Customization

*   **Agent Building:** Modify `build_agent.def` to change how individual agent containers are built (e.g., different base OS, dependencies).
*   **Match Execution Environment:** Modify `run_match.def` to change the environment for running matches.
*   **Match Logic:** Edit `run_match.py` to alter how games are played (number of games, time controls if not using `TIMEOUT` from `.env`).
*   **Tournament Logic:** The core logic resides in `c4league/tournament_manager.py`. This includes pairings, statistics generation, and Slurm interaction.
*   **Agent Source:** To use a different source for agents (not GCS), modify the functions in `c4league.storage.cloud_storage` (or a similar module) and update `run_tournament.py` accordingly.

## Troubleshooting

*   **Permission Errors:** Ensure the user running the scripts has read/write/execute permissions for all relevant directories and files, especially those defined in `.env`.
*   **Slurm Job Failures:** Check the `.err` files in `tournament_logs/<tournament_id>/` for specific error messages from your match scripts.
*   **Apptainer Build Failures:** Ensure the `.def` files are correct and that all necessary base images and dependencies are accessible from the build environment (compute node).
*   **Python Dependencies:** Make sure `requirements.txt` is complete and all packages are installed in the correct environment.
*   **Environment Variables:** Double-check all paths and settings in your `.env` file. The `C4LEAGUE_ROOT_DIR` is crucial.
