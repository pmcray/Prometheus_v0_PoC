Project Prometheus: Detailed Workplan for PoC System v0.65-v0.69
Executive Summary
Objective: This document outlines the workplan for the sixth development cycle of the Project Prometheus PoC, advancing the system from v0.64 to v0.69. The preceding cycles have successfully created a system capable of recursively improving its own performance within the narrow domain of its own code optimization. The singular objective of this new cycle is to break out of this specialized domain and demonstrate that the system's core Recursive Self-Improvement (RSI) loop can be leveraged to achieve competence in entirely new, unrelated problem spaces. This cycle will focus on    

generalization, tasking the agent not with solving a new problem directly, but with using its self-modification capabilities to build and evolve new, specialized "capability agents" for itself.   

The central theme is the transformation of Prometheus from a self-optimizing tool into a nascent "AGI factory." Instead of improving its existing CoderAgent, the system will be tasked with goals like "Achieve a winning record in the game of Draughts." To accomplish this, it must use its Self-Modification Module (SMM) and Introspection and Evaluation Engine (IEE) to evolve a new DraughtsAgent from a generic template. This requires a significant expansion of the IEE to support a universal benchmarking framework (   

Prometheus-Bench-v0.2) capable of evaluating performance in diverse domains like General Game Playing and conversational AI.

Successful completion of this cycle will produce a v0.69 demonstrator that, when presented with a novel task from a supported domain, can autonomously initiate an evolutionary process to create a specialized agent that achieves a quantitative measure of success in that task. This will validate that the Prometheus architecture is not merely a solution for code optimization but a general-purpose engine for automated capability generation, a critical step towards the project's long-term goal of open-ended intelligence.   

Component	State at v0.64 PoC	Target State (v0.69 PoC)	
Guiding Principle    

Task Domain	Self-modification of the agent's own codebase for performance improvement.	Generalization to classic AI domains, starting with General Game Playing (e.g., Draughts) and Conversational AI.	From Specialist to Generalist: Demonstrating that the RSI loop is a domain-general process for acquiring novel skills, not just optimizing existing ones.
Introspection & Evaluation Engine (IEE)	IEE v0.3 (Dynamic): Can dynamically generate new benchmarks for its own code optimization task.	IEE v0.4 (Universal): A universal benchmarking harness with a new, expanded suite (Prometheus-Bench-v0.2) and tool integrations to evaluate performance in disparate domains like game-playing and conversation.	Environmental Grounding: The agent's self-improvement must be grounded in objective, external feedback from the target problem environment.
Causal Agentic Mesh (CAM)	A CurriculumAgent generates new code optimization tasks for the EvolutionaryOrchestratorAgent.	A new GeneralistPlannerAgent decomposes high-level domain goals (e.g., "master chess") into a meta-task for the SMM: "Evolve a new agent that maximizes the fitness score on the chess benchmark."	Metacognitive Control: The agentic architecture must be capable of reasoning about its own capabilities and formulating plans to acquire new ones.
Section 1: IEE v0.4 - The Universal Benchmark Engine
Rationale
To generalize, the agent's "reality check" must also be generalized. The IEE's ability to evaluate performance is the bedrock of the entire RSI loop; without a reliable fitness signal from a new domain, no learning can occur. This section details the expansion of the IEE from a code-centric evaluator into a universal harness capable of measuring success across a variety of classic AI tasks.   

1.1 Task Block v0.65: Prometheus-Bench-v0.2 - The Generalist Benchmark Suite
Methodology: The static Prometheus-Bench-v0.1 suite will be deprecated as the primary evaluation tool and supplemented by a new, multi-domain suite.

General Game Playing (GGP) Suite: A set of benchmarks for two-player, perfect-information games will be created.

Environment: Integrate standard game logic engines (e.g., for Draughts, Chess).

Fitness Metric: The primary metric will be win rate over 1,000 games against a fixed-strength baseline opponent (e.g., a standard Minimax agent with a small search depth).

