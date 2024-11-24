$TTL 86400
@   IN  SOA ns1.mg. admin.mg. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.mg.
@   IN  NS  ns2.mg.
ns1.mg. IN A 10.0.0.1
ns2.mg. IN A 10.0.0.2
google IN A 65.98.255.149
