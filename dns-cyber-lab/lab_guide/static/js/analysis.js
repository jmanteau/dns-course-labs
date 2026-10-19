const DEFAULT_THRESHOLDS = {
    entropy:              { value: 4.0,  direction: 'greater', min: 0, max: 6,   step: 0.1,  label: 'Entropy' },
    non_letter_ratio:     { value: 0.3,  direction: 'greater', min: 0, max: 1,   step: 0.05, label: 'Non-letter ratio' },
    hex_char_ratio:       { value: 0.5,  direction: 'greater', min: 0, max: 1,   step: 0.05, label: 'Hex char ratio' },
    vowel_ratio:          { value: 0.3,  direction: 'less',    min: 0, max: 1,   step: 0.05, label: 'Vowel ratio' },
    n_gram_2:             { value: 10.0, direction: 'less',    min: 0, max: 50,  step: 1,    label: 'N-gram (2)' },
    gini_index:           { value: 0.9,  direction: 'greater', min: 0, max: 1,   step: 0.01, label: 'Gini index' },
    classification_error: { value: 0.85, direction: 'greater', min: 0, max: 1,   step: 0.01, label: 'Classification err' },
    number_of_labels:     { value: 3,    direction: 'greater', min: 1, max: 10,  step: 1,    label: 'Label count' },
    average_interval:     { value: 5.0,  direction: 'less',    min: 0, max: 30,  step: 0.5,  label: 'Avg interval (s)' },
    payload_size:         { value: 50,   direction: 'greater', min: 0, max: 255, step: 5,    label: 'Payload size (B)' },
};

const DEFAULT_WEIGHTS = {
    entropy: 1.5, non_letter_ratio: 0.8, hex_char_ratio: 0.8,
    vowel_ratio: 1.0, n_gram_2: 0.9, gini_index: 1.0,
    classification_error: 0.5, number_of_labels: 1.1,
    average_interval: 1.1, payload_size: 2.0,
};

class AnalysisDashboard {
    constructor(containerEl) {
        this.el = containerEl;
        this.thresholds = {};
        this.weights = {};
        this.thresholdScore = 4.5;
        this.results = null;
        this.loading = false;
        this._debounceTimer = null;

        this.resetDefaults();
        this.render();
    }

    resetDefaults() {
        for (const [k, v] of Object.entries(DEFAULT_THRESHOLDS)) {
            this.thresholds[k] = { value: v.value, direction: v.direction };
        }
        this.weights = { ...DEFAULT_WEIGHTS };
        this.thresholdScore = 4.5;
    }

    render() {
        this.el.innerHTML = `
            <div class="analysis-actions">
                <button class="btn-primary" id="run-analysis">Run Analysis</button>
                <button class="btn-secondary" id="reset-analysis">Reset Defaults</button>
                <span id="analysis-status" style="font-size:12px;color:var(--text-muted);margin-left:8px;"></span>
            </div>
            <div class="analysis-controls">
                <div class="control-group">
                    <h4>Detection Threshold</h4>
                    <div class="slider-row">
                        <label>Score threshold</label>
                        <input type="range" id="threshold-score" min="0" max="15" step="0.5" value="${this.thresholdScore}">
                        <span class="slider-value" id="threshold-score-val">${this.thresholdScore}</span>
                    </div>
                    <h4 style="margin-top:12px">Metric Thresholds</h4>
                    <div id="threshold-sliders"></div>
                </div>
                <div class="control-group">
                    <h4>Metric Weights</h4>
                    <div id="weight-sliders"></div>
                </div>
            </div>
            <div id="analysis-results"></div>
        `;

        this._renderSliders();
        this._bindEvents();
    }

    _renderSliders() {
        const thresholdContainer = this.el.querySelector('#threshold-sliders');
        const weightContainer = this.el.querySelector('#weight-sliders');

        for (const [key, config] of Object.entries(DEFAULT_THRESHOLDS)) {
            const dir = config.direction === 'greater' ? '&gt;' : '&lt;';
            thresholdContainer.innerHTML += `
                <div class="slider-row">
                    <label title="${key}">${config.label} (${dir})</label>
                    <input type="range" data-key="${key}" class="threshold-slider"
                           min="${config.min}" max="${config.max}" step="${config.step}"
                           value="${this.thresholds[key].value}">
                    <span class="slider-value" id="tv-${key}">${this.thresholds[key].value}</span>
                </div>
            `;
        }

        for (const [key, config] of Object.entries(DEFAULT_THRESHOLDS)) {
            weightContainer.innerHTML += `
                <div class="slider-row">
                    <label title="${key}">${config.label}</label>
                    <input type="range" data-key="${key}" class="weight-slider"
                           min="0" max="3" step="0.1"
                           value="${this.weights[key]}">
                    <span class="slider-value" id="wv-${key}">${this.weights[key]}</span>
                </div>
            `;
        }
    }

