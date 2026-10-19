document.addEventListener('DOMContentLoaded', async () => {
    // Initialize topology
    const svgEl = document.getElementById('topology-svg');
    Topology.createTopology(svgEl);

    // Initialize terminal manager
    const termPanel = document.getElementById('terminal-panel');
    const termManager = new TerminalManager(termPanel);
    window._termManager = termManager;

    // Terminal toggle
    document.getElementById('terminal-toggle').addEventListener('click', () => termManager.toggle());

    // Initialize analysis dashboard
    const analysisDash = new AnalysisDashboard(document.getElementById('analysis-body'));

    // Load containers
    let containers = [];
    async function refreshContainers() {
        try {
            const resp = await fetch('/api/containers');
            containers = await resp.json();
            renderContainerStatus(containers);
            Topology.updateContainerStatus(containers);
        } catch (e) {
            console.error('Failed to refresh containers:', e);
        }
    }

    function renderContainerStatus(containers) {
        const statusBar = document.getElementById('status-bar');
        statusBar.innerHTML = '';
        for (const c of containers) {
            const badge = document.createElement('div');
            badge.className = 'container-badge';
            badge.innerHTML = `<span class="status-dot ${c.status}"></span><span>${c.name}</span>`;
            badge.addEventListener('click', () => termManager.open(c.name));
            badge.title = `Click to open terminal for ${c.name}`;
            statusBar.appendChild(badge);
        }

        const sidebar = document.getElementById('container-list');
        sidebar.innerHTML = '';
        for (const c of containers) {
            const ips = Object.values(c.networks || {}).filter(Boolean).join(', ');
            const item = document.createElement('div');
            item.className = 'container-item';
            item.innerHTML = `
                <span class="status-dot ${c.status}"></span>
                <span class="name">${c.name}</span>
                <span class="ip">${ips || 'N/A'}</span>
            `;
            item.addEventListener('click', () => termManager.open(c.name));
            sidebar.appendChild(item);
        }
    }

    await refreshContainers();
    setInterval(refreshContainers, 10000);

    // Load lab steps
    let steps = {};
    try {
        const resp = await fetch('/api/lab/steps');
        steps = await resp.json();
    } catch (e) {
        console.error('Failed to load steps:', e);
    }

    // Phase tabs
    let activePhase = 'red';
    const openSteps = new Set();

    function renderPhase(phase) {
        activePhase = phase;
        document.querySelectorAll('.phase-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.phase === phase);
        });

        const phaseSteps = steps[phase] || [];
        const stepsEl = document.getElementById('steps-list');
        stepsEl.innerHTML = '';
        stepsEl.className = `phase-${phase}`;

        phaseSteps.forEach((step, idx) => {
            const stepEl = document.createElement('div');
            stepEl.className = `step ${openSteps.has(step.id) ? 'open' : ''}`;
            stepEl.innerHTML = `
                <div class="step-header" data-step-id="${step.id}">
                    <div class="step-number">${idx + 1}</div>
                    <div class="step-title">${step.title}</div>
                    <div class="step-chevron">&#9654;</div>
                </div>
                <div class="step-body" style="display:${openSteps.has(step.id) ? 'block' : 'none'}">
                    <div class="step-description">${step.description}</div>
                    ${renderSubsteps(step)}
                </div>
            `;

            const header = stepEl.querySelector('.step-header');
            header.addEventListener('click', () => {
                const isOpen = stepEl.classList.toggle('open');
                stepEl.querySelector('.step-body').style.display = isOpen ? 'block' : 'none';
                if (isOpen) {
                    openSteps.add(step.id);
                    Topology.highlightContainers(step.containers_involved || []);
                    if (step.animation) Topology.animatePacketFlow(step.animation);
                } else {
                    openSteps.delete(step.id);
                    Topology.highlightContainers([]);
                }
            });

            stepsEl.appendChild(stepEl);
        });

        // Bind command buttons
        stepsEl.querySelectorAll('.btn-copy').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const cmd = e.target.closest('.command-block').querySelector('pre').textContent;
                navigator.clipboard.writeText(cmd).then(() => {
                    e.target.textContent = 'Copied!';
                    e.target.classList.add('copied');
                    setTimeout(() => {
                        e.target.textContent = 'Copy';
                        e.target.classList.remove('copied');
                    }, 1500);
                });
            });
        });

        stepsEl.querySelectorAll('.btn-run').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const container = e.target.dataset.container;
                const cmd = e.target.dataset.command;
                termManager.sendCommand(container, cmd);
            });
        });
    }

    function renderSubsteps(step) {
        return (step.substeps || []).map(sub => {
            let cmdBlock = '';
            if (sub.command) {
                const runBtn = sub.executable && sub.target_container
                    ? `<button class="btn btn-run" data-container="${sub.target_container}" data-command="${escapeAttr(sub.command)}">&#9654; Run</button>`
                    : '';
                const targetLabel = sub.target_container ? sub.target_container : 'host';
                cmdBlock = `
                    <div class="command-block">
                        <div class="command-block-header">
                            <span>${targetLabel}</span>
                            <div class="command-actions">
                                <button class="btn btn-copy">Copy</button>
                                ${runBtn}
                            </div>
                        </div>
                        <pre>${escapeHtml(sub.command)}</pre>
                    </div>
                `;
            }
            const noteHtml = sub.note ? `<div class="substep-note">${sub.note}</div>` : '';
            const expectedHtml = sub.expected_output
                ? `<details><summary style="font-size:12px;color:var(--text-muted);cursor:pointer;margin-top:4px;">Expected output</summary><div class="expected-output">${escapeHtml(sub.expected_output)}</div></details>`
                : '';
            return `
                <div class="substep">
                    <div class="substep-instruction">${sub.instruction}</div>
                    ${cmdBlock}
                    ${noteHtml}
                    ${expectedHtml}
                </div>
            `;
        }).join('');
    }

    document.querySelectorAll('.phase-tab').forEach(tab => {
        tab.addEventListener('click', () => renderPhase(tab.dataset.phase));
    });

    renderPhase('red');

    // Analysis toggle
    document.getElementById('analysis-toggle').addEventListener('click', () => {
        const body = document.getElementById('analysis-body');
        const isOpen = body.style.display !== 'none';
        body.style.display = isOpen ? 'none' : 'block';
        document.getElementById('analysis-chevron').style.transform = isOpen ? '' : 'rotate(90deg)';
    });
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
