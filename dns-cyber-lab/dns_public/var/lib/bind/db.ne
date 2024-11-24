$TTL 86400
@   IN  SOA ns1.ne. admin.ne. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.ne.
@   IN  NS  ns2.ne.
ns1.ne. IN A 10.0.0.1
ns2.ne. IN A 10.0.0.2
google IN A 66.21.27.156
