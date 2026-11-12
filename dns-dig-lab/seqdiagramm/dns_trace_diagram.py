#!/usr/bin/env python3
"""
Script de génération de diagramme de séquence DNS basé sur dig +trace.
Parse la sortie réelle de dig +trace pour créer un diagramme précis.
"""

import subprocess
import re
import sys


class DNSSequenceDiagram:
    def __init__(self):
        self.lines = []
        self.participants = set()

    def add_participant(self, name, icon="f233"):
        if name not in self.participants:
            self.participants.add(name)
            idx = len([l for l in self.lines if l.startswith("fontawesome")])
            self.lines.insert(idx, f"fontawesome5solid {icon} {name}")

    def add_query(self, src, dst, query, act_src=False, act_dst=False):
        if act_src:
            self.lines.append(f"activate {src}")
        if act_dst:
            self.lines.append(f"activate {dst}")
        self.lines.append(f"{src}->{dst}: {query}")

    def add_response(self, src, dst, resp, deact_src=False):
        self.lines.append(f"{dst}<-{src}: {resp}")
        if deact_src:
            self.lines.append(f"deactivate {src}")

    def add_note(self, participant, note):
        self.lines.append(f"abox over {participant}: {note}")

    def generate(self, title="Real DNS Resolution"):
        out = [f"title {title}"]
        out.extend([l for l in self.lines if l.startswith("fontawesome")])
        out.append("")
        out.extend([l for l in self.lines if not l.startswith("fontawesome")])
        return "\n".join(out)


def parse_dig_trace(domain):
    """Parse dig +trace output et génère le diagramme"""
    try:
        result = subprocess.run(['dig', '+trace', '+time=5', '+tries=2', domain],
                              capture_output=True, text=True, timeout=60)
        output = result.stdout
    except Exception as e:
        print(f"# Erreur dig: {e}", file=sys.stderr)
        return None

    diagram = DNSSequenceDiagram()

    # Participants de base
    diagram.add_participant("Device", "f109")
    diagram.add_participant("Recursive DNS", "f233")

    # Requête initiale
    diagram.add_query("Device", "Recursive DNS", f"{domain} ?", act_src=True)
    diagram.add_note("Recursive DNS", "Start Resolution (No Cache)")

    lines = output.split('\n')
    current_section = None
    root_ns_found = False
    tld_ns_found = False
    auth_ns_found = False

    for i, line in enumerate(lines):
        line = line.strip()

        # Détecter Root servers
        if 'root-servers.net' in line and 'NS' in line and not root_ns_found:
            root_ns_found = True
            diagram.add_participant("Root DNS", "f233")
            diagram.add_query("Recursive DNS", "Root DNS",
                            f"Query NS for .{domain.split('.')[-1]}",
                            act_src=True, act_dst=True)

        # Détecterférence vers TLD
        if 'Received' in line and root_ns_found and not tld_ns_found:
            # Chercher le NS du TLD dans les lignes précédentes
            for j in range(max(0, i-10), i):
                if 'NS' in lines[j] and '.nic.' in lines[j]:
                    match = re.search(r'NS\s+(\S+\.nic\.\S+)', lines[j])
                    if match:
                        tld_ns = match.group(1).split('.')[0]
                        tld = domain.split('.')[-1]
                        diagram.add_response("Root DNS", "Recursive DNS",
                                          f"Referral to .{tld} NS ({tld_ns})",
                                          deact_src=True)
                        tld_server = f"TLD .{tld} ({tld_ns})"
                        diagram.add_participant(tld_server, "f233")
                        tld_ns_found = True
                        break

        # Détecter référence vers Authoritative
        if tld_ns_found and not auth_ns_found:
            # Chercher les NS autoritaires
            match = re.search(r'(\S+\.gouv\.fr\.)\s+\d+\s+IN\s+NS\s+(\S+)', line)
            if match:
                auth_zone = match.group(1).rstrip('.')
                auth_ns_full = match.group(2)
                auth_ns = auth_ns_full.split('.')[0]

                # Query vers TLD
                tld_server = [p for p in diagram.participants if 'TLD' in p][0]
                diagram.add_query("Recursive DNS", tld_server,
                                f"Query NS for {auth_zone}",
                                act_dst=True)
                diagram.add_response(tld_server, "Recursive DNS",
                                   f"Referral to {auth_zone} NS ({auth_ns})",
                                   deact_src=True)

                # Auth server
                auth_server = f"Auth {auth_zone} ({auth_ns})"
                diagram.add_participant(auth_server, "f233")
                auth_ns_found = True

        # Détecter réponse finale
        if auth_ns_found and ('CNAME' in line or ('IN\t\t' in line and 'A\t' in line)):
            if 'CNAME' in line:
                match = re.search(r'CNAME\s+(\S+)', line)
                if match:
                    cname_target = match.group(1).rstrip('.')
                    auth_server = [p for p in diagram.participants if 'Auth' in p][0]
                    diagram.add_query("Recursive DNS", auth_server,
                                    f"Query A for {domain}",
                                    act_dst=True)
                    diagram.add_response(auth_server, "Recursive DNS",
                                       f"CNAME → {cname_target}",
                                       deact_src=True)
                    diagram.add_response("Recursive DNS", "Device",
                                       f"CNAME → {cname_target}",
                                       deact_src=True)
                    diagram.lines.append("deactivate Device")
                    break
            elif 'IN\t\tA\t' in line or 'IN  A ' in line:
                match = re.search(r'IN\s+A\s+(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    ip = match.group(1)
                    auth_server = [p for p in diagram.participants if 'Auth' in p][0]
                    if not any('Query A for' in l for l in diagram.lines):
                        diagram.add_query("Recursive DNS", auth_server,
                                        f"Query A for {domain}",
                                        act_dst=True)
                    diagram.add_response(auth_server, "Recursive DNS",
                                       f"A → {ip}",
                                       deact_src=True)
                    diagram.add_response("Recursive DNS", "Device",
                                       f"A → {ip}",
                                       deact_src=True)
                    diagram.lines.append("deactivate Device")
                    break

    return diagram.generate()


def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "www.impots.gouv.fr"
    print(f"# Résolution DNS réelle via dig +trace: {domain}\n", file=sys.stderr)

    diagram = parse_dig_trace(domain)
    if diagram:
        print(diagram)
    else:
        print("# Erreur lors de la génération du diagramme", file=sys.stderr)


if __name__ == "__main__":
    main()
