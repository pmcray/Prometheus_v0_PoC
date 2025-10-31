

# **Project Prometheus: Detailed Work Plan for Demonstrator v0.35 \- v0.39**

---

## **1\. Executive Summary & Version Feature Matrix**

This document outlines the work plan for Prometheus demonstrator versions v0.35 through v0.39. This development block represents the project's deepest engagement yet with I.J. Good's core philosophies, moving beyond modifying the agent's external code to recursively improving its internal cognitive substrate—the foundation model itself.1 The explicit adoption of the Gemma 270M model for this phase is a strategic decision that fully embraces Good's principle of

*computational economy*.1 Rather than relying on a large, generalist model, the agent will now learn to forge its own mind, creating a fleet of small, hyper-specialized cognitive tools from the base Gemma 270M clay.2

This work will be made tangible through significant upgrades to the "brain map" visualization introduced in v0.30.4 We will visualize the process of self-fine-tuning, the creation of a self-generated curriculum, and the dynamic assembly of a "Mixture-of-Experts" architecture from specialized LoRA adapters—a direct visual metaphor for Good's subassembly theory.1 The agent will then turn this self-improvement lens on its own understanding of the world, building an isomorphic model to predict code performance before it is written, representing a leap in strategic reasoning.5

This culminates in v0.39 with the evolution of the Modern Centrencephalic System (MCS) into a true Alignment Governor.1 With the agent now capable of altering its own learning processes and cognitive architecture, the MCS must take on the ultimate oversight role: ensuring that this rapid, targeted self-improvement remains stable, robust, and aligned with the project's foundational principles.1

### **1.1. Version Feature Matrix**

The following table summarizes the primary feature deliverables for each of the four core architectural principles across the five planned subversions. This matrix illustrates the project's focus on meta-learning and the governance of self-improvement, all visualized through the brain map.

| Principle | v0.35: The Cognitive Forge | v0.36: The Socratic Tutor | v0.37: The Assembly of Experts | v0.38: The Isomorphic World Model | v0.39: The Alignment Governor |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **CAM** | GeneBankAgent stores LoRA adapters | TutorAgent for synthetic data generation | Dynamic LoRA adapter loading | PerformancePredictorAgent integration | N/A |
| **Causal Attention** | N/A | Causal analysis of failures to guide data generation | N/A | N/A | N/A |
| **CRLS** | Self-fine-tuning of Gemma 270M | Curriculum learning from self-generated data | Task-specific expert selection | Predictive optimization before code generation | Governed fine-tuning loop |
| **MCS** | IEE evaluates fine-tuned models | N/A | N/A | N/A | Governance over training data & catastrophic forgetting |

---

## **2\. Prometheus v0.35: The Cognitive Forge**

**Primary Objective:** To empower the agent with the fundamental capability for cognitive self-modification: the ability to fine-tune its own foundation model. This version establishes the "Cognitive Forge," an integrated toolchain that allows the agent to specialize the base Gemma 270M model for the specific task of code refactoring.

**Rationale:** The selection of Gemma 270M is a deliberate choice to prioritize efficiency and specialization over generalist capability.2 The model's true power is unlocked through fine-tuning.7 This task implements the core mechanism of the next phase of Recursive Self-Improvement (RSI), moving from modifying the agent's Python code to modifying its neural parameters. This is the first and most critical step in creating a system that truly learns how to think better.

### **2.1. Task: Integrate Fine-Tuning and Model Management**

**Methodology:**

1. **Fine-Tuning Toolchain Integration:** The agent's environment will be equipped with the necessary libraries for fine-tuning, such as Hugging Face TRL and the SFTTrainer.8 The  
   CoderAgent will be upgraded with a new capability: initiate\_finetune.  
2. **Gene Bank Evolution:** The GeneBankAgent (from v0.29) will be upgraded to manage not only Python source code ("genes") but also model parameters. It will store and version control both the base Gemma 270M model and any generated fine-tuning artifacts, such as Low-Rank Adaptation (LoRA) adapters.  
3. **IEE for Models:** The Introspection and Evaluation Engine (IEE), managed by the EvaluatorAgent, will be enhanced. Its responsibility now extends to evaluating the performance of a *fine-tuned model*. After a fine-tuning run, the IEE will load the resulting adapter and run it against a held-out validation set of refactoring problems to measure performance improvement.

