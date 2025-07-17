
import subprocess
import os

class EvaluatorAgent:
    def evaluate(self, new_code, original_code, test_file_path, original_file_path):
        """
        Evaluates the new code by running unit tests.
        """
        print("EvaluatorAgent: Received new code for evaluation.")
        
        # Create a temporary file for the new code
        temp_file_path = "temp_new_code.py"
        with open(temp_file_path, "w") as f:
            f.write(new_code)
            
        # To run the tests, we need to make sure the test file can import the new code.
        # We'll create a temporary test file that imports from the temp file.
        
        with open(test_file_path, 'r') as f:
            test_code = f.read()
            
        # This is a bit of a hack. We're replacing the import of the original file
        # with an import of our temporary file. This is fragile and depends on the
        # name of the original file.
        original_module_name = os.path.basename(original_file_path).replace('.py', '')
        temp_module_name = temp_file_path.replace('.py', '')
        
        modified_test_code = test_code.replace(f'from .{original_module_name}', f'from {temp_module_name}')
        
        temp_test_file_path = "temp_test_file.py"
        with open(temp_test_file_path, 'w') as f:
            f.write(modified_test_code)

        print(f"EvaluatorAgent: Running tests from {temp_test_file_path}...")
        try:
            result = subprocess.run(["pytest", temp_test_file_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("EvaluatorAgent: Tests passed!")
                return True, result.stdout
            else:
                print("EvaluatorAgent: Tests failed.")
                print(result.stdout)
                print(result.stderr)
                return False, result.stdout + "\n" + result.stderr
        finally:
            # Clean up temporary files
            os.remove(temp_file_path)
            os.remove(temp_test_file_path)

