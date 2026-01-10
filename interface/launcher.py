import sys
from pathlib import Path

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

import src
from src.main import main

if __name__ == "__main__":
    main()