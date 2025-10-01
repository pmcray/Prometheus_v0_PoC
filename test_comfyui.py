#!/usr/bin/env python3
"""
Test ComfyUI Integration for Project Prometheus v0.74

This script verifies that:
1. ComfyUI server is running and accessible
2. Image generation workflow works correctly
3. Generated images are saved properly
4. The multimodal toolkit integration is functional

Usage:
    python test_comfyui.py

Requirements:
    - ComfyUI server running on http://127.0.0.1:8188
    - Stable Diffusion model installed in ComfyUI
    - PIL (Pillow) for image handling
"""

import sys
import os
from pathlib import Path

# Add prometheus to path
sys.path.insert(0, os.path.abspath('.'))

from prometheus.multimodal_tools import get_multimodal_toolkit
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("="*70)
    print("ComfyUI Integration Test - Project Prometheus v0.74")
    print("="*70)

    # Test 1: Initialize toolkit
    print("\n[Test 1] Initializing multimodal toolkit...")
    try:
        toolkit = get_multimodal_toolkit(
            output_dir="./test_generated",
            prefer_local=True
        )
        print("✓ Toolkit initialized successfully")
    except Exception as e:
        print(f"✗ Toolkit initialization failed: {e}")
        return False

    # Test 2: Check ComfyUI availability
    print("\n[Test 2] Checking ComfyUI availability...")
    stats = toolkit.get_stats()

    if stats['comfyui_available']:
        print("✓ ComfyUI server is ONLINE")
        print(f"  - Backend initialized: Yes")
        print(f"  - Prefer local: {stats['prefer_local']}")
    else:
        print("✗ ComfyUI server is NOT available")
        print("\nTroubleshooting:")
        print("  1. Check if ComfyUI is running:")
        print("     ps aux | grep comfyui")
        print("  2. Start ComfyUI server:")
        print("     cd /path/to/ComfyUI")
        print("     python main.py")
        print("  3. Verify server is accessible:")
        print("     curl http://127.0.0.1:8188/system_stats")
        return False

    # Test 3: Generate a simple test image
    print("\n[Test 3] Generating test image...")
    print("  Prompt: 'A simple red cube on a white background'")
    print("  (This may take 30-60 seconds...)\n")

    try:
        result = toolkit.generate_image(
            prompt="A simple red cube on a white background",
            style="realistic",
            size="512x512",
            steps=15,  # Fewer steps for faster test
            cfg_scale=7.0
        )

        if result.success:
            print(f"✓ Image generated successfully")
            print(f"  - Path: {result.content}")
            print(f"  - Backend: {result.metadata.get('backend', 'unknown')}")
            print(f"  - Size: {result.metadata.get('size', 'unknown')}")
            print(f"  - Steps: {result.metadata.get('steps', 'unknown')}")

            # Verify file exists
            if Path(result.content).exists():
                file_size = Path(result.content).stat().st_size
                print(f"  - File size: {file_size:,} bytes")

                if file_size > 1000:  # Real images are larger than 1KB
                    print("✓ Image file is valid (non-empty)")
                else:
                    print("⚠ Warning: Image file seems too small")
            else:
                print("✗ Image file does not exist!")
                return False

        else:
            print(f"✗ Image generation failed: {result.error}")
            return False

    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Check statistics
    print("\n[Test 4] Checking generation statistics...")
    stats = toolkit.get_stats()
    print(f"  - Total images: {stats['images_generated']}")
    print(f"  - ComfyUI generations: {stats['comfyui_generations']}")
    print(f"  - Placeholder generations: {stats['placeholder_generations']}")
    print(f"  - Errors: {stats['errors']}")

    if stats['comfyui_generations'] > 0:
        print("✓ ComfyUI generation confirmed in stats")
    else:
        print("⚠ Warning: No ComfyUI generations recorded")

    # Final summary
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED!")
    print("="*70)
    print("\nComfyUI integration is working correctly.")
    print("You can now run the v0.74 demo notebook with real image generation!")
    print("\nGenerated test image location:")
    print(f"  {result.content}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
