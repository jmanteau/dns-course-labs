# Request DNS with Domain Information Groper (Dig)



## Local Dig

It is installed by default on many operating systems, including Linux  and Mac OS X. It can be installed on Microsoft Windows as part of Mobaxterm or Cygwin.

1. Open Terminal (Mac and Linux) or Command Prompt / Mobaxterm (Windows).
2. Type  `dig <any hostname>`, and then press **Enter**.



## Dig on Internet

### Google Admin Toolbox Dig

Allow to easily share to non expert people in a graphical way.

Access to Gdig: https://toolbox.googleapps.com/apps/dig/

Sharing with a request ready: https://toolbox.googleapps.com/apps/dig/#A/www.bortzmeyer.org

### Dig Web Interface

More complete website but more "rough" in term of UI (and with ads on the side but technical people should not see them as a proper ads-blocker should already be setup...). Useful for resolving to different NS or with specific option.

Access to Dig Web Interface: https://www.digwebinterface.com

Sharing with a request ready: https://www.digwebinterface.com/?hostnames=www.bortzmeyer.org&type=A&showcommand=on&ns=resolver&useresolver=9.9.9.10&nameservers=



## Dig Usage



The **`dig`** command enables searching for a domain name. To perform a DNS lookup, open the terminal and type: `dig example.com` You should see something similar to the following:

```
❯ dig example.com

; <<>> DiG 9.18.4 <<>> example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 25412
;; flags: qr rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
;; QUESTION SECTION:
;example.com.			IN	A

;; ANSWER SECTION:
example.com.		4502	IN	A	93.184.216.34

;; Query time: 53 msec
;; SERVER: 172.20.10.1#53(172.20.10.1) (UDP)
;; WHEN: Mon Jul 11 20:49:43 CEST 2022
;; MSG SIZE  rcvd: 56
```



The following information can be returned:

```
;; ANSWER SECTION:
example.com.		4502	IN	A	93.184.216.34
```

- **Answer section**: The most important section is the **ANSWER** section: The first column lists the name of the server that was queried. The second column is the **Time to Live**, a set timeframe after which the record is refreshed. The third column shows the class of query – in this case, “IN” stands for Internet. The fourth column displays the type of query – in this case, “A” stands for an A (address) record The final column displays the IP address associated with the domain name

Other lines can be translated as follows:

```
; <<>> DiG 9.18.4 <<>> example.com
;; global options: +cmd
```

- The **first line** displays the version of the **`dig`** command.
- The second line list the options present on dig command

```
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 25412
;; flags: qr rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available
```

- The **HEADER** section shows the information it received from the server. 

  - **STATUS** give the DNS response code (in bold the most common ones):
    - **NOERROR** (0): No Error. Everything's cool. The zone is being served from the requested authority without issues.
    - FORMERR (1): Format Error (unable to interpret Query)
    - **SERVFAIL (2)**: Server or Feature Problem. The name that was queried exists, but there's no data or invalid data for that name at the requested authority. 
    - **NXDOMAIN** (3): FQDN doesn’t exist. The name in question does not exist, and therefore there is no authoritative DNS data to be served.
    - NOTIMPL (4): Not implemented
    - **REFUSED** (5): Action refused, e.g. Zone Transfer or DDNS. Not only does the zone not exist at the requested authority, but their  infrastructure is not in the business of serving things that don't exist at all.
    - NotAuth: Server not authoritative for Zone
    - NotZone: Name not contained in Zone
    - prereq: YXDomain, YXRRSet, NXRRSet

  - Flags refer to the answer format:
    - AA = **A**uthoritative **A**nswer
    - TC = Truncation
    - RD = **R**ecursion **D**esired , Client requested recursive Search (set in a query and copied into the response if recursion is supported)
    - RA = **R**ecursion **A**vailable, Name Server is willing to perform recursive Search (if set, denotes recursive query support is available)
    - AD = **A**uthenticated **D**ata, Name Server has validated the Signature (for DNSSEC only; indicates that the data was authenticated)
    - CD = **C**hecking **D**isabled, Client requested to not perform Validation (DNSSEC only; disables checking at the receiving server)
    - DO - Client requested to perform Validation (EDNS: **D**nssec **O**k)

```
;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
```

- The **OPT PSEUDOSECTION** displays advanced data: 
  - EDNS – Extension system for DNS, if used. 
  - Flags – blank because no flags were specified. 
  - UDP – UDP packet size

```
;; QUESTION SECTION:
;example.com.			IN	A
```

- **Question section**: The **QUESTION** section displays the query data that was sent: First column is the domain name queried.Second column is the type (IN = Internet) of query. Third column specifies the record (A = Address), unless otherwise specified
- [NOT PRESENT HERE] **Authority section**: The authoritative nameservers from which the answer to the query was received. These nameservers house the zones for a domain. You can show by requesting the request to the SOA. Here `dig example.com @ns.icann.org`

```
;; Query time: 53 msec
;; SERVER: 172.20.10.1#53(172.20.10.1) (UDP)
;; WHEN: Mon Jul 11 20:49:43 CEST 2022
;; MSG SIZE  rcvd: 56
```