Conversational AI Suite: A benchmark for evaluating chatbot capabilities will be developed.

Task: The agent will be tasked with maintaining a coherent, helpful conversation on a specific topic for a set number of turns.

Fitness Metric: An LLM-as-judge framework will be implemented. A separate, sandboxed instance of Gemini will be used to score the conversation transcript based on criteria like coherence, helpfulness, and adherence to the persona, providing a quantitative fitness score.

Deliverables:

A new /benchmarks_v0.2 directory containing the GGP and Conversational AI evaluation suites.

A set of baseline opponent agents for the GGP suite.

A documented LLM-as-judge prompting framework for the Conversational AI suite.

Verification:

The new benchmark suites can be executed automatically and produce stable, repeatable fitness scores for baseline agents.

1.2 Task Block v0.66: IEE Tooling and Environment Integration
Methodology: The IEEHarness must be upgraded to manage these new, non-code environments.

Game Engine API: The IEE will be integrated with the game engines. It will be responsible for instantiating the game environment, loading the "candidate" agent being evaluated, loading the baseline opponent, executing a full game, and parsing the result (win/loss/draw).

Conversational Simulator: The IEE will use a simulation harness that feeds prompts to the candidate chatbot agent and captures its responses, assembling a full transcript for evaluation by the LLM-as-judge.

Parallelization for GGP: The evaluate_population method will be optimized to run hundreds of game simulations in parallel to gather statistically significant win-rate data for each generation of evolved agents.

Deliverables:

An updated iee.py module with new methods for executing GGP and Conversational AI benchmarks.

Secure API wrappers for interacting with game engines and the LLM-as-judge.

Verification:

The IEE can successfully take a candidate agent (initially, a simple random-move player), execute the full benchmark suite for it, and return an accurate fitness score.

Section 2: CAM v0.4 - The Generalist Orchestrator
Rationale
With a universal evaluator in place, the agentic mesh must be taught how to use it. The system's reasoning must be elevated from "how do I improve this code?" to "how do I acquire the skill to solve this new type of problem?" This requires a new meta-level planning capability.

2.1 Task Block v0.67: The DomainExpertAgent Template
Methodology: Instead of evolving its core code, the system will now evolve new, sandboxed agents from a template.

Create Generic Agent Template: A new, simple agent class, DomainExpertAgent, will be created. It will have a basic structure with methods like perceive(environment_state) and act(). Initially, the act() method will simply return a random valid action.

Evolutionary Target: This template file will become the "genome" that the SMM's evolutionary algorithm operates on. The goal of the RSI loop will be to evolve the logic within this template to create a high-performing specialist.

Deliverables:

A new domain_expert_agent.py module containing the generic agent template.

Verification:

An instance of the unmodified DomainExpertAgent can be successfully loaded by the IEE and achieves a near-zero fitness score on the GGP benchmark (as expected for a random player).

2.2 Task Block v0.68: The GeneralistPlannerAgent
Methodology: This new agent will act as the top-level strategic director, translating user goals into self-improvement directives.

Implement GeneralistPlannerAgent: This agent will replace the CurriculumAgent as the primary initiator of the RSI loop.

Meta-Task Decomposition: When given a high-level user goal like "Master the game of Draughts," the planner will not attempt to generate game moves. Instead, it will decompose this into a meta-task for the system. It will query the IEE to find the relevant benchmark (Prometheus-Bench-Draughts-v0.1) and then issue a directive to the EvolutionaryOrchestratorAgent: "Your objective is to evolve the DomainExpertAgent template. The fitness function is the score on the Prometheus-Bench-Draughts-v0.1 benchmark. Initiate the evolutionary process and report back when a variant achieves a fitness score greater than 0.8."

Deliverables:

A new generalist_planner.py module.

Updated orchestration logic that routes high-level user goals to this new planner.

Verification:

