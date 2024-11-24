$TTL 86400
@   IN  SOA ns1.nr. admin.nr. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.nr.
@   IN  NS  ns2.nr.
ns1.nr. IN A 10.0.0.1
ns2.nr. IN A 10.0.0.2
google IN A 73.37.41.183
