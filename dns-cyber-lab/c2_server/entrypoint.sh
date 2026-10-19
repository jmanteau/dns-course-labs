#!/bin/bash
set -e

# Unpack Sliver assets on first start (moved from Dockerfile for QEMU compatibility)
if [ ! -f /root/.sliver-server-unpacked ]; then
    echo "First start: unpacking Sliver server assets..."
    /opt/sliver-server unpack --force
    touch /root/.sliver-server-unpacked
fi

# Generate operator config if not already done
mkdir -p /root/.sliver-client/configs
if [ -z "$(ls -A /root/.sliver-client/configs/ 2>/dev/null)" ]; then
    echo "Generating Sliver operator configs..."
    /opt/sliver-server operator --name root --lhost localhost --permissions all --save /root/.sliver-client/configs
    chown -R root:root /root/.sliver-client
fi

echo "Starting Sliver server daemon..."
exec /opt/sliver-server daemon
