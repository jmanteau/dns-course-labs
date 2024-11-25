import math
from collections import Counter, defaultdict
from typing import List, Dict
import re
from datetime import datetime, timedelta
import yaml
import tldextract
import logging
from rich.progress import Progress
from rich.logging import RichHandler

# Configure Rich logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)
logger = logging.getLogger("rich")

def calculate_entropy(domain: str) -> float:
    """
    Calculates the Shannon entropy of a domain name.

    **Theory and Purpose:**
    - **Entropy** measures the randomness or unpredictability in the domain's character distribution.
    - A higher entropy value indicates more randomness, which is common in algorithmically generated domains used by malware (e.g., DGA domains).
    - By calculating entropy, we can identify domains that may not be human-readable and could be suspicious.

    **Args:**
        domain (str): The domain name to analyze.

    **Returns:**
        float: The entropy value of the domain name.
    """
    domain = domain.replace('.', '')
    if not domain:
        return 0.0
    probabilities = [n / len(domain) for n in Counter(domain).values()]
    entropy = -sum(p * math.log2(p) for p in probabilities)
    return entropy

def lexical_analysis(domain: str) -> Dict[str, float]:
    """
    Performs lexical analysis on a domain name.
    Calculates ratios of non-letter characters, hex characters, and vowels.

    **Theory and Purpose:**
    - **Non-letter Ratio:** Measures the proportion of characters that are not letters (e.g., numbers, symbols).
        - High ratios may indicate randomness or encoding, common in malicious domains.
    - **Hex Character Ratio:** Measures the proportion of characters that are hexadecimal digits (0-9, a-f).
        - Malicious domains may use hex encoding to obscure content.
    - **Vowel Ratio:** Measures the proportion of vowels in the domain.
        - Natural languages have certain vowel frequencies; deviations may indicate non-human-generated domains.

    **Args:**
        domain (str): The domain name to analyze.

    **Returns:**
        Dict[str, float]: A dictionary with ratios of non-letter, hex, and vowel characters.
    """
    domain_clean = domain.replace('.', '').lower()
    length = len(domain_clean)
    if length == 0:
        return {'non_letter_ratio': 0.0, 'hex_char_ratio': 0.0, 'vowel_ratio': 0.0}
    non_letters = sum(1 for c in domain_clean if not c.isalpha())
    hex_chars = sum(1 for c in domain_clean if c in 'abcdef')
    vowels = sum(1 for c in domain_clean if c in 'aeiou')

    return {
        'non_letter_ratio': non_letters / length,
        'hex_char_ratio': hex_chars / length,
        'vowel_ratio': vowels / length
    }

def n_gram_analysis(domain: str, n: int = 2) -> float:
    """
    Analyzes the domain name using n-grams to detect randomness.
    Returns the percentage of common n-grams from multiple languages present in the domain.

    **Theory and Purpose:**
    - **N-grams** are contiguous sequences of 'n' items from a given sample of text.
    - By comparing the n-grams in the domain to common n-grams in major languages, we can assess how 'natural' the domain appears.
    - A low percentage of common n-grams may indicate that the domain is randomly generated or obfuscated.

    **Args:**
        domain (str): The domain name to analyze.
        n (int): The length of n-grams (default is 2).

    **Returns:**
        float: The percentage of common n-grams in the domain.
    """
    domain_clean = domain.replace('.', '').lower()
    ngrams = [domain_clean[i:i+n] for i in range(len(domain_clean)-n+1)]
    if not ngrams:
        return 0.0

    # Expanded set of common bigrams and trigrams from top 10 languages
    common_ngrams = {
        # English bigrams/trigrams
        'th', 'he', 'in', 'er', 'an', 're', 'on', 'at', 'en', 'nd',
        'the', 'and', 'ing', 'ion', 'tio', 'ent', 'for', 'her', 'ter',

        # Mandarin Chinese (pinyin bigrams)
        'shi', 'bu', 'wo', 'ta', 'de', 'le', 'ma', 'yi', 'ren', 'zai',
        'hen', 'you', 'mei', 'ai', 'ni', 'hao',

        # Hindi bigrams/trigrams (Romanized)
        'hai', 'nahi', 'mera', 'kya', 'haan', 'sab', 'tha', 'thi',
        'kar', 'par', 'ke', 'se', 'ko', 'mein', 'tum', 'hum',

        # Spanish bigrams/trigrams
        'de', 'la', 'que', 'el', 'en', 'los', 'del', 'se', 'las',
        'por', 'una', 'un', 'para', 'con', 'no', 'su', 'al',

        # Arabic bigrams/trigrams (transliterated)
        'al', 'wa', 'la', 'fi', 'li', 'an', 'ma', 'min', 'ila', 'bi',
        'ha', 'ya', 'allah', 'rasul', 'salam', 'rahman', 'rahim',

        # French bigrams/trigrams
        'de', 'la', 'le', 'et', 'les', 'des', 'en', 'un', 'une', 'est',
        'dans', 'que', 'pour', 'qui', 'sur', 'par', 'au', 'il', 'se',

        # Bengali bigrams/trigrams (Romanized)
        'ki', 'ami', 'tumi', 'she', 'ar', 'kintu', 'kothay', 'hoy',
        'na', 'tai', 'boli', 'kar', 'amar', 'tomar',

        # Portuguese bigrams/trigrams
        'de', 'que', 'e', 'do', 'da', 'em', 'no', 'os', 'as',
        'se', 'na', 'por', 'um', 'para', 'com', 'não', 'uma',

        # Russian bigrams/trigrams (transliterated)
        'na', 'i', 'v', 'ne', 's', 'o', 'k', 'po', 'za',
        'da', 'ot', 'do', 'ya', 'u', 'ego', 'ona', 'kak',

        # Urdu bigrams/trigrams (Romanized)
        'hai', 'mein', 'ko', 'se', 'ki', 'par', 'ke', 'ye', 'wo',
        'ap', 'aur', 'nahi', 'tha', 'ka',

        # Indonesian bigrams/trigrams
        'di', 'dan', 'yang', 'dari', 'ke', 'untuk', 'dengan', 'ini', 'itu', 'pada',
        'tidak', 'ada', 'oleh', 'saya', 'kami', 'kita',

        # German bigrams/trigrams
        'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'mit', 'das', 'auf',
        'ist', 'im', 'nicht', 'ein', 'ich', 'sie', 'als', 'auch', 'es',
    }

    common_count = sum(1 for gram in ngrams if gram in common_ngrams)
    return (common_count / len(ngrams)) * 100

