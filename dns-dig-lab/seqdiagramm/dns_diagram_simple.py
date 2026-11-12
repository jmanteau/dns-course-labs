#!/usr/bin/env python3
"""
Script simplifié de génération de diagramme de séquence DNS.
Utilise le resolver système mais trace la hiérarchie.
"""

import dns.resolver
import dns.rdatatype
import sys


class DNSSequenceDiagram:
    """Générateur de diagramme de séquence"""

    def __init__(self):
        self.lines = []
        self.participants = set()

    def add_participant(self, name, icon="f233"):
        if name not in self.participants:
            self.participants.add(name)
            self.lines.insert(len([l for l in self.lines if l.startswith("fontawesome")]),
                            f"fontawesome5solid {icon} {name}")

    def add_query(self, source, dest, query_text, activate_source=False, activate_dest=False):
        if activate_source:
            self.lines.append(f"activate {source}")
        if activate_dest:
            self.lines.append(f"activate {dest}")
        self.lines.append(f"{source}->{dest}: {query_text}")

    def add_response(self, source, dest, response_text, deactivate_source=False):
        self.lines.append(f"{dest}<-{source}: {response_text}")
        if deactivate_source:
            self.lines.append(f"deactivate {source}")

    def add_note(self, participant, note_text):
        self.lines.append(f"abox over {participant}: {note_text}")

    def generate(self, title="Real DNS Resolution"):
        output = [f"title {title}"]
        output.extend([l for l in self.lines if l.startswith("fontawesome")])
        output.append("")
        output.extend([l for l in self.lines if not l.startswith("fontawesome")])
        return "\n".join(output)


def resolve_with_diagram(domain):
    """Résout un domaine et génère le diagramme"""
    diagram = DNSSequenceDiagram()
    resolver = dns.resolver.Resolver()

    # Participants
    diagram.add_participant("Device", "f109")
    diagram.add_participant("Recursive DNS", "f233")
    diagram.add_participant("Root DNS", "f233")

    # Requête initiale
    diagram.add_query("Device", "Recursive DNS", f"{domain} ?", activate_source=True)
    diagram.add_note("Recursive DNS", "Start Resolution (No Cache)")

    # Étape 1: Root -> TLD
    parts = domain.rstrip('.').split('.')
    tld = parts[-1]

    diagram.add_query("Recursive DNS", "Root DNS", f"Query NS for .{tld}",
                     activate_dest=True, activate_source=True)

    try:
        # Obtenir les NS pour le TLD
        tld_ns_answers = resolver.resolve(f"{tld}.", 'NS')
        first_tld_ns = str(tld_ns_answers[0].target).split('.')[0]

        diagram.add_response("Root DNS", "Recursive DNS",
                           f"Referral to .{tld} NS ({first_tld_ns})",
                           deactivate_source=True)

        # TLD Server
        tld_server = f"TLD .{tld} ({first_tld_ns})"
        diagram.add_participant(tld_server, "f233")

        # Étape 2: TLD -> Authoritative
        if len(parts) >= 2:
            auth_zone = '.'.join(parts[-2:])
            diagram.add_query("Recursive DNS", tld_server,
                            f"Query NS for {auth_zone}",
                            activate_dest=True)

            try:
                # Obtenir les NS pour le domaine autoritaire
                auth_ns_answers = resolver.resolve(f"{auth_zone}.", 'NS')
                first_auth_ns = str(auth_ns_answers[0].target).split('.')[0]

                diagram.add_response(tld_server, "Recursive DNS",
                                   f"Referral to {auth_zone} NS ({first_auth_ns})",
                                   deactivate_source=True)

                # Authoritative Server
                auth_server = f"Auth {auth_zone} ({first_auth_ns})"
                diagram.add_participant(auth_server, "f233")

                # Étape 3: Query final
                diagram.add_query("Recursive DNS", auth_server,
                                f"Query A for {domain}",
                                activate_dest=True)

                # Résolution finale
                try:
                    answers = resolver.resolve(domain, 'A')
                    ips = [str(rdata) for rdata in answers]

                    # Vérifier CNAME
                    response_parts = []
                    try:
                        cname_answers = resolver.resolve(domain, 'CNAME')
                        for cname in cname_answers:
                            response_parts.append(f"CNAME → {cname.target}")
                    except:
                        pass

                    response_parts.append(f"A → {', '.join(ips[:3])}")

                    diagram.add_response(auth_server, "Recursive DNS",
                                       " | ".join(response_parts),
                                       deactivate_source=True)

                    diagram.add_response("Recursive DNS", "Device",
                                       f"A → {', '.join(ips[:3])}",
                                       deactivate_source=True)
                    diagram.lines.append("deactivate Device")

                except Exception as e:
                    diagram.add_response(auth_server, "Recursive DNS",
                                       f"Error: {str(e)[:30]}",
                                       deactivate_source=True)

            except Exception as e:
                diagram.add_response(tld_server, "Recursive DNS",
                                   f"NS lookup failed",
                                   deactivate_source=True)

    except Exception as e:
        diagram.add_response("Root DNS", "Recursive DNS",
                           f"Error: {str(e)[:30]}",
                           deactivate_source=True)

    return diagram.generate()


def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "www.impots.gouv.fr"
    print(f"# Génération diagramme pour: {domain}\n", file=sys.stderr)
    print(resolve_with_diagram(domain))


if __name__ == "__main__":
    main()
