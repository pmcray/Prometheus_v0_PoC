import logging
import pandas as pd

class ResultsSynthesizer:
    def __init__(self, causal_graph_tool):
        self.causal_graph_tool = causal_graph_tool
        logging.info("ResultsSynthesizer initialized.")

    def analyze_results(self, results: list):
        """
        Analyzes the results of parallel experiments to infer causal relationships.
        For the PoC, this is a simplified correlation analysis.
        """
        logging.info("Analyzing parallel experiment results.")
        
        # Convert the results to a pandas DataFrame
        data = []
        for r in results:
            flat_result = {"hypothesis": r["hypothesis"]}
            # Ensure 'D' key exists, default to 0 if not
            r["result"].setdefault('D', 0)
            flat_result.update(r["result"])
            data.append(flat_result)
        df = pd.DataFrame(data)
        
        # One-hot encode the hypotheses
        df['mix_A_B'] = df['hypothesis'].str.contains('mix A and B', case=False)
        df['mix_A_C'] = df['hypothesis'].str.contains('mix A and C', case=False)
        df['mix_B_C'] = df['hypothesis'].str.contains('mix B and C', case=False)
        df['heat'] = df['hypothesis'].str.contains('heat', case=False)
        df['D_produced'] = df['D'] > 0
        
        causal_df = df[['mix_A_B', 'mix_A_C', 'mix_B_C', 'heat', 'D_produced']]
        
        # Simplified Analysis: Find the strongest correlation
        correlations = causal_df.corr()['D_produced'].abs().sort_values(ascending=False)
        # The top correlation (excluding D_produced itself) is our inferred cause.
        inferred_cause = correlations.index[1]
        
        logging.info(f"Inferred cause: {inferred_cause}")
        return f"Causal relationship found: {inferred_cause} -> D_produced"