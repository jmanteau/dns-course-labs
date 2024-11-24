while read -r prefix; do
    while read -r domain; do
        echo "${prefix}.${domain}"
    done < cloudflare-radar_top-10000-domains_20241111-20241118.csv
done < top10_prefixes.txt > massdns_input.txt
