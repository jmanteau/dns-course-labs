// dig cheat sheet: one A4 landscape page, colours of the course deck.
// Build: make cheatsheet (in course/), or: quarto typst compile cheatsheet.typ
#let navy = rgb("#15315b")
#let teal = rgb("#1ba5b8")
#let muted = rgb("#5b6478")
#let rule = rgb("#dfe4ea")
#let surface = rgb("#f4f6f8")
#let terminal = rgb("#0f1b2d")

#set document(title: "dig cheat sheet", author: "Julien Manteau")
#set page(paper: "a4", flipped: true, margin: (x: 1cm, top: 0.9cm, bottom: 0.8cm), columns: 3)
#set columns(gutter: 0.7cm)
#set text(font: ("Source Sans 3", "Helvetica Neue"), size: 8.7pt, fill: rgb("#1f2a44"))
#set par(justify: false, leading: 0.45em, spacing: 0.7em)
#set list(indent: 0pt, body-indent: 4pt, spacing: 0.5em)

#show raw: set text(font: ("Menlo", "DejaVu Sans Mono"), size: 7.4pt)
#show raw.where(block: false): box.with(fill: surface, inset: (x: 1.5pt), outset: (y: 1.5pt), radius: 1.5pt)
#show raw.where(block: true): set text(size: 6.7pt, fill: rgb("#dbe4ee"))
#show raw.where(block: true): set par(leading: 0.42em)
#show heading: it => block(above: 1em, below: 0.5em, text(size: 10pt, weight: 700, fill: navy, it.body))

// A table with a navy header row and thin rules between rows.
#let tbl(columns, header, ..cells) = table(
  columns: columns,
  stroke: (x, y) => if y > 0 { (top: 0.4pt + rule) },
  inset: (x: 3pt, y: 2.6pt),
  fill: (x, y) => if y == 0 { navy },
  align: left + horizon,
  table.header(..header.map(h => text(fill: white, weight: 700, h))),
  ..cells,
)
#let term(body) = block(fill: terminal, inset: 6pt, radius: 4pt, width: 100%, body)

#place(top, float: true, scope: "parent", clearance: 5mm)[
  #grid(
    columns: (1fr, auto),
    align: (left + bottom, right + bottom),
    text(size: 20pt, weight: 700, fill: navy)[dig cheat sheet],
    text(size: 8.5pt, fill: muted)[DNS Fundamentals · IUT Blagnac · github.com/jmanteau/dns-course-labs],
  )
  #v(2pt)
  #line(length: 100%, stroke: 2pt + teal)
]

= Everyday commands

#tbl((auto, 1fr), ([Command], [What it does]),
  [`dig example.com`], [A record, full output],
  [`dig example.com MX`], [Another type: AAAA, NS, MX, TXT, SOA, CAA…],
  [`dig example.com +short`], [Values only],
  [`dig example.com +noall +answer`], [Answer section only, with TTLs: the best short form],
  [`dig @1.1.1.1 example.com`], [Ask this server, not your default resolver],
  [`dig example.com +trace`], [Walk the tree from the root, like a resolver],
  [`dig -x 8.8.8.8`], [Reverse lookup (PTR)],
  [`dig SOA example.com +multiline`], [SOA fields, one per line, with comments],
  [`dig -f list.txt TXT +noall +answer`], [One lookup per line of the file],
  [`dig example.com +tcp`], [Use TCP instead of UDP],
  [`dig example.com +dnssec`], [Also show the signatures (RRSIG)],
  [`dig @127.0.0.1 -p 5300 example.com`], [Query a non-standard port],
)

*Ask the authoritative server directly* (raw TTL, `aa` flag):\
`dig NS example.com +short`, then\
`dig @<one of the NS> example.com +norecurse`

*Get the answer for another location* (EDNS Client Subnet, needs a resolver that supports it):\
`dig @8.8.8.8 google.com +subnet=129.20.0.0/24`

*Make the short form the default:* put `+noall +answer` in `~/.digrc`. Remove it to get the full output back.

