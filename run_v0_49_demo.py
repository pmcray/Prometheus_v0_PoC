"""
Simple runner script for the Prometheus v0.49 demonstration
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prometheus_v0_49_demonstrator import main

if __name__ == "__main__":
    print("Starting Prometheus v0.49 Demonstration...")
    print("This demonstrates all features from the v0.45-v0.49 workplan")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemonstration interrupted by user")
    except Exception as e:
        print(f"\nDemonstration failed with error: {e}")
        import traceback
        traceback.print_exc()

    print("\nDemonstration complete.")