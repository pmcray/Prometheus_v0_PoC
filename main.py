
import os
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent

# This is a placeholder for where you would securely get your API key
# For this example, we're retrieving it from an environment variable
# In a real-world scenario, use a secret manager.
API_KEY = os.environ.get("GOOGLE_API_KEY", "***REMOVED***")

def main():
    # 1. Instantiate Agents
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY)
    evaluator = EvaluatorAgent()

    # Define the toy problem files
    original_file_path = "toy_problem/inefficient_sort.py"
    test_file_path = "toy_problem/test_inefficient_sort.py"

    # 2. Define Goal
    goal = "Refactor inefficient_sort.py for better time complexity"

    # 3. PlannerAgent creates a plan
    instruction = planner.plan(goal)

    # 4. CoderAgent generates new code
    new_code, original_code = coder.code(original_file_path, instruction)
    print("\\n--- Generated Code ---")
    print(new_code)
    print("----------------------\\n")

    # 5. EvaluatorAgent runs tests
    success, output = evaluator.evaluate(new_code, original_code, test_file_path, original_file_path)

    # 6. Print final result
    print("\\n--- Evaluation Result ---")
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed.")
    print(output)
    print("--------------------------")


if __name__ == "__main__":
    main()
