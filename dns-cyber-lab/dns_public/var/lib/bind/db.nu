$TTL 86400
@   IN  SOA ns1.nu. admin.nu. (
        2024010101 ; Serial
        3600       ; Refresh
        1800       ; Retry
        1209600    ; Expire
        86400 )    ; Minimum TTL
;
@   IN  NS  ns1.nu.
@   IN  NS  ns2.nu.
ns1.nu. IN A 10.0.0.1
ns2.nu. IN A 10.0.0.2
google IN A 133.77.177.195
google IN A 133.202.176.245
google IN A 203.226.64.41
mine IN A 181.144.161.131
mine IN A 27.76.90.36
mine IN A 13.112.110.155
