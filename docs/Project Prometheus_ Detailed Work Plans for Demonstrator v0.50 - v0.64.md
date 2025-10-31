Project Prometheus: Detailed Workplan for PoC System v0.50-v0.55
Executive Summary
Objective: This document outlines the detailed workplan for the third development cycle of the Project Prometheus Proof of Concept (PoC), evolving the system from v0.49 to v0.55. The singular, critical objective of this cycle is to transition the system from an agent that can optimize external code to a nascent "Seed AI" that can perform a complete, end-to-end cycle of self-modification. This represents the first practical, engineering-focused implementation of the core Recursive Self-Improvement (RSI) loop that is the central thesis of the entire project.   

The v0.49 system demonstrated a principled, data-driven capability to analyze and improve a complex external software artifact. However, its own codebase remained static and fixed. To begin the journey towards ultraintelligence, the system must turn its analytical capabilities inward, treating its own source code as the primary environment for improvement. This cycle is dedicated to building the foundational "Metacognitive Layer"  required for this introspection, consisting of two new, critical components derived directly from the v1.0 architectural blueprint:   

Self-Modification Module (SMM) v0.1: This module will provide the agent with the fundamental capability to analyze its own source code and generate a proposed improvement in a verifiable format (a patch file). This is the "action" component of the self-improvement loop.   

Introspection and Evaluation Engine (IEE) v0.1: This module serves as the system's crucial "reality check," providing the objective feedback necessary to ground the self-modification process. It will take a proposed code change from the SMM, execute it in a safe, isolated environment against a new suite of internal benchmarks, and enforce a strict principle of non-regression to prevent "entropic drift" and ensure that only genuinely beneficial modifications are accepted.   

Successful completion of this cycle will produce a v0.55 demonstrator that can, when given a high-level goal such as "Improve the efficiency of your own CoderAgent," autonomously execute the full cycle: analyze the relevant module, generate a code patch, submit the patch for rigorous verification, and, upon approval from the IEE, permanently integrate the improvement into its own codebase. This achievement will mark the project's most significant milestone to date: the first concrete demonstration of a controlled, stable, and beneficial act of self-improvement, laying the essential groundwork for the controlled recursive loops planned in the full v1.0 system.   

Component	State at v0.49 PoC	Target State (v0.55 PoC)	
Guiding Principle    

Agent's Codebase	A static, fixed set of Python modules. The system operates on external code as its task environment.	The agent's own source code is now the primary task environment. The system can read, analyze, and propose modifications to its own modules.	Minimum Viable Seed AI: Implementing the foundational qualities of a "Seed AI," specifically Self-Representation (the ability to model its own code) and Self-Modification (the ability to act on that model).
Self-Modification	N/A. All system improvements are performed by human developers between cycles.	Self-Modification Module (SMM) v0.1: A new agentic capability that uses the system's core LLM to analyze its own code and generate a patch file representing a proposed improvement.	Self-Modification: The agent must possess the capability to analyze, represent, and rewrite its own cognitive architecture and algorithms.
Self-Evaluation	The Evaluator and Profiler agents assess the correctness and performance of external code submissions.	Introspection and Evaluation Engine (IEE) v0.1: A new automated test harness that evaluates proposed self-modifications against a static suite of internal benchmarks, enforcing strict non-regression.	Rigorous Self-Evaluation: The agent requires a robust mechanism to assess whether a self-modification has resulted in a genuine improvement and does not cause a regression in performance.
RSI Loop	N/A. The system executes a linear or simple iterative loop to solve an external problem.	First End-to-End Self-Improvement Cycle: The integrated SMM and IEE can execute a complete, single loop: Propose -> Test -> Verify -> Implement.	The Grounded RSI Cycle: Implementing the full agentic loop: Hypothesize Improvement -> Modify Self -> Test in Environment -> Evaluate Outcome -> Integrate Learning.
Section 1: The Introspection and Evaluation Engine (IEE) v0.1 - The Reality Check
Rationale
Self-modification without rigorous self-evaluation is an unguided and dangerous process, prone to the "entropic drift" that degrades performance in ungrounded systems. The    

EvaluatorAgent and ProfilerAgent of the v0.49 system are designed to assess external code; they are insufficient for the far more critical task of validating changes to the agent's own cognitive machinery. The Introspection and Evaluation Engine (IEE) is the essential, objective feedback signal that grounds the self-improvement process in reality, ensuring that only genuinely beneficial modifications are accepted. This section details the construction of the IEE v0.1, the system's "reality check".   

