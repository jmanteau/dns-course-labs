$TTL 86400
@   IN  SOA ns1.tl. admin.tl. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.tl.
@   IN  NS  ns2.tl.
ns1.tl. IN A 10.0.0.1
ns2.tl. IN A 10.0.0.2
google IN A 18.235.180.75
google IN A 185.99.245.96
google IN A 107.81.219.188
