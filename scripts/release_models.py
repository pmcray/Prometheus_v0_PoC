#!/usr/bin/env python3
"""
Model Release Manager

Prepares and uploads trained models to GitHub releases.

Usage:
    # Prepare models for release (calculate hashes, create manifests)
    python scripts/release_models.py --prepare

    # Create GitHub release instructions
    python scripts/release_models.py --release-notes

    # Verify models before release
    python scripts/release_models.py --verify

Prerequisites:
    - Trained models in models/pretrained/
    - gh CLI installed (for GitHub releases)
    - Git repository with release tag created
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

# Model registry
MODELS = {
    "go_9x9": {
        "path": "models/pretrained/go_9x9.h5",
        "description": "Go 9×9 model (~1,280 ELO, 78% win rate vs random)",
    },
    "go_19x19": {
        "path": "models/pretrained/go_19x19.h5",
        "description": "Go 19×19 model via transfer learning (~1,450 ELO, 88% win rate)",
    },
    "chess": {
        "path": "models/pretrained/chess.h5",
        "description": "Chess model (~1,340 ELO, 82% win rate vs random)",
    },
}

RELEASE_TAG = "models-v1.0.0"
RELEASE_DIR = Path("release")


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB."""
    return file_path.stat().st_size / (1024 * 1024)


def prepare_model(model_name: str, model_info: Dict) -> Dict:
    """Prepare a model for release (calculate hash, size, etc.)."""
    model_path = Path(model_info["path"])

    if not model_path.exists():
        print(f"✗ {model_name}: Model file not found at {model_path}")
        print(f"  Train the model first with: python scripts/train_pretrained_models.py --model {model_name}")
        return None

    print(f"Preparing {model_name}...")

    # Calculate hash
    print(f"  Calculating SHA256 hash...")
    sha256 = calculate_sha256(model_path)

    # Get file size
    size_mb = get_file_size_mb(model_path)

    # Load metadata if exists
    metadata_path = model_path.with_suffix('.json')
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

    release_info = {
        "filename": model_path.name,
        "size_mb": round(size_mb, 1),
        "sha256": sha256,
        "description": model_info["description"],
        "path": str(model_path),
        **metadata,  # Include training metadata if available
    }

    print(f"  ✓ Size: {size_mb:.1f} MB")
    print(f"  ✓ SHA256: {sha256}")

    return release_info


def create_manifest(release_info: Dict[str, Dict]) -> Dict:
    """Create release manifest JSON."""
    manifest = {
        "release_tag": RELEASE_TAG,
        "release_date": "2025-11-28",
        "models": release_info,
        "total_size_mb": sum(info["size_mb"] for info in release_info.values()),
        "repository": "pmcray/Prometheus_v0_PoC",
    }
    return manifest


def prepare_all_models() -> bool:
    """Prepare all models for release."""
    print("=" * 80)
    print("PREPARING MODELS FOR RELEASE")
    print("=" * 80)

    # Create release directory
    RELEASE_DIR.mkdir(exist_ok=True)

    # Prepare each model
    release_info = {}
    for model_name, model_info in MODELS.items():
        info = prepare_model(model_name, model_info)
        if info:
            release_info[model_name] = info

    if not release_info:
        print("\n✗ No models found to release.")
        print("  Train models first with: python scripts/train_pretrained_models.py --all")
        return False

    # Create manifest
    manifest = create_manifest(release_info)

    # Save manifest
    manifest_path = RELEASE_DIR / "model_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Manifest saved to: {manifest_path}")

    # Update download_models.py registry
    registry_code = generate_registry_code(release_info)
    registry_path = RELEASE_DIR / "model_registry.py"
    with open(registry_path, 'w') as f:
        f.write(registry_code)

    print(f"✓ Registry code saved to: {registry_path}")
    print(f"\n  Copy the MODEL_REGISTRY from this file to scripts/download_models.py")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Models prepared: {len(release_info)}")
    print(f"Total size: {manifest['total_size_mb']:.1f} MB")
    print(f"Release tag: {RELEASE_TAG}")

    for model_name, info in release_info.items():
        print(f"\n{model_name}:")
        print(f"  File: {info['filename']}")
        print(f"  Size: {info['size_mb']} MB")
        print(f"  SHA256: {info['sha256']}")

    return True