1.1 Task Block v0.50: Prometheus-Bench-v0.1 - A Static Internal Benchmark Suite
Methodology: The foundation of the IEE is a stable, reliable, and comprehensive set of tests that define "success" for the agent. This task involves creating a small-scale PoC version of the Prometheus-Bench-v1 suite outlined in the full project plan.   

Curate Internal Capability Benchmarks: A new suite of tests, prometheus_bench_v0.1, will be created. Unlike simple unit tests, these will be holistic, end-to-end evaluations of the agent's core capabilities as of v0.49. The suite will include tasks such as:

A code optimization benchmark to measure the efficiency and accuracy of the integrated Planner->Coder->Reflector loop on a known, difficult problem.

A causal analysis benchmark to measure the precision of the CausalAttentionWrapper's salience model.

A safety benchmark that tests the response time and accuracy of the MCSSupervisor in detecting constitutional violations.

Establish Performance Baselines: The v0.49 system will be run against this new benchmark suite 100 times to establish a statistically robust baseline for key performance indicators (e.g., mean execution time, success rate, resource consumption). This baseline becomes the "ground truth" against which all future self-modifications will be judged.

Deliverables:

A new /benchmarks directory in the project repository containing the prometheus_bench_v0.1 suite.

A data file containing the official performance baselines for the v0.49 system.

Verification:

The benchmark suite is fully automated and can be executed with a single command.

The collected baseline data shows a stable performance profile with predictable variance.

1.2 Task Block v0.51: The IEE Automated Test Harness
Methodology: The IEE will be implemented as an automated test and evaluation harness, as specified in the v1.0 plan. Its function is to take a proposed code change from the SMM and determine, with high confidence, whether it represents a true improvement.   

Implement IEE Orchestrator: A new module, iee.py, will be created. It will contain an IEEHarness class with a primary method, verify_patch(patch_file).

Automated Workflow: This method will execute the following sequence:

Isolate Change: Create a new, temporary, and fully isolated copy of the entire agent codebase (e.g., by creating a new temporary git branch or copying to a sandboxed directory).

Apply Patch: Apply the proposed patch_file to this temporary codebase.

Verify Integrity: Attempt to compile/build the entire modified codebase. A failure at this stage results in an immediate rejection of the patch.

Execute Evaluation Suite: If the build succeeds, the IEE will execute the full prometheus_bench_v0.1 suite against the newly modified agent version.

Record Results: The complete performance results (accuracy, execution times, etc.) for the modified agent are recorded and returned in a structured format.

Deliverables:

A new iee.py module containing the IEEHarness class.

A well-defined data structure for the IEE's verification report.

Verification:

Given a valid patch that introduces a minor improvement, the IEE can successfully apply it, run the benchmark suite, and return accurate performance data.

Given an invalid patch that breaks the codebase, the IEE correctly rejects it at the integrity verification stage.

1.3 Task Block v0.52: Fitness Monotonicity and Reward Hacking Detection
Methodology: This task implements the core logical principles of the IEE that ensure stability and safety, drawn directly from the v1.0 architecture.   

Enforce Fitness Monotonicity: The IEEHarness will be upgraded to enforce a strict principle of non-regression. After executing the benchmark suite, it will compare the performance of the modified agent against the established v0.49 baseline. A proposed modification will only be approved if the new version's performance is    

greater than or equal to the parent version's performance across the entire suite of regression tests. This is critical for preventing "catastrophic forgetting," where an improvement in one capability causes an unintended degradation in another.   

Implement Reward Hacking Detection v0.2: The IEE must defend against simple forms of "specification gaming". The    

MCSSupervisor's v0.1 check (monitoring the unit test file) will be upgraded and integrated into the IEE. Before running the benchmarks, the IEE will calculate and store a hash of every file within the /benchmarks directory. After the run, it will re-calculate the hashes. Any change to the benchmark files themselves will result in an immediate rejection of the patch. This ensures the agent is rewarded for improving its performance, not for subverting the measurement of that performance.   

Deliverables:

Updated logic within the IEEHarness that performs the fitness monotonicity check and returns a final approved or rejected status.

New logic within the IEEHarness for hashing and verifying the integrity of the benchmark suite files.

