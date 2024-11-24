$TTL 86400
@   IN  SOA ns1.as. admin.as. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.as.
@   IN  NS  ns2.as.
ns1.as. IN A 10.0.0.1
ns2.as. IN A 10.0.0.2
google IN A 6.93.69.74
