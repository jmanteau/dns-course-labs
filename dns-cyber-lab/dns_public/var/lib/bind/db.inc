$TTL 86400
@   IN  SOA ns1.inc. admin.inc. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.inc.
@   IN  NS  ns2.inc.
ns1.inc. IN A 10.0.0.1
ns2.inc. IN A 10.0.0.2
alta IN A 192.134.76.240
