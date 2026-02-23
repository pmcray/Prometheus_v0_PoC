"""
PrometheusStar Strategy Visualisation Dashboard — Prometheus v0.97 (WP6)

Interactive Streamlit dashboard for exploring and interpreting strategies
learned by PrometheusStar evolutionary agents across OpenRA and MicroRTS
curriculum runs.

Launch
------
    pip install streamlit pandas matplotlib
    streamlit run prometheus_dashboard.py

Pages
-----
    Overview           — Stage summary badges + key metrics
    Learning Curves    — Win-rate over generations (multi-stage)
    Strategy Evolution — Parallel coordinates + per-param time series + radar
    Agent Inspector    — Per-stage/generation parameter deep-dive
    OOD Dashboard      — Out-of-distribution detection benchmark
    Value Learning     — IRL weight convergence visualisation
"""
from __future__ import annotations

import io
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Guard: check Streamlit is installed before importing
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from matplotlib.patches import Patch
except ImportError as exc:
    print(
        f"\n[prometheus_dashboard] Missing dependency: {exc}\n"
        "Install with:\n"
        "    pip install streamlit pandas matplotlib\n"
        "Then run:\n"
        "    streamlit run prometheus_dashboard.py\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Local imports (after guard)
# ---------------------------------------------------------------------------
try:
    from prometheus.strategy_data import (
        generate_synthetic_openra_run,
        generate_synthetic_microrts_run,
        flatten_generation_log,
        agent_params_over_generations,
        stage_summary_df,
        ood_summary_df,
        value_weight_df,
        load_run,
    )
    _STRATEGY_DATA_OK = True
except ImportError as _e:
    _STRATEGY_DATA_OK = False
    _STRATEGY_DATA_ERR = str(_e)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PARAM_NAMES = ["aggression", "economy_focus", "expansion_rate", "tech_priority", "defense_bias"]

STAGE_COLOURS = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52",
    "#8172B3", "#937860", "#DA8BC3", "#8C8C8C",
]