def gini_index(domain: str) -> float:
    """
    Calculates the Gini index of the character distribution in a domain name.

    **Theory and Purpose:**
    - The **Gini index** measures the inequality among values of a frequency distribution.
    - In this context, it assesses the uniformity of character distribution in the domain.
    - A higher Gini index indicates that few characters dominate, which is less likely in natural language and may suggest randomness or encoding.

    **Args:**
        domain (str): The domain name to analyze.

    **Returns:**
        float: The Gini index value.
    """
    domain_clean = domain.replace('.', '')
    if not domain_clean:
        return 0.0
    freq = Counter(domain_clean)
    total = sum(freq.values())
    probs = [count / total for count in freq.values()]
    gini = 1 - sum(p ** 2 for p in probs)
    return gini

def classification_error(domain: str) -> float:
    """
    Calculates the classification error rate of the domain's character distribution.

    **Theory and Purpose:**
    - **Classification error** measures the probability that a randomly selected character is not the most frequent one.
    - It provides insight into the variability of characters in the domain.
    - A higher error rate means the domain has a more uniform character distribution, which can be indicative of randomness.

    **Args:**
        domain (str): The domain name to analyze.

    **Returns:**
        float: The classification error rate.
    """
    domain_clean = domain.replace('.', '')
    if not domain_clean:
        return 0.0
    freq = Counter(domain_clean)
    total = sum(freq.values())
    max_prob = max(count / total for count in freq.values())
    error = 1 - max_prob
    return error

def number_of_labels(domain: str) -> int:
    """
    Counts the number of labels (subdomains) in the domain name.

    **Theory and Purpose:**
    - The number of labels (segments separated by dots) can indicate complexity.
    - Malicious domains may use multiple subdomains to evade detection or to create unique domains.
    - A higher number of labels might be suspicious.

    **Args:**
        domain (str): The domain name to analyze.

    **Returns:**
        int: The number of labels.
    """
    return len(domain.strip('.').split('.'))

def frequency_analysis(timestamps: List[datetime], interval: timedelta = timedelta(seconds=10)) -> float:
    """
    Calculates the average interval between domain queries.

    **Theory and Purpose:**
    - Malicious domains may be queried at regular, short intervals (e.g., by malware communicating with a command and control server).
    - By analyzing the time between queries, we can detect patterns indicative of automated processes.
    - Short average intervals may signal suspicious activity.

    **Args:**
        timestamps (List[datetime]): A list of timestamps when the domain was queried.
        interval (timedelta): The expected interval between queries.

    **Returns:**
        float: The average interval in seconds.
    """
    if len(timestamps) < 2:
        return 0.0
    sorted_timestamps = sorted(timestamps)
    deltas = [t - s for s, t in zip(sorted_timestamps, sorted_timestamps[1:])]
    intervals = [delta.total_seconds() for delta in deltas]
    avg_interval = sum(intervals) / len(intervals)
    return avg_interval

