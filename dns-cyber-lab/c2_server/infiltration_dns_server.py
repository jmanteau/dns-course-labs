import base64
import os
import socket
import struct
import sys
import threading
from typing import List

from dnslib import QTYPE, RR, TXT, DNSHeader, DNSRecord


def read_and_split_file(file_path: str, chunk_size: int = 220) -> List[str]:
    """
    Reads a file, encodes its content in base64, and splits it into chunks.

    Args:
        file_path (str): The path to the file to encode and split.
        chunk_size (int): The size of each chunk in bytes (default is 220).

    Returns:
        List[str]: A list of base64-encoded chunks of the file.
    """
    with open(file_path, "rb") as f:
        encoded_data = base64.b64encode(f.read()).decode("utf-8")
    return [
        encoded_data[i : i + chunk_size]
        for i in range(0, len(encoded_data), chunk_size)
    ]


def handle_request(data, addr, sock, chunks, subdomain, is_tcp=False):
    """
    Handle an incoming DNS query.
    """
    request = DNSRecord.parse(data)
    qname = str(request.q.qname).strip(".")

    # Check if the query matches our subdomain pattern
    if qname.endswith(subdomain):
        prefix = qname.split(".")[0]  # Get the prefix (e.g., "1", "2", etc.)
        if prefix.isdigit():
            index = int(prefix)
            if index < len(chunks):
                chunk_data = chunks[index]
            else:
                chunk_data = "EOF"  # Send EOF for the last record

            # Prepare DNS response with the chunk data as TXT
            reply = DNSRecord(
                DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q
            )
            reply.add_answer(RR(qname, rtype=QTYPE.TXT, rdata=TXT(chunk_data), ttl=60))
            response = reply.pack()

            # Send the response using the appropriate transport
            if is_tcp:
                # TCP DNS requires a 2-byte length prefix (RFC 1035 §4.2.2)
                sock.sendall(struct.pack("!H", len(response)) + response)
            else:
                sock.sendto(response, addr)

            print(f"Sent chunk {index} to {addr}: {chunk_data[:50]}...")
        else:
            print(f"Invalid prefix {prefix} in query: {qname}")
    else:
        print(f"Unknown query: {qname}")


def udp_server(chunks: List[str], subdomain: str):
    """
    Start a UDP DNS server.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 53))
    print("UDP DNS server started, listening for incoming queries...")

    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(
            target=handle_request, args=(data, addr, sock, chunks, subdomain, False)
        ).start()


def tcp_server(chunks: List[str], subdomain: str):
    """
    Start a TCP DNS server.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 53))
    sock.listen(5)
    print("TCP DNS server started, listening for incoming connections...")

    while True:
        conn, addr = sock.accept()
        try:
            # TCP DNS messages are prefixed with a 2-byte length (RFC 1035 §4.2.2)
            length_data = conn.recv(2)
            if len(length_data) < 2:
                conn.close()
                continue
            msg_len = struct.unpack("!H", length_data)[0]
            data = conn.recv(msg_len)
            if not data:
                conn.close()
                continue
            threading.Thread(
                target=handle_request,
                args=(data, addr, conn, chunks, subdomain, True),
            ).start()
        except Exception as e:
            print(f"TCP error from {addr}: {e}")
            conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python infiltration_dns_server.py <file_path> <subdomain>")
        sys.exit(1)

    file_path = sys.argv[1]
    subdomain = sys.argv[2]

    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    MAX_CHUNK_SIZE = 220
    chunks = read_and_split_file(file_path, MAX_CHUNK_SIZE)
    print(f"File split into {len(chunks)} chunks of up to {MAX_CHUNK_SIZE} bytes each")
    threading.Thread(target=udp_server, args=(chunks, subdomain)).start()
    threading.Thread(target=tcp_server, args=(chunks, subdomain)).start()