def _show_fig(fig: "plt.Figure") -> None:
    """Render a matplotlib figure in Streamlit via PNG buffer."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    st.image(buf, use_container_width=True)
    plt.close(fig)


@st.cache_data(show_spinner=False)
def load_data(run_file: str, game: str, seed: int) -> List[Dict[str, Any]]:
    """Load stage_results from JSON file or generate synthetic data."""
    if run_file and Path(run_file).exists():
        try:
            return load_run(run_file)
        except Exception as exc:
            st.warning(f"Could not load run file ({exc}). Using synthetic data.")

    if game == "openra":
        return generate_synthetic_openra_run(seed=seed)
    else:
        return generate_synthetic_microrts_run(seed=seed)


# ---------------------------------------------------------------------------
# Page: Overview
# ---------------------------------------------------------------------------

def page_overview(stage_results: List[Dict]) -> None:
    st.header("Overview")
    st.caption("High-level summary of the curriculum run.")

    summary = stage_summary_df(stage_results)

    # --- Badge row ---
    cols = st.columns(len(stage_results))
    for i, (_, row) in enumerate(summary.iterrows()):
        met = bool(row["target_met"])
        icon = "✅" if met else "❌"
        colour = "#2ecc71" if met else "#e74c3c"
        cols[i].markdown(
            f"""<div style="background:{colour};padding:12px;border-radius:8px;
            text-align:center;color:white;">
            <b>Stage {int(row['stage'])}</b><br>{row['name']}<br>
            {icon} {row['best_win_rate']:.1%} / {row['target']:.1%}
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # --- Key metrics ---
    n_stages = len(stage_results)
    n_met    = int(summary["target_met"].sum())
    total_g  = int(summary["generations_run"].sum())
    overall  = float(summary["best_win_rate"].mean())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stages run",         n_stages)
    m2.metric("Targets met",        f"{n_met}/{n_stages}")
    m3.metric("Total generations",  total_g)
    m4.metric("Mean best win rate", f"{overall:.1%}")

    st.markdown("---")

    # --- Stage summary table ---
    display_cols = ["stage", "name", "difficulty", "target",
                    "best_win_rate", "target_met", "generations_run", "wall_clock_s"]
    display_cols = [c for c in display_cols if c in summary.columns]
    st.dataframe(
        summary[display_cols].style.format({
            "target":        "{:.1%}",
            "best_win_rate": "{:.1%}",
            "wall_clock_s":  "{:.1f}s",
        }),
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Page: Learning Curves
# ---------------------------------------------------------------------------

def page_learning_curves(stage_results: List[Dict]) -> None:
    st.header("Learning Curves")
    st.caption("Win-rate trajectories across all curriculum stages.")

    df = flatten_generation_log(stage_results)

    mode = st.radio(
        "X-axis", ["Cumulative generation", "Per-stage generation"], horizontal=True
    )
    x_col = "cumulative_generation" if mode.startswith("Cumul") else "generation"

    show_mean = st.checkbox("Show mean win rate", value=True)
    show_target = st.checkbox("Show target line", value=True)

    fig, ax = plt.subplots(figsize=(10, 4))

    for i, r in enumerate(stage_results):
        sub = df[df["stage"] == r["stage"]]
        c   = STAGE_COLOURS[i % len(STAGE_COLOURS)]
        label = f"S{r['stage']} {r['name']}"
        ax.plot(sub[x_col], sub["best_win_rate"], color=c, lw=2,   label=f"{label} (best)")
        if show_mean:
            ax.plot(sub[x_col], sub["mean_win_rate"], color=c, lw=1,
                    linestyle="--", alpha=0.6, label=f"{label} (mean)")
        if show_target:
            ax.axhline(r["target"], color=c, lw=0.8, linestyle=":", alpha=0.5)

    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel("Win Rate")
    ax.set_title("Win Rate over Generations")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    _show_fig(fig)

    # Per-stage zoom
    st.subheader("Per-stage zoom")
    selected = st.selectbox(
        "Stage",
        [f"Stage {r['stage']}: {r['name']}" for r in stage_results],
    )
    sel_idx = int(selected.split(":")[0].split()[-1]) - 1
    r = stage_results[sel_idx]
    sub = df[df["stage"] == r["stage"]]

    fig2, ax2 = plt.subplots(figsize=(9, 3.5))
    ax2.plot(sub["generation"], sub["best_win_rate"], lw=2, label="Best win rate")
    ax2.plot(sub["generation"], sub["mean_win_rate"], lw=1, linestyle="--",
             alpha=0.7, label="Mean win rate")
    ax2.axhline(r["target"], color="red", linestyle=":", lw=1.2, label=f"Target {r['target']:.0%}")
    ax2.set_xlabel("Generation within stage")
    ax2.set_ylabel("Win Rate")
    ax2.set_title(f"Stage {r['stage']}: {r['name']} ({r.get('difficulty','')})")
    ax2.legend()
    ax2.grid(alpha=0.3)
    _show_fig(fig2)


# ---------------------------------------------------------------------------
# Page: Strategy Evolution
# ---------------------------------------------------------------------------

def page_strategy_evolution(stage_results: List[Dict]) -> None:
    st.header("Strategy Evolution")
    st.caption("How agent strategy parameters change across curriculum stages.")

    params_df = agent_params_over_generations(stage_results)

    if params_df.empty:
        st.warning("No per-generation agent parameter data found in this run.")
        return

    param_names = sorted(params_df["param_name"].unique().tolist())

    # ---- Parallel coordinates (stage-end snapshots) ----
    st.subheader("Parallel coordinates — stage-end parameters")

    summary = stage_summary_df(stage_results)
    param_cols = [c for c in summary.columns if c.startswith("param_")]

    if param_cols:
        fig, ax = plt.subplots(figsize=(10, 4))
        x_positions = list(range(len(param_cols)))
        norm = plt.Normalize(0, max(1, len(stage_results) - 1))
        cmap = cm.get_cmap("tab10")

        for i, (_, row) in enumerate(summary.iterrows()):
            vals = [float(row[c]) for c in param_cols]
            colour = cmap(norm(i))
            ax.plot(x_positions, vals, marker="o", color=colour,
                    label=f"S{int(row['stage'])} {row['name']}", lw=2)

        ax.set_xticks(x_positions)
        ax.set_xticklabels([c.replace("param_", "") for c in param_cols],
                           rotation=25, ha="right")
        ax.set_ylim(-0.05, 1.05)
        ax.set_ylabel("Parameter value")
        ax.set_title("Strategy Parameters at End of Each Stage")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        _show_fig(fig)
    else:
        st.info("Stage-summary parameter columns not found; showing per-generation data only.")

    # ---- Per-parameter time series ----
    st.subheader("Parameter evolution over generations")

    sel_param = st.selectbox("Parameter", param_names)
    sub = params_df[params_df["param_name"] == sel_param]

    fig3, ax3 = plt.subplots(figsize=(10, 3.5))
    for i, stage in enumerate(sorted(sub["stage"].unique())):
        ss = sub[sub["stage"] == stage]
        r  = stage_results[stage - 1]
        ax3.plot(ss["cumulative_generation"], ss["param_value"],
                 color=STAGE_COLOURS[i % len(STAGE_COLOURS)], lw=2,
                 label=f"S{stage} {r['name']}")
    ax3.set_xlabel("Cumulative generation")
    ax3.set_ylabel(sel_param)
    ax3.set_title(f'"{sel_param}" evolution across curriculum')
    ax3.set_ylim(-0.05, 1.05)
    ax3.legend(fontsize=8)
    ax3.grid(alpha=0.3)
    _show_fig(fig3)

    # ---- Radar chart (per-stage end params) ----
    st.subheader("Radar chart — per-stage strategy profile")

    if param_cols:
        labels = [c.replace("param_", "") for c in param_cols]
        N      = len(labels)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        angles += angles[:1]

        fig4, ax4 = plt.subplots(figsize=(5, 5), subplot_kw={"polar": True})
        cmap = cm.get_cmap("tab10")

        for i, (_, row) in enumerate(summary.iterrows()):
            vals = [float(row[c]) for c in param_cols] + [float(row[param_cols[0]])]
            colour = cmap(i / max(1, len(summary) - 1))
            ax4.plot(angles, vals, color=colour, lw=2,
                     label=f"S{int(row['stage'])} {row['name']}")
            ax4.fill(angles, vals, color=colour, alpha=0.08)

        ax4.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=9)
        ax4.set_ylim(0, 1)
        ax4.set_title("Strategy Radar", y=1.12)
        ax4.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=7)
        _show_fig(fig4)


