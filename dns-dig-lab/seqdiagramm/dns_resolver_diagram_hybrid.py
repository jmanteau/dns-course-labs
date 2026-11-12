#!/usr/bin/env python3
"""
Script de résolution DNS avec reconstruction de la chaîne itérative.
Mode hybride : utilise des requêtes DNS normales mais reconstitue le chemin itératif.
Compatible avec sequence-diagram.org
"""

import dns.resolver
import dns.message
import dns.query
import dns.rdatatype
import dns.name
import sys


class DNSSequenceDiagram:
    """Générateur de diagramme de séquence pour la résolution DNS"""

    def __init__(self):
        self.lines = []
        self.participants = set()
        self.step_counter = 0

    def add_participant(self, name, icon="f233"):
        """Ajoute un participant avec son icône FontAwesome"""
        if name not in self.participants:
            self.participants.add(name)
            self.lines.insert(len([l for l in self.lines if l.startswith("fontawesome")]),
                            f"fontawesome5solid {icon} {name}")

    def add_query(self, source, dest, query_text, activate_source=False, activate_dest=False):
        """Ajoute une requête DNS au diagramme"""
        if activate_source:
            self.lines.append(f"activate {source}")
        if activate_dest:
            self.lines.append(f"activate {dest}")
        self.lines.append(f"{source}->{dest}: {query_text}")
        self.step_counter += 1

    def add_response(self, source, dest, response_text, deactivate_source=False):
        """Ajoute une réponse DNS au diagramme"""
        self.lines.append(f"{dest}<-{source}: {response_text}")
        if deactivate_source:
            self.lines.append(f"deactivate {source}")

    def add_note(self, participant, note_text):
        """Ajoute une note sur un participant"""
        self.lines.append(f"abox over {participant}: {note_text}")

    def generate(self, title="Real DNS Resolution"):
        """Génère le code complet du diagramme"""
        output = [f"title {title}"]
        output.extend([l for l in self.lines if l.startswith("fontawesome")])
        output.append("")
        output.extend([l for l in self.lines if not l.startswith("fontawesome")])
        return "\n".join(output)


