# Dig lab: query DNS with dig

In this lab you query real DNS servers with `dig` (Domain Information Groper), read their answers, and use them to answer questions about real websites. For students of the DNS course. Updated November 2026.

**Before you start:** see the course slides on resolution, TTL (Time To Live), reverse DNS and split horizon first. The questions rely on them. The slides are on the [course site](https://jmanteau.github.io/dns-course-labs/).

**Keep the cheat sheet open:** the one-page [dig cheat sheet (PDF)](cheatsheet.pdf) lists the commands, output sections, status codes, flags, record types and cache commands.

**Prefer a game?** The same lab exists as Dig Quest, with a score and a class leaderboard: play at [dns.jmanteau.fr](https://dns.jmanteau.fr) with the class code your teacher gives you.

## Contents

- [Run dig](#run-dig)
- [Read dig's output](#read-digs-output)
- [dig commands](#dig-commands)
- [Answer the questions](#answer-the-questions)
- [Play Dig Quest](#play-dig-quest)
- [Tips](#tips)

## Run dig

### On your computer

`dig` is installed by default on many operating systems, including Linux and macOS. On Microsoft Windows, install it as part of MobaXterm or Cygwin.

1. Open a terminal: Terminal on macOS and Linux, Command Prompt or MobaXterm on Windows.
2. Type `dig <any hostname>`, then press **Enter**.

### In a web browser

Two websites run `dig` for you. Use them when you cannot install it, or to share a query with someone.

**Google Admin Toolbox Dig** is simple and graphical, so it suits people who are not DNS experts.

- Open it: https://toolbox.googleapps.com/apps/dig/
- Share a ready-made query: https://toolbox.googleapps.com/apps/dig/#A/www.bortzmeyer.org

**Dig Web Interface** has more options, such as choosing the name server, but a plainer interface (and ads on the side). Use it to query a specific server or to set an option.

- Open it: https://www.digwebinterface.com
- Share a ready-made query: https://www.digwebinterface.com/?hostnames=www.bortzmeyer.org&type=A&showcommand=on&ns=resolver&useresolver=9.9.9.10&nameservers=

## Read dig's output

To look up a name, type `dig` followed by the name, for example `dig www.example.com`. You should see something like this:

```
❯ dig www.example.com

; <<>> DiG 9.20.10 <<>> www.example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 17148
;; flags: qr rd ra; QUERY: 1, ANSWER: 4, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
; COOKIE: e2abe7f2209ce7a50100000069256f2728e9fc2ee34347a0 (good)
;; QUESTION SECTION:
;www.example.com.		IN	A

;; ANSWER SECTION:
www.example.com.	300	IN	CNAME	www.example.com-v4.edgesuite.net.
www.example.com-v4.edgesuite.net. 21600	IN CNAME a1422.dscr.akamai.net.
a1422.dscr.akamai.net.	20	IN	A	23.72.250.233
a1422.dscr.akamai.net.	20	IN	A	23.72.250.203

;; Query time: 185 msec
;; SERVER: 192.168.227.200#53(192.168.227.200) (UDP)
;; WHEN: Tue Nov 25 09:56:07 CET 2025
;; MSG SIZE  rcvd: 185
```

The output has several sections. Each one is explained below, in the order dig prints them.

### First lines: version and options

```
; <<>> DiG 9.20.10 <<>> www.example.com
;; global options: +cmd
```

- The first line shows the version of `dig` and the command you typed.
- The second line lists the options of the `dig` command.

### Header: status and flags

```
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 17148
;; flags: qr rd ra; QUERY: 1, ANSWER: 4, AUTHORITY: 0, ADDITIONAL: 1
```

The header describes the answer the server sent. **status** is the DNS response code. The four you will meet most are marked "common":

| Status | Code | Meaning | Common |
|--------|------|---------|--------|
| NOERROR | 0 | No error. The server answered without problems. | Yes |
| FORMERR | 1 | Format error: the server could not read the query. | No |
| SERVFAIL | 2 | Server failure: the server could not give a valid answer. For example, it could not reach the authoritative servers, or a DNSSEC check failed. | Yes |
| NXDOMAIN | 3 | The name does not exist, so there is no data to return. | Yes |
| NOTIMPL | 4 | Not implemented. | No |
| REFUSED | 5 | The server declines to answer because of its policy. For example, a denied zone transfer, or a resolver closed to outside clients. | Yes |
| NotAuth | | The server is not authoritative for the zone. | No |
| NotZone | | The name is not in the zone. | No |
| YXDomain, YXRRSet, NXRRSet | | Prerequisite errors of dynamic updates. | No |

**flags** describe the answer:

| Flag | Name | Meaning |
|------|------|---------|
| QR | Query/Response | 0 in a query, 1 in a response. A one-bit field rather than a flag like the others. |
| AA | Authoritative Answer | The answer comes from a server that holds the zone. |
| TC | Truncation | The answer was cut because it did not fit in one UDP packet. |
| RD | Recursion Desired | The client asks the server to resolve the name fully. Set in the query and copied into the response. |
| RA | Recursion Available | The server is willing to resolve names fully. |
| AD | Authenticated Data | The server validated the DNSSEC signatures of the data (DNSSEC only). |
| CD | Checking Disabled | The client asks the server not to validate signatures (DNSSEC only). |
| DO | DNSSEC OK | The client wants the DNSSEC records. Carried in EDNS, below. |

### OPT pseudo-section: EDNS

```
;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
```

This section shows EDNS (Extension mechanisms for DNS), when it is used:

- **EDNS**: the version of the extension.
- **flags**: blank here, because no flags were set.
- **udp**: the largest UDP packet the client accepts.

### Question section: what was asked

```
;; QUESTION SECTION:
;example.com.			IN	A
```

The query that was sent, in three columns: the name, the class (IN means Internet), and the record type (A means address) unless you asked for another.

### Answer section: the records

```
;; ANSWER SECTION:
www.example.com.	300	IN	CNAME	www.example.com-v4.edgesuite.net.
www.example.com-v4.edgesuite.net. 21600	IN CNAME a1422.dscr.akamai.net.
a1422.dscr.akamai.net.	20	IN	A	23.72.250.233
a1422.dscr.akamai.net.	20	IN	A	23.72.250.203
```

The most important section. Its columns are:

1. The name the record belongs to.
2. The TTL: how many seconds the record may stay in a cache before it must be fetched again.
3. The class: IN means Internet.
4. The record type: here CNAME (an alias to another name), then A (an address).
5. The data: here the target name of the CNAME, or the IP address.

### Authority section: who holds the zone

Not present in this example. This section lists the authoritative name servers of the zone, the servers that hold its data. To see it, send the query to an authoritative server, for example `dig example.com @ns.icann.org`.

### Statistics: how the query went

```
;; Query time: 53 msec
;; SERVER: 172.20.10.1#53(172.20.10.1) (UDP)
;; WHEN: Mon Jul 11 20:49:43 CEST 2022
;; MSG SIZE  rcvd: 56
```

- **Query time**: how long the answer took.
- **SERVER**: the IP address and port of the DNS server that answered. A loopback address here means a local program answers DNS queries for your computer.
- **WHEN**: when you ran the command.
- **MSG SIZE rcvd**: the size of the answer, in bytes.

## dig commands

| Command| Description                                                  | Example|
| ------------------------------------------------------------ | :----------------------------------------------------------- | ------------------------------------------------------------ |
| `dig [hostname]`| Returns the A record(s) of the queried hostname. | `dig wikipedia.org`                                          |
| `dig [hostname] [record type]`                               | Returns the records of that [type](https://en.wikipedia.org/wiki/List_of_DNS_record_types) found within the queried hostname's zone. | `dig MX wikipedia.org`                                       |
| `dig [hostname] +short`                                      | Provides a brief answer, usually just an IP address.         | `dig wikipedia.org +short`                                   |
| `dig @[nameserver address] [hostname]`                       | Queries a DNS resolver or the name server directly, instead of the resolver configured on your computer. | `dig @1.1.1.1 wikipedia.org`                                 |
| `dig [hostname] +trace`                                      | Resolves the name from the root name servers downwards, like a resolver does, and shows every step. | `dig wikipedia.org +trace`                                   |
| `dig -x [IP address]`                                        | Reverse lookup: the name of an IP address.                   | `dig -x 108.59.161.1`                                        |
| ` dig [hostname] +nocomments +noauthority +noadditional +nostats` | Removes the comments, authority, additional and statistics sections. | `dig wikipedia.org +nocomments +noauthority +noadditional +nostats` |
| `dig [hostname] +noall +answer`                              | Shows only the answer section. The recommended short form when you need the details (record type, TTL). | `dig wikipedia.org +noall +answer`                           |
| `dig -f [textfile] [record type]`                            | Looks up every domain of a file (one per line) at once. Can be combined with +noall +answer. | `dig -f list100.txt TXT +noall +answer`                                     |
| `dig [hostname] +subnet=xxx`                                 | Adds the EDNS Client Subnet (ECS) option, so the answer is the one for clients in that network. Needs dig 9.10 or later. | `dig @8.8.8.8 www.microsoft.com +subnet=8.7.6.0/24`          |
| `dig +multiline +noall +answer SOA [domain]`                 | Shows the [SOA](http://irbs.net/bog-4.9.5/bog41.html) record in an easier-to-read layout. Its last field sets the negative TTL: how long a server caches a "does not exist" or "nothing there" answer. | `dig +multiline +noall +answer SOA wikipedia.org`            |
| `dig +norecurse @[nameserver address] [hostname]`            | Asks an authoritative server the way a resolver does.       | `dig www.example.com @192.41.162.30 +norecurse`              |
| `dig @[nameserver address] -p [port number] google.com`      | Queries another port than 53, the standard DNS port.         | `dig @127.0.0.1 -p 5300 google.com`                          |

## Answer the questions

Before you start:

- **CDN.** A CDN (Content Delivery Network, for example Akamai or Cloudflare) serves a website from many locations, and often protects it too. A site behind a CDN usually shows up as a CNAME to the CDN's own domain.
- **Timeouts.** If your local resolver times out or filters queries, use a public one, for example `dig @1.1.1.1 ...` or `dig @8.8.8.8 ...`.
- **Changing answers.** Answers on live domains change over time (IP addresses, TTLs, counts). Reason on the structure, not on the exact values.
- **Record types.** The full list is on Wikipedia: [list of DNS record types](https://en.wikipedia.org/wiki/List_of_DNS_record_types).

The questions:

1. What is the IP address of the www.airbus.com website?
2. Is www.airbus.com an A or a CNAME record? Can you infer which protection is in place in front of the airbus.com website?
3. What are the name servers of amazon.com? And of aws.amazon.com? Which TTL do you get from your resolver, and which one from an authoritative name server (`dig NS amazon.com @<one of the NS>`)? Why do they differ?
4. What are the names of the apple.com mail servers? Which one is the primary, and which are the backups? Why might the priority levels differ?
5. What is the A record of dns-cheatsheet.com?
6. How many DNS requests are needed before you first reach www.linkedin.com? Do you have a hypothesis why? (Hint: look at the CNAME chain and the TTLs.)
7. What is the name linked to this IP address: 160.92.124.66? What is this server used for? Which DNS query can confirm your hypothesis? Can you draw a graph of the links between all the elements?
8. List the google.com records that the following subnets get. If your local DNS resolver does not support the +subnet option (EDNS Client Subnet), use a public one that does, like 8.8.8.8.

   | Country      | A subnet in the country |
   | ------------ | ----------------------- |
   | South Africa | 102.128.136.0/24        |
   | China        | 1.0.1.0/24              |
   | Chile        | 138.186.8.0/24          |
   | Belgium      | 152.152.0.0/24          |
   | France       | 129.20.0.0/24           |

9. Which of these media uses Slack: New York Times (nytimes.com), Le Monde (lemonde.fr) or BBC (bbc.com)?
10. Which certificate authorities are allowed to issue certificates for boursorama.com?
11. How many websites in the list100.txt file use Facebook Domain Verification (which allows Facebook login, comments, likes and so on)? (Hint: look for facebook-domain-verification.)
12. (Seldom used in real life.) Which city do the coordinates in the LOC record of dyndns.com point to?
13. What is the IPv6 address (AAAA record) of www.wikipedia.org?

## Play Dig Quest

Dig Quest is this lab as a game, with a score and a class leaderboard. Play at [dns.jmanteau.fr](https://dns.jmanteau.fr) with the class code your teacher gives you (how the game is built: [Dig Quest guide](game/)).

1. It starts with a short warm-up that you do with `dig` on your own computer.
2. Once the warm-up is done, the missions open, with a web dig console. Pick a name, a type, a server and options: it shows the output and the `dig` command you would type.
3. Once every mission is solved, the **Advanced** missions open, with their own leaderboard. They use DNS features the course does not cover. Read the *DNS Beyond the Basics* slides first: they are linked from the game, and on the [course site](https://jmanteau.github.io/dns-course-labs/).

## Tips

### Keep default options in $HOME/.digrc

If you only ever want the ANSWER section, you don't have to type `+noall +answer` every time. Put your default options in the `.digrc` file instead:

```
$ cat $HOME/.digrc
+noall +answer
```

**Warning:** these options apply to every `dig` call, so the full output examples above will look different. Remove the file to get them back.

### Use nslookup when dig is missing

If `dig` is not available, use `nslookup`. Its basic syntax:

```
nslookup [-option] [name | -] [server]
```

```
❯ nslookup example.com
Server:		172.20.10.1
Address:	172.20.10.1#53

Non-authoritative answer:
Name:	example.com
Address: 93.184.216.34
Name:	example.com
Address: 2606:2800:220:1:248:1893:25c8:1946
```

```
❯ nslookup example.com 1.1.1.1
Server:		1.1.1.1
Address:	1.1.1.1#53

Non-authoritative answer:
Name:	example.com
Address: 93.184.216.34
Name:	example.com
Address: 2606:2800:220:1:248:1893:25c8:1946
```

```
❯ nslookup -type=ns example.com
Server:		172.20.10.1
Address:	172.20.10.1#53

Non-authoritative answer:
example.com	nameserver = a.iana-servers.net.
example.com	nameserver = b.iana-servers.net.

Authoritative answers can be found from:
```

### Rebuild the cheat sheet

The cheat sheet's source is `cheatsheet.typ`. Rebuild the PDF with `make cheatsheet` in `course/`.
