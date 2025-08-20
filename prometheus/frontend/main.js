document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM loaded, starting Brain Map script.");

    const width = document.getElementById('brain-map-panel').clientWidth;
    const height = document.getElementById('brain-map-panel').clientHeight;

    const svg = d3.select("#brain-map-svg")
        .attr("width", width)
        .attr("height", height);

    // Define the agent nodes
    const agents = [
        { id: "Orchestrator", color: "#66c2a5" },
        { id: "Coder", color: "#fc8d62" },
        { id: "Evaluator", color: "#8da0cb" },
        { id: "Corrector", color: "#e78ac3" },
        { id: "MCS", color: "#a6d854" }
    ];

    // Define the links between agents (potential information flow)
    const links_data = [
        { source: "Orchestrator", target: "Coder" },
        { source: "Coder", target: "Evaluator" },
        { source: "Evaluator", target: "Corrector" },
        { source: "Corrector", target: "Coder" },
        { source: "Corrector", target: "Orchestrator" },
        { source: "Evaluator", target: "Orchestrator" }
    ];

    const simulation = d3.forceSimulation(agents)
        .force("link", d3.forceLink(links_data).id(d => d.id).distance(150))
        .force("charge", d3.forceManyBody().strength(-400))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(links_data)
        .enter().append("line")
        .attr("class", "link");

    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("g")
        .data(agents)
        .enter().append("g")
        .attr("class", "node");

    node.append("circle")
        .attr("r", 20)
        .attr("fill", d => d.color);

    node.append("text")
        .text(d => d.id)
        .attr("dy", 30);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    const contextContent = document.getElementById('context-content');

    // --- WebSocket Connection ---
    const socket = new WebSocket("ws://localhost:8000/ws");

    socket.onopen = function(e) {
        console.log("[open] Connection established");
        contextContent.textContent = "Connected to visualizer backend...";
    };

    socket.onmessage = function(event) {
        console.log(`[message] Data received from server: ${event.data}`);
        const message = JSON.parse(event.data);

        // Update context view
        contextContent.textContent = JSON.stringify(message.payload, null, 2);

        // Update node color based on state
        const agentNode = d3.select(node.filter(d => d.id === message.agent_id).node());

        let stateColor = "#ccc"; // Default/idle color
        switch(message.state) {
            case "thinking":
            case "evaluating":
            case "generating_patch":
            case "reloading_module":
                stateColor = "yellow";
                break;
            case "success":
                stateColor = "lime";
                break;
            case "failure":
                stateColor = "red";
                break;
        }

        agentNode.select("circle")
            .transition()
            .duration(200)
            .attr("fill", stateColor)
            .transition()
            .duration(1000)
            .attr("fill", d => d.color); // Revert to original color
    };

    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        } else {
            console.log('[close] Connection died');
        }
        contextContent.textContent = "Connection closed.";
    };

    socket.onerror = function(error) {
        console.log(`[error] ${error.message}`);
        contextContent.textContent = "WebSocket error. Could not connect to the backend.";
    };
});
