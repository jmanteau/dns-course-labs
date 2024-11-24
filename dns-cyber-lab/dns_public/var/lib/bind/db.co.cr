$TTL 86400
@   IN  SOA ns1.co.cr. admin.co.cr. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.co.cr.
@   IN  NS  ns2.co.cr.
ns1.co.cr. IN A 10.0.0.1
ns2.co.cr. IN A 10.0.0.2
google IN A 158.116.0.243