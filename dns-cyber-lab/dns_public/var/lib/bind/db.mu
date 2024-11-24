$TTL 86400
@   IN  SOA ns1.mu. admin.mu. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.mu.
@   IN  NS  ns2.mu.
ns1.mu. IN A 10.0.0.1
ns2.mu. IN A 10.0.0.2
google IN A 101.127.38.36
google IN A 157.39.200.217
google IN A 18.204.97.144
