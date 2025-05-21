# from openai import OpenAI

# client = OpenAI(
#     api_key="sk-42k6rKR5EFWxM2xlFb6bB5Da20Df45FbA56c5c6aDd834dEd",
#     base_url="https://api.xty.app/v1",
# )
# MODEL_NAME = "gpt-4o-mini"
# prompt = "你好"
# messages = [{"role": "user", "content": prompt}]

# resp = client.chat.completions.create(model=MODEL_NAME, messages=messages)
# answer = resp.choices[0].message.content
# print(answer)

# from Search.config import API_KEY

# print(API_KEY["Google"])
# SmartCADReportGenerator/test.py

# C:\Users\13004\Desktop\LAB\CG\PJ3\update\test.py

import sys
import os

# Corrected import:
from config1 import API_KEY  # Imports API_KEY directly from config1.py
from main import run_assistant, check_config # Imports from your refactored main.py
from utils import app_logger # Imports from your utils.py

def run_application_test():
    app_logger.info("--- Starting Test Execution of SmartCADReportGenerator ---")
    print("--- Starting Test Execution of SmartCADReportGenerator ---")

    # 1. Check configuration first
    if not check_config():
        error_msg = "TEST_ERROR: API key configuration is invalid or incomplete in config1.py. Please configure them before running the test."
        app_logger.critical(error_msg)
        print(error_msg)
        print("--- Test Execution Aborted ---")
        return

    app_logger.info("Configuration check passed. Attempting to run the full assistant workflow...")
    print("Configuration check passed. Attempting to run the full assistant workflow interactively...")
    
    try:
        # This will run the interactive version where you'll be prompted for input.
        run_assistant()
        
        success_msg = "--- Test Execution Completed Successfully (Interactive Mode) ---"
        app_logger.info(success_msg)
        print(success_msg)
        print("Check 'app.log' for detailed execution logs.")
        
    except Exception as e:
        error_msg = f"An unexpected error occurred during the test execution of run_assistant: {e}"
        app_logger.exception(error_msg) # Log with stack trace
        print(error_msg)
        print("--- Test Execution Failed ---")

if __name__ == "__main__":
    # Example: You can uncomment this to verify API_KEY access if needed during debugging
    # print(f"Test access to DEER_API_KEY (first 5 chars from test.py): {API_KEY.get('DEER_API_KEY', '')[:5]}...")
    
    run_application_test()