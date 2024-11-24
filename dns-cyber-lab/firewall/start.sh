#!/bin/sh

# Ensure the system is up-to-date and install iptables
apk update
apk add --no-cache iptables

echo "Setting up firewall rules..."

# Enable IP forwarding if it's not already enabled
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    echo 1 >/proc/sys/net/ipv4/ip_forward
fi

# Flush existing iptables rules to start fresh
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Set default policies to accept all traffic (permissive)
#iptables -P INPUT ACCEPT
#iptables -P FORWARD ACCEPT
#iptables -P OUTPUT ACCEPT

# Set default policies to drop all traffic
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Allow established and related connections
iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Allow DNS traffic (TCP and UDP on port 53)
iptables -A FORWARD -p udp --dport 53 -j ACCEPT
iptables -A FORWARD -p tcp --dport 53 -j ACCEPT

# Allow ICMP (ping) traffic
#iptables -A INPUT -p icmp -j ACCEPT
#iptables -A FORWARD -p icmp -j ACCEPT


# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "INPUT DROP: " --log-level 4
iptables -A OUTPUT -j LOG --log-prefix "OUTPUT DROP: " --log-level 4
iptables -A FORWARD -j LOG --log-prefix "FORWARD DROP: " --log-level 4


# Enable NAT for outgoing traffic
#iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

echo "Firewall rules applied successfully."

# Keep the container running
tail -f /dev/null