def payload_size(domain: str) -> int:
    """
    Calculates the payload size of the domain name in bytes.

    **Theory and Purpose:**
    - Malicious actors may encode data within DNS queries (DNS tunneling), resulting in unusually long domain names.
    - By measuring the payload size, we can identify domains that may be used for data exfiltration or command and control communication.
    - Larger payload sizes may be indicative of suspicious activity.

    **Args:**
        domain (str): The domain name to analyze.

    **Returns:**
        int: The payload size in bytes.
    """
    return len(domain.encode('utf-8'))

def analyze_domain(domain: str, timestamps: List[datetime]) -> Dict[str, float]:
    """
    Performs various analyses on the domain and returns a dictionary of metrics.

    **Args:**
        domain (str): The domain name to analyze.
        timestamps (List[datetime]): A list of timestamps when the domain was queried.

    **Returns:**
        Dict[str, float]: A dictionary containing calculated metrics.
    """
    analysis = {
        'entropy': calculate_entropy(domain),
        'non_letter_ratio': lexical_analysis(domain)['non_letter_ratio'],
        'hex_char_ratio': lexical_analysis(domain)['hex_char_ratio'],
        'vowel_ratio': lexical_analysis(domain)['vowel_ratio'],
        'n_gram_2': n_gram_analysis(domain, n=2),
        'n_gram_3': n_gram_analysis(domain, n=3),
        'gini_index': gini_index(domain),
        'classification_error': classification_error(domain),
        'number_of_labels': number_of_labels(domain),
        'average_interval': frequency_analysis(timestamps),
        'payload_size': payload_size(domain)
    }
    return analysis

def extract_sld(domain: str) -> str:
    """
    Extracts the Second Level Domain (SLD) from a domain name.

    **Args:**
        domain (str): The domain name to extract the SLD from.

    **Returns:**
        str: The extracted SLD.
    """
    extracted = tldextract.extract(domain)
    if extracted.domain and extracted.suffix:
        sld = f"{extracted.domain}.{extracted.suffix}."
        return sld
    else:
        return domain

def parse_dns_logs(file_path: str) -> Dict[str, Dict[str, List[datetime]]]:
    """
    Parses the YAML-formatted DNS log file and extracts FQDNs and their query timestamps,
    grouped by SLD.

    **Args:**
        file_path (str): The path to the DNS log file.

    **Returns:**
        Dict[str, Dict[str, List[datetime]]]: A nested dictionary {SLD: {FQDN: [timestamps]}}.
    """
    sld_domains = defaultdict(lambda: defaultdict(list))
    logger.info(f"Parsing DNS logs from {file_path}")
    with open(file_path, 'r') as file:
        documents = yaml.safe_load_all(file)
        for doc in documents:
            if doc is None:
                continue
            message = doc.get('message', {})
            message_type = message.get('type', '')
            if message_type not in ('CLIENT_QUERY', 'CLIENT_RESPONSE'):
                continue
            if message_type == 'CLIENT_QUERY':
                time_key = 'query_time'
                message_data_key = 'query_message_data'
            elif message_type == 'CLIENT_RESPONSE':
                time_key = 'response_time'
                message_data_key = 'response_message_data'
            else:
                continue
            time_str = message.get(time_key)
            if isinstance(time_str, datetime):
                timestamp = time_str
            else:
                timestamp = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
            message_data = message.get(message_data_key, {})
            question_section = message_data.get('QUESTION_SECTION', [])
            for question in question_section:
                domain = question.split()[0]
                sld = extract_sld(domain)
                sld_domains[sld][domain].append(timestamp)
    logger.info("Finished parsing DNS logs")
    return sld_domains

def score_domain(metrics: Dict[str, float], thresholds: Dict[str, Dict], weights: Dict[str, float]) -> float:
    """
    Calculates a score for a domain based on its metrics and specified thresholds.

    **Theory and Purpose:**
    - Each metric is compared against a threshold to determine if it indicates suspicious behavior.
    - Metrics exceeding thresholds contribute to the total score, weighted by their importance.
    - The total score helps in deciding whether a domain is likely malicious.

    **Args:**
        metrics (Dict[str, float]): The metrics calculated for the domain.
        thresholds (Dict[str, Dict]): The thresholds and directions for each metric.
        weights (Dict[str, float]): The weight of each metric in the total score.

    **Returns:**
        float: The total score for the domain.
    """
    score = 0.0
    for key, threshold_info in thresholds.items():
        value = metrics.get(key)
        if value is None:
            continue
        threshold_value = threshold_info['value']
        direction = threshold_info['direction']
        weight = weights.get(key, 1.0)
        if direction == 'greater' and value > threshold_value:
            score += weight
        elif direction == 'less' and value < threshold_value:
            score += weight
    return score

