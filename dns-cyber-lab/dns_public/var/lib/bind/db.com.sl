$TTL 86400
@   IN  SOA ns1.com.sl. admin.com.sl. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.sl.
@   IN  NS  ns2.com.sl.
ns1.com.sl. IN A 10.0.0.1
ns2.com.sl. IN A 10.0.0.2
google IN A 29.118.221.179
google IN A 167.232.64.164
google IN A 151.122.155.153
