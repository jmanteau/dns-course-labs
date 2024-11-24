$TTL 86400
@   IN  SOA ns1.com.cy. admin.com.cy. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.com.cy.
@   IN  NS  ns2.com.cy.
ns1.com.cy. IN A 10.0.0.1
ns2.com.cy. IN A 10.0.0.2
google IN A 67.174.178.55
google IN A 105.32.148.112