**Deliverables:**

* An agent environment with a fully integrated fine-tuning toolchain.  
* An updated GeneBankAgent capable of storing and versioning LoRA adapters.  
* An updated IEE capable of benchmarking fine-tuned language models.

### **2.2. Task: Visualize the Forging Process**

**Methodology:**

1. **New Brain Map State:** The brain map visualization will be updated to represent the fine-tuning process. When initiate\_finetune is called, the brain map will enter a "Forging" state.  
2. **Visual Representation:** The central "Gemma 270M" assembly node will pulse with high intensity. A new, temporary "Training Data" subassembly node will appear, connected to the GeneBankAgent. The IEE node will also activate.  
3. **Outcome Visualization:** Upon completion, if the IEE verifies a performance improvement, a new, persistent "Refactor-LoRA-v1" subassembly node will be created and linked to the base model, visually representing the creation of a new cognitive tool.

**Deliverables:**

* Updated brain map frontend with logic for the "Forging" state and the creation of specialized model nodes.

**Verification:** The agent is tasked with a set of refactoring problems. It performs poorly. The orchestrator triggers the initiate\_finetune capability. The brain map enters the Forging state. After the process, a new LoRA adapter is stored in the gene bank, and a corresponding node appears on the map. When the task is run again with the new adapter, the "Explosion" performance tracker (from v0.34) shows a marked increase in success rate.

---

## **3\. Prometheus v0.36: The Socratic Tutor**

**Primary Objective:** To evolve the agent from a passive learner that fine-tunes on pre-existing data to an active, Socratic learner that generates its own curriculum to target its specific weaknesses.

**Rationale:** A key limitation of fine-tuning is the quality and relevance of the training data. An advanced intelligence should not depend on external curricula; it should be able to teach itself.1 This version introduces a

TutorAgent that embodies this principle. It analyzes the agent's past failures to synthetically generate new, challenging problems, creating a highly efficient, targeted learning loop. This is a more advanced implementation of the CRLS principle, where the agent corrects not just its output, but its underlying knowledge gaps.

### **3.1. Task: Implement the TutorAgent for Synthetic Data Generation**

**Methodology:**

1. **TutorAgent Class:** A new TutorAgent will be created. Its primary function is generate\_curriculum.  
2. **Failure-Driven Generation:** When triggered, the TutorAgent will query the GeneBankAgent to retrieve the logs of recent failed refactoring attempts. It will analyze the SelfReferentialCritique objects (from v0.25) to identify the root *causal* reasons for failure (e.g., "failed to convert recursion to iteration," "inefficient data structure choice").  
3. **Targeted Prompting:** The TutorAgent will then use the Gemma 270M model with a specialized prompt to generate a new batch of 5-10 Python problems and their corresponding optimized solutions. The prompt will explicitly instruct the model to create problems that exercise the specific causal weakness identified in the failure analysis.  
4. **Curriculum for the Forge:** This new, synthetically generated dataset becomes the training data for the fine-tuning process established in v0.35.

**Deliverables:**

* A new tutor.py module containing the TutorAgent class.  
* An updated orchestrator that can trigger the TutorAgent after a series of failures and use its output to initiate a fine-tuning run.

### **3.2. Task: Visualize the Curriculum Generation**

**Methodology:**

1. **Socratic Loop Visualization:** The brain map will be updated to show this new learning cycle. The TutorAgent assembly will activate. It will be shown visually querying the GeneBankAgent, with edges lighting up to the stored failure logs.  
2. **Data Creation:** A new set of temporary "Synthetic Problem" subassembly nodes will appear, shown as being generated by the TutorAgent. These nodes will then flow to the "Training Data" node used by the Cognitive Forge, visually representing the complete self-generated curriculum loop.

**Deliverables:**

* Updated brain map frontend with logic to visualize the TutorAgent's data generation process.

