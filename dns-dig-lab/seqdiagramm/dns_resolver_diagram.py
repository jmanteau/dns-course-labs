#!/usr/bin/env python3
"""
Script de résolution DNS itérative réelle avec génération de diagramme de séquence.
Compatible avec sequence-diagram.org
"""

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


class IterativeDNSResolver:
    """Résolveur DNS itératif sans cache"""

    # Serveurs root DNS (quelques-uns pour redondance)
    ROOT_SERVERS = [
        "198.41.0.4",      # a.root-servers.net
        "199.9.14.201",    # b.root-servers.net
        "192.33.4.12",     # c.root-servers.net
        "199.7.91.13",     # d.root-servers.net
    ]

    def __init__(self, diagram):
        self.diagram = diagram
        self.query_count = 0

    def get_glue_records(self, response, nameservers):
        """Extrait les glue records (adresses IP des NS) de la réponse"""
        glue_ips = {}

        # Chercher dans la section additionnelle
        for rrset in response.additional:
            if rrset.rdtype == dns.rdatatype.A:
                ns_name = str(rrset.name).lower()
                for rdata in rrset:
                    glue_ips[ns_name] = str(rdata)
                    break

        # Associer les NS à leurs IPs
        ns_to_ip = {}
        for ns in nameservers:
            ns_lower = str(ns).lower()
            if ns_lower in glue_ips:
                ns_to_ip[str(ns)] = glue_ips[ns_lower]

        return ns_to_ip

    def query_server(self, server_ip, server_name, qname, qtype=dns.rdatatype.A):
        """Envoie une requête DNS à un serveur spécifique"""
        try:
            query = dns.message.make_query(qname, qtype, want_dnssec=False)
            query.flags &= ~dns.flags.RD  # Désactiver la récursion

            # Essayer UDP d'abord
            try:
                response = dns.query.udp(query, server_ip, timeout=10)
                self.query_count += 1
                return response
            except (dns.exception.Timeout, OSError) as e:
                print(f"# UDP timeout/error pour {server_name}, essai TCP...", file=sys.stderr)
                # Fallback sur TCP
                try:
                    response = dns.query.tcp(query, server_ip, timeout=10)
                    self.query_count += 1
                    return response
                except Exception as tcp_error:
                    print(f"# Erreur TCP pour {server_name} ({server_ip}): {tcp_error}",
                          file=sys.stderr)
                    return None

        except Exception as e:
            print(f"# Erreur lors de la requête vers {server_name} ({server_ip}): {e}",
                  file=sys.stderr)
            return None

    def resolve(self, domain):
        """Résout un domaine de manière itérative"""
        # Initialisation du diagramme
        self.diagram.add_participant("Device", "f109")
        self.diagram.add_participant("Recursive DNS", "f233")

        # Requête initiale du device
        self.diagram.add_query("Device", "Recursive DNS", f"{domain} ?",
                              activate_source=True)
        self.diagram.add_note("Recursive DNS", "Start Resolution (No Cache)")

        qname = dns.name.from_text(domain)

        # Essayer plusieurs serveurs root jusqu'à en trouver un qui répond
        current_server_ip = None
        for root_ip in self.ROOT_SERVERS:
            print(f"# Tentative de connexion au serveur root {root_ip}...", file=sys.stderr)
            test_query = dns.message.make_query("fr.", dns.rdatatype.NS)
            test_query.flags &= ~dns.flags.RD
            try:
                test_response = dns.query.udp(test_query, root_ip, timeout=5)
                current_server_ip = root_ip
                print(f"# Serveur root {root_ip} répond correctement", file=sys.stderr)
                break
            except:
                print(f"# Serveur root {root_ip} ne répond pas, essai suivant...", file=sys.stderr)
                continue

        if not current_server_ip:
            print(f"# ERREUR: Aucun serveur root ne répond. Vérifiez votre connexion réseau.", file=sys.stderr)
            return

        current_server_name = "Root DNS"
        self.diagram.add_participant(current_server_name, "f233")

        # Parcourir la hiérarchie DNS
        iteration = 0
        max_iterations = 15  # Protection contre les boucles infinies

        while iteration < max_iterations:
            iteration += 1

            # Envoyer la requête
            qtype_str = "A"
            self.diagram.add_query("Recursive DNS", current_server_name,
                                 f"Query {qtype_str} for {qname}",
                                 activate_dest=True,
                                 activate_source=(iteration == 1))

            response = self.query_server(current_server_ip, current_server_name,
                                        qname, dns.rdatatype.A)

            if not response:
                self.diagram.add_response(current_server_name, "Recursive DNS",
                                        "Error: No response",
                                        deactivate_source=True)
                break

            # Vérifier si on a une réponse finale
            if response.answer:
                # On a une réponse dans la section Answer
                answer_text = []
                cname_target = None
                final_ips = []

                for rrset in response.answer:
                    if rrset.rdtype == dns.rdatatype.CNAME:
                        cname_target = rrset[0].target
                        answer_text.append(f"CNAME → {cname_target}")
                    elif rrset.rdtype == dns.rdatatype.A:
                        for rdata in rrset:
                            final_ips.append(str(rdata))
                        answer_text.append(f"A → {', '.join(final_ips)}")

                self.diagram.add_response(current_server_name, "Recursive DNS",
                                        " | ".join(answer_text),
                                        deactivate_source=True)

                # Si on a un CNAME, il faut le résoudre
                if cname_target and not final_ips:
                    qname = cname_target
                    # Recommencer depuis le root pour le CNAME
                    current_server_ip = self.ROOT_SERVERS[0]
                    current_server_name = "Root DNS"
                    continue
                else:
                    # Réponse finale au device
                    final_response = " | ".join([f"A → {ip}" for ip in final_ips])
                    self.diagram.add_response("Recursive DNS", "Device",
                                            final_response,
                                            deactivate_source=True)
                    self.diagram.lines.append("deactivate Device")
                    break

            # Chercher les référencements (referrals)
            elif response.authority:
                nameservers = []
                zone = None

                # Trouver la zone et les NS
                for rrset in response.authority:
                    if rrset.rdtype == dns.rdatatype.NS:
                        zone = str(rrset.name)
                        for rdata in rrset:
                            nameservers.append(rdata.target)

                if not nameservers:
                    self.diagram.add_response(current_server_name, "Recursive DNS",
                                            "No NS found",
                                            deactivate_source=True)
                    break

                # Obtenir les glue records
                ns_to_ip = self.get_glue_records(response, nameservers)

                # Préparer la réponse
                if ns_to_ip:
                    next_ns = list(ns_to_ip.keys())[0]
                    next_ip = ns_to_ip[next_ns]
                    referral_text = f"Referral to {zone} NS ({next_ns})"
                else:
                    # Pas de glue record, prendre le premier NS
                    next_ns = str(nameservers[0])
                    referral_text = f"Referral to {zone} NS ({next_ns}, no glue)"
                    # Il faudrait résoudre le NS, mais on simplifie ici
                    self.diagram.add_response(current_server_name, "Recursive DNS",
                                            referral_text,
                                            deactivate_source=True)
                    break

                self.diagram.add_response(current_server_name, "Recursive DNS",
                                        referral_text,
                                        deactivate_source=True)

                # Préparer la prochaine itération
                # Nettoyer le nom du serveur pour le diagramme
                next_server_name = next_ns.replace('.', '_').rstrip('_')
                if len(next_server_name) > 30:
                    next_server_name = next_server_name[:27] + "..."

                # Déterminer le type de serveur
                if ".root-servers." in next_ns:
                    display_name = "Root DNS"
                elif zone.endswith(".fr.") or zone == "fr.":
                    display_name = f"TLD .fr ({next_ns.split('.')[0]})"
                else:
                    display_name = f"Auth {zone.rstrip('.')} ({next_ns.split('.')[0]})"

                self.diagram.add_participant(display_name, "f233")
                current_server_name = display_name
                current_server_ip = next_ip

            else:
                # Pas de réponse ni de referral
                self.diagram.add_response(current_server_name, "Recursive DNS",
                                        "No answer or referral",
                                        deactivate_source=True)
                break

        if iteration >= max_iterations:
            print(f"# Attention: nombre maximum d'itérations atteint",
                  file=sys.stderr)


def main():
    """Fonction principale"""
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    else:
        domain = "www.impots.gouv.fr"

    print(f"# Résolution DNS itérative pour: {domain}", file=sys.stderr)
    print(f"# Ceci peut prendre quelques secondes...\n", file=sys.stderr)

    # Créer le diagramme et le résolveur
    diagram = DNSSequenceDiagram()
    resolver = IterativeDNSResolver(diagram)

    # Effectuer la résolution
    resolver.resolve(domain)

    # Générer et afficher le diagramme
    print(diagram.generate())

    print(f"\n# Résolution terminée avec {resolver.query_count} requêtes DNS",
          file=sys.stderr)


if __name__ == "__main__":
    main()
