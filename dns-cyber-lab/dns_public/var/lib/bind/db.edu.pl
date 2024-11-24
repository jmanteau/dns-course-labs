$TTL 86400
@   IN  SOA ns1.edu.pl. admin.edu.pl. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.edu.pl.
@   IN  NS  ns2.edu.pl.
ns1.edu.pl. IN A 10.0.0.1
ns2.edu.pl. IN A 10.0.0.2
royalcanin IN A 35.143.100.162
