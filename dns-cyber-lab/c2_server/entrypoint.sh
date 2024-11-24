#!/bin/bash
set -e

echo "Starting Sliver server..."
exec /root/sliver-server daemon

#exec /bin/sh -c "tail -f /dev/null"
