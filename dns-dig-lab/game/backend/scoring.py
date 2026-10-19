"""Points, hint penalties and first-blood bonuses."""

HINT_PENALTY = {0: 0.0, 1: 0.25, 2: 0.50}
MCQ_WRONG_PENALTY = 0.25
FLOOR = 0.10
FIRST_BLOOD = {1: 50, 2: 25, 3: 10}
MAX_HINTS = 2


def part_points(base, hints_used=0, wrong_mcq=0):
    """Points earned for solving a part, given hints revealed and wrong MCQ guesses."""
    penalty = HINT_PENALTY[min(hints_used, MAX_HINTS)] + MCQ_WRONG_PENALTY * wrong_mcq
    return max(round(base * FLOOR), round(base * (1 - penalty)))


def hint_cost(base, n):
    """Points the n-th hint (1-based) takes off the part's value."""
    return round(base * (HINT_PENALTY[n] - HINT_PENALTY[n - 1]))
