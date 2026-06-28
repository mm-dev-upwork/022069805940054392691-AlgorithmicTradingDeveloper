/**
 * Trading Strategy Doctor — Dashboard Controller
 * ================================================
 * Manages filters, metrics, health score, table, theme, and export.
 */

(function () {
    'use strict';

    // --- Initialisation ---
    document.addEventListener('DOMContentLoaded', async function () {
        initTheme();
        initCharts();            // Initialise all 6 Chart.js instances
        populateFilters();
        initFilterEvents();
        initTableEvents();
        initExportButton();
        await refreshAll();
    });

    // --- Theme ---
    function initTheme() {
        const saved = localStorage.getItem('tsd-theme');
        if (saved === 'dark') {
            document.body.classList.add('dark-mode');
        }
        document.getElementById('themeToggle').addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('tsd-theme',
                document.body.classList.contains('dark-mode') ? 'dark' : 'light');
            // Re-render charts with new colours
            refreshAll();
        });
    }

    // --- Filters ---
    async function populateFilters() {
        try {
            const resp = await fetch('/api/data/filters');
            const options = await resp.json();
            document.querySelectorAll('.filter-group').forEach(group => {
                const canon = group.dataset.filter;
                const vals = options[canon] || [];
                const sel = group.querySelector('select');
                sel.innerHTML = vals.map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');
            });
        } catch (err) {
            console.error('Failed to load filter options:', err);
        }
    }

    function initFilterEvents() {
        document.getElementById('applyFiltersBtn').addEventListener('click', refreshAll);
        document.getElementById('resetFiltersBtn').addEventListener('click', () => {
            document.querySelectorAll('.filter-group select').forEach(s => s.selectedIndex = -1);
            document.getElementById('dateFrom').value = '';
            document.getElementById('dateTo').value = '';
            refreshAll();
        });
    }

    // --- Refresh all data ---
    async function refreshAll() {
        // Single consolidated API call replaces 8 separate calls
        const qs = buildFilterQueryString();
        try {
            const resp = await fetch('/api/data/dashboard' + qs);
            const data = await resp.json();
            renderMetrics(data.metrics);
            renderHealth(data.healthScore, data.diagnosis);
            renderChartsData(data);
        } catch (err) {
            console.error('Failed to load dashboard data:', err);
        }
        // Trade table is paginated — separate call (only 1 extra, not 8)
        updateTable();
    }

    // --- Metrics ---
    function renderMetrics(m) {
        const map = {
            netProfit:      { fmt: v => '$' + formatNum(v), cls: v => v >= 0 ? 'positive' : 'negative' },
            totalTrades:    { fmt: v => v, cls: () => '' },
            winRate:        { fmt: v => v + '%', cls: () => '' },
            profitFactor:   { fmt: v => v, cls: () => '' },
            avgWinner:      { fmt: v => '$' + formatNum(v), cls: () => 'positive' },
            avgLoser:       { fmt: v => '$' + formatNum(v), cls: () => 'negative' },
            avgRR:          { fmt: v => v, cls: () => '' },
            maxDrawdown:    { fmt: v => v + '%', cls: v => v > 20 ? 'negative' : '' },
            avgTradeDuration: { fmt: v => v + ' min', cls: () => '' },
            avgMfe:         { fmt: v => '$' + formatNum(v), cls: () => 'positive' },
            avgMae:         { fmt: v => '$' + formatNum(v), cls: () => 'negative' },
            largestWinner:  { fmt: v => '$' + formatNum(v), cls: () => 'positive' },
            largestLoser:   { fmt: v => '$' + formatNum(v), cls: v => v < 0 ? 'negative' : '' },
        };
        document.querySelectorAll('.metric-card').forEach(card => {
            const key = card.dataset.metric;
            const val = m[key];
            const cfg = map[key];
            const el = card.querySelector('.metric-value');
            if (cfg) {
                el.textContent = cfg.fmt(val);
                el.className = 'metric-value ' + (cfg.cls ? cfg.cls(val) : '');
            } else {
                el.textContent = val != null ? val : '—';
            }
        });
    }

    // --- Health Score ---
    function renderHealth(score, diag) {
        document.getElementById('healthScore').textContent = score.score + ' / 100';
        document.getElementById('healthScore').style.color = score.color;
        document.getElementById('healthLabel').textContent = score.label;

        renderDiagnosis('strengthsList', diag.strengths, 'text-success');
        renderDiagnosis('weaknessesList', diag.weaknesses, 'text-warning');
        renderDiagnosis('risksList', diag.risks, 'text-danger');
        renderDiagnosis('recommendationsList', diag.recommendations, 'text-info');
    }

    // --- Charts data (fed from consolidated endpoint) ---
    function renderChartsData(data) {
        if (typeof setChartData !== 'function') return;

        // Equity
        setChartData(CHARTS.equity, data.equity.map(d => d.date), data.equity.map(d => d.equity));

        // Win / Loss
        CHARTS.winLoss.data.datasets[0].data = [data.winLoss.wins, data.winLoss.losses];
        CHARTS.winLoss.update();

        // PnL Distribution
        setChartData(CHARTS.pnlDist,
            data.pnlDistribution.map(d => d.binStart.toFixed(2)),
            data.pnlDistribution.map(d => d.count));

        // Monthly PnL
        CHARTS.monthlyPnl.data.labels = data.monthlyPnl.map(d => d.month);
        CHARTS.monthlyPnl.data.datasets[0].data = data.monthlyPnl.map(d => d.pnl);
        CHARTS.monthlyPnl.data.datasets[0].backgroundColor = data.monthlyPnl.map(d => d.pnl >= 0 ? '#198754' : '#dc3545');
        CHARTS.monthlyPnl.update();

        // Drawdown
        setChartData(CHARTS.drawdown, data.drawdown.map(d => d.date), data.drawdown.map(d => d.drawdown));

        // Duration
        setChartData(CHARTS.duration,
            data.durationHistogram.map(d => d.binStart.toFixed(1) + '-' + d.binEnd.toFixed(1)),
            data.durationHistogram.map(d => d.count));
    }

    function renderDiagnosis(listId, items, className) {
        const list = document.getElementById(listId);
        if (!items || items.length === 0) {
            list.innerHTML = '<li class="text-secondary">—</li>';
            return;
        }
        list.innerHTML = items.map(i =>
            `<li class="${className} mb-1">${i.severity === 'critical' ? '⚠ ' : i.severity === 'good' ? '✓ ' : '✗ '}${escapeHtml(i.message)}</li>`
        ).join('');
    }

    // --- Trade Table ---
    let currentPage = 1;
    let currentSortBy = 'Date';
    let currentSortDir = 'desc';
    let currentSearch = '';
    let currentPerPage = 50;

    function initTableEvents() {
        document.getElementById('tableSearch').addEventListener('input', e => {
            currentSearch = e.target.value;
            currentPage = 1;
            updateTable();
        });
        document.getElementById('perPageSelect').addEventListener('change', e => {
            currentPerPage = parseInt(e.target.value);
            currentPage = 1;
            updateTable();
        });
    }

    async function updateTable() {
        const qs = buildFilterQueryString();
        const sep = qs ? '&' : '?';
        const url = `/api/data/trades${qs}${sep}page=${currentPage}&per_page=${currentPerPage}&sort_by=${currentSortBy}&sort_dir=${currentSortDir}&search=${encodeURIComponent(currentSearch)}`;

        try {
            const resp = await fetch(url);
            const data = await resp.json();

            // Render header
            const thead = document.getElementById('tableHeader');
            thead.innerHTML = data.columns.map(col =>
                `<th data-sort="${col}" class="${col === currentSortBy ? 'active' : ''}">
                    ${escapeHtml(col)}
                    <span class="sort-icon">${col === currentSortBy ? (currentSortDir === 'asc' ? '▲' : '▼') : '⇅'}</span>
                </th>`
            ).join('');

            // Attach sort handlers
            thead.querySelectorAll('th').forEach(th => {
                th.addEventListener('click', () => {
                    const col = th.dataset.sort;
                    if (col === currentSortBy) {
                        currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
                    } else {
                        currentSortBy = col;
                        currentSortDir = 'desc';
                    }
                    currentPage = 1;
                    updateTable();
                });
            });

            // Render body
            const tbody = document.getElementById('tableBody');
            if (data.trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="99" class="text-center text-secondary py-4">No trades found.</td></tr>';
            } else {
                tbody.innerHTML = data.trades.map(trade => {
                    const netPnl = parseFloat(trade.NetPnl || 0);
                    const rowClass = netPnl > 0 ? 'win' : netPnl < 0 ? 'loss' : '';
                    return `<tr class="${rowClass}">${data.columns.map(col =>
                        `<td>${escapeHtml(String(trade[col] ?? ''))}</td>`
                    ).join('')}</tr>`;
                }).join('');
            }

            // Pagination
            renderPagination(data.total, data.page, data.perPage);

        } catch (err) {
            console.error('Failed to load trades:', err);
        }
    }

    function renderPagination(total, page, perPage) {
        const totalPages = Math.max(1, Math.ceil(total / perPage));
        const nav = document.getElementById('tablePagination');
        let html = '';

        html += `<li class="page-item ${page <= 1 ? 'disabled' : ''}">
            <a class="page-link" data-page="${page - 1}">‹</a></li>`;

        const startPage = Math.max(1, page - 2);
        const endPage = Math.min(totalPages, page + 2);
        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === page ? 'active' : ''}">
                <a class="page-link" data-page="${i}">${i}</a></li>`;
        }

        html += `<li class="page-item ${page >= totalPages ? 'disabled' : ''}">
            <a class="page-link" data-page="${page + 1}">›</a></li>`;

        html += `<li class="ms-2 text-secondary small align-self-center">${total} trades</li>`;

        nav.innerHTML = html;
        nav.querySelectorAll('.page-link[data-page]').forEach(a => {
            a.addEventListener('click', e => {
                e.preventDefault();
                const p = parseInt(a.dataset.page);
                if (p >= 1 && p <= totalPages) {
                    currentPage = p;
                    updateTable();
                }
            });
        });
    }

    // --- Export ---
    function initExportButton() {
        document.getElementById('exportBtn').addEventListener('click', () => {
            const qs = buildFilterQueryString();
            window.open('/api/export/report' + qs, '_blank');
        });
    }

    // --- Utilities ---
    function formatNum(v) {
        if (v == null || isNaN(v)) return '0.00';
        if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return v.toFixed(2);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

})();
