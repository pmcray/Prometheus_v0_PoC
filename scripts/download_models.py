#!/usr/bin/env python3
"""
Model Download Manager

Downloads pre-trained Prometheus models from GitHub releases.

Usage:
    # Download all models
    python scripts/download_models.py --all

    # Download specific model
    python scripts/download_models.py --model go_9x9

    # List available models
    python scripts/download_models.py --list

    # Check model integrity
    python scripts/download_models.py --verify
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import urllib.error

# Model registry - update this when new models are released
MODEL_REGISTRY = {
    "go_9x9": {
        "filename": "go_9x9.h5",
        "version": "v1.0.0",
        "size_mb": 12.5,
        "sha256": "placeholder_sha256_hash_for_go_9x9",
        "description": "Go 9×9 model (~1,280 ELO, 78% win rate vs random)",
        "training_games": 200,
        "elo": 1280,
        "inference_ms": 8.5,
    },
    "go_19x19": {
        "filename": "go_19x19.h5",
        "version": "v1.0.0",
        "size_mb": 35.2,
        "sha256": "placeholder_sha256_hash_for_go_19x19",
        "description": "Go 19×19 model via transfer learning (~1,450 ELO, 88% win rate)",
        "training_games": 100,
        "elo": 1450,
        "inference_ms": 22.1,
    },
    "chess": {
        "filename": "chess.h5",
        "version": "v1.0.0",
        "size_mb": 18.7,
        "sha256": "placeholder_sha256_hash_for_chess",
        "description": "Chess model (~1,340 ELO, 82% win rate vs random)",
        "training_games": 200,
        "elo": 1340,
        "inference_ms": 15.3,
    },
}

# GitHub repository information
GITHUB_REPO = "pmcray/Prometheus_v0_PoC"
RELEASE_TAG = "models-v1.0.0"
BASE_URL = f"https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}"

# Output directory
MODELS_DIR = Path("models/pretrained")


def download_file(url: str, output_path: Path, show_progress: bool = True) -> bool:
    """Download a file from URL to output path with progress indicator."""
    try:
        print(f"Downloading from: {url}")
        print(f"Saving to: {output_path}")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download with progress
        def reporthook(block_num, block_size, total_size):
            if show_progress and total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                bar_length = 40
                filled = int(bar_length * downloaded / total_size)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f'\r  Progress: [{bar}] {percent:.1f}% ({downloaded/1e6:.1f}/{total_size/1e6:.1f} MB)', end='')

        urllib.request.urlretrieve(url, output_path, reporthook=reporthook)
        if show_progress:
            print()  # New line after progress bar
        print(f"✓ Downloaded successfully")
        return True

    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error {e.code}: {e.reason}")
        if e.code == 404:
            print(f"  Model not found at {url}")
            print(f"  Please ensure models have been uploaded to GitHub releases")
        return False
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_model(model_name: str, model_info: Dict) -> bool:
    """Verify a downloaded model's integrity."""
    model_path = MODELS_DIR / model_info["filename"]

    if not model_path.exists():
        print(f"✗ {model_name}: File not found")
        return False

    # Check file size
    actual_size_mb = model_path.stat().st_size / (1024 * 1024)
    expected_size_mb = model_info["size_mb"]
    size_diff = abs(actual_size_mb - expected_size_mb)

    if size_diff > 1.0:  # Allow 1MB difference
        print(f"✗ {model_name}: Size mismatch (expected {expected_size_mb:.1f}MB, got {actual_size_mb:.1f}MB)")
        return False

    # Check SHA256 hash (skip if placeholder)
    if not model_info["sha256"].startswith("placeholder"):
        actual_hash = calculate_sha256(model_path)
        if actual_hash != model_info["sha256"]:
            print(f"✗ {model_name}: Hash mismatch")
            print(f"  Expected: {model_info['sha256']}")
            print(f"  Actual:   {actual_hash}")
            return False

    print(f"✓ {model_name}: Verified ({actual_size_mb:.1f}MB)")
    return True


def list_available_models():
    """List all available models with details."""
    print("=" * 80)
    print("AVAILABLE PRE-TRAINED MODELS")
    print("=" * 80)

    for model_name, info in MODEL_REGISTRY.items():
        print(f"\n{model_name}:")
        print(f"  Description: {info['description']}")
        print(f"  File: {info['filename']}")
        print(f"  Size: {info['size_mb']} MB")
        print(f"  ELO: {info['elo']}")
        print(f"  Inference: {info['inference_ms']} ms")
        print(f"  Training Games: {info['training_games']}")
        print(f"  Version: {info['version']}")

        # Check if already downloaded
        model_path = MODELS_DIR / info["filename"]
        if model_path.exists():
            print(f"  Status: ✓ Downloaded")
        else:
            print(f"  Status: ✗ Not downloaded")

    print("\n" + "=" * 80)
    print(f"Total models: {len(MODEL_REGISTRY)}")
    print("\nDownload commands:")
    print(f"  All models:      python scripts/download_models.py --all")
    print(f"  Specific model:  python scripts/download_models.py --model <name>")


