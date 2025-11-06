#!/bin/bash
set -e

echo "Starting Sliver server (assets will unpack on first use)..."
# Sliver will auto-unpack assets on first daemon start
# Pre-create config directory
mkdir -p /root/.sliver-client/configs

# Start server - it will unpack assets automatically on first run
exec /opt/sliver-server daemon
