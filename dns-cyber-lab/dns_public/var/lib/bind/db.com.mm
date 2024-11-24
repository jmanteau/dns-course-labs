$TTL 86400
@   IN  SOA ns1.com.mm. admin.com.mm. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.mm.
@   IN  NS  ns2.com.mm.
ns1.com.mm. IN A 10.0.0.1
ns2.com.mm. IN A 10.0.0.2
google IN A 42.112.24.20
google IN A 177.160.116.237
mytel IN A 63.127.151.214
