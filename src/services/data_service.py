import logging
import os
import re
from collections import defaultdict
from datetime import timedelta

import pandas as pd
from flask import current_app, request
from sqlalchemy.exc import IntegrityError

from src.models.db_models import ConsolidatedData, db, ExchangeRate, TotalSummaryData
from src.utils.db_utils import fetch_exchange_rates
from src.utils.file_utils import get_latest_date_from_db

logger = logging.getLogger(__name__)

# Define social currencies
social_currencies = {
    'SSC', 'WOC', 'SC', 'SC.', 'YOH', 'GEM', 'BK.', 'GHC',
    'GOC', 'VBC', 'GCC', 'GLD', 'GC', 'GC.', 'TOK', 'FTN',
    'USDT', 'BT.', 'mBTC', 'FC', 'VSC', 'WOW', 'FC.'
}

#Generate all reports
def generate_all_reports():
    try:
        files = request.files.getlist("files")
        if not files:
            logger.error("No files uploaded!")
            return {'error': 'No files uploaded!'}, 400

        # Directories for file processing
        UPLOAD_FOLDER = current_app.config['UPLOAD_FOLDER']
        uploaded_file_paths = []
        file_date_mapping = {}  # Maps file paths to their extracted dates

        # Step 1: Upload files and extract dates
        for file in files:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            uploaded_file_paths.append(file_path)

            try:
                # Extract the date from the filename (e.g., '_YYYY-MM-DD')
                filename_date = file.filename.split('_')[-1].split('.')[0]
                if not re.match(r'\d{4}-\d{2}-\d{2}', filename_date):
                    raise ValueError("Invalid date format")
                file_date_mapping[file_path] = filename_date
                logger.debug(f"Extracted date {filename_date} for file {file.filename}")
            except Exception as e:
                logger.error(f"Invalid filename format for {file.filename}: {str(e)}")
                return {'error': f"Invalid filename format for {file.filename}. Expected '_YYYY-MM-DD'"}, 400

        # Ensure dates match the number of files (grouping logic)
        dates_in_order = sorted(set(file_date_mapping.values()))  # Unique and sorted dates
        files_grouped_by_date = {date: [] for date in dates_in_order}

        # Map files to their corresponding date groups
        for file_path, date in file_date_mapping.items():
            files_grouped_by_date[date].append(file_path)

        # Step 2: Fetch and store exchange rates for all unique dates
        all_rates = {}
        for date in files_grouped_by_date:
            rates = fetch_exchange_rates(date)
            if not rates:
                logger.error(f"Failed to fetch exchange rates for {date}.")
                return {'error': f"Failed to fetch exchange rates for {date}."}, 500

            # Save rates to the database
            for currency, rate in rates.items():
                existing_rate = ExchangeRate.query.filter_by(date_fetched=date, currency=currency).first()
                if not existing_rate:
                    exchange_rate = ExchangeRate(date_fetched=date, currency=currency, rate=rate)
                    db.session.add(exchange_rate)
            db.session.commit()
            all_rates[date] = rates

        # Step 3: Process and store consolidated data
        consolidated_data_entries = []

        for date, file_paths in files_grouped_by_date.items():
            for file_path in file_paths:
                data = pd.read_excel(file_path)

                for _, row in data.iterrows():
                    currency = row['Currency']
                    site_name = row['Site Name'].strip()

                    # If currency is "FC" and Site Name is "Fortune Coins", change it to "FC."
                    if currency == "FC" and site_name == "Fortune Coins":
                        currency = "FC."
                    fx_rate = all_rates[date].get(currency, None)

                    if fx_rate is None:
                        logger.error(f"Exchange rate for currency '{currency}' not found on date {row['Date']}. Setting fx_rate to 0.0")
                        fx_rate = 0.0

                    #Check conditions to skip adding the record
                    if row['Site Name'].strip() in ["ownlobby", "Netgaming( Internal )"] or row[
                        'Username'].upper().endswith("_OWN"):
                        logger.info(f"Skipping record for Username: {row['Username']}, Site Name: {row['Site Name']}")
                        continue

                    existing_record = db.session.query(ConsolidatedData).filter_by(
                        date=row['Date'].date() if isinstance(row['Date'], pd.Timestamp) else row['Date'],
                        username=row['Username'],
                        account_id=row['Account_ID']
                    ).first()

                    if existing_record:
                        logger.info(f"Duplicate found for {row['Username']} on {row['Date']}. Skipping.")
                        continue

                    consolidated_data = ConsolidatedData(
                        date=row['Date'].date() if isinstance(row['Date'], pd.Timestamp) else row['Date'],
                        username=row['Username'],
                        account_id=row['Account_ID'],
                        game_name=row['Game Name'],
                        game_id=row['Game_ID'],
                        currency=currency,
                        fx_rate=fx_rate,
                        bet=row['Bet'],
                        win=row['Win'],
                        bet_eur=row['Bet'] * fx_rate,
                        win_eur=row['Win'] * fx_rate,
                        number_of_spins=row['Number of Spins'],
                        cash_bet=row['Cash bet'],
                        bonus_bet=row['Bonus bet'],
                        cash_win=row['Cash win'],
                        bonus_win=row['Bonus win'],
                        site_name=row['Site Name']
                    )
                    consolidated_data_entries.append(consolidated_data)

        # Bulk insert consolidated data
        try:
            db.session.bulk_save_objects(consolidated_data_entries)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            logger.warning("Some records already existed and were skipped.")

        return {'message': 'Reports uploaded successfully!'}, 200

    except Exception as e:
        logger.error(f"Error in generating all reports: {str(e)}")
        return {'error': f"Error in generating all reports: {str(e)}"}, 500


