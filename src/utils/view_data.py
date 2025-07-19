import sys
import os
import pandas as pd

def main():
    """
    Displays the current scraping data.
    """
    output_csv_path = 'data/databaru_from_api.csv'
    print("[+] Latest scraping results:")
    try:
        df = pd.read_csv(output_csv_path)
        print(f'Total records: {len(df)}')
        print('Latest 5 records:')
        print('-' * 30)
        print(df.tail().to_string(index=False))
        print('-' * 30)
        print(f'Date range: {df.iloc[0,0] if len(df) > 0 else 'N/A'} to {df.iloc[-1,0] if len(df) > 0 else 'N/A'}')
    except FileNotFoundError:
        print(f"[X] No scraping data found at {output_csv_path}.")
        print("Run scraping operations first to generate data.")
    except Exception as e:
        print(f'Error reading data: {e}')

    print("\n[F] Other data files:")
    os.system('dir /b data\\')

if __name__ == "__main__":
    main()
