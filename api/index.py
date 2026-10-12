import os
import sys

# Add src folder to the Python path for the Vercel serverless function.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from trumorgpt.app import app  # noqa: E402

# Vercel's Python builder looks for a top-level ASGI callable named app/application/handler.
application = app
handler = app