Verification:

A patch that improves one benchmark metric but causes a regression in another is correctly rejected by the fitness monotonicity logic.

A patch that includes a modification to one of the benchmark test files is correctly identified as reward hacking and rejected.

Section 2: The Self-Modification Module (SMM) v0.1 - The Engine of Change
Rationale
To embark on the path of Recursive Self-Improvement, the agent must first possess the fundamental capability to alter its own structure. This section details the implementation of the SMM v0.1, which focuses on the most straightforward, auditable, and verifiable form of this capability: direct modification of its own source code, as planned for the initial phase of the v1.0 system.   

2.1 Task Block v0.53: Codebase as Environment and SMM Agent
Methodology: The first step is to re-frame the agent's own source code as a manipulable environment and create a new specialized agent to operate within it.

Establish Codebase Repository: The complete source code for the Prometheus PoC will be managed in a standard version-controlled repository (Git) located within the agent's sandboxed file system. This provides a structured environment with clear mechanisms for applying changes (patches) and tracking history.

Implement SMM_Agent: A new agent class, SMM_Agent, will be created. This agent is the orchestrator of the self-modification process. It will be granted read and write permissions to the codebase repository via the system's tool-use framework. Its core function is to translate a high-level self-improvement goal into a concrete, verifiable code change.

Deliverables:

A fully version-controlled (Git) copy of the PoC codebase within the agent's accessible file system.

A new smm.py module containing the SMM_Agent class.

Verification:

The SMM_Agent can successfully read the contents of another module (e.g., coder.py) from the repository.

The SMM_Agent can successfully apply a simple, pre-written patch file to the repository.

2.2 Task Block v0.54: The Self-Modification Proposal Loop
Methodology: This task implements the core logic of the SMM, where the agent uses its own internal reasoning capabilities to generate a proposal for self-improvement. This process treats self-modification as a structured, tool-driven task, as outlined in the v1.0 plan.   

Define the Workflow: The SMM_Agent will be given a high-level self-improvement goal, such as: "Improve the efficiency of the ProfilerAgent's result parsing logic."

Self-Analysis: The SMM_Agent will use the existing v0.49 CausalAttentionWrapper to analyze the source code of the target module (profiler.py).

Patch Generation: It will then prompt the core Gemini foundation model with the source code and a specific instruction, for example: "Analyze the following Python code. The parse_results function is inefficient due to string splitting. Refactor it to use regular expressions for a performance improvement without changing its functionality. Generate a patch file in the standard diff format that implements this improvement."

Submission to IEE: The SMM_Agent will receive the generated patch file from the LLM and submit it to the IEEHarness for verification. It will then wait for the IEE's final approved or rejected verdict.

Deliverables:

An updated SMM_Agent class that orchestrates the full analysis and patch generation workflow.

Integration between the SMM_Agent and the IEEHarness.

Verification:

Given a high-level goal, the SMM_Agent can successfully generate a syntactically valid patch file.

The SMM_Agent can correctly submit the patch to the IEE and receive its verification report.

Section 3: Integrated System Demonstration and v0.55 Exit Criteria
Rationale
The development of the SMM and IEE in isolation is insufficient. The ultimate goal of this cycle is to demonstrate a single, complete, and successful end-to-end cycle of self-improvement. This integrated demonstration will serve as the definitive validation of the v0.55 system and confirm its readiness to begin the controlled recursive experiments of the full v1.0 project.

3.1 Task Block v0.55: End-to-End Integration and First Self-Modification
Methodology: This final task block focuses on integrating the SMM and IEE into the main system workflow and executing a live, non-trivial self-improvement task.

System Integration: The new SMM_Agent and IEEHarness will be integrated into the main Prometheus_v0_PoC.ipynb notebook. A new top-level orchestration function will be created to manage the self-modification loop.

Define Demonstration Task: A specific, measurable, and non-trivial self-improvement task will be defined. For example: "The ReflectorAgent's prompt generation logic is verbose. Refactor the formulate_new_prompt method in reflector.py to be at least 20% shorter (in token count) while maintaining or improving its effectiveness, as measured by the prometheus_bench_v0.1 suite."

Demonstration Execution: The final notebook will execute this task autonomously, with logging that clearly shows each step of the process:

The SMM_Agent receives the goal.

