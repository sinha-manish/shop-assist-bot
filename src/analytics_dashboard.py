#!/usr/bin/env python3
"""
Analytics Dashboard for Advanced RAG System
===========================================
Flask-based dashboard to view analytics, metrics, and system performance.
"""

from flask import Flask, render_template, jsonify
from advanced_rag import AdvancedRAG, AnalyticsTracker
import json

app = Flask(__name__)

# Initialize RAG system
rag = None

def init_rag():
    global rag
    if not rag:
        try:
            rag = AdvancedRAG()
        except Exception as e:
            print(f"⚠️ Failed to initialize RAG: {e}")
            return None
    return rag

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Shop Assist RAG - Analytics Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
        }
        .section {
            margin-bottom: 30px;
        }
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #667eea;
            color: white;
            font-weight: 600;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
    </style>
    <script>
        function refreshData() {
            location.reload();
        }
        setInterval(refreshData, 30000); // Auto-refresh every 30 seconds
    </script>
</head>
<body>
    <div class="container">
        <h1>📊 Shop Assist RAG - Analytics Dashboard</h1>
        <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Queries</h3>
                <div class="value">{{ stats.total_queries }}</div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div class="value">{{ stats.success_rate }}</div>
            </div>
            <div class="stat-card">
                <h3>Avg Response Time</h3>
                <div class="value">{{ stats.avg_response_time }}</div>
            </div>
            <div class="stat-card">
                <h3>Cache Hit Rate</h3>
                <div class="value">{{ stats.cache_hit_rate }}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Intent Distribution</h2>
            <table>
                <thead>
                    <tr>
                        <th>Intent</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    {% for intent, count in stats.intent_distribution.items() %}
                    <tr>
                        <td>{{ intent }}</td>
                        <td>{{ count }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🔍 Query Patterns</h2>
            <table>
                <thead>
                    <tr>
                        <th>Query Type</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    {% for pattern, count in stats.query_patterns.items() %}
                    <tr>
                        <td>{{ pattern }}</td>
                        <td>{{ count }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page."""
    rag_instance = init_rag()
    if not rag_instance:
        return "RAG system not initialized. Please check your configuration.", 500
    
    stats = rag_instance.get_analytics()
    
    # Render dashboard using Flask's render_template_string
    from flask import render_template_string
    return render_template_string(DASHBOARD_HTML, stats=stats)

@app.route('/api/stats')
def api_stats():
    """API endpoint for stats."""
    rag_instance = init_rag()
    if not rag_instance:
        return jsonify({'error': 'RAG system not initialized'}), 500
    return jsonify(rag_instance.get_analytics())

@app.route('/api/feedback')
def api_feedback():
    """API endpoint for feedback stats."""
    rag_instance = init_rag()
    if not rag_instance:
        return jsonify({'error': 'RAG system not initialized'}), 500
    if hasattr(rag_instance, 'feedback_system'):
        return jsonify(rag_instance.feedback_system.get_feedback_stats())
    return jsonify({'error': 'Feedback system not initialized'})

if __name__ == '__main__':
    print("🚀 Starting Analytics Dashboard on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)

