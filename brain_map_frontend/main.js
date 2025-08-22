document.addEventListener('DOMContentLoaded', () => {
    const contextViewContent = document.getElementById('context-view-content');
    const graphContainer = document.getElementById('graph-container');

    // --- WebSocket Setup ---
    const socket = new WebSocket('ws://localhost:8000/ws');

    socket.onopen = () => {
        console.log('WebSocket connection established.');
        contextViewContent.textContent = 'Connected to visualizer backend. Waiting for agent activity...';
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received message:', message);
        updateVisualization(message);
    };

    socket.onclose = () => {
        console.log('WebSocket connection closed.');
        contextViewContent.textContent = 'Connection closed. Please refresh the page to reconnect.';
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        contextViewContent.textContent = 'An error occurred with the WebSocket connection.';
    };

    // --- D3.js Graph Setup ---
    const width = graphContainer.clientWidth;
    const height = graphContainer.clientHeight;

    const svg = d3.select('#graph-container').append('svg')
        .attr('width', width)
        .attr('height', height);

    // Define the agent nodes
    const nodes = [
        { id: 'Planner', group: 'agent', x: width / 2, y: height / 4 },
        { id: 'Coder', group: 'agent', x: width / 4, y: height / 2 },
        { id: 'Evaluator', group: 'agent', x: 3 * width / 4, y: height / 2 },
        { id: 'Corrector', group: 'agent', x: width / 2, y: 3 * height / 4 },
        { id: 'MCS', group: 'system', x: width / 2, y: height / 8 }
    ];

    const links = [
        { source: 'Planner', target: 'Coder' },
        { source: 'Coder', target: 'Evaluator' },
        { source: 'Evaluator', target: 'Corrector' },
        { source: 'Corrector', target: 'Planner' },
        { source: 'Corrector', target: 'Coder' },
        { source: 'MCS', target: 'Planner' },
        { source: 'MCS', target: 'Coder' },
        { source: 'MCS', target: 'Evaluator' },
        { source: 'MCS', target: 'Corrector' }
    ];

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('class', 'link');

    const node = svg.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('class', 'node');

    node.append('circle')
        .attr('r', 20)
        .attr('fill', d => d.group === 'agent' ? '#6baed6' : '#fd8d3c');

    node.append('text')
        .text(d => d.id)
        .attr('dy', 35);

    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // --- Visualization Update Logic ---
    function updateVisualization(message) {
        const { agent_id, state, payload } = message;

        // Update context view
        contextViewContent.textContent = `[${agent_id} / ${state}]\n\n` + JSON.stringify(payload, null, 2);

        // Special case for MCS Intervention
        if (agent_id === 'MCS' && state === 'intervention') {
            handleMCSIntervention(payload);
            return;
        }

        // Update node colors
        node.selectAll('circle')
            .transition()
            .duration(200)
            .attr('fill', d => {
                if (d.id === agent_id) {
                    return getNodeColor(state);
                }
                // Don't reset colors if an intervention has occurred
                if (d3.select(d).attr('data-intervened')) return '#aaa';
                return d.group === 'agent' ? '#6baed6' : '#fd8d3c';
            });
    }

    function handleMCSIntervention(payload) {
        // MCS node pulses red
        d3.select(node.filter(d => d.id === 'MCS').node())
            .select('circle')
            .transition()
            .duration(100)
            .attr('fill', '#ff0000') // Bright red
            .style('stroke', '#ff0000')
            .attr('r', 30)
            .transition()
            .duration(400)
            .attr('r', 25)
            .ease(d3.easeBounce);

        // Other nodes turn grey
        node.filter(d => d.id !== 'MCS').selectAll('circle')
            .attr('data-intervened', true) // Mark as intervened
            .transition()
            .duration(500)
            .attr('fill', '#aaa'); // Neutral grey

        // Update context view with intervention reason
        contextViewContent.textContent = `--- MCS INTERVENTION ---\n\nREASON: ${payload.reason}`;
        contextViewContent.style.color = '#ff0000';
        contextViewContent.style.fontWeight = 'bold';
    }

    function getNodeColor(state) {
        switch (state) {
            case 'thinking': return '#f0ad4e'; // Yellow
            case 'generating_code':
            case 'generating_patch':
            case 'reloading_module': return '#5bc0de'; // Blue
            case 'evaluating':
            case 'verifying_patch': return '#d9534f'; // Red
            case 'success': return '#5cb85c'; // Green
            case 'failure': return '#c9302c'; // Dark Red
            case 'intervention': return '#ff0000'; // Bright Red
            default: return '#6baed6'; // Default Blue
        }
    }
});
