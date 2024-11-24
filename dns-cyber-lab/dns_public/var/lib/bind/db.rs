$TTL 86400
@   IN  SOA ns1.rs. admin.rs. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.rs.
@   IN  NS  ns2.rs.
ns1.rs. IN A 10.0.0.1
ns2.rs. IN A 10.0.0.2
google IN A 31.25.252.146