#Generate all metrics summary
def generate_all_metrics():
    try:
        total_summary = calculate_total_summary_all_reports()
        if "error" in total_summary:
            logger.error("Failed to calculate total summary metrics.")
            return {'error': 'Failed to calculate total summary metrics.'}, 500

        return {
            'message': 'Total Metrics generated successfully!',
            'metrics': total_summary['metrics']
        }, 200
    except Exception as e:
        logger.error(f"Error in generating all metrics: {str(e)}")
        return {'error': f"Error in generating all metrics: {str(e)}"}, 500


# Calculate the total summary of the data and form a tabular format to frontend
def calculate_total_summary():
    try:
        logger.info("Fetching data for total summary calculation.")

        # Fetch records with pagination or in batches
        batch_size = 10000
        data = []
        page = 1
        while True:
            batch = ConsolidatedData.query.filter(ConsolidatedData.fx_rate > 0).limit(batch_size).offset(
                (page - 1) * batch_size).all()
            if not batch:
                break
            data.extend(batch)
            page += 1

        if not data:
            logger.error("No data available for total summary.")
            return {"error": "No data available for total summary."}, 404

        # Fetch exchange rates for all dates in one go
        dates = {record.date for record in data}  # Collect unique dates from the data
        exchange_rates = ExchangeRate.query.filter(ExchangeRate.date_fetched.in_(dates),
                                                   ExchangeRate.currency == 'GBP').all()

        # Map exchange rates by date for fast lookup
        rate_dict = {rate.date_fetched: rate.rate for rate in exchange_rates if rate.rate > 0}

        # Initialize date_summary dictionary
        date_summary = defaultdict(lambda: {
            "total_bet": 0,
            "total_win": 0,
            "reel_spins": 0,
            "social_spins": 0,
            "total_spins": 0
        })

        # Loop through data and aggregate metrics by date
        for record in data:
            if record.date not in rate_dict:
                logger.warning(f"No exchange rate found for date: {record.date}. Skipping record.")
                continue

            # Aggregating data by date
            date_summary[record.date]["total_bet"] += record.bet_eur
            date_summary[record.date]["total_win"] += record.win_eur
            date_summary[record.date]["total_spins"] += record.number_of_spins

            if record.currency in social_currencies:
                date_summary[record.date]["social_spins"] += record.number_of_spins
            else:
                date_summary[record.date]["reel_spins"] += record.number_of_spins

        # Sort dates in ascending order
        sorted_dates = sorted(date_summary.keys())

        # Insert or update data in TotalSummary and prepare response data
        response_data = []
        logger.info("Aggregating and processing total summary for each date.")

        for date in sorted_dates:
            logger.debug(f"Calculating RTP and GGR for date: {date}")
            # Get the exchange rate for the specific date
            if date not in rate_dict:
                logger.warning(f"No exchange rate found for date: {date}. Skipping record.")
                continue

            rate_in_gbp = rate_dict[date]  # Get the rate for the current date

            rtp = (date_summary[date]["total_win"] / date_summary[date]["total_bet"]) * 100 if date_summary[date]["total_bet"] > 0 else 0
            total_ggr_eur = date_summary[date]["total_bet"] - date_summary[date]["total_win"]
            total_ggr_gbp = total_ggr_eur / rate_in_gbp

            # Log GGR calculation for GBP
            logger.info(
                f"Date: {date}, Total GGR EUR: {total_ggr_eur}, Exchange Rate (GBP): {rate_in_gbp}, Total GGR GBP: {total_ggr_gbp}")

            # Prepare the record
            summary_record = TotalSummaryData(
                date=date,
                total_bet=round(date_summary[date]["total_bet"], 3),
                total_win=round(date_summary[date]["total_win"], 3),
                reel_spins=date_summary[date]["reel_spins"],
                social_spins=date_summary[date]["social_spins"],
                total_spins=date_summary[date]["total_spins"],
                rtp=round(rtp, 4),
                ggr_eur=round(total_ggr_eur, 3),
                ggr_gbp=round(total_ggr_gbp, 3)
            )

            # Check if a record for the date already exists
            existing_record = TotalSummaryData.query.filter_by(date=date).first()
            if existing_record:
                logger.info(f"Already there is an existing record for date: {date}")
                # Update the existing record
                existing_record.total_bet = summary_record.total_bet
                existing_record.total_win = summary_record.total_win
                existing_record.reel_spins = summary_record.reel_spins
                existing_record.social_spins = summary_record.social_spins
                existing_record.total_spins = summary_record.total_spins
                existing_record.rtp = summary_record.rtp
                existing_record.ggr_eur = summary_record.ggr_eur
                existing_record.ggr_gbp = summary_record.ggr_gbp
            else:
                logger.info(f"Adding new record for date: {date}")
                # Add a new record
                db.session.add(summary_record)

            # Prepare metrics for response
            metrics = {
                "total_bet": round(date_summary[date]["total_bet"], 3),
                "total_win": round(date_summary[date]["total_win"], 3),
                "total_spins": date_summary[date]["total_spins"],
                "social_spins": date_summary[date]["social_spins"],
                "reel_spins": date_summary[date]["reel_spins"],
                "rtp": round(rtp, 3),
                "ggr_eur": round(total_ggr_eur, 3),
                "ggr_gbp": round(total_ggr_gbp, 3)
            }

            logger.info(f"Total summary calculated successfully for {date}: {metrics}")

            # Add the data to response
            response_data.append({
                "date": date.strftime("%Y-%m-%d"),
                **metrics
            })

        # Commit changes to the database
        db.session.commit()
        logger.info("Total summary calculation completed for all dates.")
        return {"message": "Total summary calculated and saved successfully.", "data": response_data}, 200

    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Integrity error: {str(e)}")
        return {"error": f"Integrity error: {str(e)}"}, 500

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error calculating total summary: {str(e)}")
        return {"error": f"Error calculating total summary: {str(e)}"}, 500

