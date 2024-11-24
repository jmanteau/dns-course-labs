$TTL 86400
@   IN  SOA ns1.al. admin.al. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.al.
@   IN  NS  ns2.al.
ns1.al. IN A 10.0.0.1
ns2.al. IN A 10.0.0.2
google IN A 209.205.164.252
