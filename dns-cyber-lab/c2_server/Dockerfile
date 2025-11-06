# Use Debian Slim as base image - forced to x86_64
FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV SLIVER_RELEASE="v1.5.38"
ENV SLIVER_GPG_KEY_ID="0ED3900D296CFA0283A4E4667DF912404449039C"

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gpg gpg-agent dirmngr curl procps lsof vim tcpdump iproute2 jq \
    python3 python3-pip python3-netifaces python3-dnslib python3-termcolor python3-validators \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Import Sliver GPG key
RUN gpg --batch --keyserver keyserver.ubuntu.com --recv-keys ${SLIVER_GPG_KEY_ID}

# Download and verify Sliver x86_64 binaries
RUN curl -LO "https://github.com/BishopFox/sliver/releases/download/${SLIVER_RELEASE}/sliver-server_linux" && \
    curl -LO "https://github.com/BishopFox/sliver/releases/download/${SLIVER_RELEASE}/sliver-client_linux" && \
    curl -LO "https://github.com/BishopFox/sliver/releases/download/${SLIVER_RELEASE}/sliver-server_linux.sig" && \
    curl -LO "https://github.com/BishopFox/sliver/releases/download/${SLIVER_RELEASE}/sliver-client_linux.sig" && \
    gpg --verify sliver-server_linux.sig sliver-server_linux && \
    gpg --verify sliver-client_linux.sig sliver-client_linux && \
    mv sliver-server_linux /opt/sliver-server && \
    mv sliver-client_linux /opt/sliver-client && \
    rm -f *.sig

# Setup Sliver binaries and unpack server assets
RUN chmod 755 /opt/sliver-server /opt/sliver-client && \
    ln -s /opt/sliver-client /usr/local/bin/sliver && \
    echo "Unpacking Sliver server assets..." && \
    /opt/sliver-server unpack --force

# Generate Sliver client operator config for root user
RUN echo "Generating Sliver operator configs..." && \
    mkdir -p /root/.sliver-client/configs && \
    /opt/sliver-server operator --name root --lhost localhost --save /root/.sliver-client/configs && \
    chown -R root:root /root/.sliver-client

EXPOSE 8888 8443 31337 53

# Copy lab files
COPY c2_server/infiltration_dns_server.py /infiltration_dns_server.py
COPY c2_server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
