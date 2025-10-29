"""Main entry point for SPK pose detection application"""

import sys
from app.bodyModel.pose_detector import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