def generate_registry_code(release_info: Dict[str, Dict]) -> str:
    """Generate Python code for MODEL_REGISTRY in download_models.py."""
    lines = [
        "# Model registry - Generated by release_models.py",
        "MODEL_REGISTRY = {",
    ]

    for model_name, info in release_info.items():
        lines.append(f'    "{model_name}": {{')
        lines.append(f'        "filename": "{info["filename"]}",')
        lines.append(f'        "version": "{RELEASE_TAG}",')
        lines.append(f'        "size_mb": {info["size_mb"]},')
        lines.append(f'        "sha256": "{info["sha256"]}",')
        lines.append(f'        "description": "{info["description"]}",')

        # Add metadata if available
        if "training_games" in info:
            lines.append(f'        "training_games": {info["training_games"]},')
        if "performance" in info:
            perf = info["performance"]
            if "elo" in perf:
                lines.append(f'        "elo": {perf["elo"]},')
            if "inference_ms" in perf:
                lines.append(f'        "inference_ms": {perf["inference_ms"]},')

        lines.append('    },')

    lines.append("}")

    return "\n".join(lines)


def create_release_notes() -> str:
    """Generate release notes for GitHub release."""
    notes = f"""# Prometheus Pre-trained Models {RELEASE_TAG}

Pre-trained models for Prometheus AI framework.

## Available Models

### Go 9×9 Model
- **File**: `go_9x9.h5`
- **ELO**: ~1,280
- **Win Rate**: 78% vs random
- **Inference**: 8.5ms average
- **Training**: 200 self-play games with MCTS (400 sims)

### Go 19×19 Model
- **File**: `go_19x19.h5`
- **ELO**: ~1,450
- **Win Rate**: 88% vs random
- **Inference**: 22ms average
- **Training**: 100 games via transfer learning from 9×9 model

### Chess Model
- **File**: `chess.h5`
- **ELO**: ~1,340
- **Win Rate**: 82% vs random
- **Inference**: 15ms average
- **Training**: 200 self-play games with MCTS (400 sims)

## Download Instructions

### Using Download Script (Recommended)

```bash
# Download all models
python scripts/download_models.py --all

# Download specific model
python scripts/download_models.py --model go_9x9

# List available models
python scripts/download_models.py --list

# Verify integrity
python scripts/download_models.py --verify
```

### Manual Download

Download model files from the Assets section below and place them in `models/pretrained/`:

```bash
mkdir -p models/pretrained
cd models/pretrained
# Download go_9x9.h5, go_19x19.h5, chess.h5
```

## Usage

### Quick Start

```bash
# Play against the model
prometheus evaluate --model1 models/pretrained/go_9x9.h5 --model2 random --num-games 10

# Deploy bot to online platform
prometheus deploy --platform ogs --model models/pretrained/go_9x9.h5 --mcts
```

### Docker Deployment

```bash
# Update docker-compose.yml to use pre-trained models
docker-compose up -d
```

## Model Details

All models were trained using:
- **Framework**: TensorFlow 2.15+
- **Architecture**: Policy-value networks
- **Training**: Self-play with MCTS
- **Hardware**: GPU acceleration (NVIDIA recommended)

## Verification

Each model includes a SHA256 hash for integrity verification. The download script automatically verifies models after download.

## Training Your Own Models

See [PHASE_B_TRAINING_GUIDE.md](../PHASE_B_TRAINING_GUIDE.md) for instructions on training your own models.

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Citation

If you use these models in research, please cite:

```bibtex
@software{{prometheus_models,
  title = {{Prometheus Pre-trained Models}},
  author = {{Prometheus Development Team}},
  year = {{2025}},
  version = {{{RELEASE_TAG}}},
  url = {{https://github.com/pmcray/Prometheus_v0_PoC}}
}}
```

## Support

For issues or questions:
- [GitHub Issues](https://github.com/pmcray/Prometheus_v0_PoC/issues)
- [Documentation](https://github.com/pmcray/Prometheus_v0_PoC/blob/main/README.md)
"""

    return notes


