$TTL 86400
@   IN  SOA ns1.co.ma. admin.co.ma. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.co.ma.
@   IN  NS  ns2.co.ma.
ns1.co.ma. IN A 10.0.0.1
ns2.co.ma. IN A 10.0.0.2
google IN A 104.177.187.73
