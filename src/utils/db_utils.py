import logging
import requests
import mysql.connector
from mysql.connector import Error
from src.models.db_models import ExchangeRate, db

logger = logging.getLogger(__name__)

def fetch_exchange_rates(consolidate_date):
    try:
        # Check if rates already exist in the database for the given date
        existing_rates = ExchangeRate.query.filter_by(date_fetched=consolidate_date).all()

        # If rates exist, return them
        if existing_rates:
            rates = {rate.currency: rate.rate for rate in existing_rates}
            logger.info(f"Rates for {consolidate_date} already exist in the database. Returning existing rates.")
        else:
            # If rates are not in the database, fetch from API
            api_key = 'f9a3cb10586c03a09c827fcf952994c0'
            base_currency = 'EUR'
            url = f"http://data.fixer.io/api/{consolidate_date}"
            params = {'access_key': api_key, 'base': base_currency}

            response = requests.get(url, params=params)
            response.raise_for_status()
            # Parse the response JSON
            data = response.json()
            new_rates = []

            if data.get('success'):
                logger.info("Exchange rates fetched successfully.")
                for currency, rate in data['rates'].items():
                    # Calculate the inverse of the rate (1/{rate})
                    inverse_rate = 1 / rate if rate > 0 else 0
                    new_rate = ExchangeRate(currency=currency, rate=inverse_rate, date_fetched=consolidate_date)
                    new_rates.append(new_rate)

                db.session.bulk_save_objects(new_rates)
                db.session.commit()
                logger.info(f"Fetched and inserted exchange rates for {consolidate_date} from the API.")
            else:
                logger.error(f"API response unsuccessful for {consolidate_date}.")
                raise ValueError(f"API response unsuccessful for {consolidate_date}.")

            # Add the newly fetched rates to the final list
            rates = {rate.currency: rate.rate for rate in new_rates}

        # Insert social currencies and get their converted rates
        social_currency_rates = insert_social_currencies(consolidate_date)

        # Include social currencies in the final return rates
        rates.update(social_currency_rates)

        return rates

    except Exception as e:
        logger.error(f"Error fetching exchange rates: {e}")
        return {}


# Insert or update social currencies in the database and return the converted rates
def insert_social_currencies(date_fetched):
    try:
        # Fetch USD to EUR conversion rate
        usd_to_eur_rate_entry = ExchangeRate.query.filter_by(currency='USD', date_fetched=date_fetched).first()
        if not usd_to_eur_rate_entry:
            logger.error("USD to EUR rate not found in the database.")
            raise Exception("USD to EUR rate not found in the database.")

        usd_to_eur_rate = usd_to_eur_rate_entry.rate
        # Fetch BTC rate for conversion of mBTC
        btc_rate_entry = ExchangeRate.query.filter_by(currency='BTC', date_fetched=date_fetched).first()
        if not btc_rate_entry:
            logger.error("BTC rate not found in the database.")
            raise Exception("BTC rate not found in the database.")

        btc_rate = btc_rate_entry.rate

        social_currencies = {
            'SSC': 1.0,  # 1 SSC = 1 USD
            'WOC': 1.0,  # 1 WOC = 1 USD
            'SC': 1.0,  # 1 SC = 1 USD
            'SC.': 1.0,  # 1 SC = 1 USD
            'YOH': 1.0,  # 1 YOH = 1 USD
            'GEM': 1.0,  # 1 GEM = 1 USD
            'BK.': 1.0,  # 1 BK. = 1 USD
            'GHC': 0.001,  # 1 GHC = 0.001 EUR
            'GOC': 0,
            'VBC': 0,
            'GCC': 0,
            'GLD': 0,
            'GC': 0,
            'GC.': 0,
            'TOK': 0,
            'FTN': 0,
            'USDT': 0,
            'BT.': 0,  # 1 BT. = 0 USD
            'mBTC': 0.000001,  # 1 mBTC = 0.000001 BTC
            'FC': 1.0,  # 1 FC = 1 USD
            'VSC': 1.0,  # 1 VSC = 1 USD
            'WOW': 0.01  # 1 WOW = 0.01 USD
        }

        converted_rates = {}

        for currency, rate in social_currencies.items():
            if currency == 'GHC':
                rate_in_eur = rate
            elif currency == 'mBTC':
                # Convert mBTC to its BTC value using the fetched BTC rate
                rate_in_eur = rate * btc_rate
            else:
                rate_in_eur = rate * usd_to_eur_rate if rate > 0 else 0

            # Check if the exchange rate already exists
            exchange_rate = ExchangeRate.query.filter_by(currency=currency, date_fetched=date_fetched).first()
            if exchange_rate:
                exchange_rate.rate = rate_in_eur
            else:
                db.session.add(ExchangeRate(currency=currency, rate=rate_in_eur, date_fetched=date_fetched))
                logger.info(f"Added social rate for currency: {currency}")

            # Store the converted rate
            converted_rates[currency] = rate_in_eur

        db.session.commit()
        logger.info("Social currencies updated successfully.")

        # Return the converted rates
        return converted_rates

    except Exception as e:
        logger.error(f"Error inserting social currencies: {e}")
        return {}

# Database connection setup
def get_db_connection():
    try:
        # Establish a connection to the database
        connection = mysql.connector.connect(
            host='localhost',
            database='reportgenerator',
            user='cheran',
            password='Cheran@3334'
        )
        if connection.is_connected():
            logger.info("Connected to MySQL database")
            return connection
        else:
            logger.error("Failed to connect to MySQL database.")
            raise Exception("Failed to connect to MySQL database.")
    except Error as e:
        logger.error(f"Error: {e}")
        return None