When given the prompt "learn to play chess," the GeneralistPlannerAgent correctly identifies the Prometheus-Bench-Chess-v0.1 benchmark and issues a correctly formatted evolutionary task to the SMM.

Section 3: Integrated System Demonstration (v0.69)
Rationale
The final task is to demonstrate the complete, end-to-end process of automated capability acquisition in a novel domain. This will provide the definitive validation that the Prometheus architecture can be used for general-purpose problem-solving.

3.1 Task Block v0.69: Demonstration of Automated Skill Acquisition
Methodology: The final notebook will showcase the full loop on the domain of General Game Playing, using Draughts as the target.

Demonstration Execution: The notebook will guide the user through the following autonomous process:

The user provides the high-level goal: "Become an expert Draughts player."

The GeneralistPlannerAgent receives the goal and formulates the evolutionary task for the SMM.

The EvolutionaryOrchestratorAgent initializes a population of agents based on the generic DomainExpertAgent template.

The notebook shows the evolutionary loop over multiple generations:

The SMM uses its LLM-driven mutate and crossover operators to generate new agent logic (e.g., discovering concepts like piece counting, king safety, or rudimentary tree search).

The IEE evaluates each generation in parallel against the baseline opponent, and the population's average fitness score is shown to increase over time.

The process concludes when an evolved agent achieves the target 80% win rate. The final, evolved source code of the successful DraughtsAgent is displayed.

Deliverables:

A final, polished Prometheus_v0_PoC.ipynb notebook demonstrating the complete capability acquisition loop.

Logs showing the agent's fitness score on the Draughts benchmark increasing across generations.

Verification:

The integrated v0.69 system can autonomously evolve a random-playing agent into a competent Draughts-playing agent that reliably defeats the baseline opponent.

Project Prometheus: Detailed Workplan for PoC System v0.70-v0.74
Executive Summary
Objective: This document details the workplan for the seventh development cycle, v0.70-v0.74. The v0.69 system successfully demonstrated that the RSI loop can be generalized to acquire skills in new symbolic domains like game playing. The objective of this cycle is to push this generalization into two far more complex and challenging areas:    

multimodal generative AI (text, images, audio, video) and abstract mathematical reasoning. This directly addresses the user's request to demonstrate a broad suite of classic AI capabilities and aligns with the project's long-term goal of tackling automated scientific discovery, which requires both creative generation and formal reasoning.   

This cycle will focus on two key architectural enhancements. First, the agent's Capability Layer will be made natively multimodal, integrating tools for generating and processing various media types. Second, the SMM will be upgraded with a primitive form of meta-learning, allowing it to create a library of reusable "cognitive patterns" (e.g., tree search, gradient descent) and transfer them across domains. This will enable the agent to learn new skills more efficiently, for example, by applying the tree-search concepts it evolved for Chess to the problem of solving a multi-step mathematical equation.

The cycle will culminate in a multi-part demonstration (v0.74) showcasing the agent's expanded intellect. It will evolve a MathAgent that combines LLM-based intuition with a symbolic solver to solve formal equations. It will also evolve a CreativeAgent that can generate multimodal content (e.g., an image based on a textual description), demonstrating the synthesis of its new capabilities. This will validate the Prometheus architecture as a platform for not just optimization and skill acquisition, but for creative and abstract thought.

Component	State at v0.69 PoC	Target State (v0.74 PoC)	
Guiding Principle    