# Load the latest data based on the latest date available
def load_latest_data():
    try:
        # Get the latest available date
        latest_data = get_latest_date_from_db()
        if not latest_data or "No valid date found" in latest_data:
            logger.error("No latest data found.")
            return {"error": "No latest data found."}, 400

        # Fetch exchange rates for the latest date
        rates = fetch_exchange_rates(latest_data)

        # Fetch data for the latest uploaded date with fx_rate > 0
        data = ConsolidatedData.query.filter(
            ConsolidatedData.date == latest_data, ConsolidatedData.fx_rate > 0
        ).all()
        if not data:
            logger.error(f"No data available for the specified date: {latest_data}")
            return {"error": "No data available for the specified date."}, 404

        # Calculate metrics
        total_bet = sum(record.bet_eur for record in data)
        total_win = sum(record.win_eur for record in data)

        # Calculate social spins and reel spins
        social_spins = sum(
            record.number_of_spins for record in data if record.currency in social_currencies
        )
        reel_spins = sum(
            record.number_of_spins for record in data if record.currency not in social_currencies
        )
        total_spins = social_spins + reel_spins

        rtp = (total_win / total_bet) * 100 if total_bet > 0 else 0
        ggr_eur = total_bet - total_win
        ggr_gbp = ggr_eur / rates.get('GBP', 1.0)

        metrics = {
            "latest_data": latest_data,  # Add the latest data date here
            "total_bet": round(total_bet, 3),
            "total_win": round(total_win, 3),
            "reel_spins": reel_spins,
            "social_spins": social_spins,
            "total_spins": total_spins,
            "rtp": round(rtp, 3),
            "ggr_eur": round(ggr_eur, 3),
            "ggr_gbp": round(ggr_gbp, 3)
        }

        logger.info(f"Latest data loaded successfully: {metrics}")
        return {"message": "Latest data loaded successfully.", "metrics": metrics}

    except Exception as e:
        logger.error(f"Error loading latest data: {str(e)}")
        return {"error": f"Error loading latest data: {str(e)}"}, 500


