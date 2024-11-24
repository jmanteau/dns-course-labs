import csv
import random
import os

# Define output directory for configuration and zone files
output_dir = "dns_config"
zone_dir = "/var/lib/bind"
os.makedirs(output_dir, exist_ok=True)

# Define the population and weights
numbers = [1, 2, 3]
weights = [0.6, 0.2, 0.2]  # 60% chance for 1, 20% each for 2 and 3


# Define a function to generate a random public IP address
def generate_random_ip():
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

# Function to write zone file
def write_zone_file(tld, records):

    zone_file_path = os.path.join(output_dir, f"db.{tld}")
    with open(zone_file_path, "w") as zone_file:
        zone_file.write(f"$TTL 86400\n")
        zone_file.write(f"@   IN  SOA ns1.{tld}. admin.{tld}. (\n")
        zone_file.write(f"        2024010101 ; Serial\n")
        zone_file.write(f"        3600       ; Refresh\n")
        zone_file.write(f"        1800       ; Retry\n")
        zone_file.write(f"        1209600    ; Expire\n")
        zone_file.write(f"        86400 )    ; Minimum TTL\n")
        zone_file.write(f";\n")
        zone_file.write(f"@   IN  NS  ns1.{tld}.\n")
        zone_file.write(f"@   IN  NS  ns2.{tld}.\n")
        zone_file.write(f"ns1.{tld}. IN A 10.0.0.1\n")
        zone_file.write(f"ns2.{tld}. IN A 10.0.0.2\n")
        for name, ip in records:
            zone_file.write(f"{name} IN A {ip}\n")
    print(f"Zone file written: {zone_file_path}")


# Function to write named.conf.local configuration
def write_named_conf(tlds):
    named_conf_path = os.path.join(output_dir, "named.conf.local")
    with open(named_conf_path, "w") as conf_file:
        for tld in tlds:
            conf_file.write(f"zone \"{tld}\" {{\n")
            conf_file.write(f"    type primary;\n")
            conf_file.write(f"    file \"{zone_dir}/db.{tld}\";\n")
            conf_file.write(f"    allow-query {{ any; }};\n")
            conf_file.write(f"}};\n\n")
    print(f"BIND configuration written: {named_conf_path}")

# Read CSV and process DNS names
def process_csv(input_csv):
    tld_records = {}
    with open(input_csv, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].startswith("#"):  # Skip empty lines or comments
                continue
            dns_name = row[0].strip()
            if "." not in dns_name:
                continue
            name, tld = dns_name.split(".", 1)
            random_number_entries = random.choices(numbers, weights=weights, k=1)[0]
            for i in range(random_number_entries):
                ip = generate_random_ip()
                if tld not in tld_records:
                    tld_records[tld] = []
                tld_records[tld].append((name, ip))
    return tld_records

# Main function
def main():
    input_csv = "cloudflare-radar_top-10000-domains_20241111-20241118.csv"
    tld_records = process_csv(input_csv)

    # Write zone files
    for tld, records in tld_records.items():
        write_zone_file(tld, records)

    # Write named.conf.local
    write_named_conf(tld_records.keys())

if __name__ == "__main__":
    main()

