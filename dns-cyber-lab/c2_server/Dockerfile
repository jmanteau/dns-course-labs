# Use Debian Slim as the base image
FROM debian:bullseye-slim


# Set environment variables to use non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive


# RUN echo "deb http://deb.debian.org/debian $(lsb_release -cs) main contrib non-free" > /etc/apt/sources.list

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gpg \
    gpg-agent \
    dirmngr \
    curl \
    sudo \
    build-essential \
    git \
    mingw-w64 \
    binutils-mingw-w64 \
    g++-mingw-w64 \
    gcc \
    libc6-dev \
    libc6-amd64-cross \
    procps \
    lsof \
    zip \
    unzip \ 
    python3 \
    python3-pip \
    python3-netifaces \
    python3-dnslib \
    python3-termcolor \
    python3-validators \
    vim \
    tcpdump \
    iproute2 \
    jq \
    lsb-release \
    debhelper \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# # Need to compile to get the ARM_64 working

# #Set the Go version you want to install
# # When compiling v1.5.x use Go v1.20.7
# ENV GO_VERSION=1.20.7

# #Function to determine the architecture and download Go
# RUN set -e; \
#     #    Determine architecture
#     ARCH=$(uname -m); \
#     case "$ARCH" in \
#     x86_64) ARCH="amd64" ;; \
#     aarch64 | arm64) ARCH="arm64" ;; \
#     armv7l) ARCH="armv6l" ;; \
#     i686 | i386) ARCH="386" ;; \
#     *) echo "Unsupported architecture: $ARCH" && exit 1 ;; \
#     esac; \
#     \
#     #    Determine OS type
#     OS=$(uname | tr '[:upper:]' '[:lower:]'); \
#     \
#     #    Construct the download URL
#     GO_URL="https://go.dev/dl/go${GO_VERSION}.${OS}-${ARCH}.tar.gz"; \
#     echo "Downloading Go from $GO_URL"; \
#     \
#     #    Download and extract Go
#     curl -LO "$GO_URL" && \
#     tar -C /usr/local -xzf "go${GO_VERSION}.${OS}-${ARCH}.tar.gz" && \
#     rm "go${GO_VERSION}.${OS}-${ARCH}.tar.gz"; \
#     \
#     #    Set up Go environment variables
#     export PATH=$PATH:/usr/local/go/bin; \
#     \
#     #   Verify Go installation#
#     go version

# #Set Go environment variables for future use
# ENV PATH=$PATH:/usr/local/go/bin

# # RUN git clone https://github.com/coredns/deployment.git && cd deployment/ && make debian

# # RUN dpkg -i coredns*.deb

# # Create working directory
# WORKDIR /root

# # Clone the Sliver repository
# #RUN git clone https://github.com/BishopFox/sliver.git /root/sliver
# RUN git clone --branch v1.5.39 --single-branch --depth 1 https://github.com/BishopFox/sliver.git /root/sliver


# # Set the working directory to the Sliver repository
# WORKDIR /root/sliver

# # Build Sliver from source
# RUN make 

# RUN mv sliver-server /root/sliver-server && \
#     chmod 755 /root/sliver-server && \
#     mv sliver-client /usr/local/bin/sliver-client && \
#     ln -sf /usr/local/bin/sliver-client /usr/local/bin/sliver && \
#     chmod 755 /usr/local/bin/sliver-client /usr/local/bin/sliver


# # Generate Sliver client configs for root user v1.6
# # RUN echo "Generating Sliver configs for root..." && \
# #     mkdir -p /root/.sliver-client/configs && \
# #     /root/sliver-server operator --name root --lhost localhost --save /root/.sliver-client/configs --permissions all && \
# #     chown -R root:root /root/.sliver-client


### Latest release

# # Fetch the latest Sliver release URLs
# RUN curl -s "https://api.github.com/repos/BishopFox/sliver/releases/latest" | awk -F '"' '/browser_download_url/{print $4}' > artifacts.txt

# # Download Sliver server and client binaries
# RUN grep "sliver-server_linux" artifacts.txt | xargs -n 1 curl -LO && \
#     grep "sliver-client_linux" artifacts.txt | xargs -n 1 curl -LO

# # Verify the downloaded binaries using GPG
# RUN gpg --default-key "$SLIVER_GPG_KEY_ID" --verify "sliver-server_linux.sig" "sliver-server_linux" && \
#     gpg --default-key "$SLIVER_GPG_KEY_ID" --verify "sliver-client_linux.sig" "sliver-client_linux"

