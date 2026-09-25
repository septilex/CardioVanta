import os
import sys

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app

# Vercel needs a handler for serverless execution, but for FastAPI 
# it can just export the `app` instance.
