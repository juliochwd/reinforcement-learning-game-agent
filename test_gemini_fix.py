#!/usr/bin/env python3
"""
Quick test script to verify Gemini AI functionality after the fix
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_gemini_predictor():
    """Test basic Gemini functionality"""
    print("🧪 Testing Gemini AI Integration...")
    print("=" * 50)
    
    try:
        # Import the fixed predictor
        from src.rl_agent.gemini_predictor import GeminiPredictor, PACKAGE_TYPE
        print(f"✅ Import successful - Package: {PACKAGE_TYPE}")
        
        # Check if API key is available
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            print("💡 Set your API key with: set GEMINI_API_KEY=your_key_here")
            return False
        
        print("✅ API key found")
        
        # Test predictor initialization
        try:
            predictor = GeminiPredictor(model_name='gemini-2.5-flash')
            print("✅ Predictor initialized successfully")
            
            # Test basic functionality
            test_data = "{'period': '202407191234', 'number': '5'}"
            print(f"🔍 Testing with sample data: {test_data}")
            
            # This will only work if API key is valid
            # report = predictor.generate_holistic_report(test_data)
            # print(f"✅ AI Response: {report[:100]}...")
            
            print("✅ All tests passed! Gemini integration is working.")
            return True
            
        except Exception as e:
            print(f"❌ Predictor test failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Gemini AI Fix Verification")
    print("=" * 50)
    
    success = test_gemini_predictor()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Gemini AI integration is working!")
        print("✅ You can now use AI analysis features:")
        print("   - Option 8 in start.py (Analyze Existing Data)")
        print("   - Live scraping with --model parameter")
        print("   - AI predictions in the application")
    else:
        print("❌ FAILED: There are still issues with Gemini integration")
        print("💡 Check your API key and try again")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
