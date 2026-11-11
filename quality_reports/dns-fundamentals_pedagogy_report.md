# Pedagogy review: `course/dns-fundamentals.qmd`

Reviewed 2026-11-04. Read-only: the deck was not changed.

## Verdict

The deck has strong raw material: good diagrams, real labs and a clear two-part structure. Three problems would hurt students most:

1. **Labs come before the theory they need.** This affects both the dig lab and the blue-team lab.
2. **Core terms are used but never defined.** "Zone" and "delegation" are the main gaps, and "resolver" has several meanings.
3. **The deck stops without a close, and the second half has no checks for understanding.**

Slides 13, 15, 21 and others also contain factual errors. Students will memorise these, so fix them first.

## How to read this report

- **Slide numbers** match the rendered deck: the title slide is 1 and hidden slides are not counted. Line numbers refer to the `.qmd` file.
- **The 13-pattern checklist is a reconstruction.** The skill calls a `pedagogy-reviewer` agent, but that agent and its 13 patterns are not on this machine. The checklist below is my own, so these scores can't be compared with earlier reports from that agent.
- **What I reviewed:** the deck source, 14 of its diagrams, and both lab READMEs (the dig lab's questions and the cyber lab's structure, blue-team steps and C2 section, not every step).
- **What I did not review:**
  - the rendered slides, or live delivery and timing
  - the PollEverywhere quiz questions, which are held outside the repo
  - the server-level labels on the slide 11 diagram, which I couldn't read because the image is transparent
- **Assumed audience:** IUT networking students who know IP and basic TCP/UDP but are new to DNS and security. The deck doesn't state this.
- **Factual claims:** the TTL figure and entropy values were calculated. Other factual corrections come from my own knowledge and were not checked online, so confirm them before editing, especially those in section 3.

## Scorecard: 2 followed, 6 partial, 5 violated

| # | Pattern | Result | Evidence |
|---|---------|--------|----------|
| 1 | Measurable objectives | Partial | Slide 2 is clear, but its verbs are only "describe" and "identify", and the labs ask for much more |
| 2 | Motivation before mechanism | Partial | Slides 6–7 and 54 do this well; slides 36, 37, 47 and 49 don't say why the technique matters |
| 3 | Prerequisites made visible | Partial | Slide 7 draws on prior knowledge, but no prerequisites are stated and anycast, CDN, SNI and Base32 are assumed |
| 4 | Definition before use | **Violated** | Zone, DoH, RPZ, authoritative, C2 (see A2, A3) |
| 5 | Dependency order | **Violated** | Dig lab, blue-team lab, Views before Split Horizon (see A1) |
| 6 | Concrete example before practice or abstraction | Partial | Slide 23 and the DGA date example work well; slide 19 doesn't prepare students for slide 20, and Gini has no example |
| 7 | Consistent terminology | **Violated** | Resolver, client, recursive and Master/Primary all drift (see A3) |
| 8 | Regular checks for understanding | Partial | Quizzes at slides 16 and 31, then nothing across the 26 slides of part 2 |
| 9 | Signposting | Partial | The recurring pillar slide is a good device, but its labels don't match the content (see B1) |
| 10 | Multiple representations | **Followed** | Resolution is shown as a diagram (18), a sequence (19) and a terminal trace (23); reverse DNS as a tree plus a record (24) |
| 11 | Hands-on practice | **Followed** | Dig lab, Dig Quest, and a red/blue lab are the deck's biggest strength |
| 12 | Misconceptions and accuracy | **Violated** | "13 root servers", Round Robin and the errors in section 3 |
| 13 | Closure | **Violated** | Ends on Resources and an xkcd, with no summary or return to objectives |

## Critical recommendations

### A1. Move the labs after the theory they need

**Dig lab (announced on slide 17).** Lab questions depend on topics taught later:

