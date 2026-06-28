/**
 * Trading Strategy Doctor — Charts Module
 * =========================================
 * Chart.js initialisation and update helpers.
 * All 6 chart instances are held in a globally accessible object.
 */

const CHARTS = {};

const CHART_COLORS = {
    green:  '#198754',
    red:    '#dc3545',
    blue:   '#0d6efd',
    yellow: '#ffc107',
    cyan:   '#0dcaf0',
    purple: '#6f42c1',
    gray:   '#6c757d',
    grid:   'rgba(108, 117, 125, 0.12)',
};

function getTextColor() {
    return getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#1a1a2e';
}
function getGridColor() {
    return 'rgba(108, 117, 125, 0.12)';
}

/**
 * Initialise all 6 charts with empty data.
 * Called once on page load.
 */
function initCharts() {
    const opts = (title) => ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: getTextColor(), font: { size: 11 } } },
            tooltip: { backgroundColor: getComputedStyle(document.body).getPropertyValue('--bg-card').trim() || '#fff',
                       titleColor: getTextColor(), bodyColor: getTextColor(),
                       borderColor: getGridColor(), borderWidth: 1 },
        },
        scales: {
            x: { ticks: { color: getTextColor(), font: { size: 10 } }, grid: { color: getGridColor() } },
            y: { ticks: { color: getTextColor(), font: { size: 10 } }, grid: { color: getGridColor() } },
        },
    });

    // 1. Equity Curve
    const ctx1 = document.getElementById('equityChart').getContext('2d');
    CHARTS.equity = new Chart(ctx1, {
        type: 'line',
        data: { labels: [], datasets: [{
            label: 'Equity',
            data: [],
            borderColor: CHART_COLORS.blue,
            backgroundColor: 'rgba(13, 110, 253, 0.08)',
            fill: true,
            tension: 0.2,
            pointRadius: 0,
            borderWidth: 2,
        }]},
        options: { ...opts('Equity Curve'),
                   plugins: { ...opts('').plugins, legend: { display: false } } },
    });

    // 2. Win vs Loss (doughnut)
    const ctx2 = document.getElementById('winLossChart').getContext('2d');
    CHARTS.winLoss = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: ['Wins', 'Losses'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [CHART_COLORS.green, CHART_COLORS.red],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: getTextColor(), font: { size: 11 } } },
                tooltip: { backgroundColor: '#fff', titleColor: '#1a1a2e', bodyColor: '#1a1a2e' },
            },
        },
    });

    // 3. PnL Distribution
    const ctx3 = document.getElementById('pnlDistChart').getContext('2d');
    CHARTS.pnlDist = new Chart(ctx3, {
        type: 'bar',
        data: { labels: [], datasets: [{
            label: 'Frequency',
            data: [],
            backgroundColor: CHART_COLORS.blue,
            borderWidth: 0,
            borderRadius: 2,
        }]},
        options: { ...opts('PnL Distribution'),
                   plugins: { ...opts('').plugins, legend: { display: false } } },
    });

    // 4. Monthly Profit
    const ctx4 = document.getElementById('monthlyPnlChart').getContext('2d');
    CHARTS.monthlyPnl = new Chart(ctx4, {
        type: 'bar',
        data: { labels: [], datasets: [{
            label: 'PnL',
            data: [],
            backgroundColor: [],
            borderWidth: 0,
            borderRadius: 2,
        }]},
        options: { ...opts('Monthly Profit'),
                   plugins: { ...opts('').plugins, legend: { display: false } } },
    });

    // 5. Drawdown Curve
    const ctx5 = document.getElementById('drawdownChart').getContext('2d');
    CHARTS.drawdown = new Chart(ctx5, {
        type: 'line',
        data: { labels: [], datasets: [{
            label: 'Drawdown %',
            data: [],
            borderColor: CHART_COLORS.red,
            backgroundColor: 'rgba(220, 53, 69, 0.1)',
            fill: true,
            tension: 0.2,
            pointRadius: 0,
            borderWidth: 2,
        }]},
        options: { ...opts('Drawdown Curve'),
                   plugins: { ...opts('').plugins, legend: { display: false } } },
    });

    // 6. Duration Histogram
    const ctx6 = document.getElementById('durationChart').getContext('2d');
    CHARTS.duration = new Chart(ctx6, {
        type: 'bar',
        data: { labels: [], datasets: [{
            label: 'Trades',
            data: [],
            backgroundColor: CHART_COLORS.purple,
            borderWidth: 0,
            borderRadius: 2,
        }]},
        options: { ...opts('Duration Histogram'),
                   plugins: { ...opts('').plugins, legend: { display: false } } },
    });
}

/**
 * Update all charts with fresh data from the API.
 * Called after every filter change.
 */
async function updateCharts() {
    const qs = buildFilterQueryString();

    try {
        // Equity Curve
        const eqData = await fetchData('/api/data/equity' + qs);
        setChartData(CHARTS.equity, eqData.map(d => d.date), eqData.map(d => d.equity));

        // Win / Loss
        const wlData = await fetchData('/api/data/win-loss' + qs);
        CHARTS.winLoss.data.datasets[0].data = [wlData.wins, wlData.losses];
        CHARTS.winLoss.update();

        // PnL Distribution
        const pdData = await fetchData('/api/data/pnl-distribution' + qs);
        const pdLabels = pdData.map(d => d.binStart.toFixed(2));
        const pdValues = pdData.map(d => d.count);
        setChartData(CHARTS.pnlDist, pdLabels, pdValues);

        // Monthly PnL
        const mpData = await fetchData('/api/data/monthly-pnl' + qs);
        const mpLabels = mpData.map(d => d.month);
        const mpValues = mpData.map(d => d.pnl);
        CHARTS.monthlyPnl.data.labels = mpLabels;
        CHARTS.monthlyPnl.data.datasets[0].data = mpValues;
        CHARTS.monthlyPnl.data.datasets[0].backgroundColor = mpValues.map(v => v >= 0 ? CHART_COLORS.green : CHART_COLORS.red);
        CHARTS.monthlyPnl.update();

        // Drawdown
        const ddData = await fetchData('/api/data/drawdown' + qs);
        setChartData(CHARTS.drawdown, ddData.map(d => d.date), ddData.map(d => d.drawdown));

        // Duration
        const durData = await fetchData('/api/data/duration-histogram' + qs);
        const durLabels = durData.map(d => d.binStart.toFixed(1) + '-' + d.binEnd.toFixed(1));
        const durValues = durData.map(d => d.count);
        setChartData(CHARTS.duration, durLabels, durValues);

    } catch (err) {
        console.error('Failed to update charts:', err);
    }
}

/* --- Helpers --- */

function setChartData(chart, labels, values) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update();
}

async function fetchData(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

function buildFilterQueryString() {
    const params = new URLSearchParams();
    // Map canonical names (from data-filter) → backend query param names
    const paramMap = {
        'Symbol': 'symbol',
        'StrategyName': 'strategy',
        'Session': 'session',
        'TimeFrame': 'timeframe',
        'StateMachine': 'stateMachine',
        'ExitReason': 'exitReason',
    };
    document.querySelectorAll('.filter-group select').forEach(sel => {
        const canon = sel.closest('.filter-group').dataset.filter;
        const param = paramMap[canon] || canon.toLowerCase();
        Array.from(sel.selectedOptions).forEach(opt => params.append(param, opt.value));
    });
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    if (dateFrom) params.set('dateFrom', dateFrom);
    if (dateTo) params.set('dateTo', dateTo);
    const qs = params.toString();
    return qs ? '?' + qs : '';
}
