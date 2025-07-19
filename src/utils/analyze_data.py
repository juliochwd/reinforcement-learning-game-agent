import sys
import os
import pandas as pd

# Path setup
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rl_agent.gemini_predictor import GeminiPredictor

def main():
    """
    Analyzes existing data with Gemini AI.
    """
    print("[A] Analyzing existing data with Gemini AI...")
    try:
        df = pd.read_csv('data/databaru_from_api.csv')
        latest_data = df.tail(200).to_string()
        predictor = GeminiPredictor('gemini-2.5-flash')
        analysis = predictor.generate_holistic_report(f'Latest 200 records: {latest_data}')
        print('[R] GEMINI AI ANALYSIS REPORT')
        print('=' * 50)
        print(analysis)
        print('=' * 50)
    except FileNotFoundError:
        print("[X] No data file found at data/databaru_from_api.csv")
        print("Please run scraping first to generate data.")
    except Exception as e:
        print(f'[X] Analysis failed: {e}')

if __name__ == "__main__":
    main()
