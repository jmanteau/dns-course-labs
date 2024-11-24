$TTL 86400
@   IN  SOA ns1.ec. admin.ec. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.ec.
@   IN  NS  ns2.ec.
ns1.ec. IN A 10.0.0.1
ns2.ec. IN A 10.0.0.2
redecanais IN A 160.188.13.187
