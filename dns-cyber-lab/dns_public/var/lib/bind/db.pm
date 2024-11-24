$TTL 86400
@   IN  SOA ns1.pm. admin.pm. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.pm.
@   IN  NS  ns2.pm.
ns1.pm. IN A 10.0.0.1
ns2.pm. IN A 10.0.0.2
booth IN A 138.229.195.237
