import os
import sys

# Ensure the root project directory is in sys.path so modules (app, database, auth_utils, etc.) can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app

# Vercel looks for the WSGI/ASGI 'app' object
app = app
