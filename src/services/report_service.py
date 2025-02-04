import os

import pandas as pd

from src.models.db_models import ConsolidatedData
from src.utils.ggr_utils import calculate_grouped_ggr


def generate_report_for_date(consolidated_date, rates, GGR_FOLDER):
    try:
        # Fetch data for the latest uploaded date
        data = ConsolidatedData.query.filter(ConsolidatedData.date == consolidated_date,
                                             ConsolidatedData.fx_rate > 0).all()
        if not data:
            return {"error": "No data available for the specified date."}, 400

        # Convert database data to a DataFrame
        data_dict = [
            {
                "Date": d.date,
                "Username": d.username,
                "Account_ID": d.account_id,
                "Game Name": d.game_name,
                "Game_ID": d.game_id,
                "Currency": d.currency,
                "Bet": d.bet * d.fx_rate,
                "Win": d.win * d.fx_rate,
                "Number of Spins": d.number_of_spins,
                "Cash bet": d.cash_bet,
                "Bonus bet": d.bonus_bet,
                "Cash win": d.cash_win,
                "Bonus win": d.bonus_win,
                "Site Name": d.site_name,
            }
            for d in data
        ]
        df = pd.DataFrame(data_dict)

        if not isinstance(rates, dict):
            return {"error": "Failed to fetch valid exchange rates."}, 500

        # Calculate GGR and perform groupings
        ggr_cur_op, ggr_cur, ggr_op = calculate_grouped_ggr(df, rates)

        ggr_files = {}

        # File paths
        ggr_files["GGR_CUR_OP"] = f"GGR_CUR_OP_reports_TZesst_Consolidated_{consolidated_date}.xlsx"
        ggr_files["GGR_CUR"] = f"GGR_cur_reports_TZesst_Consolidated_{consolidated_date}.xlsx"
        ggr_files["GGR_OP"] = f"GGR_OP_reports_TZesst_Consolidated_{consolidated_date}.xlsx"

        # Save grouped data to Excel files
        ggr_cur_op.to_excel(os.path.join(GGR_FOLDER, ggr_files["GGR_CUR_OP"]), index=False)
        ggr_cur.to_excel(os.path.join(GGR_FOLDER, ggr_files["GGR_CUR"]), index=False)
        ggr_op.to_excel(os.path.join(GGR_FOLDER, ggr_files["GGR_OP"]), index=False)

        return {
            "message": "Reports generated successfully!",
            "files": ggr_files
        }

    except Exception as e:
        return {"error": f"Error generating report: {str(e)}"}, 500