from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Database model for consolidated data
class ConsolidatedData(db.Model):
    __tablename__ = 'consolidated_data'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    username = db.Column(db.String(100))
    account_id = db.Column(db.String(50))
    game_name = db.Column(db.String(100))
    game_id = db.Column(db.String(50))
    currency = db.Column(db.String(10))
    fx_rate = db.Column(db.Float)
    bet = db.Column(db.Float)
    win = db.Column(db.Float)
    bet_eur = db.Column(db.Float)
    win_eur = db.Column(db.Float)
    number_of_spins = db.Column(db.Integer)
    cash_bet = db.Column(db.Float)
    bonus_bet = db.Column(db.Float)
    cash_win = db.Column(db.Float)
    bonus_win = db.Column(db.Float)
    site_name = db.Column(db.String(100))
    # Adding the unique constraint
    __table_args__ = (
        db.UniqueConstraint('date', 'username', 'account_id', name='unique_data_constraint'),
    )

class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rate'
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(50), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    date_fetched = db.Column(db.Date, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('currency', 'date_fetched', name='unique_currency_date'),
    )

class TotalSummaryData(db.Model):
    __tablename__ = "total_summary_data"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)  # Unique constraint on date
    total_bet = db.Column(db.Float, nullable=False)
    total_win = db.Column(db.Float, nullable=False)
    reel_spins = db.Column(db.Integer, nullable=False)
    social_spins = db.Column(db.Integer, nullable=False)
    total_spins = db.Column(db.Integer, nullable=False)
    rtp = db.Column(db.Float, nullable=False)
    ggr_eur = db.Column(db.Float, nullable=False)
    ggr_gbp = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('date', name='uq_total_summary_date'),
    )