| Lab question | Needs | Taught on |
|---|---|---|
| Resolver TTL vs authoritative TTL, "why do they differ?" | TTL, cache, authoritative server | 21–23 |
| How many requests to reach www.linkedin.com (CNAME chain and TTLs) | Resolution, TTL | 18–23 |
| Name linked to 160.92.124.66 | Reverse DNS, PTR | 24 |
| `google.com` answers for different subnets | Location-dependent answers | 26 |
| "Which protection is in front of airbus.com?" | CDN, never taught | none |

**Fix:** split the lab. Run the basic record questions at slide 17, then the remaining questions after slide 24 or 27. Add one sentence on CDNs, ideally on slide 20, where Akamai first appears.

**Cyber lab (slide 42).** The blue-team half uses entropy, n-grams, the Gini index and RPZ. The deck covers detection on slides 44–49, after the lab slide. Sliver's implant and beacon vocabulary appears nowhere in the deck, and the lab README only defines it near the end (line 794), after the activities.

**Fix:** run the red team at slide 42 and the blue team after slide 49. Move "Understanding C2 Basics" to the start of the lab.

**Order inside part 1:**
- Swap slides 25 and 26: define Split Horizon (the concept) before Views (one way to implement it).
- Slide 26 lists RPZ two slides before it is defined. Either drop it from that list or add "see next slides".

### A2. Teach zone and delegation

This is the largest conceptual gap in the deck.

- **"Zone"** first appears on slide 10 ("zone transfers") and is used on slides 15, 23, 26, 28 and 30, but is never defined.
- **"Delegation"** doesn't appear at all. Yet "Referral" is the main step of the resolution diagrams on slides 18–19.

Without these, students can't answer the natural question: "Why does the root server point me somewhere else instead of answering?" They also can't separate a domain (part of the naming tree) from a zone (what one operator administers).

**Fix:** add one slide after slide 11. Show the same tree with zone boundaries drawn on it: `amazon.com` delegating `aws.amazon.com` versus keeping it in the same zone. The dig lab already asks for the nameservers of both, so the slide pays off immediately. Introduce "authoritative" here too. On slides it first appears on slide 23; before that it is only in the slide 18 notes and inside images.

### A3. Fix "resolver" and other drifting terms

| Term | Current use | Problem |
|---|---|---|
| Resolver | "Client (resolvers)" (10), `nslookup` as a "resolver" (17), recursive server (18, 23), OS "resolver cache" (22) | One word for three different things |
| Client side | Client, Device, Host, User | Four names for one role |
| Master/Primary | Slide 30 says "used to be called Master", then uses Master twice more | Contradicts itself |
| RPZ | "a DNS zone" (28), "a security policy" (45), also "DNS Firewall" and "Sinkhole" | No clear relationship between the terms |

**Fix:** name the stub resolver (on the device) and the recursive resolver (the server) on slide 10, then use only those terms. Teach "RPZ is the mechanism, DNS firewall is the use".

**DoH is used before it is defined.** Slide 41 attacks through DoH, and DoH is defined 11 slides later on slide 52. Slide 41 also assumes TLS SNI and the HTTP Host header. Either move the slide to after 53, which creates a useful twist ("the privacy improvement is also a covert channel"), or define DoH in one line on slide 41.

### A4. Add a close, and checks in part 2

- **Add a third quiz** around slide 50, after detection. The quiz at 16 and the one at 31 currently leave part 2 without any check.
- **Add a final slide** before Resources that revisits the objectives on slide 2, with one takeaway for each.
- **Add a bridge at slide 32.** Part 2 opens without linking back to part 1. The strongest link is available: *tunnelling works because the recursive resolver from slide 19 will faithfully deliver any query to the attacker's authoritative server, and DNS is usually allowed out.* The deck never says this outright, and it is the key idea of the second half.
- **Rewrite the objectives** to match the labs, for example: "Trace a full resolution with `dig`", "Detect a DNS C2 channel in logs", "Block a domain with RPZ". Also define "kill chain", which objective 5 uses without explanation.
- **The agenda** lists Labs as a third section, but labs actually run inside sections 1 and 2.

### A5. Correct the factual errors (section 3)

Do this first, since it is quick and students will otherwise learn them as fact.

## B. Important improvements

