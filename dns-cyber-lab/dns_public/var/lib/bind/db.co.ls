$TTL 86400
@   IN  SOA ns1.co.ls. admin.co.ls. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.co.ls.
@   IN  NS  ns2.co.ls.
ns1.co.ls. IN A 10.0.0.1
ns2.co.ls. IN A 10.0.0.2
google IN A 63.254.41.22