def download_model(model_name: str, verify: bool = True) -> bool:
    """Download a specific model."""
    if model_name not in MODEL_REGISTRY:
        print(f"✗ Unknown model: {model_name}")
        print(f"Available models: {', '.join(MODEL_REGISTRY.keys())}")
        return False

    model_info = MODEL_REGISTRY[model_name]
    model_path = MODELS_DIR / model_info["filename"]

    # Check if already exists
    if model_path.exists():
        print(f"Model {model_name} already exists at {model_path}")
        if verify:
            return verify_model(model_name, model_info)
        return True

    # Download
    url = f"{BASE_URL}/{model_info['filename']}"
    success = download_file(url, model_path)

    if success and verify:
        return verify_model(model_name, model_info)

    return success


def download_all_models(verify: bool = True) -> bool:
    """Download all available models."""
    print(f"Downloading all {len(MODEL_REGISTRY)} models...\n")

    results = {}
    for model_name in MODEL_REGISTRY.keys():
        print(f"\n[{model_name}]")
        results[model_name] = download_model(model_name, verify=verify)

    # Summary
    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    success_count = sum(results.values())
    for model_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {model_name}")

    print(f"\nSuccessful: {success_count}/{len(results)}")

    return success_count == len(results)


def verify_all_models() -> bool:
    """Verify all downloaded models."""
    print("Verifying downloaded models...\n")

    results = {}
    for model_name, model_info in MODEL_REGISTRY.items():
        model_path = MODELS_DIR / model_info["filename"]
        if model_path.exists():
            results[model_name] = verify_model(model_name, model_info)

    if not results:
        print("No models found to verify.")
        print("Download models first with: python scripts/download_models.py --all")
        return False

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    success_count = sum(results.values())
    print(f"Verified: {success_count}/{len(results)}")

    return success_count == len(results)


def save_model_metadata(model_name: str, model_info: Dict):
    """Save model metadata to JSON file."""
    model_path = MODELS_DIR / model_info["filename"]
    metadata_path = model_path.with_suffix('.json')

    metadata = {
        "model_name": model_name,
        "filename": model_info["filename"],
        "version": model_info["version"],
        "description": model_info["description"],
        "training_games": model_info["training_games"],
        "performance": {
            "elo": model_info["elo"],
            "inference_ms": model_info["inference_ms"],
        },
        "file_info": {
            "size_mb": model_info["size_mb"],
            "sha256": model_info["sha256"],
        },
        "download_url": f"{BASE_URL}/{model_info['filename']}",
    }

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to: {metadata_path}")


def main():
    global MODELS_DIR
    parser = argparse.ArgumentParser(
        description="Download pre-trained Prometheus models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available models
  python scripts/download_models.py --list

  # Download all models
  python scripts/download_models.py --all

  # Download specific model
  python scripts/download_models.py --model go_9x9

  # Verify downloaded models
  python scripts/download_models.py --verify

  # Download without verification
  python scripts/download_models.py --model chess --no-verify
        """
    )

    parser.add_argument('--list', action='store_true',
                        help='List available models')
    parser.add_argument('--all', action='store_true',
                        help='Download all models')
    parser.add_argument('--model', type=str,
                        help='Download specific model')
    parser.add_argument('--verify', action='store_true',
                        help='Verify downloaded models')
    parser.add_argument('--no-verify', action='store_true',
                        help='Skip verification after download')
    parser.add_argument('--output-dir', type=Path, default=MODELS_DIR,
                        help='Output directory for models')

    args = parser.parse_args()

    # Update output directory if specified
    MODELS_DIR = args.output_dir

    # Handle commands
    if args.list:
        list_available_models()
        return 0

    if args.verify:
        success = verify_all_models()
        return 0 if success else 1

    if args.all:
        verify = not args.no_verify
        success = download_all_models(verify=verify)
        return 0 if success else 1

    if args.model:
        verify = not args.no_verify
        success = download_model(args.model, verify=verify)
        return 0 if success else 1

    # No command specified
    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
