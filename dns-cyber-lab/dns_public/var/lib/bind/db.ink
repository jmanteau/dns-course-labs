$TTL 86400
@   IN  SOA ns1.ink. admin.ink. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.ink.
@   IN  NS  ns2.ink.
ns1.ink. IN A 10.0.0.1
ns2.ink. IN A 10.0.0.2
tracker IN A 142.103.133.169