# Process file uploads and save data to the database
def upload_files(files):
    try:
        if not files:
            logger.error("No files uploaded!")
            return {'error': 'No files uploaded!'}, 400

        uploaded_file_paths = []
        extracted_dates = []
        UPLOAD_FOLDER = current_app.config['UPLOAD_FOLDER']
        CONSOLIDATED_FOLDER = current_app.config['CONSOLIDATED_FOLDER']

        for file in files:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            uploaded_file_paths.append(file_path)

            try:
                filename_date = file.filename.split('_')[-1].split('.')[0]
                extracted_dates.append(filename_date)
            except IndexError:
                logger.error(f"Invalid filename format for {file.filename}. Expected '_YYYY-MM-DD'")
                return {'error': f"Invalid filename format for {file.filename}. Expected '_YYYY-MM-DD'"}, 400

        if len(set(extracted_dates)) > 1:
            logger.error("Uploaded files have inconsistent dates in their filenames.")
            return {'error': 'Uploaded files have inconsistent dates in their filenames.'}, 400

        consolidated_date = extracted_dates[0]
        consolidated_file_name = f"reports_TZesst_Consolidated_{consolidated_date}.xlsx"
        consolidated_file_path = os.path.join(CONSOLIDATED_FOLDER, consolidated_file_name)
        rates = fetch_exchange_rates(consolidated_date)

        if not rates:
            logger.error("Failed to fetch exchange rates!")
            return {'error': 'Failed to fetch exchange rates!'}, 500

        # Merge and save the data
        dataframes = [pd.read_excel(file) for file in uploaded_file_paths]
        merged_df = pd.concat(dataframes)
        merged_df.to_excel(consolidated_file_path, index=False)

        # Save data to database
        for _, row in merged_df.iterrows():
            currency = row['Currency']
            site_name = row['Site Name'].strip()

            # If currency is "FC" and Site Name is "Fortune Coins", change it to "FC."
            if currency == "FC" and site_name == "Fortune Coins":
                currency = "FC."

            fx_rate = rates.get(currency, None)

            if fx_rate is None:
                logger.error(f"Exchange rate for currency '{currency}' not found on date {row['Date']}. Setting fx_rate to 0.0")
                fx_rate = 0.0

            # Check conditions to skip adding the record
            if row['Site Name'].strip() in ["ownlobby", "Netgaming( Internal )"] or row[
                'Username'].upper().endswith("_OWN"):
                logger.info(f"Skipping record for Username: {row['Username']}, Site Name: {row['Site Name']}")
                continue

            existing_record = db.session.query(ConsolidatedData).filter_by(
                date=row['Date'].date() if isinstance(row['Date'], pd.Timestamp) else row['Date'],
                username=row['Username'],
                account_id=row['Account_ID']
            ).first()

            if existing_record:
                logger.info(f"Duplicate found for {row['Username']} on {row['Date']}. Skipping.")
                continue

            consolidated_data = ConsolidatedData(
                date=row['Date'].date() if isinstance(row['Date'], pd.Timestamp) else row['Date'],
                username=row['Username'],
                account_id=row['Account_ID'],
                game_name=row['Game Name'],
                game_id=row['Game_ID'],
                currency=row['Currency'],
                fx_rate=fx_rate,
                bet=row['Bet'],
                win=row['Win'],
                bet_eur=row['Bet'] * fx_rate,
                win_eur=row['Win'] * fx_rate,
                number_of_spins=row['Number of Spins'],
                cash_bet=row['Cash bet'],
                bonus_bet=row['Bonus bet'],
                cash_win=row['Cash win'],
                bonus_win=row['Bonus win'],
                site_name=row['Site Name']
            )
            db.session.add(consolidated_data)
        db.session.commit()

        logger.info(f"Files processed and saved successfully. Consolidated file: {consolidated_file_name}")
        return {'message': 'Files processed and saved successfully!', 'consolidated_file': consolidated_file_name}

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        return {'error': f'Error processing files: {str(e)}'}, 500

