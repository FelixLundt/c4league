#!/usr/bin/env python3
"""Tournament scheduler that runs periodically on the login node"""

import time
from pathlib import Path
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tournament_scheduler.log'),
        logging.StreamHandler()
    ]
)

def schedule_tournament():
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
        schedule_tournament()
        next_run = datetime.now().timestamp() + INTERVAL
        logging.info(f"Next tournament scheduled for: {datetime.fromtimestamp(next_run)}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main() 