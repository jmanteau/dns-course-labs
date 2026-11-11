import scoring


def test_part_points():
    assert scoring.part_points(100) == 100
    assert scoring.part_points(100, hints_used=1) == 75
    assert scoring.part_points(100, hints_used=2) == 50
    assert scoring.part_points(100, hints_used=2, wrong_mcq=1) == 25
    assert scoring.part_points(100, hints_used=2, wrong_mcq=9) == 10  # floor


def test_hint_cost():
    assert scoring.hint_cost(100, 1) == 25
    assert scoring.hint_cost(100, 2) == 25


def test_advanced_hint_ladder():
    """Advanced parts: 3 hints, 15 / 35 / 60 % cumulative; the main table is unchanged."""
    assert [scoring.hint_cost(100, n, "advanced") for n in (1, 2, 3)] == [15, 20, 25]
    assert scoring.part_points(100, hints_used=3, stage="advanced") == 40
    assert scoring.part_points(100, hints_used=9, stage="advanced") == 40  # never more than the table
    assert scoring.part_points(100, hints_used=2, stage="warmup") == 50  # the warm-up uses the main table
