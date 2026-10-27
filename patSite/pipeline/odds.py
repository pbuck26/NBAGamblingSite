"""American moneyline math."""


def parse_american(value):
    """Turn '+150', '-110', 'EVEN', 150 or -110.0 into an int, or None if it isn't valid odds."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        odds = int(value)
    else:
        text = str(value).strip().upper()
        if text in ("EVEN", "EV", "PK"):
            return 100
        try:
            odds = int(float(text.replace("+", "")))
        except ValueError:
            return None
    if -100 < odds < 100:
        return None
    return odds


def payout(odds):
    """Profit on a winning 1-unit bet."""
    return odds / 100 if odds > 0 else 100 / -odds


def implied_probability(odds):
    """Break-even win probability for these odds (includes the bookmaker's margin)."""
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)


def no_vig_probability(home_odds, away_odds):
    """Home win probability implied by both lines, with the bookmaker's margin removed."""
    home = implied_probability(home_odds)
    away = implied_probability(away_odds)
    return home / (home + away)


def expected_value(win_prob, odds):
    """Expected profit per 1 unit staked if the true win probability is win_prob."""
    return win_prob * payout(odds) - (1 - win_prob)


def profit(odds, won):
    return payout(odds) if won else -1.0
