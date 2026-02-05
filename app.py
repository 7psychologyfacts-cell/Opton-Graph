"""
NIFTY Option Chain Visualizer - Flask App for Vercel/Railway
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>📊 Live Option Chain Visualizer</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f172a;
            color: #f1f5f9;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 30px 0;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-bottom: 2px solid #00ff88;
            margin-bottom: 30px;
            border-radius: 10px;
        }
        .header h1 {
            color: #00ff88;
            font-size: 2.8rem;
            margin-bottom: 10px;
        }
        .header p {
            color: #94a3b8;
            font-size: 1.1rem;
        }
        .controls {
            background: #1e293b;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            border: 1px solid #334155;
        }
        .control-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #cbd5e1;
            font-weight: 600;
        }
        input, select, button {
            width: 100%;
            padding: 12px 15px;
            border-radius: 6px;
            border: 1px solid #475569;
            background: #334155;
            color: #f1f5f9;
            font-size: 1rem;
        }
        button {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #000;
            border: none;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: #1e293b;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid #00ff88;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #00ff88;
            margin: 10px 0;
        }
        .metric-label {
            color: #94a3b8;
            font-size: 0.9rem;
        }
        #chart {
            background: #1e293b;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .data-section {
            background: #1e293b;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background: #334155;
            padding: 12px;
            text-align: left;
            color: #00ff88;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #475569;
        }
        tr:hover {
            background: #2d3748;
        }
        .error {
            background: #7f1d1d;
            color: #fecaca;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .success {
            background: #064e3b;
            color: #a7f3d0;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 LIVE OPTION CHAIN VISUALIZER</h1>
            <p>Real-time NIFTY & BANKNIFTY Option Chain Analysis</p>
        </div>

        <div class="controls">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <div class="control-group">
                    <label>🔑 Access Token</label>
                    <input type="password" id="token" placeholder="Enter Upstox Access Token">
                </div>
                
                <div class="control-group">
                    <label>📈 Instrument</label>
                    <select id="instrument">
                        <option value="NSE_INDEX|Nifty 50">NIFTY 50</option>
                        <option value="NSE_INDEX|Nifty Bank">BANKNIFTY</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label>📅 Expiry Date</label>
                    <input type="date" id="expiry" value="{{ default_expiry }}">
                </div>
                
                <div class="control-group">
                    <label>🔢 Number of Strikes</label>
                    <input type="range" id="strikes" min="10" max="50" value="20">
                    <span id="strikesValue">20</span>
                </div>
            </div>
            
            <button onclick="fetchData()" style="margin-top: 20px;">
                🚀 FETCH LIVE DATA
            </button>
            
            <div style="margin-top: 20px; font-size: 0.9rem; color: #94a3b8;">
                <p>💡 <strong>How to get token:</strong> Go to <a href="https://upstox.com/developer/" style="color: #00ff88;">Upstox Developer Portal</a>, create app and generate access token</p>
                <p>⏰ <strong>Market Hours:</strong> 9:15 AM - 3:30 PM IST (Monday to Friday)</p>
            </div>
        </div>

        <div id="metrics" class="metrics" style="display: none;"></div>
        
        <div id="chart"></div>
        
        <div class="data-section">
            <h3 style="margin-bottom: 15px; color: #00ff88;">📋 OPTION CHAIN DATA</h3>
            <div id="dataTable"></div>
            <button onclick="downloadCSV()" style="margin-top: 20px; width: auto; padding: 10px 20px;">
                📥 DOWNLOAD CSV
            </button>
        </div>
    </div>

    <script>
        // Set default expiry to next Thursday
        function getNextThursday() {
            const today = new Date();
            const daysUntilThursday = (11 - today.getDay()) % 7;
            const nextThursday = new Date(today);
            nextThursday.setDate(today.getDate() + daysUntilThursday);
            return nextThursday.toISOString().split('T')[0];
        }
        
        document.getElementById('expiry').value = getNextThursday();
        
        // Update strikes value display
        document.getElementById('strikes').addEventListener('input', function() {
            document.getElementById('strikesValue').textContent = this.value;
        });
        
        let currentData = null;
        
        async function fetchData() {
            const token = document.getElementById('token').value;
            const instrument = document.getElementById('instrument').value;
            const expiry = document.getElementById('expiry').value;
            const strikes = document.getElementById('strikes').value;
            
            if (!token) {
                showError('Please enter your Upstox Access Token');
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch('/api/option-chain', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        token: token,
                        instrument: instrument,
                        expiry: expiry,
                        strikes: parseInt(strikes)
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentData = data;
                    displayMetrics(data.metrics);
                    displayChart(data);
                    displayDataTable(data.df);
                    showSuccess('Data fetched successfully!');
                } else {
                    showError(data.error || 'Failed to fetch data');
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            }
        }
        
        function displayMetrics(metrics) {
            document.getElementById('metrics').style.display = 'grid';
            document.getElementById('metrics').innerHTML = `
                <div class="metric-card">
                    <div class="metric-label">Spot Price</div>
                    <div class="metric-value">₹${metrics.spot.toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">ATM Strike</div>
                    <div class="metric-value">${metrics.atm}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">PCR</div>
                    <div class="metric-value">${metrics.pcr.toFixed(2)}</div>
                    <div class="metric-label">${metrics.pcr < 0.7 ? 'Bullish' : metrics.pcr > 1.3 ? 'Bearish' : 'Neutral'}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Last Updated</div>
                    <div class="metric-value">${new Date().toLocaleTimeString()}</div>
                </div>
            `;
        }
        
        function displayChart(data) {
            const trace1 = {
                x: data.chart.ce_strikes,
                y: data.chart.ce_oi,
                name: 'CALL OI',
                type: 'bar',
                marker: {color: '#00ff88'}
            };
            
            const trace2 = {
                x: data.chart.pe_strikes,
                y: data.chart.pe_oi,
                name: 'PUT OI',
                type: 'bar',
                marker: {color: '#ff4444'}
            };
            
            const layout = {
                title: {
                    text: `<b>${data.chart.instrument} - OPTION CHAIN OI PROFILE</b><br>` +
                          `<span style="font-size:12px">Expiry: ${data.chart.expiry_display} | ` +
                          `Spot: ₹${data.metrics.spot.toLocaleString('en-IN', {minimumFractionDigits: 2})} | ` +
                          `PCR: ${data.metrics.pcr.toFixed(2)}</span>`,
                    font: {size: 16, color: '#f1f5f9'}
                },
                xaxis: {
                    title: 'Strike Price',
                    tickangle: 45,
                    gridcolor: '#475569',
                    color: '#f1f5f9'
                },
                yaxis: {
                    title: 'Open Interest',
                    gridcolor: '#475569',
                    color: '#f1f5f9'
                },
                plot_bgcolor: '#1e293b',
                paper_bgcolor: '#1e293b',
                font: {color: '#f1f5f9'},
                barmode: 'group',
                hovermode: 'x unified',
                showlegend: true,
                legend: {
                    orientation: 'h',
                    yanchor: 'bottom',
                    y: 1.02,
                    xanchor: 'right',
                    x: 1
                }
            };
            
            Plotly.newPlot('chart', [trace1, trace2], layout);
        }
        
        function displayDataTable(df) {
            let tableHTML = `
                <table>
                    <thead>
                        <tr>
                            <th>Strike</th>
                            <th>Type</th>
                            <th>OI</th>
                            <th>LTP</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            df.forEach(row => {
                tableHTML += `
                    <tr>
                        <td>${row.strike}</td>
                        <td style="color: ${row.type === 'CE' ? '#00ff88' : '#ff4444'}">${row.type}</td>
                        <td>${parseInt(row.oi).toLocaleString('en-IN')}</td>
                        <td>₹${parseFloat(row.ltp).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                    </tr>
                `;
            });
            
            tableHTML += '</tbody></table>';
            document.getElementById('dataTable').innerHTML = tableHTML;
        }
        
        function downloadCSV() {
            if (!currentData || !currentData.csv) {
                showError('No data available to download');
                return;
            }
            
            const blob = new Blob([currentData.csv], {type: 'text/csv'});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `option_chain_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }
        
        function showLoading() {
            document.getElementById('chart').innerHTML = '<div class="loading">⏳ Fetching live data...</div>';
            document.getElementById('dataTable').innerHTML = '';
        }
        
        function showError(message) {
            const chartDiv = document.getElementById('chart');
            chartDiv.innerHTML = `<div class="error">❌ ${message}</div>`;
        }
        
        function showSuccess(message) {
            const chartDiv = document.getElementById('chart');
            chartDiv.innerHTML += `<div class="success">✅ ${message}</div>`;
        }
        
        // Auto-set expiry date
        document.getElementById('expiry').value = getNextThursday();
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    # Set default expiry to next Thursday
    today = datetime.now()
    days_ahead = 3 - today.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    default_expiry = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
    
    return render_template_string(HTML_TEMPLATE, default_expiry=default_expiry)

@app.route('/api/option-chain', methods=['POST'])
def get_option_chain():
    try:
        data = request.json
        token = data.get('token')
        instrument_key = data.get('instrument')
        expiry_date = data.get('expiry')
        num_strikes = data.get('strikes', 20)
        
        if not all([token, instrument_key, expiry_date]):
            return jsonify({'success': False, 'error': 'Missing parameters'})
        
        # Fetch from Upstox API
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
        url = 'https://api.upstox.com/v2/option/chain'
        params = {'instrument_key': instrument_key, 'expiry_date': expiry_date}
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'API Error: {response.status_code}'})
        
        api_data = response.json()
        
        if api_data.get('status') != 'success':
            return jsonify({'success': False, 'error': 'No data available'})
        
        # Process data
        rows = []
        for item in api_data['data']:
            strike = item['strike_price']
            spot = item['underlying_spot_price']
            
            if item.get('call_options') and item['call_options'].get('market_data'):
                call = item['call_options']['market_data']
                rows.append({
                    'strike': strike, 'type': 'CE',
                    'oi': call.get('oi', 0), 'ltp': call.get('ltp', 0),
                    'underlying': spot
                })
            
            if item.get('put_options') and item['put_options'].get('market_data'):
                put = item['put_options']['market_data']
                rows.append({
                    'strike': strike, 'type': 'PE',
                    'oi': put.get('oi', 0), 'ltp': put.get('ltp', 0),
                    'underlying': spot
                })
        
        df = pd.DataFrame(rows)
        
        # Filter strikes around ATM
        if not df.empty and num_strikes > 0:
            spot = df['underlying'].iloc[0]
            unique_strikes = sorted(df['strike'].unique())
            atm_strike = min(unique_strikes, key=lambda x: abs(x - spot))
            
            atm_index = unique_strikes.index(atm_strike)
            strikes_each_side = num_strikes // 2
            
            start_idx = max(0, atm_index - strikes_each_side)
            end_idx = min(len(unique_strikes), atm_index + strikes_each_side + 1)
            
            if start_idx == 0:
                end_idx = min(len(unique_strikes), num_strikes)
            elif end_idx == len(unique_strikes):
                start_idx = max(0, len(unique_strikes) - num_strikes)
            
            filtered_strikes = unique_strikes[start_idx:end_idx]
            df = df[df['strike'].isin(filtered_strikes)]
        
        if df.empty:
            return jsonify({'success': False, 'error': 'No data after filtering'})
        
        # Prepare chart data
        ce_df = df[df['type'] == 'CE'].sort_values('strike')
        pe_df = df[df['type'] == 'PE'].sort_values('strike')
        
        spot_price = df['underlying'].iloc[0]
        atm_strike = min(df['strike'].unique(), key=lambda x: abs(x - spot_price))
        
        total_ce_oi = ce_df['oi'].sum()
        total_pe_oi = pe_df['oi'].sum()
        pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        
        instrument_name = "NIFTY 50" if "Nifty 50" in instrument_key else "BANKNIFTY"
        expiry_display = datetime.strptime(expiry_date, '%Y-%m-%d').strftime('%d %b %Y')
        
        # Create CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        return jsonify({
            'success': True,
            'metrics': {
                'spot': spot_price,
                'atm': atm_strike,
                'total_ce': total_ce_oi,
                'total_pe': total_pe_oi,
                'pcr': pcr
            },
            'chart': {
                'ce_strikes': ce_df['strike'].tolist(),
                'ce_oi': ce_df['oi'].tolist(),
                'pe_strikes': pe_df['strike'].tolist(),
                'pe_oi': pe_df['oi'].tolist(),
                'instrument': instrument_name,
                'expiry_display': expiry_display
            },
            'df': df.to_dict('records'),
            'csv': csv_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
