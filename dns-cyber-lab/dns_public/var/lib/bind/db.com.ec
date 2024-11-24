$TTL 86400
@   IN  SOA ns1.com.ec. admin.com.ec. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.ec.
@   IN  NS  ns2.com.ec.
ns1.com.ec. IN A 10.0.0.1
ns2.com.ec. IN A 10.0.0.2
google IN A 3.235.24.12