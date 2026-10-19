#!/bin/sh

echo "=== Starting dns_public: $(hostname) ==="

echo "=== Fixing permissions for BIND directories ==="
# Fix permissions for bind-mounted directories (named user needs write access)
chown -R named:named /var/cache/bind /var/lib/bind /var/log /etc/bind 2>/dev/null
chmod -R 777 /var/cache/bind /var/lib/bind /var/log /etc/bind 2>/dev/null
mkdir -p /var/cache/bind /var/lib/bind

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

cp /var/lib/bind/db.com.template /var/lib/bind/db.com
sed -i "s/127.0.0.2/$C2_IP/" /var/lib/bind/db.com

cp /etc/bind/named.conf.template /etc/bind/named.conf
sed -i "s/127.0.0.2/$C2_IP/" /etc/bind/named.conf

chown named:named /var/lib/bind/db.commandcontrol.com /var/lib/bind/db.com /etc/bind/named.conf
chmod 666 /var/lib/bind/db.commandcontrol.com /var/lib/bind/db.com /etc/bind/named.conf

# IP address of dns_public
DNS_PUBLIC_IP=$(hostname -i)
echo "IP of DNS PUB $DNS_PUBLIC_IP"

echo "$DNS_PUBLIC_IP" >/shared-data/dns_public_ip.txt

# Start BIND9 in the foreground as named user
exec named -u named -g
