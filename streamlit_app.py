import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Title of the app
st.title('Investment Strategy Evaluation')

# Load the data
data = pd.read_csv('data/passive_pue_hist_returns.csv', sep=';', parse_dates=['Date'], dayfirst=True)
data = data.sort_values('Date').reset_index(drop=True)

# Calculate daily returns for SPX and LIBOR
data['SPX_return'] = data['SPX'].pct_change()
data['LIBOR_daily'] = data['LIBOR'] / 360  # Assuming a 360-day year

# User inputs
st.sidebar.header('User Input Parameters')
x_percent_list = st.sidebar.multiselect(
    'Select Initial Investment Percentage (x%)',
    options=range(0, 105, 5),
    default=[30, 40, 50]
)

sampling_frequency = st.sidebar.slider(
    'Sampling Frequency (Every Nth Day)',
    min_value=1,
    max_value=30,
    value=5,
    step=1
)

# Initialize results dictionary
results = {}
progress_bar = st.progress(0)
progress_counter = 0
total_progress = len(x_percent_list)

for x_percent in x_percent_list:
    x = x_percent / 100  # Convert percentage to decimal
    returns = []
    max_drawdowns = []

    # Loop over start dates with specified sampling frequency
    for idx in range(0, len(data), sampling_frequency):
        start_date = data.loc[idx, 'Date']
        end_date = start_date + pd.DateOffset(months=9)
        period_data = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)].reset_index(drop=True)
        if len(period_data) < 2:
            continue

        # Initialize portfolio values
        total_cash = 100.0
        invested_cash = total_cash * x
        uninvested_cash = total_cash * (1 - x)
        portfolio_values = [total_cash]
        max_value = total_cash
        drawdowns = [0]
        num_invest_days = len(period_data) - 1
        daily_investment = uninvested_cash / num_invest_days if num_invest_days > 0 else 0

        for i in range(1, len(period_data)):
            # Invest daily amount
            if uninvested_cash > 0:
                invested_cash += daily_investment
                uninvested_cash -= daily_investment

            # Update uninvested cash with LIBOR interest
            libor_rate = period_data.loc[i-1, 'LIBOR_daily']
            uninvested_cash += uninvested_cash * libor_rate

            # Update invested cash with SPX returns
            spx_return = period_data.loc[i, 'SPX_return']
            invested_cash += invested_cash * spx_return

            # Calculate total portfolio value
            total_value = invested_cash + uninvested_cash
            portfolio_values.append(total_value)

            # Calculate drawdown
            if total_value > max_value:
                max_value = total_value
            drawdown = (max_value - total_value) / max_value
            drawdowns.append(drawdown)

        # Record the return and maximum drawdown
        total_return = (portfolio_values[-1] - total_cash) / total_cash
        returns.append(total_return)
        max_drawdowns.append(max(drawdowns))

    # Store results
    results[x_percent] = {
        'returns': returns,
        'max_drawdowns': max_drawdowns
    }
    progress_counter += 1
    progress_bar.progress(progress_counter / total_progress)

# Display average returns
for x_percent in sorted(results.keys()):
    st.subheader(f"Initial Investment Percentage: {x_percent}%")
    average_return = np.mean(results[x_percent]['returns'])
    st.write(f"Average 9-month Return: {average_return * 100:.2f}%")

# Plotting the boxplot of Maximum Drawdown Distributions using Plotly
st.subheader('Maximum Drawdown Distribution by Initial Investment Percentage')

# Prepare data for Plotly
plot_data = []
for x_percent in sorted(results.keys()):
    df_temp = pd.DataFrame({
        'Initial Investment Percentage': f"{x_percent}%",
        'Maximum Drawdown': results[x_percent]['max_drawdowns']
    })
    plot_data.append(df_temp)

plot_data = pd.concat(plot_data, ignore_index=True)

# Convert Maximum Drawdown to percentage
plot_data['Maximum Drawdown'] = plot_data['Maximum Drawdown'] * 100

# Create the Plotly boxplot
fig = px.box(
    plot_data,
    x='Initial Investment Percentage',
    y='Maximum Drawdown',
    points='all',
    labels={'Maximum Drawdown': 'Maximum Drawdown (%)'},
    title='Maximum Drawdown Distribution per Initial Investment Percentage'
)

# Simplify the hover tooltip
fig.update_traces(
    hovertemplate='Maximum Drawdown: %{y:.2f}%<extra></extra>'
)

# Annotate major data points
x_categories = sorted(plot_data['Initial Investment Percentage'].unique())

for x_category in x_categories:
    y_data = plot_data[plot_data['Initial Investment Percentage'] == x_category]['Maximum Drawdown']
    median = np.median(y_data)
    q1 = np.percentile(y_data, 25)
    q3 = np.percentile(y_data, 75)
    decile_10 = np.percentile(y_data, 10)
    decile_90 = np.percentile(y_data, 90)

    # Annotate median
    fig.add_annotation(
        x=x_category,
        y=median,
        text=f"Median: {median:.2f}%",
        showarrow=False,
        yshift=10
    )

    # Annotate quartiles
    fig.add_annotation(
        x=x_category,
        y=q1,
        text=f"Q1: {q1:.2f}%",
        showarrow=False,
        yshift=10
    )
    fig.add_annotation(
        x=x_category,
        y=q3,
        text=f"Q3: {q3:.2f}%",
        showarrow=False,
        yshift=-10
    )

    # Annotate deciles
    fig.add_annotation(
        x=x_category,
        y=decile_10,
        text=f"10th %: {decile_10:.2f}%",
        showarrow=False,
        yshift=10
    )
    fig.add_annotation(
        x=x_category,
        y=decile_90,
        text=f"90th %: {decile_90:.2f}%",
        showarrow=False,
        yshift=-10
    )

# Update layout to prevent overlapping labels
fig.update_layout(
    margin=dict(l=40, r=40, t=60, b=40),
    hovermode="x unified",
    annotations=[
        dict(
            xref='x',
            yref='y',
            showarrow=False,
            textangle=0,
            font=dict(size=10)
        )
    ]
)

# Display the figure in Streamlit
st.plotly_chart(fig, use_container_width=True)