    _bindEvents() {
        this.el.querySelector('#run-analysis').addEventListener('click', () => this.runAnalysis());
        this.el.querySelector('#reset-analysis').addEventListener('click', () => {
            this.resetDefaults();
            this.render();
            if (this.results) this.rescore();
        });

        this.el.querySelector('#threshold-score').addEventListener('input', (e) => {
            this.thresholdScore = parseFloat(e.target.value);
            this.el.querySelector('#threshold-score-val').textContent = this.thresholdScore;
            this._debouncedRescore();
        });

        this.el.querySelectorAll('.threshold-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const key = e.target.dataset.key;
                this.thresholds[key].value = parseFloat(e.target.value);
                this.el.querySelector(`#tv-${key}`).textContent = e.target.value;
                this._debouncedRescore();
            });
        });

        this.el.querySelectorAll('.weight-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const key = e.target.dataset.key;
                this.weights[key] = parseFloat(e.target.value);
                this.el.querySelector(`#wv-${key}`).textContent = e.target.value;
                this._debouncedRescore();
            });
        });
    }

    _debouncedRescore() {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => this.rescore(), 300);
    }

    async runAnalysis() {
        this.loading = true;
        this._setStatus('Converting logs and analyzing...');
        try {
            const resp = await fetch('/api/analysis/run');
            this.results = await resp.json();
            if (this.results.error) {
                this._setStatus(`Error: ${this.results.error}`);
                return;
            }
            this._setStatus(`Analyzed ${this.results.total_domains_analyzed} domains`);
            this._renderResults();
        } catch (e) {
            this._setStatus(`Error: ${e.message}`);
        }
        this.loading = false;
    }

    async rescore() {
        try {
            const resp = await fetch('/api/analysis/score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    thresholds: this.thresholds,
                    weights: this.weights,
                    threshold_score: this.thresholdScore,
                }),
            });
            this.results = await resp.json();
            if (!this.results.error) {
                this._renderResults();
                this._setStatus(`${this.results.results.length} flagged SLDs (threshold: ${this.thresholdScore})`);
            }
        } catch (e) {
            this._setStatus(`Rescore error: ${e.message}`);
        }
    }

    _setStatus(msg) {
        const el = this.el.querySelector('#analysis-status');
        if (el) el.textContent = msg;
    }

    _renderResults() {
        const container = this.el.querySelector('#analysis-results');
        if (!this.results || !this.results.results) {
            container.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No results yet. Click "Run Analysis".</p>';
            return;
        }

        const rows = this.results.results;
        const globalAvg = this.results.global_averages || {};

        let html = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Domain (SLD)</th>
                        <th>Score</th>
                        <th>Flagged</th>
                        <th>Total FQDNs</th>
                        <th>Key Indicators</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (const row of rows) {
            const isC2 = row.sld.includes('commandcontrol');
            const scoreClass = row.score >= 6 ? 'high' : row.score >= 4.5 ? 'medium' : 'low';
            const flaggedMetrics = Object.entries(row.threshold_flags || {})
                .filter(([_, v]) => v)
                .map(([k]) => k.replace(/_/g, ' '))
                .slice(0, 4)
                .join(', ');

            html += `
                <tr class="${isC2 ? 'flagged' : ''}">
                    <td>${row.sld}</td>
                    <td><span class="score-badge ${scoreClass}">${row.score}</span></td>
                    <td>${row.flagged_count}</td>
                    <td>${row.total_fqdns}</td>
                    <td style="font-size:11px;color:var(--text-muted)">${flaggedMetrics || '-'}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';

        if (rows.length === 0) {
            html = '<p style="color:var(--success);font-size:13px;padding:12px;">No domains flagged at the current threshold.</p>';
        }

        container.innerHTML = html;
    }
}

window.AnalysisDashboard = AnalysisDashboard;