class HybridDNSResolver:
    """Résolveur DNS qui reconstitue la chaîne itérative"""

    def __init__(self, diagram):
        self.diagram = diagram
        self.resolver = dns.resolver.Resolver()
        self.resolver.use_edns(0, 0, 4096)

    def get_nameserver_for_zone(self, zone):
        """Obtient les serveurs de noms autoritaires pour une zone"""
        try:
            # Requête NS pour la zone
            answers = self.resolver.resolve(zone, 'NS')
            ns_records = [str(rdata.target) for rdata in answers]

            # Essayer d'obtenir l'adresse IP du premier NS
            if ns_records:
                try:
                    ns_ips = self.resolver.resolve(ns_records[0], 'A')
                    return ns_records[0], str(ns_ips[0])
                except:
                    return ns_records[0], None

            return None, None
        except Exception as e:
            print(f"# Erreur lors de la résolution NS pour {zone}: {e}", file=sys.stderr)
            return None, None

    def query_direct(self, server_ip, qname, qtype=dns.rdatatype.A):
        """Tente une requête DNS directe (itérative)"""
        if not server_ip:
            return None

        try:
            query = dns.message.make_query(qname, qtype, want_dnssec=False)
            query.flags &= ~dns.flags.RD  # Désactiver la récursion

            try:
                response = dns.query.udp(query, server_ip, timeout=3)
                return response
            except:
                try:
                    response = dns.query.tcp(query, server_ip, timeout=3)
                    return response
                except:
                    return None
        except Exception as e:
            return None

    def resolve(self, domain):
        """Résout un domaine et reconstitue la chaîne itérative"""
        # Initialisation du diagramme
        self.diagram.add_participant("Device", "f109")
        self.diagram.add_participant("Recursive DNS", "f233")

        # Requête initiale du device
        self.diagram.add_query("Device", "Recursive DNS", f"{domain} ?",
                              activate_source=True)
        self.diagram.add_note("Recursive DNS", "Start Resolution (No Cache)")

        # Décomposer le domaine en hiérarchie
        parts = domain.rstrip('.').split('.')
        hierarchy = []

        # Construire la hiérarchie : root -> TLD -> domain -> subdomain
        for i in range(len(parts)):
            zone = '.'.join(parts[i:]) + '.'
            hierarchy.append(zone)

        hierarchy.reverse()  # Commencer par la racine

        # Ajouter root explicitement
        self.diagram.add_participant("Root DNS", "f233")
        self.diagram.add_query("Recursive DNS", "Root DNS",
                             f"Query NS for {hierarchy[0] if len(hierarchy) > 0 else domain}",
                             activate_dest=True,
                             activate_source=True)

        # Simuler la réponse du root pour le TLD
        if len(hierarchy) > 0:
            tld = hierarchy[0]
            tld_ns, tld_ip = self.get_nameserver_for_zone(tld)

            if tld_ns:
                self.diagram.add_response("Root DNS", "Recursive DNS",
                                        f"Referral to {tld} NS ({tld_ns.split('.')[0]})",
                                        deactivate_source=True)

                # TLD serveur
                tld_display = f"TLD {tld.rstrip('.')} ({tld_ns.split('.')[0]})"
                self.diagram.add_participant(tld_display, "f233")

                # Si on a plus d'un niveau
                if len(hierarchy) > 1:
                    next_zone = hierarchy[1]
                    self.diagram.add_query("Recursive DNS", tld_display,
                                         f"Query NS for {next_zone.rstrip('.')}",
                                         activate_dest=True)

                    # Obtenir le NS du domaine autoritaire
                    auth_ns, auth_ip = self.get_nameserver_for_zone(next_zone)

                    if auth_ns:
                        self.diagram.add_response(tld_display, "Recursive DNS",
                                                f"Referral to {next_zone.rstrip('.')} NS ({auth_ns.split('.')[0]})",
                                                deactivate_source=True)

                        # Serveur autoritaire
                        auth_display = f"Auth {next_zone.rstrip('.')} ({auth_ns.split('.')[0]})"
                        self.diagram.add_participant(auth_display, "f233")

                        # Requête finale pour le domaine complet
                        self.diagram.add_query("Recursive DNS", auth_display,
                                             f"Query A for {domain}",
                                             activate_dest=True)

                        # Tenter d'obtenir la réponse réelle
                        try:
                            # Essayer d'abord une requête directe si on a l'IP
                            response = None
                            if auth_ip:
                                response = self.query_direct(auth_ip, domain, dns.rdatatype.A)

                            # Sinon utiliser le resolver normal
                            if not response:
                                answers = self.resolver.resolve(domain, 'A')
                                answer_text = []

                                # Vérifier s'il y a des CNAME
                                try:
                                    cname_answers = self.resolver.resolve(domain, 'CNAME')
                                    for rdata in cname_answers:
                                        answer_text.append(f"CNAME → {rdata.target}")
                                except:
                                    pass

                                # Ajouter les enregistrements A
                                ips = [str(rdata) for rdata in answers]
                                answer_text.append(f"A → {', '.join(ips)}")

                                self.diagram.add_response(auth_display, "Recursive DNS",
                                                        " | ".join(answer_text),
                                                        deactivate_source=True)

                                # Réponse finale au device
                                self.diagram.add_response("Recursive DNS", "Device",
                                                        f"A → {', '.join(ips)}",
                                                        deactivate_source=True)
                                self.diagram.lines.append("deactivate Device")

                            else:
                                # Traiter la réponse directe
                                answer_text = []
                                final_ips = []

                                for rrset in response.answer:
                                    if rrset.rdtype == dns.rdatatype.CNAME:
                                        for rdata in rrset:
                                            answer_text.append(f"CNAME → {rdata.target}")
                                    elif rrset.rdtype == dns.rdatatype.A:
                                        for rdata in rrset:
                                            final_ips.append(str(rdata))

                                if final_ips:
                                    answer_text.append(f"A → {', '.join(final_ips)}")

                                self.diagram.add_response(auth_display, "Recursive DNS",
                                                        " | ".join(answer_text) if answer_text else f"A → {', '.join(final_ips)}",
                                                        deactivate_source=True)

                                self.diagram.add_response("Recursive DNS", "Device",
                                                        f"A → {', '.join(final_ips)}",
                                                        deactivate_source=True)
                                self.diagram.lines.append("deactivate Device")

                        except dns.resolver.NoAnswer:
                            self.diagram.add_response(auth_display, "Recursive DNS",
                                                    "No A record found",
                                                    deactivate_source=True)
                        except Exception as e:
                            print(f"# Erreur lors de la résolution finale: {e}", file=sys.stderr)
                            self.diagram.add_response(auth_display, "Recursive DNS",
                                                    f"Error: {str(e)[:50]}",
                                                    deactivate_source=True)
                    else:
                        self.diagram.add_response(tld_display, "Recursive DNS",
                                                "Could not find authoritative NS",
                                                deactivate_source=True)
                else:
                    # Pas de hiérarchie supplémentaire (domaine de premier niveau)
                    self.diagram.add_response(tld_display, "Recursive DNS",
                                            "Direct resolution",
                                            deactivate_source=True)
            else:
                self.diagram.add_response("Root DNS", "Recursive DNS",
                                        "Could not resolve TLD NS",
                                        deactivate_source=True)


def main():
    """Fonction principale"""
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    else:
        domain = "www.impots.gouv.fr"

    print(f"# Résolution DNS (mode hybride) pour: {domain}", file=sys.stderr)
    print(f"# Ce mode reconstitue la chaîne itérative à partir de requêtes récursives\n", file=sys.stderr)

    # Créer le diagramme et le résolveur
    diagram = DNSSequenceDiagram()
    resolver = HybridDNSResolver(diagram)

    # Effectuer la résolution
    try:
        resolver.resolve(domain)
    except Exception as e:
        print(f"# Erreur générale: {e}", file=sys.stderr)

    # Générer et afficher le diagramme
    print(diagram.generate())


if __name__ == "__main__":
    main()
