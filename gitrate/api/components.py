"""Dashboard UI components and templates."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

router = APIRouter(tags=["Dashboard UI"])


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitRate Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 32px;
            color: #1a202c;
            margin-bottom: 10px;
        }

        .header p {
            color: #718096;
            font-size: 16px;
        }

        .ml-dashboard-link {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .ml-dashboard-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 20px rgba(0, 0, 0, 0.15);
        }

        .stat-label {
            color: #718096;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 4px;
        }

        .stat-change {
            font-size: 12px;
            color: #48bb78;
        }

        .stat-change.negative {
            color: #f56565;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .chart-title {
            font-size: 18px;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 20px;
        }

        .audits-table {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: #f7fafc;
            border-bottom: 2px solid #e2e8f0;
        }

        th {
            padding: 16px;
            text-align: left;
            font-size: 14px;
            font-weight: 600;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        td {
            padding: 16px;
            border-bottom: 1px solid #e2e8f0;
            color: #2d3748;
        }

        tbody tr:hover {
            background: #f7fafc;
        }

        .score-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            min-width: 60px;
            text-align: center;
        }

        .score-excellent {
            background: #c6f6d5;
            color: #22543d;
        }

        .score-good {
            background: #bee3f8;
            color: #2c5282;
        }

        .score-fair {
            background: #feebc8;
            color: #7c2d12;
        }

        .score-poor {
            background: #fed7d7;
            color: #742a2a;
        }

        .repo-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }

        .repo-link:hover {
            text-decoration: underline;
        }

        .filter-bar {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .filter-group {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        input[type="text"],
        input[type="number"],
        select {
            padding: 10px 15px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
        }

        input[type="text"]:focus,
        input[type="number"]:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        button {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        button:hover {
            background: #5568d3;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #e2e8f0;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .error {
            background: #fed7d7;
            color: #742a2a;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        .success {
            background: #c6f6d5;
            color: #22543d;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 24px;
            }

            .stat-value {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <h1>🚀 GitRate Dashboard</h1>
                <p>Technical Due Diligence Audit Platform - Real-time Analytics & Insights</p>
            </div>
            <a href="/ml-dashboard" class="ml-dashboard-link">🤖 ML Analytics</a>
        </div>

        <!-- Statistics -->
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Audits</div>
                <div class="stat-value" id="total-audits">-</div>
                <div class="stat-change">Updated just now</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average Score</div>
                <div class="stat-value" id="avg-score">-</div>
                <div class="stat-change">0-100 scale</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Repositories</div>
                <div class="stat-value" id="total-repos">-</div>
                <div class="stat-change">Unique repos</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value" id="success-rate">-</div>
                <div class="stat-change">Completed audits</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">Score Distribution</div>
                <canvas id="distribution-chart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Findings by Category</div>
                <canvas id="findings-chart"></canvas>
            </div>
        </div>

        <!-- Filters -->
        <div class="filter-bar">
            <div class="filter-group">
                <input type="text" id="repo-filter" placeholder="Filter by repository...">
                <input type="number" id="score-filter" placeholder="Min score" min="0" max="100">
                <button onclick="applyFilters()">Filter</button>
                <button onclick="resetFilters()" style="background: #cbd5e0; color: #2d3748;">Reset</button>
            </div>
        </div>

        <!-- Recent Audits Table -->
        <div class="audits-table">
            <table>
                <thead>
                    <tr>
                        <th>Repository</th>
                        <th>Overall Score</th>
                        <th>Security</th>
                        <th>Code Quality</th>
                        <th>Team</th>
                        <th>Findings</th>
                        <th>Date</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody id="audits-tbody">
                    <tr>
                        <td colspan="8" style="text-align: center; padding: 40px;">
                            <div class="loading"></div> Loading audits...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Global state
        let allAudits = [];
        let currentFilters = {};

        // Initialize dashboard
        async function init() {
            try {
                await loadStats();
                await loadDistribution();
                await loadFindings();
                await loadAudits();
            } catch (error) {
                console.error('Error initializing dashboard:', error);
                showError('Failed to load dashboard data');
            }
        }

        // Load statistics
        async function loadStats() {
            try {
                const response = await fetch('/api/dashboard/stats');
                if (!response.ok) throw new Error('Failed to load stats');
                
                const stats = await response.json();
                
                document.getElementById('total-audits').textContent = stats.total_audits;
                document.getElementById('avg-score').textContent = stats.average_score.toFixed(1);
                document.getElementById('total-repos').textContent = stats.repositories_audited;
                document.getElementById('success-rate').textContent = (stats.success_rate).toFixed(1) + '%';
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        // Load score distribution
        async function loadDistribution() {
            try {
                const response = await fetch('/api/dashboard/score-distribution');
                if (!response.ok) throw new Error('Failed to load distribution');
                
                const data = await response.json();
                
                const ctx = document.getElementById('distribution-chart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: Object.keys(data),
                        datasets: [{
                            label: 'Number of Audits',
                            data: Object.values(data),
                            backgroundColor: [
                                '#fed7d7',
                                '#feebc8',
                                '#bee3f8',
                                '#c6f6d5',
                                '#b2f5ea',
                            ],
                            borderColor: [
                                '#f56565',
                                '#ed8936',
                                '#4299e1',
                                '#48bb78',
                                '#38b2ac',
                            ],
                            borderWidth: 2,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 1 }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Error loading distribution:', error);
            }
        }

        // Load findings by category
        async function loadFindings() {
            try {
                const response = await fetch('/api/dashboard/findings-by-category');
                if (!response.ok) throw new Error('Failed to load findings');
                
                const data = await response.json();
                const labels = Object.keys(data);
                const values = Object.values(data);
                
                const ctx = document.getElementById('findings-chart').getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: [
                                '#667eea',
                                '#764ba2',
                                '#f093fb',
                                '#4facfe',
                                '#00f2fe',
                                '#43e97b',
                                '#fa709a',
                                '#fee140',
                            ],
                            borderColor: 'white',
                            borderWidth: 2,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Error loading findings:', error);
            }
        }

        // Load recent audits
        async function loadAudits() {
            try {
                const response = await fetch('/api/dashboard/audits?limit=50');
                if (!response.ok) throw new Error('Failed to load audits');
                
                allAudits = await response.json();
                displayAudits(allAudits);
            } catch (error) {
                console.error('Error loading audits:', error);
                showError('Failed to load audits');
            }
        }

        // Display audits in table
        function displayAudits(audits) {
            const tbody = document.getElementById('audits-tbody');
            
            if (audits.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 40px;">No audits found</td></tr>';
                return;
            }

            tbody.innerHTML = audits.map(audit => `
                <tr>
                    <td><a href="https://github.com/${audit.repository}" class="repo-link" target="_blank">${audit.repository}</a></td>
                    <td><span class="score-badge ${getScoreClass(audit.overall_score)}">${audit.overall_score.toFixed(1)}</span></td>
                    <td><span class="score-badge ${getScoreClass(audit.security_score)}">${audit.security_score.toFixed(1)}</span></td>
                    <td><span class="score-badge ${getScoreClass(audit.code_quality_score)}">${audit.code_quality_score.toFixed(1)}</span></td>
                    <td><span class="score-badge ${getScoreClass(audit.team_sustainability_score)}">${audit.team_sustainability_score.toFixed(1)}</span></td>
                    <td>${audit.findings_count} <span style="color: #f56565;">(${audit.critical_findings} 🔴)</span></td>
                    <td>${new Date(audit.created_at).toLocaleDateString()}</td>
                    <td>${audit.duration_seconds.toFixed(1)}s</td>
                </tr>
            `).join('');
        }

        // Get score CSS class
        function getScoreClass(score) {
            if (score >= 80) return 'score-excellent';
            if (score >= 60) return 'score-good';
            if (score >= 40) return 'score-fair';
            return 'score-poor';
        }

        // Apply filters
        function applyFilters() {
            const repo = document.getElementById('repo-filter').value;
            const minScore = parseFloat(document.getElementById('score-filter').value) || 0;
            
            let filtered = allAudits;
            
            if (repo) {
                filtered = filtered.filter(a => a.repository.toLowerCase().includes(repo.toLowerCase()));
            }
            
            filtered = filtered.filter(a => a.overall_score >= minScore);
            
            displayAudits(filtered);
        }

        // Reset filters
        function resetFilters() {
            document.getElementById('repo-filter').value = '';
            document.getElementById('score-filter').value = '';
            displayAudits(allAudits);
        }

        // Show error message
        function showError(message) {
            const error = document.createElement('div');
            error.className = 'error';
            error.textContent = message;
            document.querySelector('.container').insertBefore(error, document.querySelector('.header').nextSibling);
        }

        // Start initialization
        init();

        // Refresh data every 60 seconds
        setInterval(() => {
            loadStats();
            loadAudits();
        }, 60000);
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    """
    Serve main dashboard page.
    
    Returns:
        HTML dashboard page
    """
    return DASHBOARD_HTML


@router.get("/audit/{audit_id}", response_class=HTMLResponse)
async def audit_detail(audit_id: str) -> str:
    """
    Serve audit detail page.
    
    Args:
        audit_id: Audit identifier
    
    Returns:
        HTML detail page
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audit Detail - {audit_id}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50">
        <div class="container mx-auto p-8">
            <h1 class="text-3xl font-bold mb-6">Audit Detail: {audit_id}</h1>
            <div class="bg-white rounded-lg shadow p-6">
                <p>Loading audit details...</p>
            </div>
        </div>
    </body>
    </html>
    """