# ---------------------------------------------------------------------------
# Page: Agent Inspector
# ---------------------------------------------------------------------------

def page_agent_inspector(stage_results: List[Dict]) -> None:
    st.header("Agent Inspector")
    st.caption("Inspect per-generation agent parameter snapshots.")

    params_df = agent_params_over_generations(stage_results)

    col_s, col_g = st.columns(2)
    with col_s:
        stage_options = [f"Stage {r['stage']}: {r['name']}" for r in stage_results]
        sel_stage_str = st.selectbox("Stage", stage_options)
    sel_stage = int(sel_stage_str.split(":")[0].split()[-1])

    r   = stage_results[sel_stage - 1]
    gen_log = r["generation_log"]
    n_gen   = len(gen_log)

    with col_g:
        sel_gen = st.slider("Generation", 1, n_gen, n_gen)

    # Win-rate mini gauge
    g_data = gen_log[sel_gen - 1]
    bwr    = g_data["best_win_rate"]
    mwr    = g_data.get("mean_win_rate", bwr)

    g1, g2, g3 = st.columns(3)
    g1.metric("Best win rate",  f"{bwr:.2%}")
    g2.metric("Mean win rate",  f"{mwr:.2%}")
    g3.metric("Target",         f"{r['target']:.2%}",
              delta=f"{'MET' if bwr >= r['target'] else 'not met'}")

    # Parameter bar chart
    params = g_data.get("agent_params") or r.get("agent_params", {})
    if params:
        pnames = list(params.keys())
        pvals  = [float(params[k]) for k in pnames]

        fig, ax = plt.subplots(figsize=(8, 3))
        bars = ax.barh(pnames, pvals, color=STAGE_COLOURS[:len(pnames)])
        ax.set_xlim(0, 1)
        ax.set_xlabel("Parameter value")
        ax.set_title(
            f"Stage {sel_stage} · Gen {sel_gen} — Agent Parameters"
        )
        for bar, val in zip(bars, pvals):
            ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}", va="center", fontsize=9)
        ax.grid(axis="x", alpha=0.3)
        _show_fig(fig)

    # Generation log table
    st.subheader("Generation log")
    log_rows = []
    for g in gen_log:
        log_rows.append({
            "gen":            g["generation"],
            "best_win_rate":  g["best_win_rate"],
            "mean_win_rate":  g.get("mean_win_rate", None),
        })
    log_df = pd.DataFrame(log_rows)
    st.dataframe(
        log_df.style.format({
            "best_win_rate": "{:.2%}",
            "mean_win_rate": "{:.2%}",
        }),
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Page: OOD Dashboard
# ---------------------------------------------------------------------------

def page_ood_dashboard() -> None:
    st.header("OOD Dashboard")
    st.caption("Out-of-distribution detection benchmark results (inline run).")

    run_ood = st.button("Run OOD Benchmark (takes ~5 s)")

    if run_ood or st.session_state.get("ood_results") is not None:
        if run_ood:
            with st.spinner("Running OOD benchmark …"):
                try:
                    from benchmarks.ood_benchmark import OODBenchmark
                    bench = OODBenchmark(n_samples=200, seed=42)
                    results = bench.run_all()
                    st.session_state["ood_results"] = results
                except Exception as exc:
                    st.error(f"OOD benchmark error: {exc}")
                    return

        results = st.session_state["ood_results"]
        df = ood_summary_df(results)
        st.dataframe(df.style.format({"auroc": "{:.3f}", "tpr": "{:.3f}", "fpr": "{:.3f}"}),
                     use_container_width=True)

        if not df.empty and "auroc" in df.columns:
            fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=False)
            for ax, metric in zip(axes, ["auroc", "tpr", "fpr"]):
                if metric in df.columns:
                    ax.barh(df["detector"] if "detector" in df.columns else df.index,
                            df[metric], color="#4C72B0")
                    ax.set_xlabel(metric.upper())
                    ax.set_title(metric.upper())
                    ax.set_xlim(0, 1)
                    ax.grid(axis="x", alpha=0.3)
            fig.suptitle("OOD Detection Performance")
            fig.tight_layout()
            _show_fig(fig)

            # Scenario flagging rates
            flag_cols = [c for c in df.columns if c.endswith("_flagged")]
            if flag_cols:
                st.subheader("Scenario flagging rates")
                fig2, ax2 = plt.subplots(figsize=(9, 3.5))
                x = np.arange(len(df))
                width = 0.25
                for j, col in enumerate(flag_cols):
                    ax2.bar(x + j * width, df[col], width,
                            label=col.replace("_flagged", "").replace("_", " "))
                ax2.set_xticks(x + width)
                ax2.set_xticklabels(
                    df["detector"] if "detector" in df.columns else df.index,
                    rotation=20, ha="right"
                )
                ax2.set_ylabel("Flagging rate")
                ax2.set_ylim(0, 1)
                ax2.legend()
                ax2.grid(axis="y", alpha=0.3)
                _show_fig(fig2)
    else:
        st.info("Press the button above to run the OOD benchmark inline.")


