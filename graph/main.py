import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly as a script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from run_pipeline import main

if __name__ == "__main__":
    main()
