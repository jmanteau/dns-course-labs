$TTL 86400
@   IN  SOA ns1.cl. admin.cl. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.cl.
@   IN  NS  ns2.cl.
ns1.cl. IN A 10.0.0.1
ns2.cl. IN A 10.0.0.2
dump IN A 198.196.247.24
google IN A 184.142.39.134
google IN A 144.156.212.248
google IN A 70.35.133.74
tracker IN A 38.186.239.147
