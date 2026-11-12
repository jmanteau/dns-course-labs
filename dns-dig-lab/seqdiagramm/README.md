# Générateur de Diagrammes de Séquence DNS

Scripts Python pour générer des diagrammes de séquence compatibles avec sequence-diagram.org, visualisant la résolution DNS réelle.

## Installation

```bash
uv sync
```

## Scripts Disponibles

### dns_trace_diagram.py (RECOMMANDÉ)

Utilise `dig +trace` pour capturer la résolution DNS réelle et générer le diagramme.

**Utilisation:**
```bash
uv run python dns_trace_diagram.py www.impots.gouv.fr
```

**Avantages:**
- Résolution DNS 100% réelle
- Parse la sortie de `dig +trace`
- Fonctionne même avec restrictions réseau

**Sortie:**
Le script génère du code pour sequence-diagram.org montrant:
1. Device → Recursive DNS
2. Recursive DNS → Root DNS
3. Root DNS → TLD (.fr)
4. TLD → Authoritative (impots.gouv.fr)
5. Résultat final (A ou CNAME)

### dns_resolver_diagram.py

Tentative de résolution itérative pure avec `dnspython`.

**Note:** Peut ne pas fonctionner si les serveurs root sont bloqués par le firewall.

## Exemple de Sortie

```
title Real DNS Resolution
fontawesome5solid f109 Device
fontawesome5solid f233 Recursive DNS
fontawesome5solid f233 Root DNS
fontawesome5solid f233 TLD .fr (d)
fontawesome5solid f233 Auth impots.gouv.fr (dns2)

activate Device
Device->Recursive DNS: www.impots.gouv.fr ?
abox over Recursive DNS: Start Resolution (No Cache)
activate Recursive DNS
activate Root DNS
Recursive DNS->Root DNS: Query NS for .fr
Recursive DNS<-Root DNS: Referral to .fr NS (d)
deactivate Root DNS
activate TLD .fr (d)
Recursive DNS->TLD .fr (d): Query NS for impots.gouv.fr
Recursive DNS<-TLD .fr (d): Referral to impots.gouv.fr NS (dns2)
deactivate TLD .fr (d)
activate Auth impots.gouv.fr (dns2)
Recursive DNS->Auth impots.gouv.fr (dns2): Query A for www.impots.gouv.fr
Recursive DNS<-Auth impots.gouv.fr (dns2): CNAME → www.impots.gouv.fr.edgesuite.net
deactivate Auth impots.gouv.fr (dns2)
Device<-Recursive DNS: CNAME → www.impots.gouv.fr.edgesuite.net
deactivate Recursive DNS
deactivate Device
```

## Visualisation

1. Copier la sortie du script
2. Aller sur https://sequence-diagram.org
3. Coller le code dans l'éditeur
4. Le diagramme s'affiche automatiquement

## Dépendances

- Python 3.8+
- dnspython
- dig (outil système)
