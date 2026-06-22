#!/bin/bash
set -e

echo "Syncing dependencies with uv..."
uv sync

echo "Starting the StreamDAQ API..."
uv run python run_api.py
