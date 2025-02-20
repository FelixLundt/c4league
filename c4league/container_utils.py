import os
import shutil
import tempfile
from dotenv import load_dotenv
from c4league.storage.cloud_storage import download_agent
from c4league.utils import TournamentPlayer, get_tournament_player_from_sif, get_sif_file_name_from_tournament_player
import subprocess
import time

load_dotenv()


def get_containerized_agents() -> list[TournamentPlayer]:
    containerized_agents = []
    for file in os.listdir(os.getenv("AGENT_CONTAINER_DIRECTORY")):
        if file.endswith(".sif"):
            containerized_agents.append(get_tournament_player_from_sif(file))
        else:
            print(f"Warning: File {file} is not a .sif file")
    return containerized_agents

def get_sif_file_path_from_tournament_player(tournament_player: TournamentPlayer) -> str:
    return os.path.join(os.getenv("AGENT_CONTAINER_DIRECTORY"), get_sif_file_name_from_tournament_player(tournament_player))

def remove_old_agents(agents: list[TournamentPlayer]) -> None:
    for agent in agents:
        os.remove(get_sif_file_path_from_tournament_player(agent))

def containerize_agents(agents: list[TournamentPlayer]) -> None:
    for agent in agents:
        temp_dir = None
        try:
            # Create temp directory in shared location
            temp_dir = tempfile.mkdtemp(dir=os.getenv("C4LEAGUE_ROOT_DIR"))
            print(f'Downloading agent {agent.team_name} {agent.agent_name} {agent.version} to {temp_dir}')
            download_agent(agent.get_dict(), temp_dir)
            
            # Unzip agent code
            filename = os.listdir(temp_dir)[0]
            shutil.unpack_archive(temp_dir + '/' + filename, temp_dir)
            
            # Clean up files except agent code and requirements
            for item in os.listdir(temp_dir):
                full_path = os.path.join(temp_dir, item)
                if os.path.isfile(full_path) and item != 'requirements.txt':
                    os.remove(full_path)
                elif os.path.isdir(full_path) and item != 'agent':
                    shutil.rmtree(full_path)
            
            # Copy c4utils package and def file
            shutil.copytree(os.getenv("C4UTILS_DIR"), f'{temp_dir}/c4utils')
            def_file_path = os.path.join(os.getenv("C4LEAGUE_ROOT_DIR"), 'build_agent.def')
            shutil.copy(def_file_path, temp_dir)
            
            # Create build script
            build_script = f"""#!/bin/bash
#SBATCH --job-name=build_{agent.team_name}_{agent.agent_name}
#SBATCH --output=build_%j.out
#SBATCH --error=build_%j.err
#SBATCH --partition=cpu-2h
#SBATCH --ntasks=1
#SBATCH --time=0:30:00

TEMP_DIR=$(mktemp -d)
SHARED_DIR="{os.path.abspath(temp_dir)}"

# Set up build environment
mkdir -p "$TEMP_DIR/agent"
[ -d "$SHARED_DIR/agent" ] && cp -r "$SHARED_DIR/agent/"* "$TEMP_DIR/agent/"
[ -f "$SHARED_DIR/build_agent.def" ] && cp "$SHARED_DIR/build_agent.def" "$TEMP_DIR/"
[ -d "$SHARED_DIR/c4utils" ] && cp -r "$SHARED_DIR/c4utils" "$TEMP_DIR/"
[ -f "$SHARED_DIR/requirements.txt" ] && cp "$SHARED_DIR/requirements.txt" "$TEMP_DIR/"

cd "$TEMP_DIR"
apptainer build "{os.path.abspath(os.path.join(os.getenv('AGENT_CONTAINER_DIRECTORY', ''), get_sif_file_name_from_tournament_player(agent)))}" build_agent.def

rm -rf "$TEMP_DIR"
"""
            # Submit and monitor build job
            script_path = os.path.join(temp_dir, "build.sh")
            with open(script_path, "w") as f:
                f.write(build_script)
            os.chmod(script_path, 0o755)
            
            print(f'Submitting build job for {agent.team_name} {agent.agent_name}')
            result = subprocess.run(["sbatch", script_path], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to submit job: {result.stderr}")
            
            job_id = result.stdout.strip().split()[-1]
            
            # Wait for job completion
            while True:
                status_result = subprocess.run(
                    ["sacct", "-j", job_id, "--format=JobID,State", "--parsable2", "--noheader"], 
                    capture_output=True, text=True
                )
                if status_result.returncode != 0:
                    raise Exception(f"Failed to check job status: {status_result.stderr}")
                
                for line in status_result.stdout.strip().split('\n'):
                    if line.strip():
                        job_id_str, status = line.split('|')
                        if job_id_str == str(job_id) and status in ["COMPLETED", "FAILED", "CANCELLED"]:
                            if status != "COMPLETED":
                                error_file = f"build_{job_id}.err"
                                if os.path.exists(error_file):
                                    with open(error_file, 'r') as f:
                                        error_content = f.read().strip()
                                        if error_content:
                                            print(f"Build error output:\n{error_content}")
                                raise Exception(f"Build job failed with status: {status}")
                            return
                
                time.sleep(10)
            
        except Exception as e:
            print(f"Error building container for {agent.team_name} {agent.agent_name}: {e}")
            raise e
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"Removed temp directory {temp_dir}")
                print(f"Containerized {agent.team_name} {agent.agent_name}.")