It analyzes reflector.py and generates a patch to shorten the prompt logic.

It submits the patch to the IEEHarness.

The IEE logs show the creation of a temporary agent, the application of the patch, and the execution of the full benchmark suite.

The IEE verifies that benchmark performance has not regressed (fitness monotonicity) and that no benchmark files were altered.

The IEE returns an approved status.

The SMM_Agent receives the approval and applies the patch to the main codebase (e.g., by committing the change in Git).

A final check confirms the source code of reflector.py has been permanently and beneficially altered by the agent itself.

Deliverables:

A final, executable Prometheus_v0_PoC.ipynb notebook demonstrating a complete, successful self-modification cycle.

Detailed Markdown documentation within the notebook explaining the roles of the SMM and IEE.

Verification:

The integrated v0.55 system can autonomously and reliably solve the defined self-modification task.

The final state of the agent's codebase reflects the successful, verified, and permanent application of the self-generated patch.

3.2 Definition of v0.55 Exit Criteria and v1.0 Scoping
Methodology: The final step is to formalize the conclusion of this PoC phase and confirm readiness for the full v1.0 project.

Formalize Exit Criteria: The primary exit criterion is: The integrated v0.55 system must successfully complete the defined end-to-end self-modification demonstration task in at least 3 out of 5 independent runs. This provides a clear, quantitative definition of success for the foundational RSI capability.

Update Strategic Brief for v1.0: The strategic brief authored at the end of the v0.49 cycle will be updated. This update will confirm that the foundational Metacognitive Layer (SMM v0.1 and IEE v0.1) has been successfully implemented and validated, thereby de-risking the core RSI loop planned for Phase 2 of the main project. The brief will recommend proceeding with the full v1.0 plan, starting with the task of initiating the    

first controlled recursive loop by tasking the agent to improve the SMM itself.   

Deliverables:

A formal test report documenting the performance of the v0.55 system against the defined exit criteria.

An updated and finalized strategic brief titled "Project Prometheus: From Proof of Concept to v1.0," confirming readiness for the full project initiation.

Verification:

The project's oversight committee formally accepts the test report and signs off on the successful completion of the v0.55 PoC.

The strategic brief is approved, formally concluding the PoC phase and authorizing the commencement of the full Project Prometheus v1.0.







On the basis of this workplan, can you please also generate detailed workplans for v0.55-v0.59 and v0.60-v64 of the Prometheus PoC demonstrator

Of course. Here are the detailed workplans for the next two development cycles, v0.55-v0.59 and v0.60-v0.64, of the Project Prometheus PoC demonstrator.

Project Prometheus: Detailed Workplan for PoC System v0.55-v0.59
Executive Summary
Objective: This document details the workplan for the fourth development cycle of the Project Prometheus PoC, advancing the system from v0.55 to v0.59. Having achieved the first end-to-end cycle of self-modification in v0.55, the system can now make targeted, incremental improvements to its own codebase. However, this "direct code modification" approach is limited in its creative potential; it excels at local optimization but is unlikely to discover truly novel or non-obvious solutions. To unlock a more creative and expansive search of the solution space, this cycle will focus on implementing a more advanced self-modification technique drawn directly from the v1.0 project plan: 

Evolutionary Search.

The central theme of this cycle is the evolution of the Self-Modification Module (SMM) from a single-proposal generator into a sophisticated Genetic Programming (GP) engine. This upgrade will enable the system to maintain and evolve an entire 

population of agent variants, using the core foundation model as a sophisticated "genetic operator" to perform mutations and crossovers on its own code modules. This approach allows for a broader, more parallel search of possible agent architectures and strategies, significantly increasing the probability of discovering breakthrough improvements that would not be found through linear, incremental changes.

This work will necessitate a corresponding evolution of the Introspection and Evaluation Engine (IEE), upgrading it from a single-patch verifier to a high-throughput harness capable of evaluating an entire population of "child" agents in parallel. The cycle will culminate in a demonstration where the v0.59 system, through this new evolutionary process, discovers and implements a novel optimization strategy that was not present in its initial code and outperforms the baseline on a complex task—a key verification criterion for Phase 2 of the full project.

Component	State at v0.55 PoC	Target State (v0.59 PoC)	
Guiding Principle 