Task Domain	Symbolic, single-modality domains (code, board games, text-based conversation).	Multimodal generative tasks (image/audio/video generation) and abstract formal reasoning (solving mathematical equations).	Towards AGI: Demonstrating the ability to operate and create across multiple modalities and levels of abstraction is a key milestone for general intelligence.
Self-Modification Module (SMM)	SMM v0.2 (Evolutionary): Evolves new agents from scratch for each new domain.	SMM v0.3 (Meta-Learning): Maintains a library of successful "cognitive patterns" (e.g., tree search, optimization loops) and uses them to accelerate learning in new domains via transfer learning.	Meta-Learning ("Learning to Learn"): The agent must not only learn new skills but learn how to learn more efficiently by generalizing its problem-solving strategies.
Capability Layer	Core Engine: A primarily text-based foundation model. Tool Use: Limited to code interpreters and game engines.	Core Engine: A natively multimodal foundation model. Tool Use: Expanded to include generative model APIs (e.g., for diffusion models) and symbolic math solvers (e.g., SymPy).	Hybrid Intelligence: True general intelligence requires the ability to seamlessly integrate neural/intuitive reasoning with formal/symbolic tool use.
Section 1: Capability Layer v0.2 - The Multimodal & Symbolic Engine
Rationale
To operate in multimodal and abstract domains, the agent's "body" must be equipped with the necessary senses and appendages. This requires upgrading the core foundation model to handle diverse data types and expanding its tool-use framework to include specialized generative and symbolic processors.

1.1 Task Block v0.70: Multimodal Tool Integration
Methodology: The agent's sandboxed environment will be equipped with a suite of generative tools.

Image Generation API: Integrate a secure wrapper around a standard text-to-image diffusion model API (e.g., Stable Diffusion). The agent will be able to call this tool with a text prompt and receive an image file in return.

Audio/Video Generation Tools: Integrate similar APIs for simple audio (e.g., text-to-speech) and video (e.g., text-to-video) generation services.

Multimodal Core Model: The core Gemini model will be upgraded to a natively multimodal version, allowing it to process and reason about image and audio data directly within its prompts, not just as opaque files.

Deliverables:

New, secure tool wrappers for image, audio, and video generation APIs within the agent's tool library.

Upgrade of the core foundation model to a multimodal version.

Verification:

A simple, non-evolved agent script can successfully call the new tools to generate an image, a sound file, and a short video clip from text prompts.

1.2 Task Block v0.71: Symbolic Reasoning Tool Integration
Methodology: To ground the agent's mathematical reasoning, it will be given access to a formal computer algebra system.

Integrate Symbolic Solver: Integrate the SymPy library into the agent's sandboxed code interpreter.

Create SymbolicMathAgent: Create a new, non-evolving agent that acts as a simple wrapper. It will be able to accept a mathematical equation as a string, pass it to the SymPy solver, and return the formal result. This agent will serve as a tool that more complex, evolved agents can choose to call.

Deliverables:

A sandboxed Python environment with the SymPy library installed.

A new symbolic_math_agent.py module.

Verification:

The SymbolicMathAgent can correctly solve a simple symbolic equation (e.g., "solve(x**2 - 4, x)") and return the correct result.

Section 2: Metacognitive Layer v0.3 - Cross-Domain Meta-Learning
Rationale
As the number of domains grows, evolving each new capability from scratch becomes inefficient. A truly intelligent system should get better at learning over time. This section details an upgrade to the SMM to enable a primitive form of transfer learning, allowing the agent to reuse successful strategies discovered in one domain to accelerate learning in another.

2.1 Task Block v0.72: SMM with a "Cognitive Pattern" Library
Methodology: The EvolutionaryOrchestratorAgent will be upgraded to identify, store, and reuse successful algorithmic patterns.

Pattern Extraction: After a successful evolutionary run (e.g., the creation of a competent ChessAgent), a new process will be triggered. The SMM_Agent will analyze the source code of the successful agent and, guided by the LLM, attempt to extract the core algorithmic pattern into a generic, reusable code block. For example, it might extract the agent's alpha-beta search logic and save it as a "tree_search_pattern."

Pattern Library: These extracted patterns will be stored in a "cognitive pattern library" or "gene bank".   

Pattern-Seeded Evolution: When the GeneralistPlannerAgent initiates a new evolutionary task, it will first prompt the LLM to determine if any patterns in the library might be relevant. If so, the initial population of the new evolutionary run will be "seeded" with variants that already incorporate this pattern, giving the search a significant head start.

