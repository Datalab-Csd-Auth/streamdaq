#!/bin/bash
set -e

echo "Starting the StreamDAQ API..."
uv run python run_api.py
