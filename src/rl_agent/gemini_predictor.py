import os
import sys
from dotenv import load_dotenv

# Try to import the correct Google AI package
try:
    # Try the newer google-genai package first
    import google.genai as genai
    from google.genai import types
    PACKAGE_TYPE = "google-genai"
    HAS_ADVANCED_TYPES = True
except ImportError:
    try:
        # Fallback to older google-generativeai package
        import google.generativeai as genai
        from google.generativeai import types
        PACKAGE_TYPE = "google-generativeai"
        HAS_ADVANCED_TYPES = True
    except ImportError:
        # Last resort - try without types
        try:
            import google.generativeai as genai
            types = None
            PACKAGE_TYPE = "google-generativeai-basic"
            HAS_ADVANCED_TYPES = False
        except ImportError:
            raise ImportError("No compatible Google AI package found. Please install google-genai or google-generativeai")

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
        
        # Print version info for debugging
        print(f"[I] Using package: {PACKAGE_TYPE}")
        try:
            if hasattr(genai, '__version__'):
                print(f"[I] Package version: {genai.__version__}")
        except AttributeError:
            print("[W] Could not determine package version")
        
        # Configure based on package type
        if PACKAGE_TYPE == "google-genai":
            # For google-genai package
            client = genai.Client(api_key=api_key)
            self.client = client
            self.model_name = model_name
        else:
            # For google-generativeai package
            genai.configure(api_key=api_key)
        
        self.constitution = self._load_prompt_file('gemini_gems/petunjuk_gemini.md')
        self.knowledge_codex = self._load_prompt_file('gemini_gems/KODEKS_FINAL_PREDIKSI.md')
        
        system_instruction = self.constitution + "\n\n" + self.knowledge_codex
        
        # Create model based on package type
        if PACKAGE_TYPE == "google-genai":
            # For google-genai package - simpler initialization
            self.model = None  # Will use client directly
            self.system_instruction = system_instruction
        else:
            # For google-generativeai package
            generation_config = None
            if "2.5" in model_name and HAS_ADVANCED_TYPES and types:
                try:
                    # Try to use thinking config if available (newer API versions)
                    if hasattr(types, 'ThinkingConfig'):
                        generation_config = types.GenerationConfig(
                            thinking_config=types.ThinkingConfig(
                                thinking_budget=-1,
                                include_thoughts=True
                            )
                        )
                        print("[V] Using advanced thinking configuration")
                    else:
                        # Fallback to basic generation config
                        generation_config = types.GenerationConfig(
                            temperature=0.7,
                            top_p=0.9,
                            max_output_tokens=2048
                        )
                        print("[W] ThinkingConfig not available, using basic config")
                except (AttributeError, TypeError) as e:
                    print(f"[W] Advanced thinking config not available, using basic config: {e}")
                    if types:
                        generation_config = types.GenerationConfig(
                            temperature=0.7,
                            top_p=0.9,
                            max_output_tokens=2048
                        )
            else:
                print("[I] Using default model configuration")

            self.model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
                generation_config=generation_config
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
            if PACKAGE_TYPE == "google-genai":
                # For google-genai package - use simpler format
                # Combine system instruction with user prompt
                full_prompt = f"{self.system_instruction}\n\nUser Request: {prompt}"
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        {"role": "user", "parts": [{"text": full_prompt}]}
                    ]
                )
                return response.candidates[0].content.parts[0].text
            else:
                # For google-generativeai package
                response = self.model.generate_content(prompt)
                
                # Handle different response formats
                if hasattr(response, 'text') and response.text:
                    return response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    return response.candidates[0].content.parts[0].text
                else:
                    return "No response generated"
                    
        except Exception as e:
            return f"An error occurred while generating the report: {e}"

    def predict_next_period(self, latest_data_df):
        """
        Menganalisis data terbaru dan menghasilkan prediksi untuk periode berikutnya.
        """
        # Ubah DataFrame menjadi format teks yang lebih mudah dibaca
        data_str = latest_data_df.to_string(index=False)
        
        # Dapatkan periode terakhir dan hitung periode berikutnya
        try:
            last_period = int(latest_data_df['Period'].iloc[-1])
            next_period = last_period + 1
        except (ValueError, IndexError):
            next_period = "berikutnya"

        prompt = f"Berdasarkan data terbaru ini:\n{data_str}\n\nLakukan analisis dan berikan prediksi untuk periode {next_period}."
        
        try:
            if PACKAGE_TYPE == "google-genai":
                # For google-genai package - use simpler format
                # Combine system instruction with user prompt
                full_prompt = f"{self.system_instruction}\n\nUser Request: {prompt}"
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        {"role": "user", "parts": [{"text": full_prompt}]}
                    ]
                )
                answer = response.candidates[0].content.parts[0].text
                return f"--- PREDICTION ---\n{answer}"
            else:
                # For google-generativeai package
                response = self.model.generate_content(prompt)
                
                # Handle different response formats
                if hasattr(response, 'candidates') and response.candidates:
                    thoughts = ""
                    answer = ""
                    
                    try:
                        # Try to parse thinking parts if available
                        for part in response.candidates[0].content.parts:
                            if not part.text:
                                continue
                            if hasattr(part, 'thought') and part.thought:
                                thoughts += part.text
                            else:
                                answer += part.text
                        
                        if thoughts:
                            return f"--- THOUGHTS ---\n{thoughts}\n\n--- PREDICTION ---\n{answer}"
                        else:
                            return f"--- PREDICTION ---\n{answer if answer else response.text}"
                            
                    except AttributeError:
                        # Fallback to simple text response
                        return f"--- PREDICTION ---\n{response.text}"
                else:
                    return f"--- PREDICTION ---\n{response.text}"
                
        except Exception as e:
            return f"Terjadi kesalahan saat membuat prediksi: {e}"

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
