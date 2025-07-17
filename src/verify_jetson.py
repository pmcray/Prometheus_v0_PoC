import os
import google.generativeai as genai
import sys

def verify_gemini():
    """
    Verifies the Gemini API setup by reading an API key from an environment
    variable, configuring the API, and making a simple test call.
    """
    print("--- Starting Jetson Environment Verification ---")

    # 1. Get API Key from environment variable
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)
    print("Successfully read GEMINI_API_KEY environment variable.")

    # 2. Configure the Gemini API
    try:
        genai.configure(api_key=api_key)
        print("Gemini API key configured successfully.")
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        sys.exit(1)

    # 3. Call the API
    try:
        print("Making a test call to the Gemini API...")
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello, world! This is a test from a Jetson Nano container.")
        
        print("\nVerification successful! Response from Gemini:")
        print(response.text)
        print("\n--- Verification Complete ---")
    except Exception as e:
        print(f"An error occurred during API call: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_gemini()
