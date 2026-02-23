import os
import logging
from src.health_simulator import HealthSimulator
import google.generativeai as genai

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")
genai.configure(api_key=API_KEY)

def main():
    logging.info("--- Verifying Causal Reasoning Benchmark ---")
    
    # 1. Generate the data
    simulator = HealthSimulator()
    simulator.generate_data()
    
    # 2. Define the benchmark task
    question = "If we were to intervene and force a person with a poor diet to stop eating ice cream, would their health improve?"
    
    # 3. Ask a standard LLM
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Based on the health_data.csv dataset, answer the following question:\n\n{question}"
    response = model.generate_content(prompt)
    
    logging.info(f"Benchmark Question: {question}")
    logging.info(f"Standard LLM Answer: {response.text.strip()}")

if __name__ == "__main__":
    main()
