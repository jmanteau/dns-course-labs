"""Points, hint penalties and first-blood bonuses."""

# share of a part's points that its hints take, cumulative, by stage (the warm-up uses the main table):
# the advanced missions have a 3-step ladder, concept, ingredients, then the full command
HINT_PENALTY = {
    "main": {0: 0.0, 1: 0.25, 2: 0.50},
    "advanced": {0: 0.0, 1: 0.15, 2: 0.35, 3: 0.60},
}
MCQ_WRONG_PENALTY = 0.25
FLOOR = 0.10
FIRST_BLOOD = {1: 50, 2: 25, 3: 10}


def penalty(stage, n):
    table = HINT_PENALTY["advanced" if stage == "advanced" else "main"]
    return table[min(n, max(table))]


def part_points(base, hints_used=0, wrong_mcq=0, stage="main"):
    """Points earned for solving a part, given hints revealed and wrong MCQ guesses."""
    total = penalty(stage, hints_used) + MCQ_WRONG_PENALTY * wrong_mcq
    return max(round(base * FLOOR), round(base * (1 - total)))


def hint_cost(base, n, stage="main"):
    """Points the n-th hint (1-based) takes off the part's value."""
    return round(base * (penalty(stage, n) - penalty(stage, n - 1)))