**B1. Pillar labels don't match their content (slides 34–50).**
- Pillar 1, "Preventing communication over DNS", actually teaches how attackers communicate (36–41).
- Pillar 2, "Stopping APTs/malware", is what actually prevents that communication (44–49). Students can't tell the two apart.
- Slide 39 (lookalike detection) and slide 40 (legitimate tunnelling) are defender topics sitting in the attacker section.
- **Fix:** rename them along the lines of "1. How attackers abuse DNS", "2. Detecting and blocking abuse", "3. Protecting DNS itself". Move slides 39–40 into pillar 2.

**B2. Add a bridging example before the slide 20 exercise.** Slide 19 resolves `www.example.com` with no CNAME. Slide 20 then asks for `www.impots.gouv.fr`, which runs through a chain of CNAMEs across several zones. Nothing shows that a CNAME restarts resolution for a new name, which is the difficult part of the exercise. Add one short example, and point students to `dig +trace`, which is in the dig lab but not on these slides.

**B3. Make slide 40 an exercise.** It's a bare list of domains with no stated point. Ask: "Which of these are malicious?" The answer (none) shows why detection produces false positives, which also motivates slides 47–49. Add one attacker example to make it harder.

**B4. Add a worked example to the heuristics (47–49).** Entropy is described but never computed, Gini and classification error are defined only in abstract terms, and the n-gram charts never get applied to a domain name. Comparing real names would make this concrete, and would expose an important limit:

| Name | Length | Entropy (bits per character) |
|---|---|---|
| `wikipedia` | 9 | 2.64 |
| `facebook` | 8 | 2.75 |
| `vlbqryjd` (DGA, slide 38) | 8 | 3.00 |
| `ab6d54340c1a` (DGA, slide 38) | 12 | 3.25 |
| `b83ed4877eec1997fcc39b7ae590007a` (DGA, slide 38) | 32 | 3.59 |
| `KS93KDKSK344SD3434DS` (tunnel chunk, slide 36) | 20 | **2.48** |

The deck's own tunnel example scores *lower* than `facebook`. That makes a memorable point: no single indicator is enough, which is why the lab script combines several into a score. It also suggests slide 36's example string isn't realistic encoded data (see section 3).

**B5. Connect attacks to defences (51–55).**
- Slide 51 lists 11 attacks in a single table, with no example and no link to what follows. Tie the improvements to specific attacks: cache poisoning → DNSSEC; on-path observation → DoT/DoH.
- Cache poisoning is the natural motivation for DNSSEC, but the Kaminsky attack appears only as a link on slide 56.
- Slide 53 misses the most relevant point for this course: DoH can bypass the enterprise resolver, and with it the RPZ that students just built.
- DNSSEC is only described as "signed". The chain of trust isn't shown, though it mirrors the hierarchy students already know.

**B6. Explain why, not only what.**
- **DGA (38):** say why attackers use it: they need to register one domain, while defenders must block them all.
- **Reverse DNS (24):** say why the octets are reversed. DNS names get more specific from right to left, while IP addresses get more specific from left to right.
- **"Loosely coherent" (9):** the description doesn't explain the term. Link it to caching and TTL.
- **Round Robin (27):** the server normally returns all addresses in rotated order. Slide 27 says it provides "a different IP" and the diagram shows one address per client, but the slide 20 output shows two A records. Also note that caching makes the balancing rough.
- **13 root servers (11):** make clear these are 13 identities served by many anycast instances, and explain anycast in a sentence.

**B7. Speaker notes.** Only five slides have notes (14, 18, 21, 22, 52), and none of slides 33–51 do, so part 2 can't be delivered by anyone else. Slide 22's notes are a copy of the TTL notes from slide 21, with nothing about caches. The library analogy in the slide 18 notes is good, but students never see it. Put it on the slide.

**B8. Reduce density.** Slides 12, 13, 36, 37, 44 and 51 are walls of text. Slides 44–51 are the weakest stretch for pacing, with mostly text and no activity. Slide 46 describes vendor products ("in hardware, at line speed") and could be cut back to what the lab needs.

