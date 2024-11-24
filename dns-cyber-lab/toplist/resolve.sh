massdns -c 10 -s 100 -r resolvers.txt -o S -t A -t CNAME -t AAAA massdns_input.txt > massdns_output.txt
massdns -c 10 -s 100 -r resolvers.txt -o S -t NS -t MX -t CAA -t TXT -t SOA cloudflare-radar_top-10000-domains_20241111-20241118.csv > massdns_output2.txt
