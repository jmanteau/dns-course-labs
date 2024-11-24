$TTL 86400
@   IN  SOA ns1.sc. admin.sc. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.sc.
@   IN  NS  ns2.sc.
ns1.sc. IN A 10.0.0.1
ns2.sc. IN A 10.0.0.2
google IN A 15.156.30.47
google IN A 139.108.29.12
google IN A 45.90.234.254
