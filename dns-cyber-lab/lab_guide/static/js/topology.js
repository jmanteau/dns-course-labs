const CONTAINERS = {
    webserver:    { x: 120, y: 80,  network: 'public',   label: 'webserver',    icon: '🌐' },
    dns_public:   { x: 350, y: 80,  network: 'public',   label: 'dns_public',   icon: '📡' },
    c2_server:    { x: 580, y: 80,  network: 'public',   label: 'c2_server',    icon: '💀' },
    firewall:     { x: 350, y: 230, network: 'both',     label: 'firewall',     icon: '🛡️' },
    dns_internal: { x: 250, y: 380, network: 'internal', label: 'dns_internal', icon: '📡' },
    client:       { x: 480, y: 380, network: 'internal', label: 'client',       icon: '💻' },
};

const CONNECTIONS = [
    { from: 'client', to: 'dns_internal', style: 'solid' },
    { from: 'dns_internal', to: 'firewall', style: 'solid' },
    { from: 'firewall', to: 'dns_public', style: 'solid' },
    { from: 'dns_public', to: 'c2_server', style: 'dashed' },
    { from: 'firewall', to: 'webserver', style: 'dashed', opacity: 0.3 },
];

const PATHS = {
    dns_query: ['client', 'dns_internal', 'firewall', 'dns_public', 'firewall', 'dns_internal', 'client'],
    c2_tunnel: ['client', 'dns_internal', 'firewall', 'dns_public', 'c2_server', 'dns_public', 'firewall', 'dns_internal', 'client'],
    infiltration: ['client', 'dns_internal', 'firewall', 'dns_public', 'c2_server', 'dns_public', 'firewall', 'dns_internal', 'client'],
};

let _highlighted = [];
let _animationId = null;

function createTopology(svgEl) {
    const svg = svgEl;
    svg.setAttribute('viewBox', '0 0 700 470');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.innerHTML = '';

    // Defs
    const defs = _el('defs');
    defs.innerHTML = `
        <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#484f58"/></marker>
    `;
    svg.appendChild(defs);

    // Network zones
    const publicZone = _rect(30, 20, 640, 170, 'rgba(248,81,73,0.04)', 'rgba(248,81,73,0.15)');
    svg.appendChild(publicZone);
    svg.appendChild(_text(50, 44, 'PUBLIC NETWORK', '10px', '#f85149', 0.6));

    const internalZone = _rect(30, 300, 640, 150, 'rgba(88,166,255,0.04)', 'rgba(88,166,255,0.15)');
    svg.appendChild(internalZone);
    svg.appendChild(_text(50, 324, 'INTERNAL NETWORK', '10px', '#58a6ff', 0.6));

    // Firewall zone
    const fwZone = _rect(270, 210, 160, 60, 'rgba(210,153,34,0.08)', 'rgba(210,153,34,0.2)');
    svg.appendChild(fwZone);
    svg.appendChild(_text(295, 255, 'DNS only (port 53)', '9px', '#d29922', 0.7));

    // Connections
    for (const conn of CONNECTIONS) {
        const from = CONTAINERS[conn.from];
        const to = CONTAINERS[conn.to];
        const line = _line(from.x, from.y, to.x, to.y, conn.style === 'dashed');
        line.setAttribute('data-from', conn.from);
        line.setAttribute('data-to', conn.to);
        if (conn.opacity) line.style.opacity = conn.opacity;
        line.classList.add('topo-connection');
        svg.appendChild(line);
    }

    // Container nodes
    for (const [name, c] of Object.entries(CONTAINERS)) {
        const g = _el('g');
        g.setAttribute('data-container', name);
        g.classList.add('topo-node');
        g.style.cursor = 'pointer';

        const box = _rect(c.x - 45, c.y - 25, 90, 50, '#1c2128', '#30363d', 6);
        box.classList.add('node-box');
        g.appendChild(box);

        g.appendChild(_text(c.x, c.y - 5, c.icon, '16px', null, 1, 'middle'));
        g.appendChild(_text(c.x, c.y + 16, c.label, '10px', '#e6edf3', 1, 'middle'));

        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dot.setAttribute('cx', c.x + 35);
        dot.setAttribute('cy', c.y - 18);
        dot.setAttribute('r', 4);
        dot.setAttribute('fill', '#484f58');
        dot.classList.add('status-indicator');
        g.appendChild(dot);

        svg.appendChild(g);
    }

    // Packet element (hidden by default)
    const packet = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    packet.setAttribute('r', 6);
    packet.setAttribute('fill', '#58a6ff');
    packet.setAttribute('filter', 'url(#glow)');
    packet.style.display = 'none';
    packet.id = 'packet';
    svg.appendChild(packet);
}

