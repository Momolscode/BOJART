#!/usr/bin/env python3
"""Absolute-path entry point for any compatible local MCP stdio client."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bojart_memory.mcp import main
if __name__ == '__main__': main()
