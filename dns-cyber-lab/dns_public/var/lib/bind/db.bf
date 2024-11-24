$TTL 86400
@   IN  SOA ns1.bf. admin.bf. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.bf.
@   IN  NS  ns2.bf.
ns1.bf. IN A 10.0.0.1
ns2.bf. IN A 10.0.0.2
google IN A 154.12.110.84
