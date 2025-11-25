#!/bin/sh

echo "Starting of $(hostname)"

apk add tcpdump fstrm-utils protobuf-c python3 py3-pip vim

pip install rich tldextract pyyaml  --break-system-packages
tldextract --update

# Remove existing vi symlink or binary
rm -f /usr/bin/vi

# Create symlink from vi to vim
ln -s /usr/bin/vim /usr/bin/vi


cat << 'EOF' > ~/.vimrc
" Vim configuration for Python development
syntax on
filetype plugin indent on
set number
set autoindent
set tabstop=4
set shiftwidth=4
set expandtab
set background=dark
colorscheme desert
EOF

cat << 'EOF' > /root/.vimrc
" Vim configuration for Python development
syntax on
filetype plugin indent on
set number
set autoindent
set tabstop=4
set shiftwidth=4
set expandtab
set background=dark
colorscheme desert
EOF



touch  /var/log/queries.log
#chown bind:bind /var/log/queries.log
#chmod 640 /var/log/queries.log

touch  /var/log/responses.log
#chown bind:bind /var/log/responses.log
#chmod 640 /var/log/responses.log

FIREWALL_IP=$(getent hosts firewall | awk '{ print $1 }')
# Set the default route to the firewall
ip route del default
ip route add default via $FIREWALL_IP

# Wait for the IP file to be created by dns_public
while [ ! -f /shared-data/dns_public_ip.txt ]; do
    echo "Waiting for dns_public to write its IP address..."
    sleep 2
done

# Read the IP address from the file
DNS_PUBLIC_IP=$(cat /shared-data/dns_public_ip.txt)

rm /shared-data/dns_public_ip.txt

echo "Using dns_public IP: $DNS_PUBLIC_IP as forwarder"

# Replace placeholder IP (127.0.0.2) in named.conf.options with dns_public's actual IP
cp /etc/bind/named.conf.template /etc/bind/named.conf
sed -i "s/127.0.0.2/$DNS_PUBLIC_IP/" /etc/bind/named.conf



echo "Starting BIND9 service with dns_public as forwarder"

# Start the BIND service
named

fstrm_capture -t protobuf:dnstap.Dnstap -u /var/run/named/dnstap.sock -w /var/log/log.dnstap 

# Keep the container running
exec /bin/sh -c "tail -f /dev/null"