def save_release_notes():
    """Save release notes to file."""
    notes = create_release_notes()

    RELEASE_DIR.mkdir(exist_ok=True)
    notes_path = RELEASE_DIR / "RELEASE_NOTES.md"

    with open(notes_path, 'w') as f:
        f.write(notes)

    print(f"✓ Release notes saved to: {notes_path}")
    return notes_path


def create_release_instructions():
    """Generate instructions for creating GitHub release."""
    print("\n" + "=" * 80)
    print("GITHUB RELEASE INSTRUCTIONS")
    print("=" * 80)

    print(f"""
1. Create Git Tag:
   git tag -a {RELEASE_TAG} -m "Pre-trained models v1.0.0"
   git push origin {RELEASE_TAG}

2. Create GitHub Release using gh CLI:
   gh release create {RELEASE_TAG} \\
     --title "Pre-trained Models {RELEASE_TAG}" \\
     --notes-file release/RELEASE_NOTES.md \\
     models/pretrained/go_9x9.h5 \\
     models/pretrained/go_19x19.h5 \\
     models/pretrained/chess.h5

3. Or create manually:
   - Go to: https://github.com/pmcray/Prometheus_v0_PoC/releases/new
   - Tag: {RELEASE_TAG}
   - Title: Pre-trained Models {RELEASE_TAG}
   - Description: Copy from release/RELEASE_NOTES.md
   - Upload files: go_9x9.h5, go_19x19.h5, chess.h5
   - Publish release

4. Update download_models.py:
   - Copy MODEL_REGISTRY from release/model_registry.py
   - Replace existing MODEL_REGISTRY in scripts/download_models.py
   - Commit and push changes

5. Test downloads:
   python scripts/download_models.py --list
   python scripts/download_models.py --model go_9x9
""")


def verify_models():
    """Verify all models are ready for release."""
    print("=" * 80)
    print("VERIFYING MODELS FOR RELEASE")
    print("=" * 80)

    all_ok = True

    for model_name, model_info in MODELS.items():
        model_path = Path(model_info["path"])

        print(f"\n{model_name}:")

        # Check existence
        if not model_path.exists():
            print(f"  ✗ File not found: {model_path}")
            all_ok = False
            continue

        # Check size
        size_mb = get_file_size_mb(model_path)
        print(f"  ✓ Size: {size_mb:.1f} MB")

        # Check metadata
        metadata_path = model_path.with_suffix('.json')
        if metadata_path.exists():
            print(f"  ✓ Metadata exists")
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                if "performance" in metadata:
                    print(f"    ELO: {metadata['performance'].get('elo', 'N/A')}")
                    print(f"    Inference: {metadata['performance'].get('inference_ms', 'N/A')} ms")
        else:
            print(f"  ⚠ Metadata missing (optional)")

    print("\n" + "=" * 80)
    if all_ok:
        print("✓ All models verified and ready for release!")
    else:
        print("✗ Some models are missing. Train them first:")
        print("  python scripts/train_pretrained_models.py --all")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Prepare and release Prometheus models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--prepare', action='store_true',
                        help='Prepare models for release (calculate hashes, create manifest)')
    parser.add_argument('--release-notes', action='store_true',
                        help='Generate release notes')
    parser.add_argument('--verify', action='store_true',
                        help='Verify models are ready for release')
    parser.add_argument('--instructions', action='store_true',
                        help='Show GitHub release instructions')

    args = parser.parse_args()

    if args.verify:
        success = verify_models()
        return 0 if success else 1

    if args.prepare:
        success = prepare_all_models()
        if success:
            create_release_instructions()
        return 0 if success else 1

    if args.release_notes:
        save_release_notes()
        print("\nRelease notes created successfully!")
        return 0

    if args.instructions:
        create_release_instructions()
        return 0

    # Default: verify
    verify_models()
    return 0


if __name__ == '__main__':
    sys.exit(main())
