"""
Advanced Brain Map Visualization System
Implements visualization features from v0.30-v0.34 onwards
"""

import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
import queue
import socketserver
import http.server
from urllib.parse import urlparse, parse_qs
import asyncio
import websockets

class VisualizationServer:
    """WebSocket server for real-time brain map updates"""

    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.agent_states = {}
        self.running = False
        self.server = None

    async def register_client(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        logging.info(f"Client connected. Total clients: {len(self.clients)}")

        # Send current state to new client
        if self.agent_states:
            await websocket.send(json.dumps({
                "type": "full_state_update",
                "agents": self.agent_states,
                "timestamp": datetime.now().isoformat()
            }))

    async def unregister_client(self, websocket):
        """Unregister a client"""
        self.clients.discard(websocket)
        logging.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast_state_update(self, update: Dict[str, Any]):
        """Broadcast state update to all clients"""
        if not self.clients:
            return

        message = json.dumps({
            "type": "state_update",
            "update": update,
            "timestamp": datetime.now().isoformat()
        })

        # Send to all connected clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except Exception as e:
                logging.error(f"Error sending to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        for client in disconnected:
            self.clients.discard(client)

    async def handle_client(self, websocket, path):
        """Handle client connection"""
        await self.register_client(websocket)
        try:
            await websocket.wait_closed()
        finally:
            await self.unregister_client(websocket)

    def update_agent_state(self, agent_id: str, state: Dict[str, Any]):
        """Update agent state and broadcast to clients"""
        self.agent_states[agent_id] = {
            **state,
            "last_updated": datetime.now().isoformat()
        }

        # Schedule broadcast (non-blocking)
        asyncio.create_task(self.broadcast_state_update({
            "agent_id": agent_id,
            "state": self.agent_states[agent_id]
        }))

    async def start_server(self):
        """Start the WebSocket server"""
        self.running = True
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        logging.info(f"Visualization server started on {self.host}:{self.port}")

    async def stop_server(self):
        """Stop the WebSocket server"""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()

class BrainMapVisualizer:
    """Main brain map visualization controller"""

    def __init__(self, server_port: int = 8765):
        self.server = VisualizationServer(port=server_port)
        self.assembly_definitions = self._define_assemblies()
        self.subassembly_definitions = self._define_subassemblies()
        self.visualization_states = {
            "normal": "normal_operation",
            "forging": "cognitive_forging",
            "uncertainty": "uncertainty_cloud",
            "intervention": "mcs_intervention",
            "rsi": "recursive_self_improvement"
        }
        self.current_state = "normal"

    def _define_assemblies(self) -> Dict[str, Dict[str, Any]]:
        """Define main agent assemblies based on Good's cognitive model"""
        return {
            "planner_agent": {
                "type": "assembly",
                "label": "Planner Assembly",
                "description": "Strategic planning and goal decomposition",
                "color": "#4CAF50",
                "size": 100,
                "position": {"x": 200, "y": 100}
            },
            "coder_agent": {
                "type": "assembly",
                "label": "Coder Assembly",
                "description": "Code generation and synthesis",
                "color": "#2196F3",
                "size": 100,
                "position": {"x": 400, "y": 200}
            },
            "evaluator_agent": {
                "type": "assembly",
                "label": "Evaluator Assembly",
                "description": "Performance assessment and critique",
                "color": "#FF9800",
                "size": 100,
                "position": {"x": 400, "y": 400}
            },
            "corrector_agent": {
                "type": "assembly",
                "label": "Corrector Assembly",
                "description": "Meta-reasoning and correction",
                "color": "#9C27B0",
                "size": 100,
                "position": {"x": 200, "y": 500}
            },
            "mcs_supervisor": {
                "type": "assembly",
                "label": "MCS Governor",
                "description": "Central governance and stability",
                "color": "#F44336",
                "size": 120,
                "position": {"x": 300, "y": 300}
            },
            "memory_agent": {
                "type": "assembly",
                "label": "Memory Bank",
                "description": "Experiential knowledge storage",
                "color": "#607D8B",
                "size": 80,
                "position": {"x": 100, "y": 300}
            }
        }

    def _define_subassemblies(self) -> Dict[str, Dict[str, Any]]:
        """Define subassemblies (tools and components)"""
        return {
            "ast_analyzer": {
                "type": "subassembly",
                "label": "AST Analyzer",
                "parent": "evaluator_agent",
                "color": "#FFE0B2",
                "size": 40
            },
            "causal_attention": {
                "type": "subassembly",
                "label": "Causal Attention",
                "parent": "planner_agent",
                "color": "#C8E6C9",
                "size": 40
            },
            "dynamic_profiler": {
                "type": "subassembly",
                "label": "Dynamic Profiler",
                "parent": "evaluator_agent",
                "color": "#FFE0B2",
                "size": 40
            },
            "pattern_matcher": {
                "type": "subassembly",
                "label": "Pattern Matcher",
                "parent": "memory_agent",
                "color": "#CFD8DC",
                "size": 40
            }
        }

    def emit_agent_status(self, agent_id: str, status: str, data: Dict[str, Any] = None):
        """Emit agent status update"""
        state_update = {
            "status": status,
            "activation_level": self._calculate_activation_level(status),
            "data": data or {},
            "connections": self._get_active_connections(agent_id, status)
        }

        self.server.update_agent_state(agent_id, state_update)
        logging.debug(f"Emitted status for {agent_id}: {status}")

    def _calculate_activation_level(self, status: str) -> float:
        """Calculate activation level based on status"""
        activation_map = {
            "idle": 0.1,
            "thinking": 0.4,
            "generating_code": 0.8,
            "evaluating": 0.6,
            "correcting": 0.7,
            "intervening": 1.0,
            "success": 0.9,
            "failure": 0.3,
            "reloading": 0.5
        }
        return activation_map.get(status, 0.5)

    def _get_active_connections(self, agent_id: str, status: str) -> List[str]:
        """Get active connections based on agent status"""
        connection_map = {
            "planner_agent": {
                "thinking": ["memory_agent", "causal_attention"],
                "generating_code": ["coder_agent"]
            },
            "coder_agent": {
                "generating_code": ["evaluator_agent"],
                "reloading": ["mcs_supervisor"]
            },
            "evaluator_agent": {
                "evaluating": ["corrector_agent", "ast_analyzer", "dynamic_profiler"]
            },
            "corrector_agent": {
                "correcting": ["memory_agent", "coder_agent"],
                "meta_correction": ["mcs_supervisor"]
            },
            "mcs_supervisor": {
                "intervening": ["planner_agent", "coder_agent", "evaluator_agent", "corrector_agent"]
            }
        }

        agent_connections = connection_map.get(agent_id, {})
        return agent_connections.get(status, [])

    def visualize_causal_flow(self, source_agent: str, target_agent: str,
                            causal_strength: float, data: Dict[str, Any] = None):
        """Visualize causal flow between agents (v0.31+)"""
        flow_update = {
            "type": "causal_flow",
            "source": source_agent,
            "target": target_agent,
            "strength": causal_strength,
            "data": data or {}
        }

        asyncio.create_task(self.server.broadcast_state_update(flow_update))

    def enter_cognitive_forging_state(self, target_model: str, training_data_info: Dict[str, Any]):
        """Enter cognitive forging visualization state (v0.35+)"""
        self.current_state = "forging"

        forging_update = {
            "type": "state_change",
            "new_state": "cognitive_forging",
            "target_model": target_model,
            "training_info": training_data_info,
            "visual_effects": {
                "central_node_pulse": True,
                "training_data_flow": True,
                "forge_animation": True
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(forging_update))

    def visualize_uncertainty_cloud(self, problem_keywords: List[str],
                                  subassemblies: List[str]):
        """Visualize uncertainty cloud and pattern collapse (v0.33+)"""
        self.current_state = "uncertainty"

        uncertainty_update = {
            "type": "uncertainty_cloud",
            "keywords": problem_keywords,
            "active_subassemblies": subassemblies,
            "visual_effects": {
                "cloud_formation": True,
                "weak_activations": True,
                "multiple_candidates": True
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(uncertainty_update))

    def visualize_pattern_collapse(self, winning_pattern: str, confidence: float):
        """Visualize pattern collapse to single interpretation"""
        collapse_update = {
            "type": "pattern_collapse",
            "winning_pattern": winning_pattern,
            "confidence": confidence,
            "visual_effects": {
                "cloud_collapse": True,
                "single_activation": True,
                "high_confidence": confidence > 0.8
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(collapse_update))

    def visualize_mcs_intervention(self, violation_type: str, affected_agents: List[str]):
        """Visualize MCS intervention as inhibitory signals (v0.32+)"""
        self.current_state = "intervention"

        intervention_update = {
            "type": "mcs_intervention",
            "violation_type": violation_type,
            "affected_agents": affected_agents,
            "visual_effects": {
                "mcs_flash_red": True,
                "inhibitory_pulses": True,
                "agent_shutdown": True,
                "emergency_state": True
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(intervention_update))

    def visualize_rsi_cycle(self, target_module: str, modification_type: str,
                          generation: int):
        """Visualize recursive self-improvement cycle (v0.34+)"""
        self.current_state = "rsi"

        rsi_update = {
            "type": "rsi_cycle",
            "target_module": target_module,
            "modification_type": modification_type,
            "generation": generation,
            "visual_effects": {
                "candidate_gene_creation": True,
                "iee_activation": True,
                "hot_swap_animation": True,
                "version_increment": True
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(rsi_update))

    def visualize_mixture_of_experts(self, problem_type: str, selected_expert: str,
                                   available_experts: List[str]):
        """Visualize dynamic expert selection (v0.37+)"""
        expert_update = {
            "type": "expert_selection",
            "problem_type": problem_type,
            "selected_expert": selected_expert,
            "available_experts": available_experts,
            "visual_effects": {
                "expert_activation": True,
                "docking_animation": True,
                "specialized_composition": True
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(expert_update))

    def update_performance_curve(self, generation: int, performance_metrics: Dict[str, float]):
        """Update performance curve for intelligence explosion tracking (v0.34+)"""
        curve_update = {
            "type": "performance_update",
            "generation": generation,
            "metrics": performance_metrics,
            "curve_data": {
                "x": generation,
                "y": performance_metrics.get("success_rate", 0.0),
                "trend": self._calculate_performance_trend(generation, performance_metrics)
            }
        }

        asyncio.create_task(self.server.broadcast_state_update(curve_update))

    def _calculate_performance_trend(self, generation: int,
                                   metrics: Dict[str, float]) -> str:
        """Calculate performance trend"""
        success_rate = metrics.get("success_rate", 0.0)

        if generation < 3:
            return "establishing_baseline"
        elif success_rate > 0.8:
            return "exponential_growth"
        elif success_rate > 0.6:
            return "linear_improvement"
        else:
            return "plateau"

    def generate_brain_map_html(self) -> str:
        """Generate the HTML interface for the brain map"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prometheus Brain Map</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff00;
            overflow: hidden;
        }

        #container {
            display: flex;
            height: 100vh;
        }

        #brain-map {
            flex: 2;
            background: radial-gradient(circle, #1a1a2e 0%, #0a0a0a 100%);
            position: relative;
        }

        #context-panel {
            flex: 1;
            background: #111;
            border-left: 2px solid #00ff00;
            padding: 20px;
            overflow-y: auto;
        }

        .node {
            cursor: pointer;
            stroke-width: 2px;
        }

        .assembly {
            stroke: #fff;
        }

        .subassembly {
            stroke: #888;
        }

        .link {
            stroke: #666;
            stroke-width: 2px;
            fill: none;
        }

        .active-link {
            stroke: #00ff00;
            stroke-width: 4px;
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0% { opacity: 0.5; }
            50% { opacity: 1; }
            100% { opacity: 0.5; }
        }

        .intervention {
            animation: flash 0.5s infinite;
        }

        @keyframes flash {
            0% { fill: #ff0000; }
            50% { fill: #ff6666; }
            100% { fill: #ff0000; }
        }

        #status-display {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.8);
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #00ff00;
        }

        #performance-chart {
            width: 100%;
            height: 200px;
            margin-top: 20px;
        }

        .context-section {
            margin-bottom: 20px;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 5px;
        }

        .context-title {
            color: #00ffff;
            font-weight: bold;
            margin-bottom: 10px;
        }

        pre {
            background: #1a1a1a;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="brain-map">
            <div id="status-display">
                <div>Status: <span id="current-status">Initializing</span></div>
                <div>Active Agents: <span id="active-count">0</span></div>
                <div>Cortical Load: <span id="cortical-load">0%</span></div>
            </div>
        </div>
        <div id="context-panel">
            <div class="context-section">
                <div class="context-title">Current Activity</div>
                <div id="current-activity">Waiting for agent activity...</div>
            </div>
            <div class="context-section">
                <div class="context-title">Code Context</div>
                <pre id="code-display"></pre>
            </div>
            <div class="context-section">
                <div class="context-title">Performance Curve</div>
                <svg id="performance-chart"></svg>
            </div>
            <div class="context-section">
                <div class="context-title">System Log</div>
                <div id="system-log"></div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection
        const ws = new WebSocket('ws://localhost:8765');

        // D3.js visualization setup
        const width = window.innerWidth * 0.67;
        const height = window.innerHeight;

        const svg = d3.select("#brain-map")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        // Performance chart setup
        const chartSvg = d3.select("#performance-chart");
        const performanceData = [];

        // Brain map state
        let agents = {};
        let currentState = "normal";

        // WebSocket event handlers
        ws.onopen = function(event) {
            console.log("Connected to brain map server");
            updateStatus("Connected");
        };

        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            handleBrainMapUpdate(message);
        };

        ws.onerror = function(error) {
            console.error("WebSocket error:", error);
            updateStatus("Connection Error");
        };

        function handleBrainMapUpdate(message) {
            switch(message.type) {
                case "full_state_update":
                    agents = message.agents;
                    renderBrainMap();
                    break;
                case "state_update":
                    updateAgentState(message.update);
                    break;
                case "causal_flow":
                    visualizeCausalFlow(message.update);
                    break;
                case "state_change":
                    handleStateChange(message.update);
                    break;
                case "mcs_intervention":
                    visualizeIntervention(message.update);
                    break;
                case "performance_update":
                    updatePerformanceChart(message.update);
                    break;
            }
        }

        function renderBrainMap() {
            // Clear existing visualization
            svg.selectAll("*").remove();

            // Render agents as nodes
            Object.entries(agents).forEach(([agentId, state]) => {
                renderAgent(agentId, state);
            });

            updateActivityDisplay();
        }

        function renderAgent(agentId, state) {
            const node = svg.append("circle")
                .attr("class", "node assembly")
                .attr("id", agentId)
                .attr("cx", Math.random() * width)
                .attr("cy", Math.random() * height)
                .attr("r", 20 + (state.activation_level * 30))
                .style("fill", getAgentColor(agentId))
                .style("opacity", 0.3 + (state.activation_level * 0.7));

            // Add label
            svg.append("text")
                .attr("x", node.attr("cx"))
                .attr("y", node.attr("cy"))
                .attr("text-anchor", "middle")
                .attr("dy", "0.35em")
                .style("fill", "#fff")
                .style("font-size", "12px")
                .text(agentId.replace("_", " ").toUpperCase());
        }

        function updateAgentState(update) {
            const agentId = update.agent_id;
            agents[agentId] = update.state;

            // Update visual representation
            const node = svg.select("#" + agentId);
            if (!node.empty()) {
                node.transition()
                    .duration(500)
                    .attr("r", 20 + (update.state.activation_level * 30))
                    .style("opacity", 0.3 + (update.state.activation_level * 0.7));
            }

            updateActivityDisplay();
            updateContextPanel(agentId, update.state);
        }

        function getAgentColor(agentId) {
            const colors = {
                "planner_agent": "#4CAF50",
                "coder_agent": "#2196F3",
                "evaluator_agent": "#FF9800",
                "corrector_agent": "#9C27B0",
                "mcs_supervisor": "#F44336",
                "memory_agent": "#607D8B"
            };
            return colors[agentId] || "#666";
        }

        function updateActivityDisplay() {
            const activeAgents = Object.values(agents).filter(s => s.activation_level > 0.3).length;
            const avgLoad = Object.values(agents).reduce((sum, s) => sum + s.activation_level, 0) / Object.keys(agents).length;

            document.getElementById("active-count").textContent = activeAgents;
            document.getElementById("cortical-load").textContent = Math.round(avgLoad * 100) + "%";
        }

        function updateContextPanel(agentId, state) {
            document.getElementById("current-activity").textContent =
                `${agentId}: ${state.status} (${Math.round(state.activation_level * 100)}%)`;

            if (state.data && state.data.code) {
                document.getElementById("code-display").textContent = state.data.code;
            }
        }

        function updateStatus(status) {
            document.getElementById("current-status").textContent = status;
        }

        function visualizeIntervention(update) {
            // Flash MCS node red
            const mcsNode = svg.select("#mcs_supervisor");
            mcsNode.classed("intervention", true);

            setTimeout(() => {
                mcsNode.classed("intervention", false);
            }, 2000);

            // Log intervention
            const logDiv = document.getElementById("system-log");
            logDiv.innerHTML = `<div style="color: #ff0000;">MCS INTERVENTION: ${update.violation_type}</div>` + logDiv.innerHTML;
        }

        function updatePerformanceChart(update) {
            performanceData.push(update.curve_data);

            // Redraw performance chart
            const margin = {top: 20, right: 30, bottom: 30, left: 40};
            const chartWidth = parseInt(chartSvg.style("width")) - margin.left - margin.right;
            const chartHeight = 160 - margin.top - margin.bottom;

            chartSvg.selectAll("*").remove();

            const xScale = d3.scaleLinear()
                .domain(d3.extent(performanceData, d => d.x))
                .range([0, chartWidth]);

            const yScale = d3.scaleLinear()
                .domain([0, 1])
                .range([chartHeight, 0]);

            const line = d3.line()
                .x(d => xScale(d.x))
                .y(d => yScale(d.y))
                .curve(d3.curveMonotoneX);

            const g = chartSvg.append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            g.append("path")
                .datum(performanceData)
                .attr("fill", "none")
                .attr("stroke", "#00ff00")
                .attr("stroke-width", 2)
                .attr("d", line);

            g.selectAll(".dot")
                .data(performanceData)
                .enter().append("circle")
                .attr("class", "dot")
                .attr("cx", d => xScale(d.x))
                .attr("cy", d => yScale(d.y))
                .attr("r", 3)
                .attr("fill", "#00ff00");
        }

        // Initialize
        updateStatus("Initializing");
    </script>
</body>
</html>
        """

        return html_content

    def save_brain_map_interface(self, file_path: str = "brain_map.html"):
        """Save the brain map HTML interface to file"""
        html_content = self.generate_brain_map_html()
        with open(file_path, 'w') as f:
            f.write(html_content)
        logging.info(f"Brain map interface saved to {file_path}")

# Visualization client for agents to use
class VisualizationClient:
    """Client for agents to emit status updates to the visualizer"""

    def __init__(self, server_host: str = "localhost", server_port: int = 8765):
        self.server_host = server_host
        self.server_port = server_port
        self.visualizer = None

    def set_visualizer(self, visualizer: BrainMapVisualizer):
        """Set the visualizer instance"""
        self.visualizer = visualizer

    def emit_status(self, agent_id: str, status: str, data: Dict[str, Any] = None):
        """Emit status update (non-blocking)"""
        if self.visualizer:
            self.visualizer.emit_agent_status(agent_id, status, data)
        else:
            # Fallback logging
            logging.info(f"Visualization: {agent_id} -> {status}")

# Global visualization client instance
visualization_client = VisualizationClient()