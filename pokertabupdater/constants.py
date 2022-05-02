"""Stores constants for all modules."""

import os


PROJECT_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_BASE_DIR, "config.json")
CREDS_PATH = os.path.join(PROJECT_BASE_DIR, "credentials.json")
