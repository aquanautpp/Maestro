"""Railway entry point - imports the Flask app from algorithm folder."""
import sys
from pathlib import Path

# Add algorithm folder to path
sys.path.insert(0, str(Path(__file__).parent / "algorithm"))

from realtime_detector import app

if __name__ == "__main__":
    app.run()
