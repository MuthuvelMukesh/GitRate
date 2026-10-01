"""ML Analytics Dashboard UI Component - Phase 8

Interactive dashboard for ML features:
- Anomaly detection visualization
- Score predictions with confidence intervals
- Repository clustering charts
- Automated insights display
- Real-time alerts
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ML Dashboard UI"])


ML_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitRate ML Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1600px;
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

        .back-link {
            background: #4a5568;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .back-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
            background: #2d3748;
        }

        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .nav-tab {
            background: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .nav-tab:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .nav-tab.active {
            background: #667eea;
            color: white;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }

        .card h3 {
            font-size: 20px;
            color: #1a202c;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }

        .insight-card {
            background: white;
            border-left: 4px solid;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }

        .insight-card:hover {
            transform: translateX(4px);
        }

        .insight-card.critical {
            border-left-color: #f56565;
            background: #fff5f5;
        }

        .insight-card.high {
            border-left-color: #ed8936;
            background: #fffaf0;
        }

        .insight-card.medium {
            border-left-color: #ecc94b;
            background: #fffff0;
        }

        .insight-card.low {
            border-left-color: #48bb78;
            background: #f0fff4;
        }

        .insight-title {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 8px;
            color: #1a202c;
        }

        .insight-description {
            color: #4a5568;
            font-size: 14px;
            margin-bottom: 12px;
            line-height: 1.5;
        }

        .insight-recommendations {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #e2e8f0;
        }

        .recommendation {
            display: flex;
            align-items: start;
            gap: 8px;
            padding: 6px 0;
            font-size: 13px;
            color: #2d3748;
        }

        .recommendation::before {
            content: "→";
            color: #667eea;
            font-weight: bold;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }

        .badge-critical {
            background: #fed7d7;
            color: #c53030;
        }

        .badge-high {
            background: #feebc8;
            color: #c05621;
        }

        .badge-medium {
            background: #faf089;
            color: #975a16;
        }

        .badge-low {
            background: #c6f6d5;
            color: #276749;
        }

        .anomaly-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            margin-bottom: 12px;
        }

        .anomaly-indicator.detected {
            background: #fed7d7;
            color: #c53030;
        }

        .anomaly-indicator.normal {
            background: #c6f6d5;
            color: #276749;
        }

        .prediction-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 20px;
        }

        .prediction-value {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .prediction-confidence {
            font-size: 14px;
            opacity: 0.9;
        }

        .cluster-card {
            background: white;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }

        .cluster-title {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 8px;
            color: #1a202c;
        }

        .cluster-repos {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }

        .repo-tag {
            background: #edf2f7;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            color: #2d3748;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #718096;
        }

        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .repo-selector {
            margin-bottom: 20px;
        }

        .repo-selector select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            background: white;
        }

        canvas {
            max-height: 400px;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }

        .stat-row:last-child {
            border-bottom: none;
        }

        .stat-label {
            color: #718096;
            font-size: 14px;
        }

        .stat-value {
            font-weight: 600;
            color: #1a202c;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <h1>🤖 ML Analytics Dashboard</h1>
                <p>AI-powered insights for repository analysis</p>
            </div>
            <a href="/" class="back-link">← Back to Dashboard</a>
        </div>

        <!-- Repository Selector -->
        <div class="repo-selector">
            <select id="repo-select" onchange="loadMLData()">
                <option value="">Select a repository...</option>
                <option value="test-repo">test-repo (Demo)</option>
                <option value="sample-project">sample-project (Demo)</option>
            </select>
        </div>

        <!-- Navigation Tabs -->
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('anomalies')">🔍 Anomaly Detection</button>
            <button class="nav-tab" onclick="switchTab('predictions')">📈 Score Predictions</button>
            <button class="nav-tab" onclick="switchTab('insights')">💡 Insights</button>
            <button class="nav-tab" onclick="switchTab('clustering')">🎯 Repository Clustering</button>
            <button class="nav-tab" onclick="switchTab('trends')">📊 Trend Forecasts</button>
            <button class="nav-tab" onclick="switchTab('health')">❤️ Health Status</button>
        </div>

        <!-- Anomaly Detection Tab -->
        <div id="anomalies-tab" class="tab-content active">
            <div class="card">
                <h3>🔍 Anomaly Detection</h3>
                <div id="anomaly-status"></div>
                <div class="grid-2">
                    <div>
                        <canvas id="anomaly-chart"></canvas>
                    </div>
                    <div id="anomaly-details"></div>
                </div>
            </div>
        </div>

        <!-- Predictions Tab -->
        <div id="predictions-tab" class="tab-content">
            <div class="card">
                <h3>📈 Score Predictions</h3>
                <div id="prediction-box"></div>
                <canvas id="prediction-chart"></canvas>
            </div>
        </div>

        <!-- Insights Tab -->
        <div id="insights-tab" class="tab-content">
            <div class="card">
                <h3>💡 Automated Insights</h3>
                <div id="insights-container"></div>
            </div>
        </div>

        <!-- Clustering Tab -->
        <div id="clustering-tab" class="tab-content">
            <div class="card">
                <h3>🎯 Repository Clustering</h3>
                <div id="clusters-container"></div>
            </div>
        </div>

        <!-- Trends Tab -->
        <div id="trends-tab" class="tab-content">
            <div class="card">
                <h3>📊 Trend Forecasts</h3>
                <canvas id="forecast-chart"></canvas>
            </div>
        </div>

        <!-- Health Tab -->
        <div id="health-tab" class="tab-content">
            <div class="card">
                <h3>❤️ Repository Health Status</h3>
                <div id="health-details"></div>
            </div>
        </div>
    </div>

    <script>
        let currentRepo = null;
        let charts = {};

        // Initialize
        function init() {
            console.log('ML Dashboard initialized');
        }

        // Switch tabs
        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active from all nav tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(`${tabName}-tab`).classList.add('active');
            event.target.classList.add('active');
        }

        // Load ML data for selected repository
        async function loadMLData() {
            const repo = document.getElementById('repo-select').value;
            if (!repo) return;
            
            currentRepo = repo;
            
            // Load all ML features
            await Promise.all([
                loadAnomalies(repo),
                loadPredictions(repo),
                loadInsights(repo),
                loadClustering(),
                loadForecast(repo),
                loadHealth(repo)
            ]);
        }

        // Load anomaly detection
        async function loadAnomalies(repo) {
            try {
                const response = await fetch(`/api/ml/anomalies/detect/${repo}?current_score=75&findings=10&critical=2`);
                const data = await response.json();
                
                displayAnomalyStatus(data);
                createAnomalyChart(data);
            } catch (error) {
                console.error('Error loading anomalies:', error);
                document.getElementById('anomaly-status').innerHTML = '<div class="error">Failed to load anomaly data</div>';
            }
        }

        // Display anomaly status
        function displayAnomalyStatus(data) {
            const statusHTML = `
                <div class="anomaly-indicator ${data.is_anomaly ? 'detected' : 'normal'}">
                    ${data.is_anomaly ? '⚠️ Anomaly Detected' : '✅ Normal Behavior'}
                </div>
                <div id="anomaly-details">
                    <div class="stat-row">
                        <span class="stat-label">Anomaly Score</span>
                        <span class="stat-value">${(data.anomaly_score * 100).toFixed(1)}%</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Severity</span>
                        <span class="stat-value">${data.severity}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Reason</span>
                        <span class="stat-value">${data.reason}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Expected Range</span>
                        <span class="stat-value">${data.expected_range.min.toFixed(1)} - ${data.expected_range.max.toFixed(1)}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Actual Value</span>
                        <span class="stat-value">${data.actual_value.toFixed(1)}</span>
                    </div>
                </div>
            `;
            document.getElementById('anomaly-status').innerHTML = statusHTML;
        }

        // Create anomaly chart
        function createAnomalyChart(data) {
            const ctx = document.getElementById('anomaly-chart');
            
            if (charts.anomaly) charts.anomaly.destroy();
            
            charts.anomaly = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Expected Min', 'Actual Value', 'Expected Max'],
                    datasets: [{
                        label: 'Score Values',
                        data: [data.expected_range.min, data.actual_value, data.expected_range.max],
                        backgroundColor: [
                            'rgba(72, 187, 120, 0.5)',
                            data.is_anomaly ? 'rgba(245, 101, 101, 0.5)' : 'rgba(72, 187, 120, 0.5)',
                            'rgba(72, 187, 120, 0.5)'
                        ],
                        borderColor: [
                            'rgb(72, 187, 120)',
                            data.is_anomaly ? 'rgb(245, 101, 101)' : 'rgb(72, 187, 120)',
                            'rgb(72, 187, 120)'
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Anomaly Detection Analysis'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }

        // Load predictions
        async function loadPredictions(repo) {
            try {
                const response = await fetch(`/api/ml/predictions/next-score/${repo}?current_score=75&days_ahead=30`);
                const data = await response.json();
                
                displayPrediction(data);
                createPredictionChart(data);
            } catch (error) {
                console.error('Error loading predictions:', error);
                document.getElementById('prediction-box').innerHTML = '<div class="error">Failed to load prediction data</div>';
            }
        }

        // Display prediction
        function displayPrediction(data) {
            const trendEmoji = data.trend === 'improving' ? '📈' : data.trend === 'declining' ? '📉' : '➡️';
            const predictionHTML = `
                <div class="prediction-box">
                    <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">Predicted Score (${data.forecast_days} days)</div>
                    <div class="prediction-value">${data.predicted_score.toFixed(1)} ${trendEmoji}</div>
                    <div class="prediction-confidence">
                        Confidence: ${(data.confidence * 100).toFixed(0)}% | 
                        Trend: ${data.trend} | 
                        Range: ${data.prediction_range[0].toFixed(1)} - ${data.prediction_range[1].toFixed(1)}
                    </div>
                </div>
            `;
            document.getElementById('prediction-box').innerHTML = predictionHTML;
        }

        // Create prediction chart
        function createPredictionChart(data) {
            const ctx = document.getElementById('prediction-chart');
            
            if (charts.prediction) charts.prediction.destroy();
            
            // Generate historical and forecast data
            const labels = [];
            const historicalData = [];
            const forecastData = [];
            
            // Historical (last 7 days)
            for (let i = 7; i > 0; i--) {
                labels.push(`-${i}d`);
                historicalData.push(75 - (Math.random() * 5));
                forecastData.push(null);
            }
            
            // Current
            labels.push('Today');
            historicalData.push(75);
            forecastData.push(75);
            
            // Forecast (next 7 days)
            let currentScore = 75;
            const increment = (data.predicted_score - 75) / 7;
            for (let i = 1; i <= 7; i++) {
                labels.push(`+${i}d`);
                historicalData.push(null);
                currentScore += increment;
                forecastData.push(currentScore);
            }
            
            charts.prediction = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Historical Scores',
                            data: historicalData,
                            borderColor: 'rgb(102, 126, 234)',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            tension: 0.3
                        },
                        {
                            label: 'Predicted Scores',
                            data: forecastData,
                            borderColor: 'rgb(237, 137, 54)',
                            backgroundColor: 'rgba(237, 137, 54, 0.1)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: 'Score Prediction (30-day forecast)'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }

        // Load insights
        async function loadInsights(repo) {
            try {
                const response = await fetch(`/api/ml/insights/${repo}`);
                const data = await response.json();
                
                displayInsights(data.insights || []);
            } catch (error) {
                console.error('Error loading insights:', error);
                document.getElementById('insights-container').innerHTML = '<div class="error">Failed to load insights</div>';
            }
        }

        // Display insights
        function displayInsights(insights) {
            if (insights.length === 0) {
                document.getElementById('insights-container').innerHTML = '<p style="text-align: center; padding: 40px; color: #718096;">No insights available. Select a repository to generate insights.</p>';
                return;
            }
            
            const insightsHTML = insights.map(insight => `
                <div class="insight-card ${insight.severity}">
                    <div class="insight-title">
                        <span class="badge badge-${insight.severity}">${insight.severity.toUpperCase()}</span>
                        ${insight.title}
                    </div>
                    <div class="insight-description">${insight.description}</div>
                    ${insight.recommendations && insight.recommendations.length > 0 ? `
                        <div class="insight-recommendations">
                            <strong>Recommendations:</strong>
                            ${insight.recommendations.map(rec => `
                                <div class="recommendation">${rec.action}</div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `).join('');
            
            document.getElementById('insights-container').innerHTML = insightsHTML;
        }

        // Load clustering
        async function loadClustering() {
            try {
                const response = await fetch('/api/ml/clustering/repositories?num_clusters=5');
                const data = await response.json();
                
                displayClusters(data.clusters || []);
            } catch (error) {
                console.error('Error loading clustering:', error);
                document.getElementById('clusters-container').innerHTML = '<div class="error">Failed to load clustering data</div>';
            }
        }

        // Display clusters
        function displayClusters(clusters) {
            if (clusters.length === 0) {
                document.getElementById('clusters-container').innerHTML = '<p style="text-align: center; padding: 40px; color: #718096;">No clustering data available.</p>';
                return;
            }
            
            const clustersHTML = clusters.map(cluster => `
                <div class="cluster-card">
                    <div class="cluster-title">
                        Cluster ${cluster.cluster_id}: ${cluster.description}
                    </div>
                    <div style="color: #718096; font-size: 14px; margin-bottom: 8px;">
                        ${cluster.size} repositories
                    </div>
                    <div class="cluster-repos">
                        ${cluster.repositories.map(repo => `
                            <span class="repo-tag">${repo}</span>
                        `).join('')}
                    </div>
                </div>
            `).join('');
            
            document.getElementById('clusters-container').innerHTML = clustersHTML;
        }

        // Load forecast
        async function loadForecast(repo) {
            try {
                const response = await fetch(`/api/ml/trends/forecast/${repo}?days=90`);
                const data = await response.json();
                
                createForecastChart(data);
            } catch (error) {
                console.error('Error loading forecast:', error);
            }
        }

        // Create forecast chart
        function createForecastChart(data) {
            const ctx = document.getElementById('forecast-chart');
            
            if (charts.forecast) charts.forecast.destroy();
            
            const labels = data.forecast_points ? data.forecast_points.map((_, i) => `Week ${i + 1}`) : [];
            const scores = data.forecast_points || [];
            
            charts.forecast = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Forecasted Score',
                        data: scores,
                        borderColor: 'rgb(102, 126, 234)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: `Trend Forecast (${data.forecast_days || 90} days)`
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }

        // Load health status
        async function loadHealth(repo) {
            try {
                const response = await fetch(`/api/ml/health/${repo}`);
                const data = await response.json();
                
                displayHealth(data);
            } catch (error) {
                console.error('Error loading health:', error);
                document.getElementById('health-details').innerHTML = '<div class="error">Failed to load health data</div>';
            }
        }

        // Display health status
        function displayHealth(data) {
            const statusEmoji = data.status === 'healthy' ? '✅' : data.status === 'warning' ? '⚠️' : '🔴';
            const trendEmoji = data.trend === 'improving' ? '📈' : data.trend === 'declining' ? '📉' : '➡️';
            
            const healthHTML = `
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">${statusEmoji}</div>
                    <h2 style="font-size: 32px; color: #1a202c; margin-bottom: 10px;">
                        ${data.status.toUpperCase()}
                    </h2>
                    <p style="color: #718096; font-size: 16px; margin-bottom: 30px;">
                        Repository: ${data.repository}
                    </p>
                </div>
                <div style="max-width: 600px; margin: 0 auto;">
                    <div class="stat-row">
                        <span class="stat-label">Average Score</span>
                        <span class="stat-value">${data.average_score.toFixed(1)}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Trend</span>
                        <span class="stat-value">${trendEmoji} ${data.trend}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Consistency</span>
                        <span class="stat-value">${(data.consistency * 100).toFixed(0)}%</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Total Audits</span>
                        <span class="stat-value">${data.audit_count}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Last Audit</span>
                        <span class="stat-value">${new Date(data.last_audit).toLocaleDateString()}</span>
                    </div>
                </div>
            `;
            
            document.getElementById('health-details').innerHTML = healthHTML;
        }

        // Initialize on load
        init();
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def ml_dashboard() -> str:
    """
    Serve ML Analytics dashboard page.
    
    Returns:
        HTML ML dashboard page with interactive visualizations
    """
    return ML_DASHBOARD_HTML