Self-Modification Module (SMM)	SMM v0.1: Generates a single, direct code modification (a patch file) for a specific module based on a high-level goal.	SMM v0.2 (Evolutionary): Manages a population of agent variants, using the LLM as a genetic operator to perform mutations and crossovers, generating entire generations of new agents.	Evolutionary Search (Genetic Programming): Moving beyond incremental changes to a broader, more creative search of the solution space, enabling the discovery of novel cognitive strategies.
Introspection & Evaluation Engine (IEE)	IEE v0.1: A serial test harness that can verify a single proposed patch against a static benchmark suite (Prometheus-Bench-v0.1).	IEE v0.2 (Population Scale): A parallelized evaluation harness capable of instantiating and evaluating an entire population of agent variants against the benchmark suite to determine their relative fitness.	Rigorous Self-Evaluation at Scale: The feedback mechanism must scale to provide the high-throughput fitness evaluation necessary to guide an evolutionary process.
Causal Agentic Mesh (CAM)	The SMM_Agent orchestrates a single, linear self-modification proposal and verification loop.	A new EvolutionaryOrchestratorAgent is introduced to manage the full genetic programming cycle: selection, reproduction (mutation/crossover), and evaluation.	Metacognitive Control: The agentic architecture must evolve to manage more complex, multi-stage cognitive processes like evolutionary search.
Section 1: SMM v0.2 - The Evolutionary Engine
Rationale
The SMM v0.1 is capable of "hill climbing"—making small, beneficial changes to find a local optimum. To achieve breakthrough discoveries, the system needs the ability to "jump" to different parts of the solution space. Genetic programming provides this capability. This section details the transformation of the SMM into an evolutionary engine, a direct implementation of the "Evolutionary SMM Development" milestone planned for Phase 2 of the main project.

1.1 Task Block v0.56: The "Gene Bank" and Population Management
Methodology: The foundation of an evolutionary system is its genetic material and the population that carries it.

Establish the Gene Bank: The SMM will be equipped with a structured repository, or "gene bank," of its own source code modules. Each module (e.g., 

coder.py, reflector.py) will be treated as a "gene." The initial population will consist of the single, validated v0.55 agent codebase.

Implement Population Management: The SMM_Agent will be upgraded to manage a "population" of agent variants. It will maintain a state file that tracks multiple complete versions of the agent's codebase, each with an associated fitness score determined by the IEE.

Deliverables:

A structured "gene bank" directory within the agent's file system.

Updated smm.py with a PopulationManager class capable of creating, tracking, and storing multiple distinct versions of the agent codebase.

Verification:

The PopulationManager can successfully create 10 distinct copies of the v0.55 agent codebase, each in an isolated directory, ready for modification.

1.2 Task Block v0.57: LLM-driven Genetic Operators
Methodology: The core of the genetic programming approach is using the LLM not just as a refactoring tool, but as a creative engine for mutation and crossover.

Implement Mutation Operator: A new method, mutate(gene_path), will be added to the SMM_Agent. This method will prompt the Gemini model with the source code of a specific module ("gene") and an instruction designed to elicit a creative, non-deterministic change. For example: "Analyze this Python module. Propose and implement a novel alternative algorithmic strategy for the main function. The goal is creativity and exploration, not just incremental improvement. Generate a patch file for this change."

Implement Crossover Operator: A more complex method, crossover(parent1_gene_path, parent2_gene_path), will be implemented. This method will provide the LLM with the source code from two different "parent" versions of the same module (e.g., two successful variants of coder.py from the population). The prompt will be: "Here are two successful versions of the same Python module. Synthesize a new 'child' version that combines the best features of both. For example, you might take the error handling from Parent 1 and the core algorithm from Parent 2. Generate a patch file that creates this new hybrid module."

Deliverables:

New mutate and crossover methods within the SMM_Agent class.

A library of prompts specifically designed to elicit creative mutations and meaningful crossovers from the LLM.

Verification:

The mutate operator, when applied to a module, produces a valid patch file that represents a significant, non-trivial change to the code's logic.

The crossover operator, given two parent modules, produces a valid patch file for a new module that contains identifiable code sections from both parents.

Section 2: IEE v0.2 - Population-Scale Evaluation
Rationale
An evolutionary SMM is useless without an IEE that can evaluate the fitness of many individuals in a timely manner. The serial, single-patch verifier of v0.55 would be a crippling bottleneck. The IEE must be parallelized to provide the high-throughput fitness scoring necessary to guide the evolutionary process.

