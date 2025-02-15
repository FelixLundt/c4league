#!/home/felix/c4league_env/bin/python3
"""Add shebang to use Python from virtual environment"""

import os
import sys
import time
from pathlib import Path
import logging
from datetime import datetime

# Activate virtual environment if not already activated
venv_path = Path.home() / "c4league_env"
if not sys.prefix == str(venv_path):
    activate_script = venv_path / "bin" / "activate_this.py"
    exec(open(activate_script).read(), {'__file__': str(activate_script)})

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tournament_scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_tournament():
    try:
        from run_tournament import run_tournament
        logging.info("Starting tournament...")
        run_tournament()
        logging.info("Tournament completed successfully")
    except Exception as e:
        logging.error(f"Tournament failed: {e}", exc_info=True)

def main():
    INTERVAL = 4 * 60 * 60  # 4 hours in seconds
    
    logging.info("Tournament scheduler started")
    
    while True:
        run_tournament()
        next_run = datetime.now().timestamp() + INTERVAL
        logging.info(f"Next tournament scheduled for: {datetime.fromtimestamp(next_run)}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main() 