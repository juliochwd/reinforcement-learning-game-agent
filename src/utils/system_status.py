import sys
import os
import subprocess

def main():
    """
    Checks the system status and environment.
    """
    print("Python Environment:")
    if os.path.exists("venv_aipredict/Scripts/python.exe"):
        print("[V] Virtual environment: READY")
        subprocess.run(["venv_aipredict/Scripts/python.exe", "--version"])
        print("\nKey packages:")
        packages = ['selenium', 'seleniumwire', 'customtkinter', 'pandas', 'pyyaml', 'google-genai', 'cryptography']
        for pkg in packages:
            try:
                __import__(pkg.replace('-', '_'))
                print(f'[V] {pkg}: INSTALLED')
            except ImportError:
                print(f'[X] {pkg}: MISSING')
    else:
        print("[X] Virtual environment: NOT FOUND")
        print("Please run option 4 (Initial Setup) first.")

    print("\n[K] Credentials Status:")
    if os.getenv('PHONE_NUMBER'):
        print("[V] Phone number: CONFIGURED")
    else:
        print("[X] Phone number: NOT SET")
    if os.getenv('PASSWORD'):
        print("[V] Password: CONFIGURED")
    else:
        print("[X] Password: NOT SET")
    if os.getenv('GEMINI_API_KEY'):
        print("[V] Gemini API key: CONFIGURED")
    else:
        print("(!) Gemini API key: NOT SET (AI features disabled)")

    print("\n[F] Directory Structure:")
    for d in ['data', 'logs', 'backup', 'src', 'venv_aipredict']:
        if os.path.exists(d):
            print(f"[V] {d}: EXISTS")
        else:
            print(f"[X] {d}: MISSING")

    print("\nNetwork and Dependencies:")
    try:
        subprocess.run(["ping", "-n", "1", "google.com"], check=True, capture_output=True)
        print("[V] Internet connection: AVAILABLE")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[X] Internet connection: UNAVAILABLE")

if __name__ == "__main__":
    main()