# Calculate metrics for the latest uploaded data
def calculate_metrics(consolidated_date):
    try:
        rates = fetch_exchange_rates(consolidated_date)
        data = ConsolidatedData.query.filter(ConsolidatedData.date == consolidated_date, ConsolidatedData.fx_rate > 0).all()
        if not data:
            logger.error(f"No data available for the specified date: {consolidated_date}")
            return {"error": "No data available for the specified date."}, 400

        total_bet = sum(record.bet_eur for record in data)
        total_win = sum(record.win_eur for record in data)
        # Calculate social spins and reel spins
        social_spins = sum(
            record.number_of_spins for record in data if record.currency in social_currencies
        )
        reel_spins = sum(
            record.number_of_spins for record in data if record.currency not in social_currencies
        )
        total_spins = social_spins + reel_spins

        rtp = (total_win / total_bet) * 100 if total_bet > 0 else 0
        ggr_eur = total_bet - total_win
        ggr_gbp = ggr_eur / rates.get('GBP', 1.0)

        metrics = {
            "total_bet": round(total_bet, 3),
            "total_win": round(total_win, 3),
            "reel_spins": reel_spins,
            "social_spins": social_spins,
            "total_spins": total_spins,
            "rtp": round(rtp, 3),
            "ggr_eur": round(ggr_eur, 3),
            "ggr_gbp": round(ggr_gbp, 3)
        }

        logger.info(f"Metrics calculated for date {consolidated_date}: {metrics}")
        return metrics

    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        return {'error': f'Error calculating metrics: {str(e)}'}, 500

#Calculate total summary for all reports
def calculate_total_summary_all_reports():
    try:
        # Fetch all data and exchange rates in a single query
        data = ConsolidatedData.query.filter(ConsolidatedData.fx_rate > 0).all()
        rates = {
            rate.date_fetched: rate.rate for rate in ExchangeRate.query.filter_by(currency='GBP').all()
        }

        if not data:
            logger.error("No data available for total summary.")
            return {"error": "No data available for total summary."}, 404

        # Use a dictionary to store aggregated metrics
        totals = {"total_bet": 0, "total_win": 0, "total_spins": 0, "social_spins": 0, "reel_spins": 0, "ggr_eur": 0, "ggr_gbp": 0}

        # Process records in bulk
        for record in data:
            rate_in_gbp = rates.get(record.date, 1.0)  # Default rate to 1.0 if missing
            ggr_eur = record.bet_eur - record.win_eur
            ggr_gbp = ggr_eur / rate_in_gbp

            totals["total_bet"] += record.bet_eur
            totals["total_win"] += record.win_eur
            totals["total_spins"] += record.number_of_spins
            totals["ggr_eur"] += ggr_eur
            totals["ggr_gbp"] += ggr_gbp

            # Social vs Reel spins
            if record.currency in social_currencies:
                totals["social_spins"] += record.number_of_spins
            else:
                totals["reel_spins"] += record.number_of_spins

        # Calculate RTP
        rtp = (totals["total_win"] / totals["total_bet"]) * 100 if totals["total_bet"] > 0 else 0

        # Return final metrics
        metrics = {key: round(value, 3) for key, value in totals.items()}
        metrics["rtp"] = round(rtp,3)


        logger.info(f"Total summary calculated successfully: {metrics}")
        return {"message": "Total summary calculated successfully.", "metrics": metrics}

    except Exception as e:
        logger.error(f"Error calculating total summary: {str(e)}")
        return {"error": f"Error calculating total summary: {str(e)}"}, 500

