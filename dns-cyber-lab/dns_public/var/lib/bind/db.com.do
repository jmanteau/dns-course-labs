$TTL 86400
@   IN  SOA ns1.com.do. admin.com.do. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.do.
@   IN  NS  ns2.com.do.
ns1.com.do. IN A 10.0.0.1
ns2.com.do. IN A 10.0.0.2
google IN A 178.28.34.72
google IN A 114.31.106.141
google IN A 116.73.42.16
