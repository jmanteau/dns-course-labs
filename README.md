# DNS course and labs

The Domain Name System (DNS) course of IUT Blagnac: slides, two hands-on labs and a game. For students taking the course and teachers running it. Updated November 2026.

**Open the course site: [jmanteau.github.io/dns-course-labs](https://jmanteau.github.io/dns-course-labs/).** It has the slides, the PDFs and the links to the labs, in the order to follow.

## What this repository holds

| Part | What it is | For | Where |
|------|------------|-----|-------|
| Slides | *Domain Name System Fundamentals*, the course | Students | [Course site](https://jmanteau.github.io/dns-course-labs/), or the [course slides as PDF](Domain%20Name%20System%20Fundamentals.pdf) |
| Dig lab | Query real DNS servers with `dig` and answer questions | Students | [Dig lab handout](dns-dig-lab/) |
| Dig Quest | The dig lab as a game, with a score, a class leaderboard and advanced missions | Students, at [dns.jmanteau.fr](https://dns.jmanteau.fr) with the class code given in class | [Dig Quest guide](dns-dig-lab/game/) |
| Cyber lab | Hide traffic inside DNS as an attacker, then detect and block it as a defender | Students | [Cyber lab guide](dns-cyber-lab/) |
| Slide sources | The Quarto sources of both slide decks and of the course site | Teachers | [Course sources](course/) |

## Where to start

**As a student:**

1. Read the slides, or follow them in class.
2. Do the [dig lab](dns-dig-lab/), or play it as Dig Quest when your teacher gives you the link.
3. Do the [cyber lab](dns-cyber-lab/) after the course's security slides.

**As a teacher:**

- To edit or build the slides, or publish the course site, read the [course sources guide](course/).
- To run Dig Quest for a class, read the [Dig Quest guide](dns-dig-lab/game/).
- To prepare the cyber lab, read the [cyber lab maintainer notes](dns-cyber-lab/MAINTAINERS.md).