def add_missing_dates_data_to_total_summary():
    try:
        # Fetch all TotalSummaryData records
        data = TotalSummaryData.query.all()

        if not data:
            logger.error("No data available in the TotalSummaryData table.")
            return {"error": "No data available in the TotalSummaryData table."}, 404

        # Get date range from ConsolidatedData
        latest_consolidated = ConsolidatedData.query.order_by(ConsolidatedData.date.desc()).first()
        oldest_consolidated = ConsolidatedData.query.order_by(ConsolidatedData.date.asc()).first()

        if not latest_consolidated or not oldest_consolidated:
            logger.error("No ConsolidatedData found.")
            return {"error": "No ConsolidatedData found."}, 404

        min_date = oldest_consolidated.date
        max_date = latest_consolidated.date

        # Get all dates present in TotalSummaryData
        existing_dates = {record.date for record in TotalSummaryData.query.with_entities(TotalSummaryData.date).all()}

        # Find missing dates
        missing_dates = []
        current_date = min_date
        while current_date <= max_date:
            if current_date not in existing_dates:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        if not missing_dates:
            logger.info("No missing dates found in TotalSummaryData.")
            return {"message": "No missing dates found in TotalSummaryData."}, 200
        else:
            logger.info(f"Missing dates to be added: {missing_dates}")

        # Process each missing date
        for missing_date in missing_dates:
            # Fetch relevant data for the missing date
            consolidated_data = ConsolidatedData.query.filter(
                ConsolidatedData.date == missing_date,
                ConsolidatedData.fx_rate > 0
            ).all()

            if not consolidated_data:
                logger.warning(f"No data found for missing date: {missing_date}")
                return {"error": f"No consolidated data found for missing date: {missing_date}"}, 404

            # Fetch exchange rate for GBP
            exchange_rate_gbp = ExchangeRate.query.filter(
                ExchangeRate.currency == "GBP",
                ExchangeRate.date_fetched == missing_date
            ).first()

            if not exchange_rate_gbp:
                logger.warning(f"No exchange rate found for GBP on {missing_date}")
                return {"error": f"No exchange rate found for GBP on {missing_date}"}, 404

            # Compute metrics
            total_bet = sum(record.bet_eur or 0 for record in consolidated_data)
            total_win = sum(record.win_eur or 0 for record in consolidated_data)
            social_spins = sum(
                record.number_of_spins or 0 for record in consolidated_data if record.currency in social_currencies)
            reel_spins = sum(
                record.number_of_spins or 0 for record in consolidated_data if record.currency not in social_currencies)
            total_spins = social_spins + reel_spins
            rtp = (total_win / total_bet) * 100 if total_bet > 0 else 0
            ggr_eur = total_bet - total_win
            ggr_gbp = ggr_eur / exchange_rate_gbp.rate


            # Insert the missing date data into TotalSummaryData
            new_summary_data = TotalSummaryData(
                date=missing_date,
                total_bet=round(total_bet, 3),
                total_win=round(total_win, 3),
                total_spins=total_spins,
                reel_spins=reel_spins,
                social_spins=social_spins,
                ggr_eur=round(ggr_eur, 3),
                ggr_gbp=round(ggr_gbp, 3),
                rtp=round(rtp, 3),
            )
            db.session.add(new_summary_data)

        # Commit all new records
        db.session.commit()
        logger.info("Missing TotalSummaryData entries added successfully.")
        return {"message": "Total summary data updated with missing dates."}, 200

    except Exception as e:
        logger.error(f"Error fetching total summary: {str(e)}")
        return {"error": f"Error fetching total summary: {str(e)}"}, 500