## 3. Factual errors and items to verify

| Slide | Line | Current text | Correction |
|---|---|---|---|
| 21 | 287 | TTL up to "248555 days" | 2³¹−1 seconds is about **24,855 days**; one digit too many (calculated) |
| 12 | 147 | IANA "manages root servers" | IANA manages the root *zone*. Root servers are run by 12 independent operators |
| 13 | 159 | `edu` as unsponsored | `.edu` is sponsored |
| 13 | 160 | `.airbus` as sponsored | `.airbus` is a brand gTLD. `.museum` and `.travel` are correct |
| 13 | 155–162 | Six parallel tiles | The categories overlap (sTLD is a kind of gTLD), but the layout presents them as peers |
| 14 | 186 | Domain "needs to be loaned/registered" | The diagram's "domain" brace covers `aws.amazon.com`, but only `amazon.com` is registered. `aws` also has no label |
| 15 | 217 | "GLUE" listed with record types | Glue is not a record type; it is A/AAAA records supplied at a delegation |
| 17 | 230 | `nslookup` "officially deprecated" | ISC withdrew the deprecation years ago. "`dig` is better for diagnosis" is the safer claim |
| 17 | 232 | "only resolver on Windows" | It's a tool, not a resolver, and PowerShell has `Resolve-DnsName` |
| 22 | 318 | `resolvectl query` under "Check Cache" | That runs a query rather than showing the cache |
| 22 | 318–319 | Chrome: "check" filled in, "clear" blank | Current `net-internals` offers clearing, not viewing. Check in a current browser |
| 22 | 317 | "Mac (12.x)" | Dated; retest on a current version |
| 36 | 526 | `kjhHJhUy7UjfryGF…` as encoded data | Contradicts the slide's "a-z, 0-9" encoding: DNS names are case-insensitive, so mixed case can't be relied on to carry data. The other chunk's `8` and `9` are also not in standard Base32 |
| 39 | 583 | "Alexa top-100" | Alexa was retired in 2022; the lab already uses Cloudflare Radar |
| 41 | 611 | `curl … malwareC2.com’` | A curly closing quote breaks the command if copied |
| 41 | 610–614 | Domain fronting through Google | Google blocked this in 2018, so students trying it will fail. Present it as history or use a verified example |
| 53 | 791–800 | Title says DoT/DoQ and DoH/DoH3 | The table only compares DoT and DoH, and has an empty cell |

**Typos students will see:**
- "2st" in both resolution diagrams (slides 18, 19; these need re-exporting from the images)
- "as local zone present" (slide 25 image)
- spell-check squiggles in the slide 21 image
- "Ressources" (8, 56)
- "They are 47" (15)
- "Quizz" (16, 31)
- "Bézier" for Béziers (3)
- the garbled sentences on slide 54 ("provide DNS clients via a digital signature (resolvers)" and "thereby mitigate, such as…")
- the unbalanced bracket on slide 52

**Dated figures:** the TLD and domain counts on slide 11 are from 2024.

**Lab bug found during review (`dns-cyber-lab/README.md`, Step 4):** the RPZ example is commented "returning NXDOMAIN" but uses `CNAME *.`, which returns NODATA. `CNAME .` is the NXDOMAIN form. Slide 45 presents these as two separate actions, so students may notice the mismatch.

## What to keep

- **The opening (6–7):** the joke and the question activate prior knowledge before any definitions.
- **TTL lookup (23):** the best slide in the deck. The same record is shown at 403 and 600 seconds, so students see caching rather than being told about it.
- **Three views of resolution (18–20),** followed by doing it themselves.
- **Homograph example (39):** rendering `appIe.com` in two fonts makes the risk obvious at once.
- **DGA flow (38):** the concrete date example, then real families, then the NXDOMAIN sequence.
- **Transport vs data split (52):** a clear frame for separating DoT/DoH from DNSSEC.
- **Red team then blue team:** the best design decision in the course. It only needs the sequencing fix in A1.

---