**Verification:** A test case is created where the agent repeatedly fails to refactor a problem involving recursion. The TutorAgent activates, the brain map shows it analyzing the failure logs, and it successfully generates a new dataset of recursion-to-iteration problems. The agent then uses this data to fine-tune a new LoRA adapter, which subsequently succeeds on the original failed task.

---

## **4\. Prometheus v0.37: The Assembly of Experts**

**Primary Objective:** To implement a direct, functional, and visual analogue of I.J. Good's subassembly theory by evolving the agent from a single specialized model into a dynamic "Assembly of Experts".1

**Rationale:** Good's theory posits that intelligence arises from the flexible combination of shared, specialized subassemblies.1 This is a model of extreme cognitive efficiency. This version operationalizes that theory using LoRA adapters as subassemblies. Instead of creating one large, monolithic fine-tuned model, the agent will learn to create a portfolio of small, expert LoRA adapters, each specialized for a different sub-problem, and dynamically load the correct one for the task at hand. This is a concrete step towards a more brain-like, composable cognitive architecture.

### **4.1. Task: Implement Dynamic, Task-Specific Adapter Loading**

**Methodology:**

1. **Problem Classification:** The PlannerAgent will be upgraded. Before passing a task to the CoderAgent, it will first perform a classification step, using the base Gemma 270M model to determine the *type* of refactoring required (e.g., LOOP\_OPTIMIZATION, RECURSION\_REFACTOR, DATA\_STRUCTURE\_SWAP).  
2. **Dynamic Adapter Orchestration:** The main orchestrator will be refactored. Based on the classification from the PlannerAgent, it will instruct the GeneBankAgent to load the corresponding specialized LoRA adapter onto the base model before the CoderAgent begins its work. If no specific adapter exists, it can fall back to a general-purpose adapter or the base model.  
3. **Targeted Fine-Tuning:** The self-improvement loop from v0.36 is now more targeted. The TutorAgent will generate data for a specific problem class, and the CognitiveForge will train or improve a LoRA adapter for just that class.

**Deliverables:**

* An updated PlannerAgent with problem classification capabilities.  
* An orchestrator capable of dynamically loading and unloading LoRA adapters.  
* An expanded GeneBankAgent that stores adapters indexed by their specialized task.

### **4.2. Task: Visualize the Subassembly Composition**

**Methodology:**

1. **Brain Map Overhaul:** The brain map's central component will now be the base "Gemma 270M" assembly. Stored LoRA adapters will be visualized as smaller, dormant "Subassembly" nodes surrounding it.  
2. **Dynamic Composition:** When the PlannerAgent classifies a task, the brain map will show a signal traveling to the corresponding LoRA subassembly. That node will activate, move towards the central assembly, and visually "dock" with it. The link between them will glow brightly, indicating that the specialized mind for the current task has been composed. After the task, the subassembly will detach and return to a dormant state.

**Deliverables:**

* A significantly updated brain map frontend capable of visualizing the dynamic composition of a base model and specialized LoRA adapters.

**Verification:** The agent is presented with three different problems in sequence: one loop-based, one recursion-based, and one loop-based again. The brain map correctly shows the "Loop-LoRA" subassembly activating for the first task, the "Recursion-LoRA" activating for the second, and the "Loop-LoRA" activating again for the third, demonstrating successful classification and dynamic composition.

---

## **5\. Prometheus v0.38: The Isomorphic World Model**

**Primary Objective:** To implement a more profound form of "Isomorphism" by teaching the agent to build an internal world model that can *predict* the consequences of its actions, enabling more efficient, strategic reasoning.5

**Rationale:** A truly intelligent agent doesn't just react; it anticipates. The agent's "world" is the domain of code and its performance characteristics. Currently, it can only measure performance *after* generating and running code (v0.26).9 This version tasks the agent with creating a specialized subassembly—a

PerformancePredictorAgent—that is fine-tuned to predict the performance of a code snippet from its static structure alone. This creates an isomorphism between its internal model and the external reality of runtime, allowing it to strategically prune bad ideas without the expensive process of full code generation and testing.