= Without dig

#tbl((auto, 1fr), ([Tool], [Example]),
  [nslookup], [`nslookup -type=MX example.com 1.1.1.1`],
  [PowerShell], [`Resolve-DnsName example.com -Type MX -Server 1.1.1.1`],
  [Browser], [`toolbox.googleapps.com/apps/dig`],
)

#colbreak()

= Reading the output

#term(```
❯ dig www.example.com
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 17148
;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 0, …

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
;; QUESTION SECTION:
;www.example.com.          IN A

;; ANSWER SECTION:
www.example.com.       300 IN CNAME a1422.dscr.akamai.net.
a1422.dscr.akamai.net.  20 IN A     23.72.250.233

;; Query time: 185 msec
;; SERVER: 192.168.1.1#53(192.168.1.1) (UDP)
```)

An answer line reads: *name · TTL · class · type · value*.

#tbl((auto, 1fr), ([Section], [Contains]),
  [HEADER], [Status, flags, number of records per section],
  [OPT], [EDNS: UDP answers over 512 bytes, cookie, client subnet],
  [QUESTION], [What you asked: name, class, type],
  [ANSWER], [The records],
  [AUTHORITY], [The zone's NS (a referral) or SOA (a negative answer)],
  [ADDITIONAL], [Extra records, e.g. the IP of a listed NS (glue)],
  [Footer], [Server that answered, time, transport, size],
)

= Status codes

#tbl((auto, 1fr), ([Status], [Meaning]),
  [`NOERROR`], [The query worked],
  [`NXDOMAIN`], [This name does not exist],
  [NODATA], [The name exists, but has no record of this type: `NOERROR` with `ANSWER: 0`],
  [`SERVFAIL`], [No valid answer, e.g. DNSSEC failure, servers unreachable],
  [`REFUSED`], [The server declines to answer (policy)],
)

= Flags

#tbl((auto, 1fr), ([Flag], [Meaning]),
  [`qr`], [This is a response],
  [`aa`], [Authoritative answer: from the zone's own server],
  [`rd`], [Recursion desired (set by the client)],
  [`ra`], [Recursion available (the server is a resolver)],
  [`tc`], [Truncated: retry over TCP],
  [`ad`], [Validated by DNSSEC, according to the resolver],
)

#colbreak()

= Record types

#tbl((auto, 1fr), ([Type], [Holds]),
  [`A` / `AAAA`], [IPv4 / IPv6 address],
  [`CNAME`], [An alias: resolution restarts with the new name],
  [`MX`], [Mail servers, lowest preference number first],
  [`NS`], [Name servers of the zone],
  [`SOA`], [Zone origin: primary server, serial, timers, negative TTL],
  [`TXT`], [Free text: SPF, domain verification],
  [`PTR`], [Name of an IP, under `in-addr.arpa` or `ip6.arpa`],
  [`SRV`], [Host and port of a service, with priority],
  [`CAA`], [Certificate authorities allowed to issue for the domain],
  [`DNSKEY` `DS` `RRSIG`], [DNSSEC: keys, delegation, signatures],
)

= TTL and caches

- *From a resolver*, the TTL is the time left in its cache. *From the authoritative server* (`@ns +norecurse`), it is the configured value.
- *Negative answers are cached too*, for the lower of the SOA's TTL and its last field (MINIMUM).
- *Lookup order:* browser cache → OS cache and hosts file → recursive resolver → root, TLD, authoritative.
- *Before a change*, lower the TTL at least one old TTL in advance.

= Flush the caches

#tbl((auto, 1fr), ([Where], [Command]),
  [Windows], [`ipconfig /flushdns` (`/displaydns` lists it)],
  [Linux], [`resolvectl flush-caches`],
  [macOS], [`sudo dscacheutil -flushcache`\ `sudo killall -HUP mDNSResponder`],
  [Chrome], [`chrome://net-internals/#dns`],
  [Firefox], [`about:networking#dns`],
)
