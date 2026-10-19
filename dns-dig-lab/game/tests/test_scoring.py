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
