$TTL 86400
@    IN    SOA   ns1.commandcontrol.com. admin.commandcontrol.com. (
                2024111201   ; Serial (YYYYMMDDNN format)
                3600         ; Refresh (1 hour)
                1800         ; Retry (30 minutes)
                1209600      ; Expire (2 weeks)
                86400        ; Minimum TTL (1 day)
)

; Nameservers
@    IN    NS    ns1.commandcontrol.com.

ns1.commandcontrol.com.  IN A 10.89.1.4
s.commandcontrol.com.  IN NS 10.89.1.4

test.commandcontrol.com.  IN A  1.1.1.1

