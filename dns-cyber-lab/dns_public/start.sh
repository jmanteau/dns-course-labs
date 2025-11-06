#!/bin/sh

echo "=== Starting dns_public: $(hostname) ==="

apk add tcpdump

echo "=== Fixing permissions for BIND directories ==="
# Fix permissions for BIND directories (BIND runs as user 'bind' UID 53, GID 53)
chown -R 53:53 /var/cache/bind /var/lib/bind /var/log /etc/bind 2>&1
chmod -R 775 /var/cache/bind /var/lib/bind 2>&1
chmod 755 /var/log /etc/bind 2>&1
find /etc/bind -type f -exec chmod 644 {} \; 2>&1
# Ensure writable subdirectories
mkdir -p /var/cache/bind /var/lib/bind
chown 53:53 /var/cache/bind /var/lib/bind

echo "=== Permissions fixed, verifying ==="
ls -la /var/cache/bind/ | head -5
ls -la /etc/bind/ | head -5
echo "=== Verification complete ==="

# Set the default route to the firewall
FIREWALL_IP=$(getent hosts firewall | awk '{ print $1 }')
echo "IP of FIREWALL_IP $FIREWALL_IP"

ip route del default
ip route add default via $FIREWALL_IP

sleep 1

# C2 Zone config
C2_IP=$(getent hosts c2_server | awk '{ print $1 }')
echo "IP of C2 $C2_IP"
cp /var/lib/bind/db.commandcontrol.com.template /var/lib/bind/db.commandcontrol.com
sed -i "s/127.0.0.2/$C2_IP/" /var/lib/bind/db.commandcontrol.com

cp /etc/bind/named.conf.template /etc/bind/named.conf
sed -i "s/127.0.0.2/$C2_IP/" /etc/bind/named.conf

# Fix permissions after copying/modifying files
chown 53:53 /var/lib/bind/db.commandcontrol.com /etc/bind/named.conf
chmod 644 /var/lib/bind/db.commandcontrol.com /etc/bind/named.conf

# IP address of dns_public
DNS_PUBLIC_IP=$(hostname -i)
echo "IP of DNS PUB $DNS_PUBLIC_IP"

echo "$DNS_PUBLIC_IP" >/shared-data/dns_public_ip.txt

# Start BIND9 in the foreground as bind user
exec named -u bind -g
