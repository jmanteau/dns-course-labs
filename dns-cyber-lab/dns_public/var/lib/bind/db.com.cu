$TTL 86400
@   IN  SOA ns1.com.cu. admin.com.cu. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.cu.
@   IN  NS  ns2.com.cu.
ns1.com.cu. IN A 10.0.0.1
ns2.com.cu. IN A 10.0.0.2
google IN A 51.196.183.47
