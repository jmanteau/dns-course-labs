$TTL 86400
@   IN  SOA ns1.com.ni. admin.com.ni. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.ni.
@   IN  NS  ns2.com.ni.
ns1.com.ni. IN A 10.0.0.1
ns2.com.ni. IN A 10.0.0.2
google IN A 73.67.26.14
