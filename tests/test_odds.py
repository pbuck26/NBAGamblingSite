import pytest

from patSite.pipeline.odds import (expected_value, implied_probability, no_vig_probability,
                                   parse_american, payout, profit)


@pytest.mark.parametrize("raw,expected", [
    ("+150", 150), ("-110", -110), ("EVEN", 100), ("even", 100), (150, 150), (-110.0, -110),
    ("OFF", None), ("", None), (None, None), (0, None), ("50", None), (True, None),
])
def test_parse_american(raw, expected):
    assert parse_american(raw) == expected


def test_implied_and_no_vig_probability():
    assert implied_probability(-110) == pytest.approx(0.5238, abs=1e-4)
    assert implied_probability(150) == pytest.approx(0.4)
    assert no_vig_probability(-110, -110) == pytest.approx(0.5)
    assert no_vig_probability(-200, 170) == pytest.approx(0.6429, abs=1e-4)


def test_payout_profit_and_ev():
    assert payout(150) == 1.5
    assert payout(-200) == 0.5
    assert profit(150, won=True) == 1.5
    assert profit(-200, won=False) == -1.0
    assert expected_value(0.5, 100) == pytest.approx(0.0)
    assert expected_value(0.6, 100) == pytest.approx(0.2)
    assert expected_value(0.5, -110) < 0
