def calculate_grouped_ggr(df, rates):
    # Add FX rates and GGR calculation to the DataFrame
    df['FX Rate'] = df['Currency'].map(rates).fillna(1.0)  # Default FX rate is 1.0 for unknown currencies
    df['GGR_EUR'] = (df['Bet'] - df['Win']) * df['FX Rate']
    df['GGR_GBP'] = df['GGR_EUR'] / rates.get('GBP', 1.0)  # Convert to GBP using FX rate

    # Grouping and aggregation for GGR_CUR_OP report
    ggr_cur_op = df.groupby(['Site Name', 'Currency']).agg({
        'Bet': 'sum',
        'Win': 'sum',
        'Number of Spins': 'sum',
        'GGR_EUR': 'sum',
        'GGR_GBP': 'sum'
    }).reset_index()

    # Grouping and aggregation for GGR_CUR report
    ggr_cur = df.groupby(['Currency']).agg({
        'Number of Spins': 'sum',
        'Bet': 'sum',
        'Win': 'sum',
        'GGR_EUR': 'sum',
        'GGR_GBP': 'sum'
    }).reset_index()

    # Grouping and aggregation for GGR_OP report
    ggr_op = df.groupby(['Site Name']).agg({
        'Bet': 'sum',
        'Win': 'sum',
        'Number of Spins': 'sum',
        'GGR_EUR': 'sum',
        'GGR_GBP': 'sum'
    }).reset_index()

    return ggr_cur_op, ggr_cur, ggr_op