### **5.1. Task: Fine-Tune a Performance Prediction Model**

**Methodology:**

1. **Data Collection:** The orchestrator will be modified to systematically log the results of the dynamic analysis performed by the EvaluatorAgent (from v0.26). For every piece of code analyzed, it will create a training example pairing a simplified representation of its AST with its measured performance metrics (execution time, memory usage).  
2. **Predictor Fine-Tuning:** A new fine-tuning workflow will be created. The agent will use this collected data to fine-tune a new, dedicated LoRA adapter for the Gemma 270M model. The goal of this model is to take an AST representation as input and output a JSON object predicting its performance.  
3. **PerformancePredictorAgent:** A new PerformancePredictorAgent will be created that uses this specialized LoRA adapter.

**Deliverables:**

* A data logging mechanism to create a code-to-performance dataset.  
* A new PerformancePredictorAgent powered by a fine-tuned LoRA adapter.

### **5.2. Task: Integrate Predictive Reasoning into Planning**

**Methodology:**

1. **Strategic Planning:** The PlannerAgent's workflow will be upgraded. After receiving a task, it will now first generate 3-5 high-level *strategies* for refactoring (e.g., "Strategy 1: Replace nested loop with hash map," "Strategy 2: Pre-sort the list and use binary search").  
2. **Predictive Evaluation:** It will then pass these abstract strategies to the PerformancePredictorAgent. The predictor will estimate the likely performance outcome of each strategy.  
3. **Informed Decision:** The PlannerAgent will select the strategy with the best-predicted outcome and pass this specific, targeted instruction to the CoderAgent. This avoids wasting cycles on generating and testing code for inferior strategies.

**Deliverables:**

* An updated PlannerAgent that generates and predictively evaluates multiple strategies before committing to one.

### **5.3. Task: Visualize the "World Model" Simulation**

**Methodology:**

1. **New Brain Map Region:** A new, distinct region will be added to the brain map labeled "Internal World Model."  
2. **Simulation Visualization:** When the PlannerAgent is active, the visualization will show it generating several "Potential Strategy" subassemblies. These will move into the "World Model" region, where the PerformancePredictorAgent node will activate and test each one. The predicted outcomes (e.g., "faster," "slower") will be briefly displayed on each strategy node. Finally, the map will show the "best" strategy node being selected and moving into the main execution area, while the others fade away. This visually distinguishes the agent's "imagination" and strategic planning from its execution.

**Deliverables:**

* An updated brain map with a dedicated "World Model" region and animations for visualizing predictive evaluation.

**Verification:** Given a complex refactoring task, the brain map clearly shows the PlannerAgent generating three strategies. The PerformancePredictorAgent correctly predicts that two will be inefficient. The PlannerAgent selects the third, and the subsequent code generated by the CoderAgent is successful on the first attempt, demonstrating a significant increase in efficiency.

---

## **6\. Prometheus v0.39: The Alignment Governor**

**Primary Objective:** To evolve the Modern Centrencephalic System (MCS) into a true Alignment Governor, capable of overseeing the agent's now-powerful meta-learning and cognitive modification capabilities to ensure stability and safety.

**Rationale:** The agent can now modify its own cognitive processes through fine-tuning (v0.35), create its own training data (v0.36), and assemble specialized minds (v0.37). This level of autonomy requires a corresponding leap in internal governance.1 The MCS must move beyond simple rule-checking to become the guardian of the entire learning process, preventing issues like alignment drift, catastrophic forgetting, and the introduction of biases through flawed self-generated data.1

### **6.1. Task: Implement MCS Oversight of Meta-Learning**

**Methodology:**