#Fetch latest and cumulative summary
def get_total_summary_data():
    try:
        add_missing_dates_data_to_total_summary()
        data = TotalSummaryData.query.all()

        if not data:
            logger.error("No data available in the TotalSummaryData table.")
            return {"error": "No data available in the TotalSummaryData table."}, 404

        # Initialize cumulative and latest metrics
        cumulative_metrics = {
            "total_bet": 0, "total_win": 0, "total_spins": 0, "reel_spins": 0,
            "social_spins": 0, "ggr_eur": 0, "ggr_gbp": 0, "total_players": 0
        }
        latest_metrics = cumulative_metrics.copy()

        # Aggregate cumulative metrics
        for record in data:
            cumulative_metrics["total_bet"] += record.total_bet
            cumulative_metrics["total_win"] += record.total_win
            cumulative_metrics["total_spins"] += record.total_spins
            cumulative_metrics["reel_spins"] += record.reel_spins
            cumulative_metrics["social_spins"] += record.social_spins
            cumulative_metrics["ggr_eur"] += record.ggr_eur
            cumulative_metrics["ggr_gbp"] += record.ggr_gbp

        cumulative_metrics["total_bet"] = round(cumulative_metrics["total_bet"], 3)
        cumulative_metrics["total_win"] = round(cumulative_metrics["total_win"], 3)
        cumulative_metrics["ggr_eur"] = round(cumulative_metrics["ggr_eur"], 3)
        cumulative_metrics["ggr_gbp"] = round(cumulative_metrics["ggr_gbp"], 3)

        # Fetch total unique players for cumulative data
        cumulative_metrics["total_players"] = db.session.query(ConsolidatedData.account_id.distinct()) \
            .filter(ConsolidatedData.fx_rate > 0).count()

        max_date_record = ConsolidatedData.query.order_by(ConsolidatedData.date.desc()).first()
        min_date_record = ConsolidatedData.query.order_by(ConsolidatedData.date.asc()).first()

        if not max_date_record or not min_date_record:
            logger.error("No valid date records found in ConsolidatedData.")
            return {"error": "No valid date records found."}, 404

        max_date = max_date_record.date
        min_date = min_date_record.date

        # Fetch latest summary data
        total_summary_latest = TotalSummaryData.query.filter_by(date=max_date).first()

        if not total_summary_latest:
            logger.warning(f"No latest summary data found for date: {max_date}")
            return {"error": f"No latest summary data found for date: {max_date}"}, 404

        latest_metrics.update({
            "total_bet": round(total_summary_latest.total_bet, 3),
            "total_win": round(total_summary_latest.total_win, 3),
            "total_spins": total_summary_latest.total_spins,
            "reel_spins": total_summary_latest.reel_spins,
            "social_spins": total_summary_latest.social_spins,
            "ggr_eur": round(total_summary_latest.ggr_eur, 3),
            "ggr_gbp": round(total_summary_latest.ggr_gbp, 3),
            "total_players": db.session.query(ConsolidatedData.account_id.distinct()) \
                .filter(ConsolidatedData.date == max_date, ConsolidatedData.fx_rate > 0) \
                .count()
        })

        # Calculate RTP for cumulative and latest metrics
        cumulative_metrics["rtp"] = round(
            (cumulative_metrics["total_win"] / cumulative_metrics["total_bet"]) * 100 if cumulative_metrics["total_bet"] > 0 else 0, 3
        )
        latest_metrics["rtp"] = round(
            (latest_metrics["total_win"] / latest_metrics["total_bet"]) * 100 if latest_metrics["total_bet"] > 0 else 0, 3
        )

        # Add date information
        cumulative_metrics["max_date"] = max_date.strftime("%Y-%m-%d")
        cumulative_metrics["min_date"] = min_date.strftime("%Y-%m-%d")
        latest_metrics["max_date"] = max_date.strftime("%Y-%m-%d")

        logger.info(f"Total summary fetched successfully: {cumulative_metrics}")
        logger.info(f"Latest summary fetched successfully: {latest_metrics}")

        return {
            "message": "Latest and Total summary fetched successfully.",
            "cumulative_metrics": cumulative_metrics,
            "latest_date_metrics": latest_metrics,
        }, 200

    except Exception as e:
        logger.error(f"Error fetching total summary: {str(e)}")
        return {"error": f"Error fetching total summary: {str(e)}"}, 500
