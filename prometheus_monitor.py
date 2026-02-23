#!/usr/bin/env python3
"""
Prometheus Monitoring Dashboard

Real-time interactive dashboard for visualizing model performance,
training progress, and system metrics using Dash/Plotly.

Usage:
    python prometheus_monitor.py

    # Custom port
    python prometheus_monitor.py --port 8080

    # Debug mode
    python prometheus_monitor.py --debug

Then open: http://localhost:8050
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List
import numpy as np

try:
    import dash
    from dash import dcc, html, Input, Output
    import plotly.graph_objs as go
except ImportError:
    print("Error: Dash not installed. Install with:")
    print("  pip install dash plotly")
    print("\nAlternatively, use the Streamlit dashboard:")
    print("  streamlit run prometheus_dashboard.py")
    sys.exit(1)


# Dashboard configuration
DASHBOARD_TITLE = "Prometheus AI Monitor"
DEFAULT_PORT = 8050


class PrometheusMonitor:
    """Real-time monitoring dashboard for Prometheus AI."""

    def __init__(self):
        self.app = dash.Dash(__name__, title=DASHBOARD_TITLE)
        self.setup_layout()
        self.setup_callbacks()

    def load_benchmark_data(self) -> List[Dict]:
        """Load benchmark results from benchmarks/ directory."""
        benchmarks_dir = Path("benchmarks")
        if not benchmarks_dir.exists():
            return []

        results = []
        for json_file in benchmarks_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    data['filename'] = json_file.name
                    results.append(data)
            except Exception:
                pass

        return results

    def load_comparison_data(self) -> List[Dict]:
        """Load model comparison results."""
        comparisons_dir = Path("comparisons")
        if not comparisons_dir.exists():
            return []

        results = []
        for json_file in comparisons_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    results.append(data)
            except Exception:
                pass

        return results

    def setup_layout(self):
        """Setup dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("🔥 Prometheus AI Monitor",
                        style={'textAlign': 'center', 'color': '#2c3e50', 'margin': '0'}),
                html.P("Real-time model performance and system monitoring",
                       style={'textAlign': 'center', 'color': '#7f8c8d', 'margin': '10px 0'}),
            ], style={'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderBottom': '3px solid #3498db'}),

            # Tabs
            dcc.Tabs(id='dashboard-tabs', value='overview', children=[
                dcc.Tab(label='📊 Overview', value='overview'),
                dcc.Tab(label='🎯 Performance', value='performance'),
                dcc.Tab(label='⚡ Benchmarks', value='benchmarks'),
                dcc.Tab(label='🔬 Comparisons', value='comparisons'),
            ], style={'marginBottom': '20px'}),

            # Content area
            html.Div(id='tab-content', style={'padding': '20px'}),

            # Auto-refresh every 10 seconds
            dcc.Interval(
                id='interval-component',
                interval=10*1000,  # milliseconds
                n_intervals=0
            )
        ])

    def setup_callbacks(self):
        """Setup dashboard callbacks."""

        @self.app.callback(
            Output('tab-content', 'children'),
            [Input('dashboard-tabs', 'value'),
             Input('interval-component', 'n_intervals')]
        )
        def render_content(tab, n_intervals):
            if tab == 'overview':
                return self.render_overview()
            elif tab == 'performance':
                return self.render_performance()
            elif tab == 'benchmarks':
                return self.render_benchmarks()
            elif tab == 'comparisons':
                return self.render_comparisons()

    def render_overview(self):
        """Render overview tab."""
        # Count models
        models_dir = Path("models/pretrained")
        num_models = len(list(models_dir.glob("*.h5"))) if models_dir.exists() else 0

        # Count benchmarks
        benchmarks = self.load_benchmark_data()

        # Count comparisons
        comparisons = self.load_comparison_data()

        return html.Div([
            html.H2("System Overview", style={'marginBottom': '30px'}),

            # Stats cards
            html.Div([
                # Models card
                html.Div([
                    html.Div("📦", style={'fontSize': '48px'}),
                    html.H3(str(num_models), style={'fontSize': '48px', 'margin': '10px 0'}),
                    html.P("Trained Models", style={'fontSize': '18px', 'opacity': '0.9'}),
                ], style={
                    'flex': '1',
                    'padding': '30px',
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'borderRadius': '10px',
                    'textAlign': 'center',
                    'margin': '10px',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                }),

                # Benchmarks card
                html.Div([
                    html.Div("⚡", style={'fontSize': '48px'}),
                    html.H3(str(len(benchmarks)), style={'fontSize': '48px', 'margin': '10px 0'}),
                    html.P("Benchmark Results", style={'fontSize': '18px', 'opacity': '0.9'}),
                ], style={
                    'flex': '1',
                    'padding': '30px',
                    'backgroundColor': '#2ecc71',
                    'color': 'white',
                    'borderRadius': '10px',
                    'textAlign': 'center',
                    'margin': '10px',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                }),

                # Comparisons card
                html.Div([
                    html.Div("🔬", style={'fontSize': '48px'}),
                    html.H3(str(len(comparisons)), style={'fontSize': '48px', 'margin': '10px 0'}),
                    html.P("Model Comparisons", style={'fontSize': '18px', 'opacity': '0.9'}),
                ], style={
                    'flex': '1',
                    'padding': '30px',
                    'backgroundColor': '#e74c3c',
                    'color': 'white',
                    'borderRadius': '10px',
                    'textAlign': 'center',
                    'margin': '10px',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                }),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '30px'}),

            # Quick Start Commands
            html.Div([
                html.H3("🚀 Quick Start Commands", style={'marginBottom': '20px'}),
                html.Div([
                    html.Div([
                        html.Strong("Train a Model:"),
                        html.Code(" python scripts/train_pretrained_models.py --model go_9x9", style={
                            'display': 'block',
                            'padding': '10px',
                            'backgroundColor': '#f4f4f4',
                            'borderRadius': '5px',
                            'marginTop': '5px'
                        }),
                    ], style={'marginBottom': '15px'}),

                    html.Div([
                        html.Strong("Run Benchmark:"),
                        html.Code(" python scripts/benchmark_models.py --model models/pretrained/go_9x9.h5 --metric all", style={
                            'display': 'block',
                            'padding': '10px',
                            'backgroundColor': '#f4f4f4',
                            'borderRadius': '5px',
                            'marginTop': '5px'
                        }),
                    ], style={'marginBottom': '15px'}),

                    html.Div([
                        html.Strong("Compare Models:"),
                        html.Code(" python scripts/compare_models.py --model1 models/go_9x9.h5 --model2 random --num-games 20", style={
                            'display': 'block',
                            'padding': '10px',
                            'backgroundColor': '#f4f4f4',
                            'borderRadius': '5px',
                            'marginTop': '5px'
                        }),
                    ]),
                ], style={
                    'padding': '20px',
                    'backgroundColor': 'white',
                    'borderRadius': '10px',
                    'border': '1px solid #ddd'
                }),
            ]),
        ])

    def render_performance(self):
        """Render model performance tab."""
        benchmarks = self.load_benchmark_data()

        if not benchmarks:
            return html.Div([
                html.H2("Model Performance"),
                html.Div([
                    html.P("📊 No benchmark data available yet."),
                    html.P("Run benchmarks to see performance metrics:"),
                    html.Code("python scripts/benchmark_models.py --model models/pretrained/go_9x9.h5 --metric all"),
                ], style={
                    'padding': '20px',
                    'backgroundColor': '#fff3cd',
                    'borderRadius': '5px',
                    'border': '1px solid #ffc107'
                }),
            ])

        # Extract data for visualization
        model_names = []
        elo_scores = []
        inference_times = []
        memory_usage = []

        for bench in benchmarks:
            if 'model_path' in bench:
                model_name = Path(bench['model_path']).stem
                model_names.append(model_name)

                # ELO from MCTS results
                if 'mcts' in bench and '400_sims' in bench['mcts']:
                    elo_scores.append(bench['mcts']['400_sims'].get('elo', 0))
                else:
                    elo_scores.append(0)

                # Inference time
                if 'inference' in bench:
                    inference_times.append(bench['inference'].get('mean_ms', 0))
                else:
                    inference_times.append(0)

                # Memory
                if 'memory' in bench:
                    memory_usage.append(bench['memory'].get('memory_delta_mb', 0))
                else:
                    memory_usage.append(0)

        # Create ELO chart
        elo_fig = go.Figure(data=[
            go.Bar(
                x=model_names,
                y=elo_scores,
                marker_color='#3498db',
                text=elo_scores,
                textposition='auto',
            )
        ])
        elo_fig.update_layout(
            title="Model ELO Ratings (400 MCTS simulations)",
            xaxis_title="Model",
            yaxis_title="ELO Rating",
            height=400,
            template='plotly_white'
        )

        # Create inference time chart
        inference_fig = go.Figure(data=[
            go.Bar(
                x=model_names,
                y=inference_times,
                marker_color='#2ecc71',
                text=[f"{t:.1f}ms" for t in inference_times],
                textposition='auto',
            )
        ])
        inference_fig.update_layout(
            title="Inference Speed",
            xaxis_title="Model",
            yaxis_title="Time (ms)",
            height=400,
            template='plotly_white'
        )

        # Create memory usage chart
        memory_fig = go.Figure(data=[
            go.Bar(
                x=model_names,
                y=memory_usage,
                marker_color='#e74c3c',
                text=[f"{m:.0f}MB" for m in memory_usage],
                textposition='auto',
            )
        ])
        memory_fig.update_layout(
            title="Memory Usage",
            xaxis_title="Model",
            yaxis_title="Memory (MB)",
            height=400,
            template='plotly_white'
        )

        return html.Div([
            html.H2("Model Performance Metrics"),

            html.Div([
                dcc.Graph(figure=elo_fig),
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.Div([
                    dcc.Graph(figure=inference_fig),
                ], style={'flex': '1'}),

                html.Div([
                    dcc.Graph(figure=memory_fig),
                ], style={'flex': '1'}),
            ], style={'display': 'flex', 'gap': '20px'}),
        ])

    def render_benchmarks(self):
        """Render benchmarks tab with detailed table."""
        benchmarks = self.load_benchmark_data()

        if not benchmarks:
            return html.Div([
                html.H2("Benchmark Results"),
                html.P("No benchmark data available."),
            ])

        # Create detailed benchmark table
        table_header = [
            html.Thead(html.Tr([
                html.Th("Model", style={'padding': '12px', 'textAlign': 'left'}),
                html.Th("ELO (400)", style={'padding': '12px', 'textAlign': 'right'}),
                html.Th("Win Rate", style={'padding': '12px', 'textAlign': 'right'}),
                html.Th("Inference", style={'padding': '12px', 'textAlign': 'right'}),
                html.Th("Memory", style={'padding': '12px', 'textAlign': 'right'}),
                html.Th("Throughput", style={'padding': '12px', 'textAlign': 'right'}),
            ]))
        ]

        rows = []
        for bench in benchmarks:
            model_name = Path(bench.get('model_path', 'unknown')).stem

            # Get metrics
            elo = "N/A"
            win_rate = "N/A"
            if 'mcts' in bench and '400_sims' in bench['mcts']:
                elo = f"{bench['mcts']['400_sims'].get('elo', 0):.0f}"
                win_rate = f"{bench['mcts']['400_sims'].get('win_rate', 0):.1%}"

            inference = "N/A"
            throughput = "N/A"
            if 'inference' in bench:
                inference = f"{bench['inference'].get('mean_ms', 0):.1f}ms"
                throughput = f"{bench['inference'].get('inferences_per_second', 0):.0f}/s"

            memory = "N/A"
            if 'memory' in bench:
                memory = f"{bench['memory'].get('memory_delta_mb', 0):.0f}MB"

            rows.append(html.Tr([
                html.Td(model_name, style={'padding': '12px', 'fontWeight': 'bold'}),
                html.Td(elo, style={'padding': '12px', 'textAlign': 'right'}),
                html.Td(win_rate, style={'padding': '12px', 'textAlign': 'right'}),
                html.Td(inference, style={'padding': '12px', 'textAlign': 'right'}),
                html.Td(memory, style={'padding': '12px', 'textAlign': 'right'}),
                html.Td(throughput, style={'padding': '12px', 'textAlign': 'right'}),
            ], style={'backgroundColor': '#f9f9f9' if len(rows) % 2 == 0 else 'white'}))

        table_body = [html.Tbody(rows)]

        return html.Div([
            html.H2("Detailed Benchmark Results"),

            html.Table(
                table_header + table_body,
                style={
                    'width': '100%',
                    'borderCollapse': 'collapse',
                    'marginTop': '20px',
                    'backgroundColor': 'white',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'borderRadius': '5px',
                }
            ),
        ])

    def render_comparisons(self):
        """Render model comparisons tab."""
        comparisons = self.load_comparison_data()

        if not comparisons:
            return html.Div([
                html.H2("Model Comparisons"),
                html.Div([
                    html.P("📊 No comparison data available yet."),
                    html.P("Run comparisons to see head-to-head results:"),
                    html.Code("python scripts/compare_models.py --model1 A.h5 --model2 B.h5 --num-games 50"),
                ], style={
                    'padding': '20px',
                    'backgroundColor': '#fff3cd',
                    'borderRadius': '5px',
                    'border': '1px solid #ffc107'
                }),
            ])

        # Create comparison cards
        comparison_cards = []
        for comp in comparisons:
            agent1_name = comp['agent1']['name']
            agent2_name = comp['agent2']['name']
            wins = comp['results']['agent1_wins']
            losses = comp['results']['agent2_wins']
            draws = comp['results']['draws']
            win_rate = comp['results']['win_rate']
            elo_diff = comp['results']['elo_difference']

            # Determine winner color
            card_color = '#2ecc71' if elo_diff > 0 else '#e74c3c' if elo_diff < 0 else '#95a5a6'

            card = html.Div([
                html.Div([
                    html.H3(f"{agent1_name} vs {agent2_name}", style={'margin': '0 0 15px 0'}),
                ], style={'borderBottom': f'3px solid {card_color}', 'paddingBottom': '10px', 'marginBottom': '15px'}),

                html.Div([
                    html.Div([
                        html.Div("Win Rate", style={'fontSize': '14px', 'color': '#7f8c8d'}),
                        html.Div(f"{win_rate:.1%}", style={'fontSize': '32px', 'fontWeight': 'bold'}),
                    ], style={'flex': '1', 'textAlign': 'center'}),

                    html.Div([
                        html.Div("ELO Diff", style={'fontSize': '14px', 'color': '#7f8c8d'}),
                        html.Div(f"{elo_diff:+.0f}", style={'fontSize': '32px', 'fontWeight': 'bold', 'color': card_color}),
                    ], style={'flex': '1', 'textAlign': 'center'}),

                    html.Div([
                        html.Div("W-L-D", style={'fontSize': '14px', 'color': '#7f8c8d'}),
                        html.Div(f"{wins}-{losses}-{draws}", style={'fontSize': '24px', 'fontWeight': 'bold'}),
                    ], style={'flex': '1', 'textAlign': 'center'}),
                ], style={'display': 'flex', 'gap': '20px'}),

                html.Div(f"Games: {comp['num_games']}", style={
                    'marginTop': '15px',
                    'paddingTop': '15px',
                    'borderTop': '1px solid #eee',
                    'fontSize': '14px',
                    'color': '#7f8c8d'
                }),
            ], style={
                'border': '1px solid #ddd',
                'borderRadius': '10px',
                'padding': '20px',
                'margin': '10px 0',
                'backgroundColor': 'white',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            })

            comparison_cards.append(card)

        return html.Div([
            html.H2("Head-to-Head Comparisons"),
            html.Div(comparison_cards),
        ])

    def run(self, host='127.0.0.1', port=8050, debug=False):
        """Run the dashboard server."""
        print("=" * 80)
        print(f"🔥 {DASHBOARD_TITLE}")
        print("=" * 80)
        print(f"\n✓ Dashboard starting on http://{host}:{port}")
        print("\n📊 Features:")
        print("  • Real-time model performance monitoring")
        print("  • Benchmark visualization")
        print("  • Model comparison charts")
        print("  • Auto-refresh every 10 seconds")
        print("\n⌨️  Press Ctrl+C to stop")
        print("=" * 80)

        self.app.run_server(host=host, port=port, debug=debug)


def main():
    parser = argparse.ArgumentParser(
        description="Prometheus Monitoring Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start dashboard (default port 8050)
  python prometheus_monitor.py

  # Custom port
  python prometheus_monitor.py --port 8080

  # Debug mode with auto-reload
  python prometheus_monitor.py --debug

Then open your browser to http://localhost:8050
        """
    )

    parser.add_argument('--host', default='127.0.0.1',
                        help='Host address (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port number (default: {DEFAULT_PORT})')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode with auto-reload')

    args = parser.parse_args()

    # Create and run dashboard
    try:
        monitor = PrometheusMonitor()
        monitor.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Install dependencies: pip install dash plotly")
        print("  2. Check port availability: lsof -i :8050")
        print("  3. Try different port: --port 8080")
        return 1

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n✓ Dashboard stopped.")
        sys.exit(0)
