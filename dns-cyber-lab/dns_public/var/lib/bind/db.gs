$TTL 86400
@   IN  SOA ns1.gs. admin.gs. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.gs.
@   IN  NS  ns2.gs.
ns1.gs. IN A 10.0.0.1
ns2.gs. IN A 10.0.0.2
airthin IN A 128.164.90.147
airthin IN A 106.63.182.161
