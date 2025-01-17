"""Google Cloud Storage operations for tournament results."""

import json
from typing import Any, Dict, List, Optional
from google.cloud import storage
from datetime import datetime
import os

class TournamentStorage:
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """Initialize storage client.
        
        Args:
            bucket_name: Name of the GCS bucket
            credentials_path: Path to service account key file (optional in production)
        """
        if credentials_path:
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        
    def save_json(self, path: str, data: Dict[str, Any]) -> None:
        """Save JSON data to GCS path."""
        blob = self.bucket.blob(path)
        blob.upload_from_string(json.dumps(data, indent=2))
        
    def load_json(self, path: str) -> Dict[str, Any]:
        """Load JSON data from GCS path."""
        blob = self.bucket.blob(path)
        return json.loads(blob.download_as_string())
    
    def list_files(self, prefix: str) -> List[str]:
        """List all files under prefix."""
        return [blob.name for blob in self.bucket.list_blobs(prefix=prefix)]
    
    def get_tournament_path(self, timestamp: Optional[datetime] = None) -> str:
        """Get path for tournament results.
        
        Args:
            timestamp: Tournament timestamp, defaults to current time
        
        Returns:
            Path like 'tournament_results/matches/20240113_143000/'
        """
        if timestamp is None:
            timestamp = datetime.now()
        return f"tournament_results/matches/{timestamp.strftime('%Y%m%d_%H%M%S')}/"
    
    def get_mini_match_path(self, tournament_path: str, team1: str, team2: str) -> str:
        """Get path for mini-match results.
        
        Args:
            tournament_path: Base tournament path
            team1: First team ID
            team2: Second team ID
        
        Returns:
            Path like '.../mini_matches/team1_vs_team2/'
        """
        return os.path.join(tournament_path, "mini_matches", f"{team1}_vs_{team2}")
    
    def get_group_stats_path(self, group_id: str) -> str:
        """Get path for group statistics.
        
        Args:
            group_id: Group identifier
        
        Returns:
            Path like 'tournament_results/by_group/team1/stats.json'
        """
        return f"tournament_results/by_group/{group_id}/stats.json" 