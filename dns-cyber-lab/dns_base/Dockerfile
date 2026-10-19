# Multi-arch BIND9 image based on Alpine (works on amd64 + arm64)
FROM alpine:3.20

RUN apk add --no-cache bind bind-tools tcpdump iproute2 \
    fstrm-utils protobuf-c python3 py3-pip vim && \
    pip install --no-cache-dir --break-system-packages rich tldextract pyyaml && \
    mkdir -p /var/cache/bind /var/lib/bind /var/run/named /var/log && \
    chown -R named:named /var/cache/bind /var/lib/bind /var/run/named /var/log /etc/bind && \
    rm -f /usr/bin/vi && ln -s /usr/bin/vim /usr/bin/vi

EXPOSE 53/tcp 53/udp 953/tcp
