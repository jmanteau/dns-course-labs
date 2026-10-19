class TerminalManager {
    constructor(panelEl) {
        this.panel = panelEl;
        this.tabs = [];
        this.activeTab = -1;
        this.expanded = false;
    }

    open(containerName) {
        const existing = this.tabs.findIndex(t => t.name === containerName && !t.closed);
        if (existing >= 0) {
            this.activate(existing);
            return;
        }

        this.expand();

        const idx = this.tabs.length;
        const tabData = {
            name: containerName,
            term: null,
            fitAddon: null,
            ws: null,
            closed: false,
            el: null,
        };

        // Create terminal instance div
        const termDiv = document.createElement('div');
        termDiv.className = 'terminal-instance';
        termDiv.id = `term-${containerName}-${idx}`;
        this.panel.querySelector('.terminal-body').appendChild(termDiv);
        tabData.el = termDiv;

        // Create xterm instance
        const term = new Terminal({
            cursorBlink: true,
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            theme: {
                background: '#0d1117',
                foreground: '#e6edf3',
                cursor: '#58a6ff',
                selectionBackground: 'rgba(88, 166, 255, 0.3)',
                black: '#484f58',
                red: '#f85149',
                green: '#3fb950',
                yellow: '#d29922',
                blue: '#58a6ff',
                magenta: '#bc8cff',
                cyan: '#39d353',
                white: '#e6edf3',
            },
        });

        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(termDiv);

        setTimeout(() => fitAddon.fit(), 50);

        tabData.term = term;
        tabData.fitAddon = fitAddon;

        // WebSocket connection
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${location.host}/ws/terminal/${containerName}`);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
            term.writeln(`\x1b[1;34m--- Connected to ${containerName} ---\x1b[0m\r`);
            // Send initial resize
            const dims = fitAddon.proposeDimensions();
            if (dims) {
                ws.send(JSON.stringify({ type: 'resize', cols: dims.cols, rows: dims.rows }));
            }
        };

        ws.onmessage = (event) => {
            if (event.data instanceof ArrayBuffer) {
                term.write(new Uint8Array(event.data));
            } else {
                term.write(event.data);
            }
        };

        ws.onclose = () => {
            term.writeln('\r\n\x1b[1;31m--- Disconnected ---\x1b[0m');
        };

        ws.onerror = () => {
            term.writeln('\r\n\x1b[1;31m--- Connection error ---\x1b[0m');
        };

        term.onData(data => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(data);
            }
        });

        term.onResize(({ cols, rows }) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'resize', cols, rows }));
            }
        });

        tabData.ws = ws;
        this.tabs.push(tabData);
        this.activate(idx);
        this.renderTabs();

        // Refit on window resize
        const resizeHandler = () => {
            if (!tabData.closed && this.expanded) fitAddon.fit();
        };
        window.addEventListener('resize', resizeHandler);
        tabData._resizeHandler = resizeHandler;
    }

    activate(idx) {
        this.activeTab = idx;
        this.tabs.forEach((t, i) => {
            if (t.el) {
                t.el.classList.toggle('active', i === idx);
            }
        });
        this.renderTabs();
        const tab = this.tabs[idx];
        if (tab && tab.fitAddon && this.expanded) {
            setTimeout(() => tab.fitAddon.fit(), 50);
        }
    }

    close(idx) {
        const tab = this.tabs[idx];
        if (!tab) return;
        tab.closed = true;
        if (tab.ws) tab.ws.close();
        if (tab.term) tab.term.dispose();
        if (tab.el) tab.el.remove();
        if (tab._resizeHandler) window.removeEventListener('resize', tab._resizeHandler);

        if (this.activeTab === idx) {
            const nextOpen = this.tabs.findIndex((t, i) => i !== idx && !t.closed);
            if (nextOpen >= 0) {
                this.activate(nextOpen);
            } else {
                this.activeTab = -1;
                this.collapse();
            }
        }
        this.renderTabs();
    }

    expand() {
        this.expanded = true;
        this.panel.classList.remove('collapsed');
        this.panel.classList.add('expanded');
        if (this.activeTab >= 0) {
            const tab = this.tabs[this.activeTab];
            if (tab && tab.fitAddon) setTimeout(() => tab.fitAddon.fit(), 100);
        }
    }

    collapse() {
        this.expanded = false;
        this.panel.classList.remove('expanded');
        this.panel.classList.add('collapsed');
    }

    toggle() {
        if (this.expanded) this.collapse();
        else this.expand();
    }

    renderTabs() {
        const container = this.panel.querySelector('.terminal-tabs');
        const toggle = container.querySelector('.terminal-toggle');
        // Remove old tabs
        container.querySelectorAll('.terminal-tab').forEach(el => el.remove());

        this.tabs.forEach((tab, idx) => {
            if (tab.closed) return;
            const el = document.createElement('div');
            el.className = `terminal-tab ${idx === this.activeTab ? 'active' : ''}`;
            el.innerHTML = `<span>${tab.name}</span><span class="close-tab">&times;</span>`;
            el.querySelector('span:first-child').addEventListener('click', () => this.activate(idx));
            el.querySelector('.close-tab').addEventListener('click', (e) => {
                e.stopPropagation();
                this.close(idx);
            });
            container.insertBefore(el, toggle);
        });
    }

    sendCommand(containerName, command) {
        this.open(containerName);
        setTimeout(() => {
            const tab = this.tabs.find(t => t.name === containerName && !t.closed);
            if (tab && tab.ws && tab.ws.readyState === WebSocket.OPEN) {
                tab.ws.send(command + '\n');
            }
        }, 500);
    }
}

window.TerminalManager = TerminalManager;
