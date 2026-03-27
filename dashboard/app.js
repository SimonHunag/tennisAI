const defaultDataPath = '../analysis/training-summary.json';

const sourceStatus = document.getElementById('source-status');
const helperText = document.getElementById('helper-text');
const reloadButton = document.getElementById('reload-button');
const uploadInput = document.getElementById('json-upload');
const filtersGrid = document.getElementById('filters-grid');
const statsGrid = document.getElementById('stats-grid');
const actionBreakdown = document.getElementById('action-breakdown');
const focusBreakdown = document.getElementById('focus-breakdown');
const issueBreakdown = document.getElementById('issue-breakdown');
const autoIssueBreakdown = document.getElementById('auto-issue-breakdown');
const sessionTable = document.getElementById('session-table');
const emptyStateTemplate = document.getElementById('empty-state-template');

function clearNode(node) {
    node.innerHTML = '';
}

function createEmptyState(message) {
    const element = emptyStateTemplate.content.firstElementChild.cloneNode(true);
    element.querySelector('p').textContent = message;
    return element;
}

function formatFilterValue(value, fallback = 'all') {
    if (Array.isArray(value)) {
        return value.length ? value.join(', ') : fallback;
    }
    if (value === null || value === undefined || value === '') {
        return fallback;
    }
    return String(value);
}

function formatScore(value) {
    if (value === null || value === undefined || value === 'n/a') {
        return 'n/a';
    }
    return String(value);
}

function renderFilters(filters = {}) {
    clearNode(filtersGrid);
    const items = [
        { label: 'Action Types', value: formatFilterValue(filters.action_types, 'all') },
        { label: 'Athletes', value: formatFilterValue(filters.athletes, 'all') },
        { label: 'Date From', value: formatFilterValue(filters.date_from, 'none') },
        { label: 'Date To', value: formatFilterValue(filters.date_to, 'none') }
    ];

    items.forEach((item) => {
        const chip = document.createElement('div');
        chip.className = 'filter-chip';
        chip.innerHTML = `
            <div class="filter-label">${item.label}</div>
            <div class="filter-value">${item.value}</div>
        `;
        filtersGrid.appendChild(chip);
    });
}

function renderStats(overview = {}) {
    clearNode(statsGrid);
    const items = [
        { label: 'Total Sessions', value: formatScore(overview.total_sessions) },
        { label: 'Avg Consistency', value: formatScore(overview.average_consistency_score) },
        { label: 'Avg Balance', value: formatScore(overview.average_balance_score) },
        { label: 'Avg Timing', value: formatScore(overview.average_timing_score) }
    ];

    items.forEach((item) => {
        const card = document.createElement('article');
        card.className = 'stat-card';
        card.innerHTML = `
            <p class="stat-label">${item.label}</p>
            <p class="stat-value">${item.value}</p>
        `;
        statsGrid.appendChild(card);
    });
}

function renderMetricList(node, items, emptyMessage) {
    clearNode(node);
    if (!Array.isArray(items) || !items.length) {
        node.appendChild(createEmptyState(emptyMessage));
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'metric-item';
        row.innerHTML = `
            <span class="metric-name">${item.name || item.action_type || 'n/a'}</span>
            <span class="metric-count">${item.count ?? '0'}</span>
        `;
        node.appendChild(row);
    });
}

function badgeMarkup(values) {
    if (!Array.isArray(values) || !values.length) {
        return '<span class="badge">-</span>';
    }
    return values.map((value) => `<span class="badge">${value}</span>`).join('');
}

function textList(values) {
    if (!Array.isArray(values) || !values.length) {
        return '-';
    }
    return values.join(', ');
}

function issueCodeList(items) {
    if (!Array.isArray(items) || !items.length) {
        return '-';
    }
    return items.map((item) => item.issue_code || item.name || '-').join(', ');
}

function metricPairs(metrics) {
    if (!metrics || typeof metrics !== 'object') {
        return '-';
    }
    const entries = Object.entries(metrics)
        .filter(([, value]) => value !== null && value !== undefined)
        .slice(0, 5)
        .map(([key, value]) => `${key}: ${value}`);
    return entries.length ? entries.join(', ') : '-';
}

