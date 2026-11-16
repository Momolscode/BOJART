"""One private default shared by the CLI, launcher and HTTP read endpoints."""
import os
from pathlib import Path


def default_state():
    value = os.environ.get('BOJART_MEMORY_STATE')
    return Path(value).expanduser() if value else Path.home() / 'BOJART' / 'memory'
