$TTL 86400
@   IN  SOA ns1.gp. admin.gp. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.gp.
@   IN  NS  ns2.gp.
ns1.gp. IN A 10.0.0.1
ns2.gp. IN A 10.0.0.2
google IN A 161.121.253.204
google IN A 219.13.222.253
google IN A 66.29.19.17
