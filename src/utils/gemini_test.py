import sys
import os

# Path setup
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rl_agent.gemini_predictor import GeminiPredictor

def main():
    """
    Tests the Gemini AI integration with sample data.
    """
    print("[T] Testing Gemini AI with sample data...")
    try:
        predictor = GeminiPredictor('gemini-2.5-flash')
        result = predictor.generate_holistic_report('Test data: 12345')
        print('[V] Gemini AI Test SUCCESSFUL!')
        print('Sample Response:')
        print('-' * 40)
        print(result)
        print('-' * 40)
    except Exception as e:
        print(f'[X] Gemini AI Test FAILED: {e}')

if __name__ == "__main__":
    main()
