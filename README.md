# Pat's Gambling Site

Daily NBA moneyline picks from a machine-learning model, with a public track record.

- **Today's picks** (`/`): each game's moneylines, the model's and the market's win
  probabilities, and any value bet.
- **Performance** (`/performance`): every pick graded after the game (record, units,
  ROI, Brier score against the market) plus a walk-forward backtest.

For entertainment only. Picks are model estimates, not guarantees.

## How the model works

Data: scores, schedules and moneylines from ESPN's public scoreboard feed, **only for
games on or after `DATA_START_DATE` (default 2026-01-01)**. Nothing earlier is stored
or used.

1. **Features**, each computed only from games that finished before the one being
   predicted: Elo rating (margin-of-victory adjusted, home edge, partly reset each
   season), last-10-games and season scoring margin, rest days, back-to-backs,
   neutral sites.
2. **Model**: logistic regression on those features.
3. **Market blend**: a second logistic regression combines the model's probability with
   the betting line's (bookmaker margin removed), fitted on earlier out-of-sample
   predictions. Its weights show how much the model adds beyond the market.
4. **Value bets**: flagged only when the blended estimate expects at least +3% return at
   the posted odds, the model's weight in the blend is at least 0.1, the model itself
   leans the same way, and the odds are no longer than +400. If the model isn't adding
   information beyond the betting line, the site flags no bets.

Everything is evaluated **walk-forward**: each day's games are predicted by a model
trained only on earlier days. Beating the closing line consistently is hard; the
performance page shows honestly whether the model does.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then set SECRET_KEY
flask --app wsgi sync-games   # fetch 2026 games (first run takes a minute or two)
flask --app wsgi daily        # grade, backtest and make today's picks
flask --app wsgi run          # http://127.0.0.1:5000
pytest
```

Without `DATABASE_URL` the app uses a local SQLite file (`nba.db`).

## Deploy for free

| Piece | Service | Free plan notes |
|---|---|---|
| Web app | [Render](https://render.com) web service | Sleeps after 15 minutes idle; first visit after that takes about a minute |
| Database | [Neon](https://neon.com) Postgres | Doesn't expire (Render's free Postgres is deleted after 30 days) |
| Daily job | GitHub Actions | Free for public repos |

1. **Neon**: create a project and copy its connection string.
2. **GitHub**: add it as a repository secret named `DATABASE_URL`
   (Settings → Secrets and variables → Actions). Run the *Daily picks* workflow once by
   hand from the Actions tab to load the 2026 games.
3. **Render**: New → Blueprint, pick this repo. `render.yaml` sets everything up; paste
   the same Neon connection string when asked for `DATABASE_URL`.

The daily workflow runs twice a day (morning and late afternoon Eastern). GitHub pauses
scheduled workflows in public repos after 60 days with no commits; re-enable it from the
Actions tab if that happens.

## Security note

Before October 2026 this repo tracked a `.env` file containing the secret key and database
URL. It is no longer tracked, but it remains in git history, so treat those values as
public: use a new `SECRET_KEY` and a new database password.