function renderSessionTable(sessions) {
    clearNode(sessionTable);
    if (!Array.isArray(sessions) || !sessions.length) {
        sessionTable.appendChild(createEmptyState('No sessions matched the current filters.'));
        return;
    }

    const table = document.createElement('table');
    table.innerHTML = `
        <thead>
            <tr>
                <th>Date</th>
                <th>Athlete</th>
                <th>Session</th>
                <th>Action</th>
                <th>Focus</th>
                <th>Issues</th>
                <th>Next Steps</th>
                <th>Scores</th>
                <th>Auto Analysis</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector('tbody');

    sessions.forEach((session) => {
        const autoAnalysis = session.auto_analysis || null;
        const reportLink = session.serve_report_json
            ? `serve-report.html?file=${encodeURIComponent(`../${session.serve_report_json}`)}`
            : null;
        const sessionTitleMarkup = reportLink
            ? `<a class="session-link" href="${reportLink}">${session.session_id || '-'}</a>`
            : `${session.session_id || '-'}`;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="session-cell">${session.date || '-'}</td>
            <td class="session-cell">${session.athlete || session.athlete_id || '-'}</td>
            <td class="session-cell">
                <div class="session-title">${sessionTitleMarkup}</div>
                <div class="session-badges">${badgeMarkup(session.session_tags)}</div>
            </td>
            <td class="session-cell">${session.action_type || '-'}</td>
            <td class="session-cell">${textList(session.focus_points)}</td>
            <td class="session-cell">${textList(session.issues)}</td>
            <td class="session-cell">${textList(session.next_steps)}</td>
            <td class="session-cell">
                <div class="score-stack">
                    <span>C: ${formatScore(session.scores?.consistency)}</span>
                    <span>B: ${formatScore(session.scores?.balance)}</span>
                    <span>T: ${formatScore(session.scores?.timing)}</span>
                </div>
            </td>
            <td class="session-cell">
                <div class="score-stack">
                    <span>Flags: ${issueCodeList(autoAnalysis?.issues)}</span>
                    <span>Next: ${textList(autoAnalysis?.next_focus)}</span>
                    <span>Metrics: ${metricPairs(autoAnalysis?.metrics)}</span>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });

    sessionTable.appendChild(table);
}

function renderDashboard(data) {
    renderFilters(data.filters || {});
    renderStats(data.overview || {});
    renderMetricList(actionBreakdown, data.action_breakdown, 'No action distribution yet.');
    renderMetricList(focusBreakdown, data.top_focus_points, 'No focus points available yet.');
    renderMetricList(issueBreakdown, data.top_issues, 'No recurring issues available yet.');
    renderMetricList(autoIssueBreakdown, data.top_auto_issues, 'No automatic rule hits available yet.');
    renderSessionTable(data.sessions || []);
}

function setLoadedState(message) {
    sourceStatus.innerHTML = message;
    helperText.textContent = 'Refresh the page after regenerating training-summary.json, or choose a different export file manually.';
}

function setErrorState(message) {
    sourceStatus.innerHTML = message;
    helperText.textContent = 'Tip: browsers often block fetch on file:// pages. If that happens, start a local server or choose the JSON file manually.';
}

async function loadFromPath(path) {
    try {
        const response = await fetch(path, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        renderDashboard(data);
        setLoadedState(`Loaded dashboard data from <code>${path}</code>.`);
    } catch (error) {
        renderDashboard({});
        setErrorState(`Auto-load failed for <code>${path}</code>. ${error.message}`);
    }
}

async function loadFromFile(file) {
    if (!file) {
        return;
    }
    try {
        const text = await file.text();
        const data = JSON.parse(text);
        renderDashboard(data);
        setLoadedState(`Loaded dashboard data from selected file <code>${file.name}</code>.`);
    } catch (error) {
        setErrorState(`Could not read <code>${file.name}</code>. ${error.message}`);
    }
}

reloadButton.addEventListener('click', () => {
    loadFromPath(defaultDataPath);
});

uploadInput.addEventListener('change', (event) => {
    loadFromFile(event.target.files?.[0]);
});

loadFromPath(defaultDataPath);
