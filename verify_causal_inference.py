
import os
import logging
import json
import time
from prometheus import *
from prometheus.experiment_orchestrator import ExperimentOrchestrator
from prometheus.results_synthesizer import ResultsSynthesizer
from prometheus.tools import CausalGraphTool

API_KEY = os.environ.get('GOOGLE_API_KEY')
os.environ['GOOGLE_API_KEY'] = API_KEY
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

planner = PlannerAgent()
hypotheses = planner.generate_hypotheses('Synthesize molecule D')
orchestrator = ExperimentOrchestrator()

def new_mix(self, c1, c2):
    if {c1, c2} == {'A', 'C'}:
        self.state['D'] = 100
    else:
        self.state['D'] = 0
    return self.state

ToyChemistrySim.mix = new_mix

results = orchestrator.run_parallel_experiments(hypotheses)
causal_tool = CausalGraphTool()
synthesizer = ResultsSynthesizer(causal_tool)
causal_graph = synthesizer.analyze_results(results)

knowledge_agent = KnowledgeAgent(api_key=API_KEY, performance_logger=None, pdf_tool=None)
knowledge_agent.update_causal_rules(causal_graph)
assert 'mix_A_C' in knowledge_agent.get_causal_rules()[0]