if __name__ == "__main__":
    # Configuration
    dns_log_file = 'var/log/dnslog.txt'
    threshold_score = 0.5  # Adjust this threshold

    # Thresholds and directions for indicators
    thresholds = {
        'entropy': {'value': 4.0, 'direction': 'greater'},
        'non_letter_ratio': {'value': 0.3, 'direction': 'greater'},
        'hex_char_ratio': {'value': 0.5, 'direction': 'greater'},
        'vowel_ratio': {'value': 0.3, 'direction': 'less'},
        'n_gram_2': {'value': 10.0, 'direction': 'less'},
        'gini_index': {'value': 0.9, 'direction': 'greater'},
        'classification_error': {'value': 0.85, 'direction': 'greater'},
        'number_of_labels': {'value': 3, 'direction': 'greater'},
        'average_interval': {'value': 5.0, 'direction': 'less'},
        'payload_size': {'value': 50, 'direction': 'greater'}
    }

    # Weights for each indicator in the scoring function
    weights = {
        'entropy': 1.5,
        'non_letter_ratio': 0.8,
        'hex_char_ratio': 0.8,
        'vowel_ratio': 1.0,
        'n_gram_2': 0.9,
        'gini_index': 1.0,
        'classification_error': 0.5,
        'number_of_labels': 1.1,
        'average_interval': 1.1,
        'payload_size': 2.0  
    }

    # Parse DNS logs
    sld_domains = parse_dns_logs(dns_log_file)

    # Dictionaries to keep track of metrics and flagged domains per SLD
    sld_flagged_domains = defaultdict(list)
    sld_metrics = defaultdict(list)
    fqdn_metrics = {}
    global_metrics = defaultdict(list)

    # Total number of FQDNs for progress bar
    total_fqdns = sum(len(domains) for domains in sld_domains.values())
    processed_fqdns = 0

    logger.info("Starting analysis of domains")

    # Use Rich progress bar for processing domains
    with Progress() as progress:
        task = progress.add_task("[green]Analyzing domains...", total=total_fqdns)

        for sld, domains in sld_domains.items():
            for fqdn, timestamps in domains.items():
                metrics = analyze_domain(fqdn, timestamps)
                domain_score = score_domain(metrics, thresholds, weights)
                # Store metrics for averaging
                sld_metrics[sld].append(metrics)
                fqdn_metrics[fqdn] = metrics
                # Collect global metrics
                for key, value in metrics.items():
                    global_metrics[key].append(value)
                if domain_score >= threshold_score:
                    sld_flagged_domains[sld].append(fqdn)
                processed_fqdns += 1
                progress.update(task, advance=1)

    logger.info("Finished analysis of domains")

    # Calculate global average metrics
    global_avg_metrics = {}
    for key, values in global_metrics.items():
        global_avg_metrics[key] = sum(values) / len(values)

    # Report
    for sld in sld_flagged_domains.keys():
        flagged_domains = sld_flagged_domains[sld]
        sld_score = 0.0
        # Calculate the score for the SLD by averaging the scores of its domains
        sld_scores = []
        for domain in sld_domains[sld]:
            metrics = fqdn_metrics[domain]
            domain_score = score_domain(metrics, thresholds, weights)
            sld_scores.append(domain_score)
        sld_score = sum(sld_scores) / len(sld_scores)

        print("=" * 40)
        print(f"SLD: {sld}")
        print(f"Score: {sld_score:.2f} (Threshold: {threshold_score})")
        print(f"Number of flagged domains: {len(flagged_domains)}")
        print("FQDNs under this SLD:")
        for domain in sld_domains[sld]:
            print(f"   - {domain}")
        # Calculate average indicators for the FQDNs under this SLD
        sld_avg_metrics = {}
        metric_keys = sld_metrics[sld][0].keys()
        total_domains = len(sld_metrics[sld])
        for key in metric_keys:
            sld_avg_metrics[key] = sum(metrics[key] for metrics in sld_metrics[sld]) / total_domains
        # Print average indicators with comparison to global averages and flag if exceeded thresholds
        print("Averaged indicators (* is flagged, average value (global average value) :")
        for key in metric_keys:
            avg_value = sld_avg_metrics[key]
            global_avg = global_avg_metrics[key]
            threshold_info = thresholds.get(key)
            flag = ''
            if threshold_info:
                threshold_value = threshold_info['value']
                direction = threshold_info['direction']
                if direction == 'greater' and avg_value > threshold_value:
                    flag = '*'
                elif direction == 'less' and avg_value < threshold_value:
                    flag = '*'
            print(f"   {key}: {avg_value:.4f} ({global_avg:.4f}){flag}")
        print("-" * 30)
