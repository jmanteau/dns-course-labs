$TTL 86400
@   IN  SOA ns1.td. admin.td. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.td.
@   IN  NS  ns2.td.
ns1.td. IN A 10.0.0.1
ns2.td. IN A 10.0.0.2
google IN A 133.11.132.82
