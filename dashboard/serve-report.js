const defaultDataPath = '../analysis/Serving_practice_1-serve-report.json';

const sourceStatus = document.getElementById('source-status');
const helperText = document.getElementById('helper-text');
const reloadButton = document.getElementById('reload-button');
const uploadInput = document.getElementById('json-upload');
const overallAssessment = document.getElementById('overall-assessment');
const trainingPriorities = document.getElementById('training-priorities');
const statsGrid = document.getElementById('stats-grid');
const commonIssues = document.getElementById('common-issues');
const strengths = document.getElementById('strengths');
const metricOverview = document.getElementById('metric-overview');
const clipGrid = document.getElementById('clip-grid');
const emptyStateTemplate = document.getElementById('empty-state-template');

function clearNode(node) {
    node.innerHTML = '';
}

function createEmptyState(message) {
    const element = emptyStateTemplate.content.firstElementChild.cloneNode(true);
    element.querySelector('p').textContent = message;
    return element;
}

function formatMetric(value) {
    if (value === null || value === undefined) {
        return '未稳定识别';
    }
    if (typeof value === 'number') {
        return value.toFixed(3);
    }
    return String(value);
}

function formatSeconds(value) {
    if (value === null || value === undefined) {
        return '-';
    }
    const minutes = Math.floor(value / 60);
    const seconds = value - minutes * 60;
    if (minutes > 0) {
        return `${minutes}:${seconds.toFixed(1).padStart(4, '0')}`;
    }
    return `${seconds.toFixed(1)}s`;
}

function renderStory(data) {
    overallAssessment.textContent = data.overall_assessment || '暂无整体判断。';
    clearNode(trainingPriorities);
    if (!Array.isArray(data.training_priorities) || !data.training_priorities.length) {
        trainingPriorities.appendChild(createEmptyState('暂无训练建议。'));
        return;
    }

    data.training_priorities.forEach((item) => {
        const block = document.createElement('div');
        block.className = 'callout-item';
        block.textContent = item;
        trainingPriorities.appendChild(block);
    });
}

function renderStats(data) {
    clearNode(statsGrid);
    const items = [
        { label: '原始视频', value: data.video_file || '-' },
        { label: '分析模型', value: data.provider || '-' },
        { label: '识别片段', value: data.clip_count ?? '-' },
        { label: '首要问题', value: data.common_issues?.[0]?.label || '-' }
    ];

    items.forEach((item) => {
        const card = document.createElement('article');
        card.className = 'stat-tile';
        card.innerHTML = `
            <p class="stat-label">${item.label}</p>
            <p class="stat-value">${item.value}</p>
        `;
        statsGrid.appendChild(card);
    });
}

function renderCommonIssues(items) {
    clearNode(commonIssues);
    if (!Array.isArray(items) || !items.length) {
        commonIssues.appendChild(createEmptyState('暂无共性问题。'));
        return;
    }

    items.forEach((item) => {
        const row = document.createElement('article');
        row.className = 'issue-item';
        row.innerHTML = `
            <div class="issue-top">
                <div class="issue-name">${item.label}</div>
                <div class="issue-count">${item.count}</div>
            </div>
            <div class="issue-explanation">${item.explanation || ''}</div>
            <div class="issue-training">训练建议: ${item.training || '-'}</div>
        `;
        commonIssues.appendChild(row);
    });
}

function renderPills(node, items, emptyMessage) {
    clearNode(node);
    if (!Array.isArray(items) || !items.length) {
        node.appendChild(createEmptyState(emptyMessage));
        return;
    }

    items.forEach((item) => {
        const pill = document.createElement('div');
        pill.className = 'pill';
        pill.innerHTML = `
            <span class="pill-name">${item.name}</span>
            <span class="pill-count">${item.count}</span>
        `;
        node.appendChild(pill);
    });
}

function renderMetricOverview(items) {
    clearNode(metricOverview);
    if (!Array.isArray(items) || !items.length) {
        metricOverview.appendChild(createEmptyState('暂无指标概览。'));
        return;
    }

    items.forEach((item) => {
        const tile = document.createElement('article');
        tile.className = 'metric-tile';
        tile.innerHTML = `
            <p class="metric-label">${item.name}</p>
            <p class="metric-value">${formatMetric(item.average)}</p>
        `;
        metricOverview.appendChild(tile);
    });
}

function badgeMarkup(values, key = 'label') {
    if (!Array.isArray(values) || !values.length) {
        return '<span class="badge">-</span>';
    }
    return values.map((value) => `<span class="badge">${value[key] || value}</span>`).join('');
}

function renderClips(items) {
    clearNode(clipGrid);
    if (!Array.isArray(items) || !items.length) {
        clipGrid.appendChild(createEmptyState('暂无分段结果。'));
        return;
    }

    items.forEach((clip) => {
        const card = document.createElement('article');
        card.className = 'clip-card';

        const metricLines = Object.entries(clip.metrics || {})
            .map(([name, value]) => `
                <div class="metric-line">
                    <span>${name}</span>
                    <strong>${formatMetric(value)}</strong>
                </div>
            `)
            .join('');

        card.innerHTML = `
            <div class="clip-header">
                <h3 class="clip-title">${clip.clip_id}</h3>
                <div class="clip-time">${formatSeconds(clip.time_start)} - ${formatSeconds(clip.time_end)} · ${clip.duration_seconds.toFixed(1)}s</div>
            </div>
            <div>
                <p class="clip-label">命中问题</p>
                <div class="badge-row">${badgeMarkup(clip.issues)}</div>
            </div>
            <div>
                <p class="clip-label">下次重点</p>
                <div class="badge-row">${badgeMarkup(clip.next_focus)}</div>
            </div>
            <div>
                <p class="clip-label">相对较好</p>
                <div class="badge-row">${badgeMarkup(clip.strengths)}</div>
            </div>
            <div>
                <p class="clip-label">关键指标</p>
                <div class="metric-lines">${metricLines}</div>
            </div>
        `;
        clipGrid.appendChild(card);
    });
}

function renderReport(data) {
    renderStory(data);
    renderStats(data);
    renderCommonIssues(data.common_issues || []);
    renderPills(strengths, data.strengths || [], '暂无明显强项。');
    renderMetricOverview(data.metric_overview || []);
    renderClips(data.clips || []);
}

function setLoadedState(message) {
    sourceStatus.innerHTML = message;
    helperText.textContent = '重新生成报告 JSON 后点 Reload，或者手动选择别的 serve-report.json。';
}

function setErrorState(message) {
    sourceStatus.innerHTML = message;
    helperText.textContent = '如果 file:// 页面拦截了读取，请先启动本地静态服务器，或者手动选择报告 JSON。';
}

async function loadFromPath(path) {
    try {
        const response = await fetch(path, { cache: 'no-store' });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        renderReport(data);
        setLoadedState(`Loaded serve report from <code>${path}</code>.`);
    } catch (error) {
        renderReport({});
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
        renderReport(data);
        setLoadedState(`Loaded serve report from selected file <code>${file.name}</code>.`);
    } catch (error) {
        setErrorState(`Could not read <code>${file.name}</code>. ${error.message}`);
    }
}

reloadButton.addEventListener('click', () => loadFromPath(defaultDataPath));
uploadInput.addEventListener('change', (event) => loadFromFile(event.target.files?.[0]));

loadFromPath(defaultDataPath);
