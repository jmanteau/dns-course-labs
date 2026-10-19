import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import tldextract
import yaml


def calculate_entropy(domain: str) -> float:
    domain = domain.replace(".", "")
    if not domain:
        return 0.0
    probabilities = [n / len(domain) for n in Counter(domain).values()]
    return -sum(p * math.log2(p) for p in probabilities)


def lexical_analysis(domain: str) -> Dict[str, float]:
    domain_clean = domain.replace(".", "").lower()
    length = len(domain_clean)
    if length == 0:
        return {"non_letter_ratio": 0.0, "hex_char_ratio": 0.0, "vowel_ratio": 0.0}
    non_letters = sum(1 for c in domain_clean if not c.isalpha())
    hex_chars = sum(1 for c in domain_clean if c in "abcdef")
    vowels = sum(1 for c in domain_clean if c in "aeiou")
    return {
        "non_letter_ratio": non_letters / length,
        "hex_char_ratio": hex_chars / length,
        "vowel_ratio": vowels / length,
    }


COMMON_NGRAMS = {
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd",
    "the", "and", "ing", "ion", "tio", "ent", "for", "her", "ter",
    "shi", "bu", "wo", "ta", "de", "le", "ma", "yi", "ren", "zai",
    "hen", "you", "mei", "ai", "ni", "hao",
    "hai", "nahi", "mera", "kya", "haan", "sab", "tha", "thi",
    "kar", "par", "ke", "se", "ko", "mein", "tum", "hum",
    "la", "que", "el", "los", "del", "las", "por", "una", "un",
    "para", "con", "no", "su", "al",
    "wa", "fi", "li", "min", "ila", "bi", "ha", "ya",
    "et", "les", "des", "une", "est", "dans", "qui", "sur", "au", "il",
    "ki", "ami", "she", "ar", "na", "tai", "da",
    "do", "em", "os", "as", "um", "com",
    "ne", "po", "za", "ot", "ego", "ona", "kak",
    "di", "dan", "yang", "dari", "ini", "itu", "pada", "ada",
    "der", "die", "und", "den", "von", "zu", "mit", "das", "auf",
    "ist", "im", "ein", "ich", "sie", "als", "auch", "es",
}


def n_gram_analysis(domain: str, n: int = 2) -> float:
    domain_clean = domain.replace(".", "").lower()
    ngrams = [domain_clean[i : i + n] for i in range(len(domain_clean) - n + 1)]
    if not ngrams:
        return 0.0
    common_count = sum(1 for gram in ngrams if gram in COMMON_NGRAMS)
    return (common_count / len(ngrams)) * 100


def gini_index(domain: str) -> float:
    domain_clean = domain.replace(".", "")
    if not domain_clean:
        return 0.0
    freq = Counter(domain_clean)
    total = sum(freq.values())
    probs = [count / total for count in freq.values()]
    return 1 - sum(p**2 for p in probs)


def classification_error(domain: str) -> float:
    domain_clean = domain.replace(".", "")
    if not domain_clean:
        return 0.0
    freq = Counter(domain_clean)
    total = sum(freq.values())
    max_prob = max(count / total for count in freq.values())
    return 1 - max_prob


def number_of_labels(domain: str) -> int:
    return len(domain.strip(".").split("."))


def frequency_analysis(timestamps: List[datetime]) -> float:
    if len(timestamps) < 2:
        return 0.0
    sorted_ts = sorted(timestamps)
    deltas = [
        (t - s).total_seconds() for s, t in zip(sorted_ts, sorted_ts[1:])
    ]
    return sum(deltas) / len(deltas)


def payload_size(domain: str) -> int:
    return len(domain.encode("utf-8"))


def analyze_domain(domain: str, timestamps: List[datetime]) -> Dict[str, float]:
    lex = lexical_analysis(domain)
    return {
        "entropy": calculate_entropy(domain),
        "non_letter_ratio": lex["non_letter_ratio"],
        "hex_char_ratio": lex["hex_char_ratio"],
        "vowel_ratio": lex["vowel_ratio"],
        "n_gram_2": n_gram_analysis(domain, n=2),
        "n_gram_3": n_gram_analysis(domain, n=3),
        "gini_index": gini_index(domain),
        "classification_error": classification_error(domain),
        "number_of_labels": number_of_labels(domain),
        "average_interval": frequency_analysis(timestamps),
        "payload_size": payload_size(domain),
    }


def extract_sld(domain: str) -> str:
    extracted = tldextract.extract(domain)
    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}."
    return domain


