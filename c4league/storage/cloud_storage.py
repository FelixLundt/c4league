"""Handles interface with Google Cloud Storage."""

import json
from typing import Any, Dict, List, Optional
from google.cloud import storage
from google.cloud.storage.client import Client
from google.cloud.storage.bucket import Bucket
import os
from dotenv import load_dotenv

load_dotenv()

def get_storage_client() -> Client:
    return storage.Client.from_service_account_json(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

def get_bucket() -> Bucket:
    return get_storage_client().bucket(os.getenv("GCS_BUCKET_NAME"))

def get_submitted_agents() -> list[dict[str, str]]:
    bucket = get_bucket()
    agent_blobs = bucket.list_blobs(prefix="submissions")
    submitted_agents = []
    for agent_blob in agent_blobs:
        data = agent_blob.name.split("/")
        assert len(data) == 4
        team_name, agent_name = data[1], data[2]
        version = data[3].split("_")[1].split(".")[0][1:]
        submitted_agents.append({'team_name': team_name, 'agent_name': agent_name, 'version': version})
    return submitted_agents

def download_agent(agent: dict[str, str], destination_dir: str) -> None:
    bucket = get_bucket()
    team_name, agent_name, version = agent['team_name'], agent['agent_name'], agent['version']
    filename = f"{agent_name}_v{version}.zip"
    blob_path = f"submissions/{team_name}/{agent_name}/{filename}"
    agent_blob = bucket.blob(blob_path)
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    agent_blob.download_to_filename(os.path.join(destination_dir, filename))
