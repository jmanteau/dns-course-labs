$TTL 86400
@   IN  SOA ns1.ml. admin.ml. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.ml.
@   IN  NS  ns2.ml.
ns1.ml. IN A 10.0.0.1
ns2.ml. IN A 10.0.0.2
chai IN A 166.222.3.113
google IN A 2.197.227.167