Deliverables:

An updated smm.py with logic for pattern extraction and library management.

An updated evolutionary_orchestrator.py that can seed new populations with stored patterns.

Verification:

After evolving a DraughtsAgent, the system successfully extracts and stores a generic "minimax_search" pattern.

When subsequently tasked with learning Chess, the orchestrator correctly identifies this pattern as relevant and uses it to seed the initial population.

2.2 Task Block v0.73: IEE with Advanced Generative & Formal Benchmarks
Methodology: The IEE's benchmark suite will be expanded to provide fitness signals for the new domains.

Generative Media Benchmarks:

Image/Video: Fitness will be measured by passing the generated media and the original text prompt to a multimodal model (like Gemini) and asking it to score the alignment on a scale of 1-10.

Audio: Fitness for tasks like text-to-speech will be measured using standard metrics like Word Error Rate from a speech-to-text model.

Mathematical Reasoning Benchmarks:

Dataset: A suite of mathematical problems of varying difficulty will be curated from standard datasets (e.g., MATH).

Fitness Metric: The fitness score will be binary: 1 if the agent's final answer matches the correct solution, 0 otherwise. Correctness is an unambiguous reward signal.   

Deliverables:

New benchmark modules within Prometheus-Bench-v0.2 for generative media and mathematical reasoning.

Verification:

The IEE can successfully evaluate a generated image against a prompt and produce a coherent alignment score.

The IEE can successfully evaluate a proposed solution to a math problem and return a correct pass/fail fitness score.

Section 3: Integrated Demonstrations (v0.74)
Rationale
The final set of demonstrations will showcase the agent's newfound versatility, demonstrating its ability to synthesize its capabilities to tackle creative, multimodal, and abstract reasoning tasks that were previously impossible.

3.1 Task Block v0.74: Multi-Domain Capability Demonstrations
Methodology: The final notebook will be a portfolio of the agent's capabilities, executing several distinct demonstrations.

Demo A - Accelerated Game Playing:

Task: Having already mastered Draughts in v0.69, the user will task the agent: "Learn to play Chess."

Showcase: The logs will show the GeneralistPlannerAgent identifying the tree_search_pattern from the SMM's library as relevant. The evolutionary process will be shown to reach the target 80% win rate against its baseline opponent significantly faster (in fewer generations) than the Draughts agent did, demonstrating successful transfer learning.

Demo B - Multimodal Creativity:

Task: The user provides a creative, multimodal goal: "Act as a creative assistant. Generate a concept and an image for a 'cyberpunk detective in a rainy neon city'."

Showcase: The system will evolve a CreativeAgent. The demonstration will show the evolved agent's chain of thought: first, using its chatbot capability to ask clarifying questions ("What style of cyberpunk? Anime or realistic?"); then, using its text generation capability to write a detailed image prompt; and finally, calling the image generation tool to produce the final artwork. The IEE's fitness score will confirm the high alignment between the final image and the conversation.

Demo C - Hybrid Mathematical Reasoning:

Task: The user provides a complex symbolic integration problem that is difficult for an LLM to solve directly.

Showcase: The system will evolve a MathAgent. The logs will show the agent learning a hybrid strategy over generations. Early, unsuccessful attempts will show the LLM trying to solve it alone. Later, successful generations will show the agent learning to use the LLM for high-level strategy ("The structure of this integral suggests using integration by parts") but then calling the SymbolicMathAgent tool to execute the steps reliably and provide the final, formally correct answer.

Deliverables:

A final, executable Prometheus_v0_PoC.ipynb notebook with three distinct, successful demonstrations of the agent's generalized capabilities.

Verification:

The integrated v0.74 system successfully completes all three demonstration scenarios, validating its ability to acquire skills in General Game Playing, generate novel multimodal content, and solve formal mathematical problems through its generalized RSI framework.


Sources and related content

