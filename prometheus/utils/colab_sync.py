"""
Prometheus Colab & GDrive Synchronization Utilities

Provides frictionless coordination between local development, GitHub, 
Google Colab, and Google Drive persistent storage.
"""

import os
import sys
import subprocess
from typing import Optional

def is_colab() -> bool:
    """Check if the code is running in Google Colab."""
    return 'google.colab' in sys.modules

def mount_gdrive(mount_point: str = '/content/drive') -> bool:
    """Mount Google Drive in Colab."""
    if not is_colab():
        print("Not running in Colab. Skipping GDrive mount.")
        return False
    
    from google.colab import drive
    drive.mount(mount_point)
    return True

def setup_persistent_project(repo_url: str, project_name: str = 'Prometheus_v0_PoC', 
                             gdrive_path: str = '/content/drive/MyDrive') -> str:
    """
    Setup a persistent project folder on GDrive and sync with GitHub.
    
    This ensures that models, logs, and code changes persist between Colab sessions.
    """
    if not is_colab():
        return os.getcwd()

    mount_gdrive()
    
    full_project_path = os.path.join(gdrive_path, project_name)
    
    if not os.path.exists(full_project_path):
        print(f"Creating persistent project at {full_project_path}...")
        os.makedirs(gdrive_path, exist_ok=True)
        subprocess.run(['git', 'clone', repo_url, full_project_path])
    else:
        print(f"Persistent project found at {full_project_path}")
        # Optionally pull latest changes
        # subprocess.run(['git', '-C', full_project_path, 'pull'])

    # Add project to sys.path
    if full_project_path not in sys.path:
        sys.path.insert(0, full_project_path)
    
    os.chdir(full_project_path)
    print(f"Working directory changed to: {os.getcwd()}")
    
    return full_project_path

def install_dependencies(project_path: Optional[str] = None):
    """Install required packages from requirements.txt and install current package in dev mode."""
    if not is_colab():
        return

    path = project_path or os.getcwd()
    req_file = os.path.join(path, 'requirements.txt')
    
    if os.path.exists(req_file):
        print("Installing dependencies from requirements.txt...")
        subprocess.run(['pip', 'install', '-q', '-r', req_file])
    
    print("Installing Prometheus in development mode...")
    subprocess.run(['pip', 'install', '-q', '-e', path])
    
    # Install LLM dependencies if missing
    subprocess.run(['pip', 'install', '-q', 'google-generativeai'])

def load_secrets(env_file: str = '.env'):
    """Load secrets from a .env file into environment variables."""
    if not os.path.exists(env_file):
        print(f"No {env_file} file found. Make sure to set your API keys manually.")
        return

    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
                print(f"Loaded secret: {key}")

def sync_results_to_gdrive(local_results_path: str, gdrive_results_path: str):
    """Utility to copy local results/models to GDrive if not already working directly on GDrive."""
    if not is_colab():
        return
        
    subprocess.run(['cp', '-r', local_results_path, gdrive_results_path])
    print(f"Results synced to {gdrive_results_path}")


def export_output_file(filename: str, gdrive_subdir: str = "results") -> bool:
    """
    Saves/downloads any generated output file to both Google Drive and local storage.
    If in Colab, mounts Google Drive if needed, copies the file to the persistent Drive directory,
    and triggers an automatic browser download.
    """
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found.")
        return False
        
    print(f"Saved locally: {os.path.abspath(filename)}")
    
    if is_colab():
        # 1. Save to GDrive if drive is mounted
        gdrive_dir = '/content/drive/MyDrive/Prometheus_v0_PoC'
        if os.path.exists('/content/drive'):
            dest_dir = os.path.join(gdrive_dir, gdrive_subdir)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(filename))
            import shutil
            shutil.copy(filename, dest_path)
            print(f"Saved permanently to GDrive: {dest_path}")
        else:
            print("Google Drive not mounted. Call mount_gdrive() to enable persistent GDrive saving.")
            
        # 2. Trigger browser download
        try:
            from google.colab import files
            print(f"Triggering browser download for {filename}...")
            files.download(filename)
        except Exception as e:
            print(f"Failed to trigger browser download: {e}")
            
    return True