1. **Training Data Auditing:** The MCSSupervisor will be given a new role. Before any fine-tuning process is initiated, the MCS will now audit the training data generated by the TutorAgent. It will use the base Gemma 270M model to perform a "constitutional review" of the synthetic data, checking for patterns that could encourage reward hacking or violate core principles.  
2. **Catastrophic Forgetting Detection:** The IEE's evaluation process will be expanded. After a new specialized LoRA adapter is trained, the IEE will not only test it on its target task but also run it against a diverse, held-out suite of general capability benchmarks. The MCSSupervisor will monitor these results. If performance on general tasks degrades significantly, it will flag a "catastrophic forgetting" event and can veto the adoption of the new adapter.  
3. **Cognitive Portfolio Management:** The MCS will monitor the agent's "I" Dashboard (from v0.28), which now represents its portfolio of specialized experts. If it detects over-specialization in one area, it can proactively instruct the TutorAgent to generate a curriculum for a different, under-developed capability to ensure balanced cognitive growth.

**Deliverables:**

* An updated MCSSupervisor that audits synthetic training data.  
* An expanded IEE benchmark suite for detecting catastrophic forgetting.  
* Logic within the MCS to direct curriculum generation for balanced development.

### **6.2. Task: Visualize Governance in Action**

**Methodology:**

1. **Centralized Governor:** The MCSSupervisor node on the brain map will be repositioned to a more central, overseeing location.  
2. **Active Auditing Visualization:** During the Socratic Tutor loop, the map will show the MCS node actively scanning the "Synthetic Problem" nodes before they are used for training. If it approves, the nodes will flash green and proceed. If it rejects a data point, the node will flash red and be deleted.  
3. **Forgetting Intervention:** If the IEE detects catastrophic forgetting, the brain map will show a red alert signal traveling from the IEE to the MCS. The MCS will then send a visible inhibitory pulse (as in v0.32) to the GeneBankAgent, preventing the flawed new LoRA adapter from being saved. This provides a clear, striking visual of the governor maintaining the cognitive stability of the entire system.

**Deliverables:**

* An updated brain map layout and animations that clearly depict the MCS's role in governing the entire self-improvement lifecycle.

**Verification:** A test is run where the TutorAgent is prompted to generate data that subtly encourages an obfuscated but technically correct solution. The brain map shows the MCS scanning this data and correctly identifying and deleting the flawed examples. In a separate test, a fine-tuning run results in a model that is highly specialized but has lost general capabilities. The map shows the IEE's alert and the MCS's successful intervention to block the flawed model.

#### **Works cited**

1. Ultraintelligence Implementation Detailed Breakdown\_.pdf  
2. Introducing Gemma 3 270M: The compact model for hyper-efficient AI, accessed on August 18, 2025, [https://developers.googleblog.com/en/introducing-gemma-3-270m/](https://developers.googleblog.com/en/introducing-gemma-3-270m/)  
3. AI Tasks 2025.8 \- Perfect for fine tuned Gemma 3 270M : r/homeassistant \- Reddit, accessed on August 18, 2025, [https://www.reddit.com/r/homeassistant/comments/1mqjqfj/ai\_tasks\_20258\_perfect\_for\_fine\_tuned\_gemma\_3\_270m/](https://www.reddit.com/r/homeassistant/comments/1mqjqfj/ai_tasks_20258_perfect_for_fine_tuned_gemma_3_270m/)  
4. Project Prometheus: Detailed Work Plan for Demonstrator v0.30 \- v0.34  
5. Hofstadter Concepts in Prometheus AI  
6. DeepMind Just Dropped Gemma 270M... And Here's Why It Matters \- YouTube, accessed on August 18, 2025, [https://www.youtube.com/watch?v=VZDw6C2A\_8E](https://www.youtube.com/watch?v=VZDw6C2A_8E)  
7. Introducing Gemma 3 270M: The compact model for hyper-efficient AI, accessed on August 18, 2025, [https://simonwillison.net/2025/Aug/14/gemma-3-270m/](https://simonwillison.net/2025/Aug/14/gemma-3-270m/)  
8. Full Model Fine-Tune using Hugging Face Transformers | Gemma \- Gemini API, accessed on August 18, 2025, [https://ai.google.dev/gemma/docs/core/huggingface\_text\_full\_finetune](https://ai.google.dev/gemma/docs/core/huggingface_text_full_finetune)  
9. Project Prometheus: Detailed Work Plan for Demonstrator v0.25 \- v0.29