#!/usr/bin/env python3
"""
ARC Challenge Dataset Downloader

Downloads the ARC (Abstraction and Reasoning Corpus) dataset required for
ARC benchmark tests and related experiments.

Dataset source: https://github.com/fchollet/ARC-AGI

Usage:
    python scripts/download_arc_dataset.py
    python scripts/download_arc_dataset.py --output-dir data/arc
    python scripts/download_arc_dataset.py --verify
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import zipfile
from pathlib import Path


# Official ARC-AGI dataset from François Chollet's repository
ARC_REPO_URL = "https://github.com/fchollet/ARC-AGI/archive/refs/heads/master.zip"
ARC_ZIP_FILENAME = "ARC-AGI-master.zip"

# Expected subdirectory structure inside the zip
ARC_TRAINING_PATH = "ARC-AGI-master/data/training"
ARC_EVALUATION_PATH = "ARC-AGI-master/data/evaluation"

# Default output location (matches what tests expect)
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "arc"


def download_file(url: str, dest_path: Path, show_progress: bool = True) -> bool:
    """Download a file from a URL with optional progress display."""
    print(f"Downloading {url}")
    print(f"  -> {dest_path}")

    try:
        def reporthook(block_num, block_size, total_size):
            if show_progress and total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                mb_done = downloaded / 1024 / 1024
                mb_total = total_size / 1024 / 1024
                print(f"\r  Progress: {percent:.1f}% ({mb_done:.1f}/{mb_total:.1f} MB)", end="", flush=True)

        urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
        if show_progress:
            print()  # newline after progress bar
        return True

    except urllib.error.HTTPError as e:
        print(f"\nHTTP error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\nURL error: {e.reason}")
        return False
    except OSError as e:
        print(f"\nFile error: {e}")
        return False


def extract_arc_dataset(zip_path: Path, output_dir: Path) -> bool:
    """Extract ARC training and evaluation tasks from the zip archive."""
    print(f"Extracting dataset to {output_dir}")

    training_dir = output_dir / "training"
    evaluation_dir = output_dir / "evaluation"
    training_dir.mkdir(parents=True, exist_ok=True)
    evaluation_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            all_names = zf.namelist()

            # Extract training tasks
            training_files = [n for n in all_names if n.startswith(ARC_TRAINING_PATH) and n.endswith(".json")]
            for name in training_files:
                filename = Path(name).name
                with zf.open(name) as src, open(training_dir / filename, "wb") as dst:
                    dst.write(src.read())

            # Extract evaluation tasks
            evaluation_files = [n for n in all_names if n.startswith(ARC_EVALUATION_PATH) and n.endswith(".json")]
            for name in evaluation_files:
                filename = Path(name).name
                with zf.open(name) as src, open(evaluation_dir / filename, "wb") as dst:
                    dst.write(src.read())

        print(f"  Extracted {len(training_files)} training tasks -> {training_dir}")
        print(f"  Extracted {len(evaluation_files)} evaluation tasks -> {evaluation_dir}")
        return True

    except (zipfile.BadZipFile, KeyError, OSError) as e:
        print(f"Extraction failed: {e}")
        return False


def verify_dataset(output_dir: Path) -> bool:
    """Verify that the ARC dataset is present and readable."""
    training_dir = output_dir / "training"
    evaluation_dir = output_dir / "evaluation"

    issues = []

    if not training_dir.exists():
        issues.append(f"Training directory missing: {training_dir}")
    else:
        training_tasks = list(training_dir.glob("*.json"))
        if len(training_tasks) < 400:
            issues.append(f"Training set too small: {len(training_tasks)} tasks (expected ~400)")
        else:
            # Spot-check a few files are valid JSON
            for task_file in training_tasks[:5]:
                try:
                    with open(task_file) as f:
                        data = json.load(f)
                    if "train" not in data or "test" not in data:
                        issues.append(f"Invalid task format: {task_file.name}")
                except (json.JSONDecodeError, OSError) as e:
                    issues.append(f"Unreadable task file {task_file.name}: {e}")

    if not evaluation_dir.exists():
        issues.append(f"Evaluation directory missing: {evaluation_dir}")
    else:
        evaluation_tasks = list(evaluation_dir.glob("*.json"))
        if len(evaluation_tasks) < 400:
            issues.append(f"Evaluation set too small: {len(evaluation_tasks)} tasks (expected ~400)")

    if issues:
        print("Dataset verification FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    training_count = len(list(training_dir.glob("*.json")))
    evaluation_count = len(list(evaluation_dir.glob("*.json")))
    print(f"Dataset verified:")
    print(f"  Training tasks:   {training_count}")
    print(f"  Evaluation tasks: {evaluation_count}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download the ARC Challenge dataset for Prometheus ARC experiments."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to store the dataset (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify the existing dataset without downloading.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if dataset already exists.",
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir.resolve()

    print("=" * 60)
    print("ARC Challenge Dataset Downloader")
    print("=" * 60)

    # Verify-only mode
    if args.verify:
        ok = verify_dataset(output_dir)
        sys.exit(0 if ok else 1)

    # Check if dataset already exists
    if not args.force and verify_dataset(output_dir):
        print("\nDataset already present. Use --force to re-download.")
        sys.exit(0)

    print()

    # Download the zip
    zip_path = output_dir.parent / ARC_ZIP_FILENAME
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    if not download_file(ARC_REPO_URL, zip_path):
        print("\nDownload failed. Check your internet connection and try again.")
        sys.exit(1)

    print()

    # Extract
    if not extract_arc_dataset(zip_path, output_dir):
        print("\nExtraction failed.")
        sys.exit(1)

    # Clean up zip
    try:
        zip_path.unlink()
        print(f"Removed temporary file: {zip_path.name}")
    except OSError:
        pass

    print()

    # Final verification
    if verify_dataset(output_dir):
        print("\nARC dataset downloaded and verified successfully.")
        print(f"Location: {output_dir}")
        print("\nYou can now run ARC benchmark tests:")
        print("  pytest tests/arc_tests/ -v")
    else:
        print("\nVerification failed after download. Please check the output directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
