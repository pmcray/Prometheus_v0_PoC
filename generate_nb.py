import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🚀 Prometheus Frictionless Setup (GitHub ↔ Colab ↔ GDrive)
",
    "
",
    "This notebook provides a persistent setup for the Prometheus project. It mounts your Google Drive and clones/syncs the repository there, so your models and logs are never lost."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# @title 🛠️ Persistent Environment Setup
",
    "REPO_URL = 'https://github.com/pmcray/Prometheus_v0_PoC.git'
",
    "PROJECT_NAME = 'Prometheus_v0_PoC'
",
    "USE_GDRIVE = True
",
    "
",
    "import os
",
    "import sys
",
    "import subprocess
",
    "
",
    "if 'google.colab' in sys.modules:
",
    "    if USE_GDRIVE:
",
    "        from google.colab import drive
",
    "        drive.mount('/content/drive')
",
    "        PROJECT_PATH = f'/content/drive/MyDrive/{PROJECT_NAME}'
",
    "    else:
",
    "        PROJECT_PATH = f'/content/{PROJECT_NAME}'
",
    "
",
    "    if not os.path.exists(PROJECT_PATH):
",
    "        print(f'📥 Cloning repository to {PROJECT_PATH}...')
",
    "        subprocess.run(['git', 'clone', REPO_URL, PROJECT_PATH])
",
    "    else:
",
    "        print(f'✅ Project found at {PROJECT_PATH}')
",
    "        # subprocess.run(['git', '-C', PROJECT_PATH, 'pull'])
",
    "
",
    "    os.chdir(PROJECT_PATH)
",
    "    if PROJECT_PATH not in sys.path:
",
    "        sys.path.insert(0, PROJECT_PATH)
",
    "    
",
    "    print('📦 Installing dependencies...')
",
    "    subprocess.run(['pip', 'install', '-q', '-r', 'requirements.txt'])
",
    "    subprocess.run(['pip', 'install', '-q', '-e', '.'])
",
    "    subprocess.run(['pip', 'install', '-q', 'google-generativeai'])
",
    "    
",
    "    print(f'✅ Setup Complete! Working directory: {os.getcwd()}')
",
    "else:
",
    "    print('Running locally. Ensure you have installed with pip install -e .')
"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# @title 🔑 Load API Keys
",
    "from prometheus.utils.colab_sync import load_secrets
",
    "load_secrets()
",
    "
",
    "import os
",
    "if not os.environ.get('GOOGLE_API_KEY'):
",
    "    print('⚠️ GOOGLE_API_KEY not found. Some features will be disabled.')
",
    "else:
",
    "    print('✅ API Keys loaded successfully.')
"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 🧪 Verify Today's New Features
",
    "Run this block to test the code written in the last session (ARC v0.96, Go MCTS, RSI Loop)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!python scripts/verify_colab_features.py"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

with open('Colab_Master_Setup.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)
