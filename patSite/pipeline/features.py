"""Pre-game features. Each game's features use only games that finished before it,
so the model never sees the result it is predicting."""
from collections import defaultdict, deque

ELO_START = 1500.0
ELO_MEAN = 1505.0
ELO_K = 20.0
ELO_HOME_EDGE = 100.0      # home court is worth about 100 Elo points (~3.5 points of margin)
ELO_SEASON_CARRY = 0.75    # at a new season, keep 75% of a team's distance from average
FORM_GAMES = 10
REST_CAP = 4               # 4+ days off counts as fully rested


def elo_win_prob(diff):
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


class TeamState:
    def __init__(self):
        self.elo = ELO_START
        self.season = None
        self.games = 0                       # completed games seen, across seasons
        self.season_margin_total = 0.0
        self.season_games = 0
        self.recent = deque(maxlen=FORM_GAMES)
        self.last_date = None

    def start_season(self, season):
        if self.season is not None and season != self.season:
            self.elo = ELO_SEASON_CARRY * self.elo + (1 - ELO_SEASON_CARRY) * ELO_MEAN
            self.season_margin_total, self.season_games = 0.0, 0
            self.recent.clear()
        self.season = season

    # Averages are shrunk toward zero so a two-game sample can't dominate.
    def form(self):
        return sum(self.recent) / (len(self.recent) + 3)

    def season_margin(self):
        return self.season_margin_total / (self.season_games + 5)

    def rest(self, day):
        if self.last_date is None:
            return REST_CAP
        return min((day - self.last_date).days, REST_CAP)

    def record(self, margin):
        self.games += 1
        self.season_margin_total += margin
        self.season_games += 1
        self.recent.append(margin)


def update_elo(home, away, home_edge, margin):
    """FiveThirtyEight-style update with a margin-of-victory multiplier."""
    diff = home.elo + home_edge - away.elo
    home_won = margin > 0
    winner_diff = diff if home_won else -diff
    multiplier = (abs(margin) + 3) ** 0.8 / (7.5 + 0.006 * winner_diff)
    shift = ELO_K * multiplier * ((1.0 if home_won else 0.0) - elo_win_prob(diff))
    home.elo += shift
    away.elo -= shift


def compute(games):
    """Feature rows for games (objects with Game's attributes), in chronological order."""
    teams = defaultdict(TeamState)
    rows = []
    for g in sorted(games, key=lambda g: (g.start_time, g.id)):
        home, away = teams[g.home_team], teams[g.away_team]
        home.start_season(g.season)
        away.start_season(g.season)
        home_edge = 0.0 if g.neutral_site else ELO_HOME_EDGE
        diff = home.elo + home_edge - away.elo
        rest_home, rest_away = home.rest(g.game_date), away.rest(g.game_date)
        rows.append({
            "game_id": g.id,
            "game_date": g.game_date,
            "home_court": 0 if g.neutral_site else 1,
            "elo_diff": diff / 100,
            "elo_prob": elo_win_prob(diff),
            "form_diff": (home.form() - away.form()) / 10,
            "season_margin_diff": (home.season_margin() - away.season_margin()) / 10,
            "rest_diff": rest_home - rest_away,
            "home_b2b": int(rest_home == 1),
            "away_b2b": int(rest_away == 1),
            "min_games": min(home.games, away.games),
            "label": int(g.home_score > g.away_score) if g.completed else None,
            "home_ml": g.home_ml,
            "away_ml": g.away_ml,
        })
        if g.completed:
            margin = g.home_score - g.away_score
            update_elo(home, away, home_edge, margin)
            home.record(margin)
            away.record(-margin)
        # Scheduled games count for rest too, so tomorrow's back-to-back is flagged tonight.
        if g.completed or g.state in ("pre", "in"):
            home.last_date = away.last_date = g.game_date
    return rows
