#!/bin/bash

DOMAIN=$1
ROOT_SERVER="127.0.0.1"

echo "Starting trace for $DOMAIN..."
CURRENT_DOMAIN=$DOMAIN

while true; do
    # Query the current domain's NS record
    echo "Querying NS for $CURRENT_DOMAIN at $ROOT_SERVER"
    OUTPUT=$(dig @$ROOT_SERVER $CURRENT_DOMAIN NS +short)
    if [[ -z $OUTPUT ]]; then
        echo "No further NS records found for $CURRENT_DOMAIN."
        break
    fi

    # Get the next authoritative server
    NEXT_SERVER=$(echo "$OUTPUT" | head -n 1)

    echo "Next server: $NEXT_SERVER"

    # If we're at the final authoritative server, query the A record
    if [[ $CURRENT_DOMAIN == $DOMAIN ]]; then
        echo "Querying A record for $DOMAIN at $NEXT_SERVER"
        dig @$NEXT_SERVER $DOMAIN A
        break
    fi

    # Update the current domain and root server
    CURRENT_DOMAIN=$(echo "$CURRENT_DOMAIN" | sed 's/^[^\.]*\.//')
    ROOT_SERVER=$NEXT_SERVER
done

