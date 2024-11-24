$TTL 86400
@   IN  SOA ns1.do. admin.do. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.do.
@   IN  NS  ns2.do.
ns1.do. IN A 10.0.0.1
ns2.do. IN A 10.0.0.2
zalan IN A 35.170.210.202
