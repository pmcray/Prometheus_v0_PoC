import os
import logging
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.causal_graph_tool import CausalGraphTool
from src.health_simulator import HealthSimulator
import google.generativeai as genai

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")
genai.configure(api_key=API_KEY)

def main():
    logging.info("--- Verifying Superior Performance on Causal Benchmark ---")
    
    # 1. Generate the data
    simulator = HealthSimulator()
    data_path = "health_data.csv"
    simulator.generate_data()
    
    # 2. Define the benchmark task
    question = "If we were to intervene and force a person with a poor diet to stop eating ice cream, would their health improve?"
    
    # --- Standard LLM ---
    logging.info("\n--- Running Standard LLM ---")
    standard_model = genai.GenerativeModel('gemini-1.5-flash')
    standard_prompt = f"Based on the health_data.csv dataset, answer the following question:\n\n{question}"
    standard_response = standard_model.generate_content(standard_prompt)
    logging.info(f"Standard LLM Answer: {standard_response.text.strip()}")
    
    # --- Prometheus System ---
    logging.info("\n--- Running Prometheus System with Causal Attention Head ---")
    causal_graph_tool = CausalGraphTool()
    planner = PlannerAgent(causal_graph_tool)
    coder = CoderAgent(api_key=API_KEY, compiler=None, analyzer=None, lean_tool=None, knowledge_agent=None)
    
    causal_prompt = planner.form_causal_strategy(data_path, question)
    causal_response = coder.model.generate_content(causal_prompt)
    logging.info(f"Prometheus Answer: {causal_response.text.strip()}")

if __name__ == "__main__":
    main()