#!/bin/sh

echo "Starting of $(hostname)"

# Install dig (bind-tools) for DNS testing
apk add --no-cache bind-tools bash tcpdump

# Wait until dns_internal is available
until nslookup dns_internal >/dev/null 2>&1; do
    echo "Waiting for dns_internal to be available..."
    sleep 2
done

# Get the IP address of dns_internal
DNS_SERVER_IP=$(getent hosts dns_internal | awk '{ print $1 }')

# Check if DNS_SERVER_IP was successfully retrieved
if [ -z "$DNS_SERVER_IP" ]; then
    echo "Failed to get IP address of dns_internal"
    exit 1
fi

echo "Using dns_internal IP: $DNS_SERVER_IP as DNS server"

# Configure resolv.conf to use dns_internal as the DNS server
echo "nameserver $DNS_SERVER_IP" >/etc/resolv.conf

cat <<EOF > /flag.txt
888888888888888888888888888888888888888888888888888888888888
888888888888888888888888888888888888888888888888888888888888
8888888888888888888888888P""  ""9888888888888888888888888888
8888888888888888P"88888P          988888"9888888888888888888
8888888888888888  "9888            888P"  888888888888888888
888888888888888888bo "9  d8o  o8b  P" od88888888888888888888
888888888888888888888bob 98"  "8P dod88888888888888888888888
888888888888888888888888    db    88888888888888888888888888
88888888888888888888888888      8888888888888888888888888888
88888888888888888888888P"9bo  odP"98888888888888888888888888
88888888888888888888P" od88888888bo "98888888888888888888888
888888888888888888   d88888888888888b   88888888888888888888
8888888888888888888oo8888888888888888oo888888888888888888888
8888888888888888888888888888888888888888888888888O8888888888
EOF


# Keep the container running for testing
#exec /bin/sh -c "tail -f /dev/null"


# Run the DNS resolution script
echo "Starting DNS resolution loop..."


# Path to the DNS list file
DNS_LIST="/shared-data/dnslist.txt"


# Check if the file exists
if [[ ! -f "$DNS_LIST" ]]; then
  echo "Error: $DNS_LIST not found!"
  exit 1
fi


# Infinite loop to resolve a random DNS entry
while true; do
  # Read all lines into a list
  dns_entries=$(cat "$DNS_LIST")
  
  # Check if the file is not empty
  if [ -z "$dns_entries" ]; then
    echo "Error: $DNS_LIST is empty!"
    exit 1
  fi

  # Convert lines to an array equivalent
  dns_array=$(echo "$dns_entries" | tr '\n' ' ')

  # Count the number of entries
  entry_count=$(echo "$dns_array" | wc -w)

  # Pick a random index between 1 and entry_count
  random_index=$(shuf -i 1-"$entry_count" -n 1)

  # Extract the DNS entry at the random index
  random_entry=$(echo "$dns_array" | awk "{print \$${random_index}}")

  # Resolve the DNS entry
  echo "Resolving: $random_entry"
  nslookup "$random_entry" > /dev/null 2>&1

  # Wait for half a second
  sleep 0.5
done