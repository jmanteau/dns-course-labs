$TTL 86400
@   IN  SOA ns1.com.com. admin.com.com. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.com.
@   IN  NS  ns2.com.com.
ns1.com.com. IN A 10.0.0.1
ns2.com.com. IN A 10.0.0.2
channelexco IN A 65.89.212.183
channelexco IN A 64.173.212.17
