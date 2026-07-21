import sys
import os

# Add src folder to python path for Vercel Serverless Function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from trumorgpt.app import app
