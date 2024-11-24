$TTL 86400
@   IN  SOA ns1.bi. admin.bi. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.bi.
@   IN  NS  ns2.bi.
ns1.bi. IN A 10.0.0.1
ns2.bi. IN A 10.0.0.2
google IN A 66.124.211.65
newsroom IN A 108.131.146.136
newsroom IN A 111.205.141.207