- The **STATISTICS** section shows metadata about the query: 
  - Query time – The amount of time it took for a response
  - SERVER – The IP address and port of the responding DNS server. You may notice a loopback address in this line – this refers to a local setting that  translates DNS addresses
  - WHEN – Timestamp when the command was run
  - MSG SIZE rcvd – The size of the reply from the DNS server



## dig Commands

| Command&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; | Description                                                  | Example&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; |
| ------------------------------------------------------------ | :----------------------------------------------------------- | ------------------------------------------------------------ |
| `dig [hostname]`&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; | Returns any A records found within the queried hostname's zone. | `dig wikipedia.org`                                          |
| `dig [hostname] [record type]`                               | Returns the records of that [type](https://en.wikipedia.org/wiki/List_of_DNS_record_types) found within the queried hostname's zone. | `dig MX wikipedia.org`                                       |
| `dig [hostname] +short`                                      | Provides a brief answer, usually just an IP address.         | `dig wikipedia.org +short`                                   |
| `dig @[nameserver address] [hostname]`                       | Queries  a DNS resolver or the nameserver directly instead of the resolver configured in your local system. | `dig @1.1.1.1 wikipedia.org`                                 |
| `dig [hostname] +trace`                                      | Adding `+trace` instructs dig to resolve the query from the root nameserver downwards and to report the results from each query step (like a Resolver is doing) | `dig wikipedia.org +trace`                                   |
| `dig -x [IP address]`                                        | Reverse lookup for IP addresses.                             | `dig -x 108.59.161.1`                                        |
| ` dig [hostname] +nocomments +noauthority +noadditional +nostats` | Remove the comment, authority, additional and stats section of the return | `dig wikipedia.org +nocomments +noauthority +noadditional +nostats` |
| `dig [hostname] +noall +answer`                              | Remove all sections of the return and add only the answer one. This is the recommend short form for having the details (record type, TTL). | `dig wikipedia.org +noall +answer`                           |
| `dig [record type] -f [textfile] `                           | Perform a number of DNS lookups for a list of domains instead of doing the same for each one individually. Can be combined with +noall +answer to do searches | `dig -f /tmp/dns.txt MX`                                     |
| `dig [hostname] +subnet=xxx`                                 | Perform a DNS lookup and add the EDNS Client Subnet option to the request for client geo answer. Need dig version >=9.10 | `dig @8.8.8.8 www.microsoft.com +subnet=8.7.6.0/24`          |
| `dig +multiline +noall +answer SOA [domain]`                 | Pull the domain-wide TTL setting, which controls negative-TTLs (how long a server will cache an NX or ‘nothing there’  reply). This will also break out the [SOA](http://irbs.net/bog-4.9.5/bog41.html) into an easier to read format | `dig +multiline +noall +answer SOA wikipedia.org`            |
| `dig +norecurse @[nameserver address] [hostname]`            | Allow to simulate a DNS Resolver query to an authoritative server | `dig www.example.com @192.41.162.30 +norecurse`              |
| `dig @[nameserver address] -p [port number] google.com`      | By default the dig command queries port 53 which is the standard DNS  port, however we can optionally specify an alternate port if required. | `dig @127.0.0.1 -p 5300 google.com`                          |



## Questions

Reminder: Valid record type list can be found [here](https://en.wikipedia.org/wiki/List_of_DNS_record_types)

* What is the IP of the www.airbus.com website ? 

* Is the www.airbus.com a A or CNAME record ? Can you infer which protection is in place in front of airbus.com website ?

* What are the nameservers of amazon.com ? And of aws.amazon.com ? What is the TTL of the amazon.com NS ?

* What is the name of apple.com mail servers ? Which mail server is the primary and which are the backups? Why might the priority levels differ?

* What is the A record of dns-cheatsheet.com ?

* How many DNS requests are needed before first acceeding to www.linkedin.com ? Do you have an hypothesis why ? (hint: check TTL)

* What is the name linked to this IP : 160.92.124.66 ? What is the usage of this server ? What DNS query can you do to confirm your hypothesis ? Can you do a graph showing the links between all elements ?

*  List the google.com records that the following subnet will get :
  
  | Country      | A subnet in the country |
  | ------------ | ----------------------- |
  | South Africa | 102.128.136.0/24        |
  | China        | 1.0.1.0/24              |
  | Chile        | 138.186.8.0/24          |
  | Belgium      | 152.152.0.0/24          |
  | France       | 129.20.0.0/24           |


* Which of the following media is using Slack : New York Times (nytimes.com), Le Monde (lemonde.fr) or BBC (bbc.com)?
* Which certificate authority(ies) have the right to deliver certificate for boursorama.com ?
* How many website use Facebook Domain Verification in the list100 file (to allow using facebook identity, comments, like, etc) (hint: check for facebook-domain-verification)
* [Seldom used in real life] What is the city indicated on DNS dyndns.com ?
* What is the IPv6 address (AAAA record) of www.wikipedia.org ?


### Tip: Use $HOME/.digrc File to Store Default dig Options

If you are always trying to view only the ANSWER section of the dig  output, you don’t have to keep typing “+noall +answer” on your every dig command. Instead, add your dig options to the .digrc file as shown  below.

```
$ cat $HOME/.digrc
+noall +answer
```

## Nslookup syntax

In case of dig is not available, here is the basic syntax of nslookup:

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