function updateContainerStatus(containers) {
    for (const c of containers) {
        const node = document.querySelector(`[data-container="${c.name}"] .status-indicator`);
        if (node) {
            node.setAttribute('fill', c.status === 'running' ? '#3fb950' : '#f85149');
        }
    }
}

function highlightContainers(names) {
    _highlighted = names;
    document.querySelectorAll('.topo-node').forEach(n => {
        const name = n.getAttribute('data-container');
        if (names.length === 0) {
            n.classList.remove('node-highlight', 'node-dim');
        } else if (names.includes(name)) {
            n.classList.add('node-highlight');
            n.classList.remove('node-dim');
        } else {
            n.classList.remove('node-highlight');
            n.classList.add('node-dim');
        }
    });
    document.querySelectorAll('.topo-connection').forEach(l => {
        const from = l.getAttribute('data-from');
        const to = l.getAttribute('data-to');
        if (names.length === 0) {
            l.style.opacity = l.getAttribute('data-orig-opacity') || '';
        } else if (names.includes(from) && names.includes(to)) {
            l.style.opacity = 1;
        } else {
            l.style.opacity = 0.15;
        }
    });
}

function animatePacketFlow(pathName) {
    if (_animationId) {
        cancelAnimationFrame(_animationId);
        _animationId = null;
    }
    const path = PATHS[pathName];
    if (!path) return;

    const packet = document.getElementById('packet');
    if (!packet) return;

    const colors = { dns_query: '#58a6ff', c2_tunnel: '#f85149', infiltration: '#d29922' };
    packet.setAttribute('fill', colors[pathName] || '#58a6ff');
    packet.style.display = '';

    const points = path.map(name => CONTAINERS[name]);
    const totalSegments = points.length - 1;
    const segmentDuration = 400;
    const totalDuration = totalSegments * segmentDuration;
    const startTime = performance.now();

    function step(now) {
        const elapsed = now - startTime;
        if (elapsed >= totalDuration) {
            packet.style.display = 'none';
            _animationId = null;
            return;
        }
        const progress = elapsed / totalDuration;
        const segFloat = progress * totalSegments;
        const segIdx = Math.min(Math.floor(segFloat), totalSegments - 1);
        const segProgress = segFloat - segIdx;

        const from = points[segIdx];
        const to = points[segIdx + 1];
        const x = from.x + (to.x - from.x) * segProgress;
        const y = from.y + (to.y - from.y) * segProgress;

        packet.setAttribute('cx', x);
        packet.setAttribute('cy', y);
        _animationId = requestAnimationFrame(step);
    }
    _animationId = requestAnimationFrame(step);
}

// SVG helpers
function _el(tag) {
    return document.createElementNS('http://www.w3.org/2000/svg', tag);
}

function _rect(x, y, w, h, fill, stroke, rx) {
    const r = _el('rect');
    r.setAttribute('x', x);
    r.setAttribute('y', y);
    r.setAttribute('width', w);
    r.setAttribute('height', h);
    r.setAttribute('fill', fill || 'none');
    if (stroke) r.setAttribute('stroke', stroke);
    r.setAttribute('stroke-width', '1');
    r.setAttribute('rx', rx || 8);
    return r;
}

function _line(x1, y1, x2, y2, dashed) {
    const l = _el('line');
    l.setAttribute('x1', x1);
    l.setAttribute('y1', y1);
    l.setAttribute('x2', x2);
    l.setAttribute('y2', y2);
    l.setAttribute('stroke', '#484f58');
    l.setAttribute('stroke-width', '1.5');
    if (dashed) l.setAttribute('stroke-dasharray', '6,4');
    return l;
}

function _text(x, y, content, size, fill, opacity, anchor) {
    const t = _el('text');
    t.setAttribute('x', x);
    t.setAttribute('y', y);
    t.setAttribute('font-size', size || '12px');
    t.setAttribute('fill', fill || '#e6edf3');
    t.setAttribute('font-family', "'Inter', sans-serif");
    if (opacity !== undefined) t.setAttribute('opacity', opacity);
    if (anchor) t.setAttribute('text-anchor', anchor);
    t.textContent = content;
    return t;
}

window.Topology = { createTopology, updateContainerStatus, highlightContainers, animatePacketFlow };
