import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Path setup
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class GeminiPredictor:
    def __init__(self, model_name='gemini-2.5-flash'):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        genai.configure(api_key=api_key)
        
        self.constitution = self._load_prompt_file('gemini_gems/petunjuk_gemini.md')
        self.knowledge_codex = self._load_prompt_file('gemini_gems/KODEKS_FINAL_PREDIKSI.md')
        
        system_instruction = self.constitution + "\n\n" + self.knowledge_codex
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )

    def _load_prompt_file(self, file_path):
        full_path = os.path.join(project_root, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at: {full_path}")

    def generate_holistic_report(self, new_data):
        prompt = f"Data baru telah tiba: {new_data}. Laksanakan protokol pelaporan holistik Anda."
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"An error occurred while generating the report: {e}"

if __name__ == '__main__':
    # Example usage for testing
    try:
        predictor = GeminiPredictor(model_name='gemini-2.5-flash')
        # Simulate new data
        sample_data = "{'period': '202407191234', 'number': '5'}"
        report = predictor.generate_holistic_report(sample_data)
        print("--- Holistic Report ---")
        print(report)
        print("-----------------------")
    except Exception as e:
        print(f"Error during test run: {e}")
