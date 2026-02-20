#!/usr/bin/env python3
"""
Prometheus Live Training Dashboard
Real-time monitoring of chess training progress with GPU metrics

Author: Patrick Mineault & Claude Code
Date: October 9, 2025
"""

import streamlit as st
import json
import time
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
import subprocess

# Page config
st.set_page_config(
    page_title="Prometheus Live Training",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def get_gpu_stats():
    """Get GPU utilization and memory stats"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            gpu_util, mem_used, mem_total, temp = result.stdout.strip().split(', ')
            return {
                'utilization': float(gpu_util),
                'memory_used': float(mem_used),
                'memory_total': float(mem_total),
                'temperature': float(temp)
            }
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def load_training_data(results_dir: str = "chess_uci_results"):
    """Load latest training data"""
    results_path = Path(results_dir)

    if not results_path.exists():
        return None

    # Try to load session data
    session_file = results_path / "training_session.json"
    if session_file.exists():
        with open(session_file, 'r') as f:
            return json.load(f)

    # Otherwise look for checkpoints
    checkpoints = sorted(results_path.glob("checkpoint_*.json"))
    if checkpoints:
        with open(checkpoints[-1], 'r') as f:
            return json.load(f)

    return None


def plot_elo_progression(games_data):
    """Plot Elo rating over time"""
    if not games_data:
        return None

    game_numbers = [g['game_number'] for g in games_data]
    elos = [g['prometheus_elo_after'] for g in games_data]
    starting_elo = games_data[0]['prometheus_elo_before']

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(game_numbers, elos, 'b-', linewidth=2, label='Prometheus Elo')
    ax.axhline(y=starting_elo, color='r', linestyle='--', label='Starting Elo', alpha=0.7)
    ax.fill_between(game_numbers, starting_elo, elos, alpha=0.3)
    ax.set_xlabel('Game Number', fontsize=12)
    ax.set_ylabel('Elo Rating', fontsize=12)
    ax.set_title('Elo Progression (Intelligence Explosion)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    return fig


def plot_win_rate(games_data):
    """Plot rolling win rate"""
    if not games_data:
        return None

    results_numeric = []
    for g in games_data:
        if g['result'] == '1-0':
            results_numeric.append(1.0)
        elif g['result'] == '1/2-1/2':
            results_numeric.append(0.5)
        else:
            results_numeric.append(0.0)

    window = min(10, len(results_numeric))
    rolling_win_rate = []
    for i in range(len(results_numeric)):
        start = max(0, i - window + 1)
        rolling_win_rate.append(np.mean(results_numeric[start:i+1]) * 100)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(range(1, len(rolling_win_rate) + 1), rolling_win_rate, 'g-', linewidth=2)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% baseline')
    ax.set_xlabel('Game Number', fontsize=12)
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title(f'Rolling Win Rate (window={window})', fontsize=14, fontweight='bold')
    ax.set_ylim([0, 100])
    ax.legend()
    ax.grid(True, alpha=0.3)

    return fig


def main():
    st.markdown('<h1 class="main-header">🎮 Prometheus Live Training Dashboard</h1>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        refresh_interval = st.slider("Refresh Interval (seconds)", 1, 30, 5)
        results_dir = st.text_input("Results Directory", "chess_uci_results")

        st.markdown("---")
        st.header("📊 GPU Status")

        gpu_stats = get_gpu_stats()
        if gpu_stats:
            st.metric("GPU Utilization", f"{gpu_stats['utilization']:.1f}%")
            st.metric("GPU Memory", f"{gpu_stats['memory_used']:.0f} / {gpu_stats['memory_total']:.0f} MB")
            st.metric("GPU Temperature", f"{gpu_stats['temperature']:.0f}°C")
        else:
            st.info("GPU stats not available")

        st.markdown("---")
        if st.button("🔄 Force Refresh"):
            st.rerun()

        # Auto-refresh
        st.markdown(f"**Auto-refresh:** {refresh_interval}s")

    # Load data
    data = load_training_data(results_dir)

    if data is None:
        st.warning("⚠️ No training data found. Start a training session to see live updates!")
        st.code(f"""
# Start training with:
python prometheus_chess_uci_gpu.py --games 1000 --hours 12

# Or use existing chess benchmark:
python prometheus_chess_benchmark.py --num_games 100
        """, language="bash")

        time.sleep(refresh_interval)
        st.rerun()
        return

    # Main content
    col1, col2, col3, col4 = st.columns(4)

    # Determine data structure (session vs checkpoint)
    if 'games' in data:
        # Full session data
        games = data['games']
        current_elo = data['final_elo']
        starting_elo = data['starting_elo']
        games_played = data['total_games']
        meta_learning = data.get('meta_learning_rate', 1.0)
    else:
        # Checkpoint data
        games = []
        current_elo = data.get('elo', 800)
        starting_elo = 800
        games_played = data.get('game_num', 0)
        meta_learning = data.get('meta_learning_rate', 1.0)

    # Calculate stats
    if games:
        wins = sum(1 for g in games if g['result'] == '1-0')
        draws = sum(1 for g in games if g['result'] == '1/2-1/2')
        losses = sum(1 for g in games if g['result'] == '0-1')
        win_rate = (wins + 0.5 * draws) / len(games) * 100
    else:
        wins, draws, losses = 0, 0, 0
        win_rate = 0

    elo_gain = current_elo - starting_elo

    with col1:
        st.metric("Current Elo", f"{current_elo:.0f}",
                 delta=f"+{elo_gain:.0f}" if elo_gain > 0 else f"{elo_gain:.0f}")

    with col2:
        st.metric("Games Played", f"{games_played}",
                 delta=f"{games_played - len(games)} pending" if games_played > len(games) else None)

    with col3:
        st.metric("Win Rate", f"{win_rate:.1f}%",
                 delta=f"+{win_rate - 50:.1f}%" if win_rate > 50 else f"{win_rate - 50:.1f}%")

    with col4:
        st.metric("Meta-Learning", f"{meta_learning:.2f}x",
                 delta=f"+{(meta_learning - 1.0) * 100:.1f}%" if meta_learning > 1 else None)

    st.markdown("---")

    # Plots
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Elo Progression")
        if games:
            fig = plot_elo_progression(games)
            if fig:
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("No game data available yet")

    with col2:
        st.subheader("🎯 Win Rate Over Time")
        if games:
            fig = plot_win_rate(games)
            if fig:
                st.pyplot(fig)
                plt.close(fig)
        else:
            st.info("No game data available yet")

    st.markdown("---")

    # Recent games table
    st.subheader("📋 Recent Games")
    if games:
        recent_games = games[-10:][::-1]  # Last 10, most recent first
        df = pd.DataFrame([
            {
                'Game': g['game_number'],
                'Result': g['result'],
                'Moves': g.get('moves', 'N/A'),
                'Opponent': g.get('opponent_name', 'Unknown')[:20],
                'Elo Before': f"{g['prometheus_elo_before']:.0f}",
                'Elo After': f"{g['prometheus_elo_after']:.0f}",
                'Δ': f"{g['prometheus_elo_after'] - g['prometheus_elo_before']:+.0f}"
            }
            for g in recent_games
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No games completed yet")

    # Training stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Wins", wins, delta=f"{wins}/{games_played}" if games_played > 0 else None)

    with col2:
        st.metric("Draws", draws, delta=f"{draws}/{games_played}" if games_played > 0 else None)

    with col3:
        st.metric("Losses", losses, delta=f"{losses}/{games_played}" if games_played > 0 else None)

    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🤖 Prometheus AGI Training System • Real-time Dashboard")

    # Auto-refresh
    time.sleep(refresh_interval)
    st.rerun()


if __name__ == "__main__":
    main()
