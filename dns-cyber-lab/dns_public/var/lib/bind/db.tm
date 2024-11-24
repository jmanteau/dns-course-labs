$TTL 86400
@   IN  SOA ns1.tm. admin.tm. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.tm.
@   IN  NS  ns2.tm.
ns1.tm. IN A 10.0.0.1
ns2.tm. IN A 10.0.0.2
google IN A 84.69.41.68
tmok IN A 115.205.46.169
tmok IN A 33.255.45.184