# ---------------------------------------------------------------------------
# Page: Value Learning
# ---------------------------------------------------------------------------

def page_value_learning() -> None:
    st.header("Value Learning")
    st.caption("Bradley-Terry IRL weight convergence demonstration.")

    n_feats   = st.slider("Feature dimensions", 2, 10, 5)
    n_epochs  = st.slider("Training epochs",   10, 200, 50)
    run_vl    = st.button("Run Value Learning demo")

    if run_vl or st.session_state.get("vl_history") is not None:
        if run_vl:
            with st.spinner("Training value learning agent …"):
                try:
                    from prometheus.value_learning import ValueLearningAgent, SyntheticOracle
                    oracle = SyntheticOracle(n_features=n_feats, seed=42)
                    agent  = ValueLearningAgent(n_features=n_feats)
                    history, true_w = agent.train_to_convergence(
                        oracle, n_epochs=n_epochs
                    )
                    st.session_state["vl_history"]  = history
                    st.session_state["vl_true_w"]   = true_w
                    st.session_state["vl_n_feats"]  = n_feats
                except Exception as exc:
                    st.error(f"Value learning error: {exc}")
                    return

        history = st.session_state["vl_history"]
        true_w  = st.session_state["vl_true_w"]
        n_feats = st.session_state["vl_n_feats"]

        feat_names = [f"φ[{i}]" for i in range(n_feats)]
        vw_df = value_weight_df(history, feat_names)

        # Convergence plot
        st.subheader("Weight convergence")
        fig, ax = plt.subplots(figsize=(10, 4))
        for name in feat_names:
            sub = vw_df[vw_df["feature_name"] == name]
            ax.plot(sub["epoch"], sub["weight_value"], lw=1.5, label=name)
        if true_w is not None:
            for j, tw in enumerate(true_w):
                ax.axhline(tw, color="grey", lw=0.6, linestyle="--", alpha=0.4)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Weight value")
        ax.set_title("IRL Weight Convergence (dashed = true weights)")
        ax.legend(fontsize=8, ncol=3)
        ax.grid(alpha=0.3)
        _show_fig(fig)

        # Final weight comparison
        if true_w is not None:
            st.subheader("Learned vs. true weights")
            final_w = np.array(history[-1])
            fig2, ax2 = plt.subplots(figsize=(8, 3))
            x = np.arange(n_feats)
            ax2.bar(x - 0.2, final_w, 0.4, label="Learned", color="#4C72B0")
            ax2.bar(x + 0.2, true_w,  0.4, label="True",    color="#DD8452", alpha=0.7)
            ax2.set_xticks(x)
            ax2.set_xticklabels(feat_names)
            ax2.set_ylabel("Weight")
            ax2.set_title("Learned vs. True Reward Weights")
            ax2.legend()
            ax2.grid(axis="y", alpha=0.3)
            _show_fig(fig2)
    else:
        st.info("Press the button above to run the value learning demo.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not _STRATEGY_DATA_OK:
        st.error(
            f"prometheus.strategy_data import failed: {_STRATEGY_DATA_ERR}\n"
            "Run from the repo root: `streamlit run prometheus_dashboard.py`"
        )
        return

    st.set_page_config(
        page_title="PrometheusStar Dashboard",
        page_icon="🌟",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🌟 PrometheusStar — Strategy Visualisation Dashboard")
    st.caption("Prometheus v0.97 · WP6 · Evolutionary agent curriculum explorer")

    # --- Sidebar ---
    st.sidebar.header("Controls")

    page = st.sidebar.radio(
        "Page",
        [
            "Overview",
            "Learning Curves",
            "Strategy Evolution",
            "Agent Inspector",
            "OOD Dashboard",
            "Value Learning",
        ],
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Data source")

    game = st.sidebar.selectbox("Game type", ["openra", "microrts"])
    seed = st.sidebar.number_input("Random seed", value=42, min_value=0, max_value=9999)
    run_file = st.sidebar.text_input(
        "Run JSON file (optional)",
        placeholder="/path/to/run.json",
    )

    stage_results = load_data(run_file.strip() or "", game, int(seed))

    if st.sidebar.button("Save current run"):
        from prometheus.strategy_data import save_run
        out = f"run_{game}_seed{seed}.json"
        save_run(stage_results, out)
        st.sidebar.success(f"Saved to {out}")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Loaded {len(stage_results)} stage(s) · "
        f"source: {'file' if (run_file.strip() and Path(run_file.strip()).exists()) else 'synthetic'}"
    )

    # --- Page dispatch ---
    if page == "Overview":
        page_overview(stage_results)
    elif page == "Learning Curves":
        page_learning_curves(stage_results)
    elif page == "Strategy Evolution":
        page_strategy_evolution(stage_results)
    elif page == "Agent Inspector":
        page_agent_inspector(stage_results)
    elif page == "OOD Dashboard":
        page_ood_dashboard()
    elif page == "Value Learning":
        page_value_learning()


if __name__ == "__main__":
    main()
