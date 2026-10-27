import click
from datetime import date
from .Models import db
from flask import Blueprint

commands_bp= Blueprint('commands', __name__, cli_group=None)

# Pipeline modules import numpy/scikit-learn, so they're imported inside the
# commands to keep them out of the web workers.

@commands_bp.cli.command('create_db')
def create_db():
    """Creates database"""
    db.create_all()

@commands_bp.cli.command('drop_db')
def drop_db():
    """Drop / Clean database - DANGER ACTION"""
    db.drop_all()

@commands_bp.cli.command('sync-games')
@click.option('--start', type=date.fromisoformat, help='First date to fetch (YYYY-MM-DD).')
def sync_games(start):
    """Fetch games and odds from ESPN into the database."""
    from patSite.pipeline import jobs
    click.echo(f"Synced {jobs.sync_games(start=start)} games")

@commands_bp.cli.command('daily')
def daily():
    """Sync games, grade finished picks, update the backtest, and make upcoming picks."""
    from patSite.pipeline import jobs, model
    click.echo(f"Synced {jobs.sync_games()} games")
    click.echo(f"Graded {jobs.grade_predictions()} picks")
    metrics = jobs.run_backtest()  # before predicting: picks use its market-blend weights
    click.echo(f"Predicted {jobs.make_predictions()} upcoming games")
    click.echo(model.format_report(metrics))

@commands_bp.cli.command('backtest')
@click.option('--report', type=click.Path(dir_okay=False), help='Also append the report to this file.')
def backtest(report):
    """Re-run the walk-forward backtest on games already in the database."""
    from patSite.pipeline import jobs, model
    metrics = jobs.run_backtest()
    text = model.format_report(metrics)
    click.echo(text)
    if report:
        with open(report, 'a') as f:
            f.write(text + '\n')
