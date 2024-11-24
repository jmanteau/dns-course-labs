$TTL 86400
@   IN  SOA ns1.md. admin.md. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.md.
@   IN  NS  ns2.md.
ns1.md. IN A 10.0.0.1
ns2.md. IN A 10.0.0.2
google IN A 18.252.73.140
obsidian IN A 87.138.9.12
obsidian IN A 17.37.88.39
obsidian IN A 48.42.210.143