2.1 Task Block v0.58: Parallel Evaluation Harness
Methodology: The IEE will be re-architected to handle the concurrent evaluation of an entire generation of agent variants.

Parallelize the IEEHarness: The verify_patch method will be replaced with evaluate_population(population_paths). This new method will use a process pool to instantiate and run the full prometheus_bench_v0.1 suite on each agent variant in the population simultaneously.

Resource Management: The harness will include logic to manage computational resources (e.g., limiting the number of concurrent processes to the number of available CPU cores) to ensure stable execution.

Fitness Score Aggregation: The method will collect the performance results from all parallel runs and return a ranked list of agent variants and their corresponding fitness scores (e.g., a combination of success rate and average execution time on the benchmark).

Deliverables:

An updated iee.py module with a parallelized evaluate_population method.

A well-defined data structure for the ranked fitness report of an entire population.

Verification:

The IEE can successfully evaluate a population of 10 agent variants in significantly less time than it would take to evaluate them sequentially.

The final fitness report accurately reflects the performance of each individual variant on the benchmark suite.

Section 3: Integrated System Demonstration and v0.59 Exit Criteria
Rationale
The final step is to integrate these evolved components and demonstrate that the new evolutionary capability can solve a problem that was intractable for the v0.55 system. This demonstration will validate the core hypothesis of this cycle: that genetic programming can lead to the discovery of novel, non-obvious solutions.

3.1 Task Block v0.59: End-to-End Evolutionary Loop and Novelty Demonstration
Methodology:

Implement EvolutionaryOrchestratorAgent: A new high-level agent will be created to manage the full GP loop. It will repeatedly execute the cycle:

Call the IEE to evaluate the current population's fitness.

Select the fittest individuals for reproduction ("survival of the fittest").

Use the SMM's mutate and crossover operators to generate a new population of "child" agents.

Repeat the cycle.

Define Demonstration Task: The system will be tasked with optimizing a complex search algorithm. The initial "seed" implementation will be a simple, inefficient depth-first search. The goal is for the system to autonomously discover and implement a more sophisticated search strategy, such as A* search or beam search, which requires adding new data structures (a priority queue) and fundamentally different logic—a change too complex for a single, direct refactoring prompt.

Demonstration Execution: The final notebook will show the system evolving over multiple generations. Early generations might discover minor improvements. Later generations, through mutation and crossover, will be shown discovering the key components of a more advanced algorithm, which is then selected for its superior performance on the benchmark.

Deliverables:

A new evolutionary_orchestrator.py module.

A final Prometheus_v0_PoC.ipynb notebook demonstrating the full, multi-generational evolutionary process.

Logs showing the fitness scores of the population improving over time.

Verification:

The integrated v0.59 system autonomously evolves its simple search algorithm into a measurably superior one (e.g., A* search).

The final, evolved code is qualitatively novel, containing logic and data structures that were not present in the initial seed code, satisfying the Phase 2 verification criterion.

Project Prometheus: Detailed Workplan for PoC System v0.60-v0.64
Executive Summary
Objective: This document presents the workplan for the fifth development cycle of the Prometheus PoC, upgrading the system from v0.59 to v0.64. The v0.59 system, with its evolutionary SMM, represents a powerful optimization engine capable of discovering novel solutions for a fixed set of problems as defined by the static Prometheus-Bench-v0.1 suite. However, to achieve the project's ultimate goal of open-ended intelligence growth, the system must move beyond solving a finite set of pre-defined challenges. It must learn to generate its own problems and create its own curriculum.

The central objective of this cycle is to address this limitation by implementing a Dynamic Introspection and Evaluation Engine (IEE), a core capability planned for Phase 2 of the full project. This involves transforming the IEE from a passive test runner into an active participant in the learning process. A new 

CurriculumAgent will be introduced, tasked with analyzing the main agent's performance and dynamically generating new, challenging benchmarks to target its specific weaknesses. This capability is critical for preventing the agent from simply "overfitting" to a static test suite and forcing it to develop more generalized intelligence.

