# Use Debian Slim as base image — multi-arch (amd64 + arm64)
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV SLIVER_RELEASE="v1.7.8"

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl procps lsof vim tcpdump iproute2 jq \
    python3 python3-pip python3-dnslib python3-termcolor python3-validators \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Determine architecture and download matching Sliver binaries
RUN ARCH=$(dpkg --print-architecture) && \
    echo "Building for architecture: ${ARCH}" && \
    curl -LO "https://github.com/BishopFox/sliver/releases/download/${SLIVER_RELEASE}/sliver-server_linux-${ARCH}" && \
    curl -LO "https://github.com/BishopFox/sliver/releases/download/${SLIVER_RELEASE}/sliver-client_linux-${ARCH}" && \
    mv "sliver-server_linux-${ARCH}" /opt/sliver-server && \
    mv "sliver-client_linux-${ARCH}" /opt/sliver-client

# Setup Sliver binaries (unpack and operator config happen at first start via entrypoint)
RUN chmod 755 /opt/sliver-server /opt/sliver-client && \
    ln -s /opt/sliver-client /usr/local/bin/sliver

EXPOSE 8888 8443 31337 53

# Copy lab files
COPY c2_server/infiltration_dns_server.py /infiltration_dns_server.py
COPY c2_server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