def parse_dns_logs(file_path: str) -> Dict[str, Dict[str, List[datetime]]]:
    sld_domains: Dict[str, Dict[str, List[datetime]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with open(file_path, "r") as f:
        for doc in yaml.safe_load_all(f):
            if doc is None:
                continue
            message = doc.get("message", {})
            msg_type = message.get("type", "")
            if msg_type == "CLIENT_QUERY":
                time_key, data_key = "query_time", "query_message_data"
            elif msg_type == "CLIENT_RESPONSE":
                time_key, data_key = "response_time", "response_message_data"
            else:
                continue
            time_str = message.get(time_key)
            if isinstance(time_str, datetime):
                timestamp = time_str
            else:
                try:
                    timestamp = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, TypeError):
                    continue
            for question in message.get(data_key, {}).get("QUESTION_SECTION", []):
                domain = question.split()[0]
                sld = extract_sld(domain)
                sld_domains[sld][domain].append(timestamp)
    return dict(sld_domains)


def score_domain(
    metrics: Dict[str, float],
    thresholds: Dict[str, dict],
    weights: Dict[str, float],
) -> float:
    score = 0.0
    for key, threshold_info in thresholds.items():
        value = metrics.get(key)
        if value is None:
            continue
        threshold_value = threshold_info["value"]
        direction = threshold_info["direction"]
        weight = weights.get(key, 1.0)
        if direction == "greater" and value > threshold_value:
            score += weight
        elif direction == "less" and value < threshold_value:
            score += weight
    return score


def _is_flagged(value: float, threshold_info: dict) -> bool:
    if not threshold_info:
        return False
    tv = threshold_info.get("value", 0)
    d = threshold_info.get("direction", "greater")
    if d == "greater":
        return value > tv
    return value < tv


class AnalysisEngine:
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self._parsed_data: Optional[dict] = None
        self._fqdn_metrics: Optional[Dict[str, Dict[str, float]]] = None

    def parse_logs(self, force: bool = False) -> bool:
        log_file = self.log_dir / "dnslog.txt"
        if not log_file.exists():
            return False
        if self._parsed_data and not force:
            return True
        self._parsed_data = parse_dns_logs(str(log_file))
        self._compute_metrics()
        return True

    def _compute_metrics(self):
        self._fqdn_metrics = {}
        for sld, domains in self._parsed_data.items():
            for fqdn, timestamps in domains.items():
                self._fqdn_metrics[fqdn] = analyze_domain(fqdn, timestamps)

    def score_all(
        self,
        thresholds: dict,
        weights: dict,
        threshold_score: float = 4.5,
    ) -> dict:
        if not self._fqdn_metrics:
            return {"error": "No data parsed yet", "results": []}

        global_metrics: Dict[str, list] = defaultdict(list)
        for metrics in self._fqdn_metrics.values():
            for key, value in metrics.items():
                global_metrics[key].append(value)
        global_avg = {k: sum(v) / len(v) for k, v in global_metrics.items()}

        sld_results = []
        for sld, domains in self._parsed_data.items():
            sld_fqdns = list(domains.keys())
            sld_scores = []
            flagged = []
            for fqdn in sld_fqdns:
                m = self._fqdn_metrics[fqdn]
                s = score_domain(m, thresholds, weights)
                sld_scores.append(s)
                if s >= threshold_score:
                    flagged.append(fqdn)
            if not flagged:
                continue
            avg_score = sum(sld_scores) / len(sld_scores)
            avg_metrics = {}
            for key in next(iter(self._fqdn_metrics.values())).keys():
                vals = [self._fqdn_metrics[f][key] for f in sld_fqdns]
                avg_metrics[key] = sum(vals) / len(vals)
            sld_results.append({
                "sld": sld,
                "score": round(avg_score, 2),
                "flagged_count": len(flagged),
                "total_fqdns": len(sld_fqdns),
                "flagged_fqdns": flagged[:20],
                "avg_metrics": {k: round(v, 4) for k, v in avg_metrics.items()},
                "threshold_flags": {
                    k: _is_flagged(avg_metrics.get(k, 0), thresholds.get(k, {}))
                    for k in avg_metrics
                },
            })
        sld_results.sort(key=lambda x: x["score"], reverse=True)
        return {
            "results": sld_results,
            "global_averages": {k: round(v, 4) for k, v in global_avg.items()},
            "total_domains_analyzed": len(self._fqdn_metrics),
            "threshold_score": threshold_score,
        }