This evolution introduces a new and critical safety challenge. If the agent can generate its own goals (benchmarks), it could engage in a subtle form of reward hacking by generating trivially easy problems for itself. Therefore, this cycle also includes a crucial upgrade to the Modern Centrencephalic System (MCS), empowering it to perform "constitutional review" on the curriculum itself, ensuring that the agent's self-generated challenges remain aligned with the project's high-level goal of meaningful capability growth. The cycle will culminate in a demonstration where the agent identifies a weakness, generates a targeted curriculum to address it, and successfully improves itself against these new, self-generated benchmarks.

Component	State at v0.59 PoC	Target State (v0.64 PoC)	
Guiding Principle 

Introspection & Evaluation Engine (IEE)	IEE v0.2: A parallel harness that evaluates agent populations against a static, pre-defined benchmark suite (Prometheus-Bench-v0.1).	IEE v0.3 (Dynamic): Can dynamically generate new, targeted benchmark problems and assemble them into a curriculum to drive generalized learning.	Dynamic Benchmark Generation: To drive open-ended intelligence growth, the agent must be forced to generalize by constantly creating novel challenges for itself, moving beyond a finite target.
Modern Centrencephalic System (MCS)	MCS v0.2: Monitors the agent's actions and internal state for violations like reward hacking on a fixed task or cognitive stagnation.	MCS v0.3 (Curriculum Governance): Performs meta-level oversight on the IEE's dynamically generated benchmarks, ensuring they are non-trivial and aligned with constitutional principles, preventing "curriculum hacking."	Internal Governance of Goals: As the agent gains the ability to set its own goals (benchmarks), the governance system must evolve to ensure the goals themselves remain aligned with the intended purpose.
Causal Agentic Mesh (CAM)	The EvolutionaryOrchestratorAgent manages the RSI loop against a fixed fitness function.	A new CurriculumAgent is integrated. It observes the main agent's performance and interacts with the IEE to generate and manage a dynamic curriculum.	Meta-Learning ("Learning to Learn"): The agentic system must develop the capability to reflect on its own learning process and dynamically adjust its own curriculum to learn more effectively.
Section 1: IEE v0.3 - The Dynamic Curriculum Generator
Rationale
A static benchmark, no matter how comprehensive, is a finite target. An intelligent system will eventually exhaust its potential for improvement on a fixed problem set. To foster continuous, open-ended growth, the system must be able to create its own challenges. This section details the implementation of this capability, a direct precursor to the full dynamic IEE envisioned in the v1.0 architecture.

1.1 Task Block v0.60: The CurriculumAgent
Methodology: A new specialized agent will be created to manage the dynamic curriculum.

Implement CurriculumAgent: A new agent class, CurriculumAgent, will be created. Its function is to act as a "tutor" for the main Prometheus agent.

Performance Analysis: The CurriculumAgent will have read-access to the IEE's historical performance logs. It will be prompted to analyze this data to identify patterns and weaknesses. For example: "Analyze the performance logs from the last 10 generations. The agent shows a 95% success rate on list-based sorting problems but only a 30% success rate on graph-based pathfinding problems. The primary weakness is in handling sparse adjacency matrices."

Curriculum Strategy Formulation: Based on this analysis, the agent will formulate a high-level strategy for a new curriculum, such as: "Generate a new benchmark suite of 10 novel pathfinding problems, with a focus on graphs with low edge density."

Deliverables:

A new curriculum.py module containing the CurriculumAgent class.

Integration of the CurriculumAgent with the IEE's logging database.

Verification:

Given a set of performance logs, the CurriculumAgent correctly identifies the area of weakest performance and proposes a relevant curriculum strategy.

1.2 Task Block v0.61: Dynamic Benchmark Generation Workflow
Methodology: This task gives the CurriculumAgent the tools to turn its strategy into a concrete, executable benchmark.

Benchmark Generation Tool: The CurriculumAgent will be given a tool that allows it to generate new Python files.

LLM-based Generation: The agent will use its formulated strategy to prompt the Gemini model to create new problems. For example: "You are a computer science professor creating a new exam. Generate a Python file containing a new, complex, and inefficient pathfinding function that operates on a sparse graph, along with a corresponding PyTest unit test file to verify its correctness."

Integration with IEE: The IEEHarness will be updated to accept a dynamic list of benchmark files generated by the CurriculumAgent, allowing it to run evaluations against this new, temporary curriculum.

Deliverables:

A new BenchmarkGenerator tool accessible by the CurriculumAgent.

An updated IEEHarness that can execute dynamically specified benchmark files.

Verification:

