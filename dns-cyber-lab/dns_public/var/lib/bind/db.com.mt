$TTL 86400
@   IN  SOA ns1.com.mt. admin.com.mt. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.mt.
@   IN  NS  ns2.com.mt.
ns1.com.mt. IN A 10.0.0.1
ns2.com.mt. IN A 10.0.0.2
google IN A 52.207.178.169
google IN A 36.20.159.8
google IN A 72.214.10.153
