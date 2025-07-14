import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
file_path = 'data/databaru_from_api.csv'
df = pd.read_csv(file_path)

# --- 1. Label Distribution ---
plt.figure(figsize=(8,4))
sns.countplot(x='Number', data=df)
plt.title('Distribution of Number (Target)')
plt.savefig('data/eda_number_distribution.png')
plt.close()

# --- 2. Time Series Plot ---
plt.figure(figsize=(16,4))
plt.plot(np.arange(len(df)), df['Number'].values, marker='.', linestyle='-', alpha=0.7)
plt.title('Number over Time')
plt.xlabel('Index (Chronological)')
plt.ylabel('Number')
plt.savefig('data/eda_number_timeseries.png')
plt.close()

# --- 3. Autocorrelation Plot ---
from pandas.plotting import autocorrelation_plot
plt.figure(figsize=(8,4))
autocorrelation_plot(pd.Series(df['Number'].values))
plt.title('Autocorrelation of Number')
plt.savefig('data/eda_number_autocorrelation.png')
plt.close()

# --- 4. Lag Feature Correlation ---
max_lag = 10
lag_corrs = []
for lag in range(1, max_lag+1):
    df[f'number_lag_{lag}'] = df['Number'].shift(lag)
    temp = df[['Number', f'number_lag_{lag}']].dropna()
    if len(temp) > 0:
        corr = temp['Number'].corr(temp[f'number_lag_{lag}'])
    else:
        corr = np.nan
    lag_corrs.append(corr)
plt.figure(figsize=(8,4))
plt.bar(range(1, max_lag+1), lag_corrs)
plt.xlabel('Lag')
plt.ylabel('Correlation with Number')
plt.title('Correlation of Lagged Number Features with Target')
plt.savefig('data/eda_lag_correlation.png')
plt.close()

# --- 5. Rolling Mean/Std ---
window = 100
plt.figure(figsize=(16,4))
plt.plot(df['Number'].rolling(window).mean(), label=f'Rolling Mean ({window})')
plt.plot(df['Number'].rolling(window).std(), label=f'Rolling Std ({window})')
plt.title(f'Rolling Mean and Std of Number (window={window})')
plt.legend()
plt.savefig('data/eda_rolling_stats.png')
plt.close()

# --- 6. Save summary statistics ---
sumstats = df['Number'].describe()
sumstats.to_csv('data/eda_number_summary.csv')

# --- 7. Print class balance to text file ---
class_balance = df['Number'].value_counts().sort_index()
class_balance.to_csv('data/eda_number_class_balance.csv')

print('EDA completed. Plots and summaries saved in data/.')