# Re-review after the fixes (2026-11-04, branch `pedagogy-fixes`)

Slide numbers in this section refer to the new deck: 67 rendered slides, up from 57. The checklist is the same reconstructed one, and I am scoring my own changes, so treat this as a self-check rather than an independent review.

## Scorecard: 10 followed, 3 partial, 0 violated (was 2, 6, 5)

| # | Pattern | Before | After | Why |
|---|---------|--------|-------|-----|
| 1 | Measurable objectives | Partial | Followed | Objectives now use "trace", "detect", "block" and match the labs |
| 2 | Motivation before mechanism | Partial | Followed | Bridge slide 34; the "why" added for DGA, reversed octets and DNSSEC |
| 3 | Prerequisites made visible | Partial | **Partial** | CDN and anycast are now explained, but no prerequisites are stated and SNI and Base32 are still assumed |
| 4 | Definition before use | Violated | Followed | Zone and delegation on slide 12, RPZ moved beside the DNS firewall, DoH defined before its C2 slide. The objectives only preview these terms |
| 5 | Dependency order | Violated | Followed | Dig lab at slide 31, blue team at slide 55, Split Horizon before Views |
| 6 | Concrete example before practice | Partial | Followed | CNAME example (21), real heuristic numbers (54) |
| 7 | Consistent terminology | Violated | **Partial** | Slide text is consistent, but diagrams still say Host, Device and User for the client |
| 8 | Regular checks for understanding | Partial | **Partial** | The third quiz slide exists (56), but its questions must be added to PollEverywhere |
| 9 | Signposting | Partial | Followed | Pillars relabelled, and their content now matches |
| 10 | Multiple representations | Followed | Followed | |
| 11 | Hands-on practice | Followed | Followed | |
| 12 | Misconceptions and accuracy | Violated | Followed | Section 3 errors fixed, or reworded where checking changed the answer |
| 13 | Closure | Violated | Followed | "What to remember" (65) mirrors the seven objectives |

## Corrections to the first report

Checking against primary sources changed some of my earlier claims:

- **`.edu` and the sponsored category:** `.edu` is sponsored only in ICANN's older grouping. IANA's root database now lists `.edu`, `.museum` and `.airbus` all as "Generic". The slide says this.
- **`nslookup`:** confirmed, and older than I implied. An ISC release note quoted in 2004 reverses the deprecation.
- **Entropy table (B4):** the "tunnel chunk scores below `facebook`" point depended on the old, unrealistic string. With real Base32 the chunk scores 3.86. The better lesson, now on slide 54, is that a legitimate Spotify label scores highest (4.29).
- **`aws.amazon.com` (A2):** it is now a CNAME, not a zone, so the delegation slide uses `impots.gouv.fr` instead.

## New issues found while fixing

- **Fixed: lab-breaking bug.** The committed `rpz.zone` already blocked the C2 domain. Measured with a live listener: the old zone gave 0 implant sessions in 180 s, and the fixed zone connected in 15 s.
- **Fixed: weak test.** The RPZ test could pass whatever the server returned. It now fails with the block absent and passes with it present (both run).
- **Fixed: `make pdf`.** It clipped every slide onto portrait pages. It now uses `course/print-pdf.mjs`.
- **Fixed: slide 11 label.** "secondary name server" meant second-level, and is now labelled that way.

## Still open

- Add the third quiz's questions to PollEverywhere (drafts are in the slide 56 notes).
- The dig lab asks for the nameservers of `aws.amazon.com`, which now returns a CNAME. The private Dig Quest questions weren't available here, so check that question there too.
- `https://www.zytrax.com/books/dns/` did not respond from this machine. The Verisign link on slide 11 returned 403 to a script, and may be fine in a browser.
- Slide 11 still places "authoritative" at only one level of the tree, while slide 12 shows that it depends on the zone. The slide 11 notes mention this.
- Firefox's Clear DNS Cache button and Chrome's lookup-only DNS page come from my own knowledge, not a test. Check them in current browsers.
- Timing is unmeasured: the deck is 10 slides longer and now has more lab breaks.
