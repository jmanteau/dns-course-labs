$TTL 86400
@   IN  SOA ns1.mk. admin.mk. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.mk.
@   IN  NS  ns2.mk.
ns1.mk. IN A 10.0.0.1
ns2.mk. IN A 10.0.0.2
google IN A 72.130.245.149