# # Move Sliver server and client to appropriate locations
# RUN mv sliver-server_linux /root/sliver-server && \
#     chmod 755 /root/sliver-server && \
#     mv sliver-client_linux /usr/local/bin/sliver-client && \
#     ln -sf /usr/local/bin/sliver-client /usr/local/bin/sliver && \
#     chmod 755 /usr/local/bin/sliver-client /usr/local/bin/sliver



# # Generate Sliver client configs for root user v1.5
# RUN echo "Generating Sliver configs for root..." && \
#     mkdir -p /root/.sliver-client/configs && \
#     /root/sliver-server operator --name root --lhost localhost --save /root/.sliver-client/configs && \
#     chown -R root:root /root/.sliver-client


#### X86 release




# Set up GPG and import the public key
RUN mkdir -p /root/.gnupg && chmod 700 /root/.gnupg && \
    gpg --batch --keyserver keyserver.ubuntu.com --recv-keys $SLIVER_GPG_KEY_ID

# Import Sliver GPG public key
RUN gpg --import <<EOF
-----BEGIN PGP PUBLIC KEY BLOCK-----

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
=lxj2
-----END PGP PUBLIC KEY BLOCK-----
EOF


# Environment variables
ENV SLIVER_URL="https://github.com/BishopFox/sliver/releases/download"
ENV SLIVER_SERVER="sliver-server_linux"
ENV SLIVER_CLIENT="sliver-client_linux"
ENV SLIVER_RELEASE="v1.5.38"
ENV URL_SERVER="${SLIVER_URL}/${SLIVER_RELEASE}/${SLIVER_SERVER}"
ENV URL_CLIENT="${SLIVER_URL}/${SLIVER_RELEASE}/${SLIVER_CLIENT}"



# Download Sliver server and client along with their signatures
RUN curl --silent -L "${URL_SERVER}" --output "/root/${SLIVER_SERVER}" && \
    curl --silent -L "${URL_CLIENT}" --output "/root/${SLIVER_CLIENT}" && \
    curl --silent -L "${URL_SERVER}.sig" --output "/root/${SLIVER_SERVER}.sig" && \
    curl --silent -L "${URL_CLIENT}.sig" --output "/root/${SLIVER_CLIENT}.sig"

# Verify signatures
RUN echo "Verifying signatures..." && \
    gpg --default-key "${SLIVER_GPG_KEY_ID}" --verify "/root/${SLIVER_SERVER}.sig" "/root/${SLIVER_SERVER}" && \
    gpg --default-key "${SLIVER_GPG_KEY_ID}" --verify "/root/${SLIVER_CLIENT}.sig" "/root/${SLIVER_CLIENT}"

# Install and unpack Sliver server
RUN if [ -f "/root/${SLIVER_SERVER}" ]; then \
        echo "Moving the Sliver server executable to /root/sliver-server..."; \
        mv "/root/${SLIVER_SERVER}" /root/sliver-server && \
        echo "Setting permissions for the Sliver server executable..."; \
        chmod 755 /root/sliver-server && \
        echo "Unpacking the Sliver server..."; \
        /root/sliver-server unpack --force; \
    else \
        exit 3; \
    fi

# Install Sliver client
RUN if [ -f "/root/${SLIVER_CLIENT}" ]; then \
        echo "Setting permissions for the Sliver client executable..."; \
        chmod 755 "/root/${SLIVER_CLIENT}" && \
        echo "Copying the Sliver client executable to /usr/local/bin/sliver-client..."; \
        cp -vv "/root/${SLIVER_CLIENT}" /usr/local/bin/sliver-client && \
        echo "Creating a symbolic link for sliver-client at /usr/local/bin/sliver..."; \
        ln -sf /usr/local/bin/sliver-client /usr/local/bin/sliver && \
        echo "Setting permissions for the symbolic link /usr/local/bin/sliver..."; \
        chmod 755 /usr/local/bin/sliver; \
    else \
        exit 3; \
    fi

# Generate Sliver client configs for root user v1.5
RUN echo "Generating Sliver configs for root..." && \
    mkdir -p /root/.sliver-client/configs && \
    /root/sliver-server operator --name root --lhost localhost --save /root/.sliver-client/configs && \
    chown -R root:root /root/.sliver-client


# Expose ports used by Sliver
EXPOSE 8888 8443 31337 53

# Copy python DNS payload transfer 
COPY c2_server/infiltration_dns_server.py /infiltration_dns_server.py

# Copy entrypoint script
COPY c2_server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]