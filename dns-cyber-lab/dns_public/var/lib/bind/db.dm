$TTL 86400
@   IN  SOA ns1.dm. admin.dm. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.dm.
@   IN  NS  ns2.dm.
ns1.dm. IN A 10.0.0.1
ns2.dm. IN A 10.0.0.2
google IN A 6.104.118.136
