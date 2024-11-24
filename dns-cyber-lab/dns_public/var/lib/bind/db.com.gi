$TTL 86400
@   IN  SOA ns1.com.gi. admin.com.gi. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.gi.
@   IN  NS  ns2.com.gi.
ns1.com.gi. IN A 10.0.0.1
ns2.com.gi. IN A 10.0.0.2
google IN A 80.102.59.217
google IN A 165.15.155.239
google IN A 16.44.50.141