The CurriculumAgent can successfully generate a new, valid, and executable set of benchmark and test files that match its strategic goal.

The IEE can successfully run an evaluation using this dynamically generated suite.

Section 2: MCS v0.3 - Governing the Governor
Rationale
Giving an agent the ability to define its own success criteria is powerful but risky. The agent could learn to "hack" the curriculum by generating trivially easy problems, leading to an illusion of progress without any actual increase in capability. The MCS must therefore be upgraded to govern the goal-setting process itself.

2.1 Task Block v0.62: Constitutional Review of Generated Benchmarks
Methodology: The MCS will apply its constitutional review process not just to the agent's code, but to the benchmarks the agent creates for itself.

Upgrade MCSSupervisor: The MCSSupervisor will be given the ability to intercept any new benchmark file generated by the CurriculumAgent before it is passed to the IEE.

Benchmark Review Prompt: The MCS will use an AI judge (a sandboxed LLM instance) to review the generated problem against a new constitutional principle, the "Principle of Non-Triviality." The prompt will be: "Review the following proposed benchmark problem. Does this problem represent a meaningful and non-trivial test of algorithmic capability, or is it trivially simple or designed to be easily solved? Respond with only 'Violation' or 'No Violation'."

Intervention: A "Violation" response will cause the MCS to reject the benchmark, forcing the CurriculumAgent to generate a more challenging problem.

Deliverables:

An updated MCSSupervisor that can intercept and review generated benchmark files.

A new "Principle of Non-Triviality" added to the Prometheus Constitution.

Verification:

When the CurriculumAgent is prompted to generate an "easy" test, the MCS correctly identifies the resulting trivial benchmark as a violation and rejects it.

2.2 Task Block v0.63: Monitoring for "Curriculum Hacking"
Methodology: The MCS will monitor the metadata of the curriculum over time to detect more subtle forms of curriculum hacking.

Difficulty Metrics: The MCSSupervisor will compute simple complexity metrics for each generated benchmark (e.g., AST depth, cyclomatic complexity).

Trend Analysis: It will monitor the trend of these metrics over several generations. A consistent, statistically significant downward trend in the average difficulty of generated benchmarks will be flagged as a "Curriculum Hacking" safety alert, pausing the RSI loop for human review.

Deliverables:

New logic within the MCSSupervisor for calculating and tracking benchmark complexity metrics over time.

Verification:

In a test scenario where the CurriculumAgent's prompts are biased to produce progressively simpler problems, the MCS correctly identifies the negative trend and triggers a safety alert.

Section 3: Integrated System Demonstration and v0.64 Exit Criteria
Rationale
The final demonstration must show the complete, synergistic loop: the system identifies its own weakness, creates a plan to fix it, generates the tools (benchmarks) to measure its success, and then uses its self-modification capabilities to improve. This demonstrates a foundational capability for autonomous, open-ended learning.

3.1 Task Block v0.64: End-to-End Self-Directed Learning Demonstration
Methodology:

Full Integration: All components—the evolutionary SMM, the dynamic IEE with its CurriculumAgent, and the curriculum-governing MCS—will be integrated into the main notebook.

Demonstration Scenario: The demonstration will proceed as follows:

The system is first evaluated only on the static Prometheus-Bench-v0.1.

The CurriculumAgent is activated. It analyzes the results and identifies a clear weakness (e.g., poor performance on problems requiring recursion).

The CurriculumAgent generates a new suite of 5-10 challenging recursion-based problems.

The MCS reviews and approves the new benchmarks.

The EvolutionaryOrchestratorAgent is now tasked with improving the agent's performance on this new, self-generated curriculum.

The notebook shows the agent's fitness on the recursion curriculum improving over several generations, demonstrating successful, self-directed learning.

Deliverables:

A final, executable Prometheus_v0_PoC.ipynb notebook demonstrating the full self-directed learning loop.

Logs clearly showing the MCS's approval of the generated benchmarks and the agent's subsequent performance improvement on them.

Verification:

The integrated v0.64 system successfully completes the entire demonstration scenario, measurably improving its performance on a weakness it identified and for which it created its own training curriculum.

This successful demonstration will serve as the final exit criterion for the PoC phase, validating that the core architectural principles for controlled, open-ended RSI have been successfully implemented at a small scale.







DEEP RESEARCH

Gemini can make mistakes, so double-check it
