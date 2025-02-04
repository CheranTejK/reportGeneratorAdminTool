import logging

import matplotlib
matplotlib.use('Agg')  # Use Agg backend for non-GUI operations
import matplotlib.pyplot as plt
import pandas as pd
import io
from flask import Response
from sqlalchemy.sql import text
from src.models.db_models import db

logger = logging.getLogger(__name__)

def generate_player_metrics_graphs():
    try:
        # Fetch player metrics data using the separate method
        data = get_player_metrics_data()

        # Convert data to DataFrame
        df = pd.DataFrame(data, columns=['rounds_range', 'player_count', 'total_spins', 'total_bet', 'total_win', 'total_RTP'])
        df.fillna(0, inplace=True)  # Prevent NaN issues
        df = df.astype({'total_RTP': 'float', 'player_count': 'int', 'total_spins': 'int'})
        # Log the DataFrame
        logger.info(f"DataFrame: {df}")

        if df.empty:
            return "No data available", 404

        # Generate and return graph
        return visualize_data(df)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating graphs: {str(e)}")
        return f"Error: {str(e)}", 500
    finally:
        db.session.close()


def visualize_data(df):
    plt.rcParams['font.family'] = 'DejaVu Sans'  # Fix font issue
    rounds_range = df['rounds_range'].tolist()
    player_count = df['player_count'].tolist()
    total_spins = df['total_spins'].tolist()
    rtp = df['total_RTP'].tolist()

    fig, axs = plt.subplots(3, 1, figsize=(14, 16), sharex=True)
    fig.tight_layout(pad=7)

    # Graph 1: Players Count
    axs[0].bar(rounds_range, player_count, color='skyblue')
    axs[0].set_title("Players Count by Round Category")
    axs[0].set_ylabel("Players Count")
    axs[0].grid(axis='y', linestyle='--', alpha=0.7)
    for i, value in enumerate(player_count):
        axs[0].text(i, value + max(player_count) * 0.02, str(value), ha='center', fontsize=10)

    # Graph 2: RTP
    axs[1].plot(rounds_range, rtp, marker='o', color='orange', linestyle='-', linewidth=2)
    axs[1].set_title("RTP by Round Category")
    axs[1].set_ylabel("RTP (%)")
    axs[1].grid(axis='y', linestyle='--', alpha=0.7)
    for i, value in enumerate(rtp):
        axs[1].text(i, value + max(rtp) * 0.0035, f"{value}%", ha='center', fontsize=10)

    # Graph 3: Total Number of Spins
    axs[2].bar(rounds_range, total_spins, color='lightgreen')
    axs[2].set_title("Total Number of Spins by Round Category")
    axs[2].set_ylabel("Total Number of Spins")
    axs[2].set_xlabel("Round Category")
    axs[2].grid(axis='y', linestyle='--', alpha=0.7)
    for i, value in enumerate(total_spins):
        axs[2].text(i, value + max(total_spins) * 0.02, str(value), ha='center', fontsize=10)

    # Save the plot to a BytesIO object
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    plt.close()
    img_io.seek(0)

    return Response(img_io.getvalue(), mimetype='image/png')

def get_player_metrics_data():
    try:
        # SQL query to fetch player metrics
        sql_query = text("""
            WITH player_metrics AS (
                SELECT 
                    account_id,
                    SUM(number_of_spins) AS total_spins, 
                    SUM(bet_eur) AS total_bet,
                    SUM(win_eur) AS total_win
                FROM reportgenerator.consolidated_data
                WHERE fx_rate > 0  -- Ensuring only valid fx_rate values are considered
                GROUP BY account_id
            ),
            categorized_metrics AS (
                SELECT 
                    *,
                    CASE
                        WHEN total_spins < 10 THEN '<10'
                        WHEN total_spins BETWEEN 10 AND 50 THEN '10-50'
                        WHEN total_spins BETWEEN 50 AND 100 THEN '50-100'
                        WHEN total_spins BETWEEN 100 AND 200 THEN '100-200'
                        WHEN total_spins BETWEEN 200 AND 500 THEN '200-500'
                        WHEN total_spins BETWEEN 500 AND 1000 THEN '500-1000'
                        WHEN total_spins BETWEEN 1000 AND 5000 THEN '1000-5000'
                        WHEN total_spins BETWEEN 5000 AND 10000 THEN '5000-10000'
                        WHEN total_spins BETWEEN 10000 AND 20000 THEN '10000-20000'
                        WHEN total_spins BETWEEN 20000 AND 50000 THEN '20000-50000'
                        ELSE '>50000'
                    END AS spins_range,
                    CASE
                        WHEN total_spins < 10 THEN 1
                        WHEN total_spins BETWEEN 10 AND 50 THEN 2
                        WHEN total_spins BETWEEN 50 AND 100 THEN 3
                        WHEN total_spins BETWEEN 100 AND 200 THEN 4
                        WHEN total_spins BETWEEN 200 AND 500 THEN 5
                        WHEN total_spins BETWEEN 500 AND 1000 THEN 6
                        WHEN total_spins BETWEEN 1000 AND 5000 THEN 7
                        WHEN total_spins BETWEEN 5000 AND 10000 THEN 8
                        WHEN total_spins BETWEEN 10000 AND 20000 THEN 9
                        WHEN total_spins BETWEEN 20000 AND 50000 THEN 10
                        ELSE 11
                    END AS range_order
                FROM player_metrics
            )
            SELECT 
                spins_range,
                COUNT(DISTINCT account_id) AS player_count,
                SUM(total_spins) AS total_spins,
                SUM(total_bet) AS total_bet,
                SUM(total_win) AS total_win,
                CASE 
                    WHEN SUM(total_bet) > 0 THEN 
                        ROUND(SUM(total_win) * 100 / SUM(total_bet), 2)
                    ELSE 
                        NULL
                END AS total_RTP
            FROM categorized_metrics
            GROUP BY spins_range, range_order
            ORDER BY range_order;
        """)

        # Fetch data from MySQL
        result = db.session.execute(sql_query)
        data = result.fetchall()
        # Log the fetched data
        logger.info(f"Fetched data: {data}")
        return data

    except Exception as e:
        logger.error(f"Error fetching player metrics data: {str(e)}")
        raise  # Reraise the exception so the calling method can handle it
