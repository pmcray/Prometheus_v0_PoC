import json
import os

notebook_path = os.path.join("notebooks", "good_notebook_6_game_learning_comparison.ipynb")

if not os.path.exists(notebook_path):
    print(f"Error: Notebook not found at {notebook_path}")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Define the cells we want to modify or replace
cells = {c.get("id"): c for c in nb.get("cells", [])}

# 1. Update intro cell (ID = intro)
if "intro" in cells:
    intro_source = cells["intro"]["source"]
    intro_str = "".join(intro_source)
    # Update timestamp
    intro_str = intro_str.replace("Last updated: 2026-06-01", "Last updated: 2026-06-02")
    intro_str = intro_str.replace("Modified: 2026-06-01 18:33:40 PDT", "Modified: 2026-06-02 13:00:00 PDT")
    cells["intro"]["source"] = [line + "\n" for line in intro_str.split("\n")]
    if cells["intro"]["source"][-1] == "\n":
        cells["intro"]["source"].pop()
    print("Updated intro cell timestamp.")

# 2. Replace config cell (ID = config)
if "config" in cells:
    config_code = """# ── 1. Global configuration ────────────────────────────────────────────────
SEED = 42
QUICK_MODE = True   # False → full run (~3 h on T4)

if QUICK_MODE:
    N_GENERATIONS   = 12   # puzzle regime shifts (3 cycles of 4 regimes)
    PUZZLES_PER_GEN = 30   # puzzles evaluated each generation
    DQN_PRETRAIN_EP = 200  # DQN training episodes before freeze
    DQN_ONLINE_EP   = 15   # DQN online training episodes per generation for online DQN (item C)
    PROMETHEUS_GAMES = 15  # Prometheus online games per generation
    GPT2_SAMPLES     = 20  # positions GPT-2 is queried on per generation
    BOARD_SIZE       = 9   # 9x9 Go
else:
    N_GENERATIONS   = 60   # 15 cycles of 4 regimes
    PUZZLES_PER_GEN = 120
    DQN_PRETRAIN_EP = 1500
    DQN_ONLINE_EP   = 80
    PROMETHEUS_GAMES = 80
    GPT2_SAMPLES     = 80
    BOARD_SIZE       = 9

# Cyclic regime sequence (item D)
REGIME_SEQUENCE = ['ATARI', 'LADDER', 'KO_FIGHT', 'TERRITORY'] * 15

print(f'Mode: {"QUICK" if QUICK_MODE else "FULL"}')
print(f'  Generations     : {N_GENERATIONS}')
print(f'  Puzzles/gen     : {PUZZLES_PER_GEN}')
print(f'  Board size      : {BOARD_SIZE}x{BOARD_SIZE}')
print(f'  DQN pretrain ep : {DQN_PRETRAIN_EP}')
print(f'  DQN online ep   : {DQN_ONLINE_EP}')
print(f'  Prometheus games: {PROMETHEUS_GAMES}/gen')"""
    cells["config"]["source"] = [line + "\n" for line in config_code.split("\n")]
    print("Replaced config cell.")

# 3. Replace puzzle_engine cell (ID = puzzle_engine)
if "puzzle_engine" in cells:
    puzzle_engine_code = """# ── 2. Tactical puzzle engine (real GoBoard, no mock) ──────────────────────
import numpy as np
from typing import Tuple, List
from prometheus.environments.go import GoBoard


# item A: Real ladder situation generator
def make_ladder_puzzle(board_size: int, rng: np.random.Generator) -> Tuple[GoBoard, int, Tuple[int,int]]:
    \"\"\"Create a real ladder situation: Black has a group of 2 stones with 2 liberties.
    White must play the correct block (r+1, c+1) to keep Black in atari.\"\"\"
    board = GoBoard(size=board_size)
    cx = board_size // 2
    # item B: Randomize position for puzzle diversity
    offset_r = rng.integers(-1, 2)
    offset_c = rng.integers(-1, 1)
    r, c = cx + offset_r, cx + offset_c
    
    # Black group
    board.board[r, c] = GoBoard.BLACK
    board.board[r, c+1] = GoBoard.BLACK
    
    # White surrounding walls
    board.board[r-1, c] = GoBoard.WHITE
    board.board[r, c-1] = GoBoard.WHITE
    board.board[r-1, c+1] = GoBoard.WHITE
    board.board[r+1, c] = GoBoard.WHITE
    
    # Correct White move: block at (r+1, c+1) to force Black to 1 liberty (atari)
    target = (r+1, c+1)
    board.current_player = GoBoard.WHITE
    return board, GoBoard.WHITE, target


# item B: Introduce randomization for all other puzzle generators
def make_atari_puzzle(board_size: int, rng: np.random.Generator) -> Tuple[GoBoard, int, Tuple[int,int]]:
    \"\"\"Create a board where Black has a stone group with exactly one liberty.
    The correct move for White is to play that liberty (capture).\"\"\"
    board = GoBoard(size=board_size)
    cx = rng.integers(2, board_size - 2)
    cy = rng.integers(2, board_size - 2)
    
    stones = [(cx, cy), (cx, cy+1), (cx+1, cy)]
    for r, c in stones:
        if board.is_on_board(r, c):
            board.board[r, c] = GoBoard.BLACK
            
    all_liberties = set()
    for r, c in stones:
        for nr, nc in board.get_neighbors(r, c):
            if board.board[nr, nc] == GoBoard.EMPTY:
                all_liberties.add((nr, nc))
    liberties = list(all_liberties)
    rng.shuffle(liberties)
    
    # Fill all but one liberty with White to create atari
    for r, c in liberties[:-1]:
        board.board[r, c] = GoBoard.WHITE
    target = liberties[-1]
    board.current_player = GoBoard.WHITE
    return board, GoBoard.WHITE, target


def make_ko_puzzle(board_size: int, rng: np.random.Generator) -> Tuple[GoBoard, int, Tuple[int,int]]:
    \"\"\"Create a Ko situation. Correct move: re-capture the Ko stone.\"\"\"
    board = GoBoard(size=board_size)
    cx = rng.integers(2, board_size - 2)
    cy = rng.integers(2, board_size - 2)
    
    board.board[cx, cy-1] = GoBoard.BLACK
    board.board[cx, cy+1] = GoBoard.WHITE
    board.board[cx-1, cy] = GoBoard.BLACK
    board.board[cx+1, cy] = GoBoard.WHITE
    
    target = (cx, cy)
    board.board[cx, cy] = GoBoard.EMPTY
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, target


def make_territory_puzzle(board_size: int, rng: np.random.Generator) -> Tuple[GoBoard, int, Tuple[int,int]]:
    \"\"\"Create a board where Black can extend into empty corner territory.
    Correct move: play into the largest empty corner quadrant.\"\"\"
    board = GoBoard(size=board_size)
    corners = [(0,0), (0, board_size-1), (board_size-1, 0), (board_size-1, board_size-1)]
    rng.shuffle(corners)
    
    for r, c in corners[:-1]:
        board.board[r, c] = GoBoard.WHITE
        
    target = corners[-1]
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, target


PUZZLE_FACTORIES = {
    'ATARI':    make_atari_puzzle,
    'LADDER':   make_ladder_puzzle,
    'KO_FIGHT': make_ko_puzzle,
    'TERRITORY':make_territory_puzzle,
}


def generate_puzzles(regime: str, n: int, board_size: int, seed: int) -> List[Tuple[GoBoard, int, Tuple[int,int]]]:
    \"\"\"Generate n puzzles for a given regime.\"\"\"
    rng = np.random.default_rng(seed)
    puzzles = []
    if regime == 'MIXED':
        regimes = ['ATARI','LADDER','KO_FIGHT','TERRITORY']
        for i in range(n):
            r = regimes[i % len(regimes)]
            puzzles.append(PUZZLE_FACTORIES[r](board_size, rng))
    else:
        factory = PUZZLE_FACTORIES[regime]
        for _ in range(n):
            puzzles.append(factory(board_size, rng))
    return puzzles


def evaluate_move(board: GoBoard, move: Tuple[int,int], correct_move: Tuple[int,int], player: int) -> bool:
    \"\"\"Return True if the proposed move matches the puzzle's correct answer,
    OR if it is a legal move that achieves the same tactical outcome.\"\"\"
    if move == correct_move:
        return True
    if board.is_legal_move(move[0], move[1], player):
        captured = board.would_capture(move[0], move[1], player)
        if len(captured) > 0:
            return True
    return False


# Quick sanity check
rng_test = np.random.default_rng(0)
b, p, m = make_atari_puzzle(BOARD_SIZE, rng_test)
print(f'Atari puzzle: player={"WHITE" if p==GoBoard.WHITE else "BLACK"}, target={m}')
print(f'  Legal move check: {b.is_legal_move(m[0], m[1], p)}')
print(f'  Would capture: {len(b.would_capture(m[0], m[1], p))} stones')
print('Puzzle engine OK.')"""
    cells["puzzle_engine"]["source"] = [line + "\n" for line in puzzle_engine_code.split("\n")]
    print("Replaced puzzle_engine cell.")

# 4. Replace end of dqn_agent cell (ID = dqn_agent) to pre-train both frozen and online agents
if "dqn_agent" in cells:
    source = cells["dqn_agent"]["source"]
    source_str = "".join(source)
    
    # Locate the training blocks and replace them
    lines = [line.rstrip() for line in source_str.split("\n")]
    target_idx = -1
    for i, line in enumerate(lines):
        if "dqn = DQNAgent(board_size=BOARD_SIZE)" in line or "# Instantiate and pre-train DQN on the initial regime" in line:
            target_idx = i
            break
            
    if target_idx != -1:
        # Keep everything up to target_idx
        new_lines = lines[:target_idx]
        new_lines.extend([
            "# Instantiate two DQN agents: one frozen, one online adaptive (item C)",
            "dqn_frozen = DQNAgent(board_size=BOARD_SIZE)",
            "dqn_online = DQNAgent(board_size=BOARD_SIZE)",
            "print(f'DQN architecture: {sum(p.numel() for p in dqn_frozen.q_net.parameters()):,} params')",
            "",
            "print(f'\\nPre-training DQN agents on ATARI puzzles ({DQN_PRETRAIN_EP} episodes)...')",
            "t0 = time.time()",
            "pretrain_rng = np.random.default_rng(99)",
            "for ep in range(DQN_PRETRAIN_EP):",
            "    board, player, correct = make_atari_puzzle(BOARD_SIZE, pretrain_rng)",
            "    reward = dqn_frozen.run_training_episode(board, player, correct)",
            "    # Mirror pretraining onto dqn_online",
            "    dqn_online.replay.push(dqn_frozen.replay.buf[-1])",
            "    dqn_online.train_step()",
            "    dqn_online.train_rewards.append(reward)",
            "",
            "# Evaluate before freezing",
            "val_puzzles = generate_puzzles('ATARI', 30, BOARD_SIZE, seed=7)",
            "dqn_pretrain_acc = evaluate_dqn_on_puzzles(dqn_frozen, val_puzzles)",
            "print(f'Pre-training done in {time.time()-t0:.1f}s')",
            "print(f'DQN pretrain accuracy on ATARI: {dqn_pretrain_acc:.1%}')",
            "",
            "dqn_frozen.freeze()  # Frozen baseline",
            "# dqn_online remains unfrozen to adapt online!",
            "print('DQN baselines ready.')"
        ])
        cells["dqn_agent"]["source"] = [line + "\n" for line in new_lines]
        print("Updated dqn_agent cell with frozen & online instantiations.")

# 5. Modify prometheus_agent cell (ID = prometheus_agent) to add tactic_ladder
if "prometheus_agent" in cells:
    source = cells["prometheus_agent"]["source"]
    source_str = "".join(source)
    
    # 1. Insert tactic_ladder into TACTICS array
    source_str = source_str.replace(
        "TACTICS = [\n    'capture_atari',   # play the last liberty of an opponent group\n    'extend_group',    # add a stone to our largest group\n    'play_centre',     # prefer intersections near board centre\n    'play_corner',     # prefer corner intersections\n    'random_legal',    # uniformly random legal move\n]",
        "TACTICS = [\n    'capture_atari',   # play the last liberty of an opponent group\n    'extend_group',    # add a stone to our largest group\n    'play_centre',     # prefer intersections near board centre\n    'play_corner',     # prefer corner intersections\n    'tactic_ladder',   # block diagonal escape routes of opponent groups (real ladder)\n    'random_legal',    # uniformly random legal move\n]"
    )
    
    # 2. Add tactic_ladder function definition after tactic_play_corner
    target_pos = source_str.find("def tactic_random_legal(board: GoBoard, player: int)")
    if target_pos != -1:
        ladder_fn_code = """def tactic_ladder(board: GoBoard, player: int) -> Optional[Tuple[int,int]]:
    \"\"\"Look for opponent groups with 2 liberties, and play the liberty that puts them in atari.\"\"\"
    opponent = -player
    for r in range(board.size):
        for c in range(board.size):
            if board.board[r, c] == opponent:
                group = board.get_group(r, c)
                if board.count_liberties(group) == 2:
                    liberties = []
                    for gr, gc in group:
                        for nr, nc in board.get_neighbors(gr, gc):
                            if board.board[nr, nc] == GoBoard.EMPTY:
                                if (nr, nc) not in liberties:
                                    liberties.append((nr, nc))
                    for lib in liberties:
                        if board.is_legal_move(lib[0], lib[1], player):
                            # Test if playing this liberty reduces the group to 1 liberty (atari)
                            board_copy = GoBoard(size=board.size)
                            board_copy.board = board.board.copy()
                            board_copy.current_player = player
                            board_copy.play_move(lib[0], lib[1], player)
                            new_group = board_copy.get_group(r, c)
                            if board_copy.count_liberties(new_group) == 1:
                                return lib
    return None


"""
        source_str = source_str[:target_pos] + ladder_fn_code + source_str[target_pos:]
        
    # 3. Add to TACTIC_FNS mapping
    source_str = source_str.replace(
        "    'play_corner':   tactic_play_corner,\n    'random_legal':  tactic_random_legal,",
        "    'play_corner':   tactic_play_corner,\n    'tactic_ladder': tactic_ladder,\n    'random_legal':  tactic_random_legal,"
    )
    
    cells["prometheus_agent"]["source"] = [line + "\n" for line in source_str.split("\n")]
    if cells["prometheus_agent"]["source"][-1] == "\n":
        cells["prometheus_agent"]["source"].pop()
    print("Updated prometheus_agent cell to include tactic_ladder.")

# 6. Replace main_experiment cell (ID = main_experiment)
if "main_experiment" in cells:
    main_exp_code = """# ── 6. Main experiment loop ────────────────────────────────────────────────
results = {
    'gpt2':       [],
    'dqn_frozen': [],
    'dqn_online': [],
    'prometheus': [],
    'regimes':    [],
}

print('=' * 80)
print(f'  Gen  Regime        GPT-2    DQN(Fz)  DQN(On)  Prometheus  Δ(Prom-DQN_On)')
print('=' * 80)

t_total = time.time()

for gen in range(N_GENERATIONS):
    regime = REGIME_SEQUENCE[min(gen, len(REGIME_SEQUENCE)-1)]
    puzzles = generate_puzzles(regime, PUZZLES_PER_GEN, BOARD_SIZE, seed=gen*100)

    # ── GPT-2 (frozen transformer) ──
    gpt2_puzzles = puzzles[:GPT2_SAMPLES]   # subset (GPT-2 is slow)
    gpt2_acc = evaluate_gpt2_on_puzzles(gpt2_puzzles)

    # ── DQN (frozen after pre-training) ──
    dqn_fz_acc = evaluate_dqn_on_puzzles(dqn_frozen, puzzles)

    # ── DQN (online adaptive - item C) ──
    online_puzzles_dqn = generate_puzzles(regime, DQN_ONLINE_EP, BOARD_SIZE, seed=gen*100+2)
    for board, player, correct in online_puzzles_dqn:
        dqn_online.run_training_episode(board, player, correct)
    dqn_on_acc = evaluate_dqn_on_puzzles(dqn_online, puzzles)

    # ── Prometheus (online, meta-cognitive) ──
    online_puzzles_prom = generate_puzzles(regime, PROMETHEUS_GAMES, BOARD_SIZE, seed=gen*100+1)
    _ = prometheus.run_generation(online_puzzles_prom)   # online adaptation
    prom_acc = prometheus.run_generation(puzzles)   # evaluation
    prometheus.end_of_generation_loop(gen, prom_acc, regime)

    results['gpt2'].append(gpt2_acc)
    results['dqn_frozen'].append(dqn_fz_acc)
    results['dqn_online'].append(dqn_on_acc)
    results['prometheus'].append(prom_acc)
    results['regimes'].append(regime)

    print(f'  {gen:3d}  {regime:<12}  {gpt2_acc:6.1%}  {dqn_fz_acc:6.1%}   {dqn_on_acc:6.1%}   {prom_acc:6.1%}      '
          f'{prom_acc - dqn_on_acc:+.1%}')

print('=' * 80)
print(f'Elapsed: {time.time()-t_total:.1f}s')

# Summary statistics
gpt2_arr        = np.array(results['gpt2'])
dqn_frozen_arr  = np.array(results['dqn_frozen'])
dqn_online_arr  = np.array(results['dqn_online'])
prom_arr        = np.array(results['prometheus'])

# Define dqn_arr as dqn_online_arr for compatibility with other notebook cells
dqn_arr = dqn_online_arr

print(f'\\nMean accuracy  GPT-2={gpt2_arr.mean():.1%}  DQN(Fz)={dqn_frozen_arr.mean():.1%}  '
      f'DQN(On)={dqn_online_arr.mean():.1%}  Prometheus={prom_arr.mean():.1%}')
print(f'Final accuracy GPT-2={gpt2_arr[-1]:.1%}  DQN(Fz)={dqn_frozen_arr[-1]:.1%}  '
      f'DQN(On)={dqn_online_arr[-1]:.1%}  Prometheus={prom_arr[-1]:.1%}')
print(f'Prometheus advantage over DQN(On)  mean={prom_arr.mean()-dqn_online_arr.mean():+.1%}  '
      f'final={prom_arr[-1]-dqn_online_arr[-1]:+.1%}')"""
    cells["main_experiment"]["source"] = [line + "\n" for line in main_exp_code.split("\n")]
    print("Replaced main_experiment cell.")

# 7. Replace plot_accuracy cell (ID = plot_accuracy)
if "plot_accuracy" in cells:
    plot_acc_code = """# ── 7. Panel 1: Accuracy curves ────────────────────────────────────────────
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(14, 6))
gens = list(range(N_GENERATIONS))

ax.plot(gens, gpt2_arr * 100, 'r--o', label='GPT-2 (autoregressive, frozen)',
        linewidth=2, markersize=6)
ax.plot(gens, dqn_frozen_arr * 100, 'b--s', label='DQN (deep RL, frozen)',
        linewidth=2, markersize=6)
ax.plot(gens, dqn_online_arr * 100, 'y-.d', color='darkorange', label='DQN (deep RL, online adaptive)',
        linewidth=2, markersize=6)
ax.plot(gens, prom_arr * 100, 'g-^',  label='Prometheus (Goodian mutation + Hofstaderian loop)',
        linewidth=3, markersize=8)

# Shade regime bands
regime_colors = {
    'ATARI': '#fff3cd', 'LADDER': '#d4edda', 'KO_FIGHT': '#f8d7da',
    'TERRITORY': '#d1ecf1', 'MIXED': '#e2d9f3'
}
prev_regime = None
band_start  = 0
for g, regime in enumerate(results['regimes']):
    if regime != prev_regime:
        if prev_regime is not None:
            ax.axvspan(band_start - 0.5, g - 0.5,
                       alpha=0.35, color=regime_colors.get(prev_regime, '#eeeeee'))
            ax.text(band_start + (g - band_start)/2 - 0.5, 95, prev_regime,
                    ha='center', fontsize=9, fontweight='bold', alpha=0.6)
        band_start = g
        prev_regime = regime
# Draw last band
ax.axvspan(band_start - 0.5, len(results['regimes']) - 0.5,
           alpha=0.35, color=regime_colors.get(prev_regime, '#eeeeee'))
ax.text(band_start + (len(results['regimes']) - band_start)/2 - 0.5, 95, prev_regime,
        ha='center', fontsize=9, fontweight='bold', alpha=0.6)

ax.set_xlabel('Generation', fontsize=11)
ax.set_ylabel('Accuracy (%)', fontsize=11)
ax.set_title('Learning and Adaptation Under Shifting Go Puzzle Regimes', fontsize=13, fontweight='bold')
ax.legend(loc='lower left', fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_ylim(-5, 105)

plt.savefig('go_accuracy_comparison.png', dpi=150, bbox_inches='tight')
print('Panel 1 saved to go_accuracy_comparison.png')"""
    cells["plot_accuracy"]["source"] = [line + "\n" for line in plot_acc_code.split("\n")]
    print("Replaced plot_accuracy cell.")

# 8. Replace statistical_test cell (ID = statistical_test)
if "statistical_test" in cells:
    stat_code = """# ── 11. Statistical significance test ─────────────────────────────────────
from scipy import stats as scipy_stats

# Paired t-test: Prometheus vs DQN (frozen)
t_stat_fz, p_val_fz = scipy_stats.ttest_rel(prom_arr, dqn_frozen_arr)
cohens_d_fz = (prom_arr.mean() - dqn_frozen_arr.mean()) / (
    np.std(prom_arr - dqn_frozen_arr, ddof=1) + 1e-9
)

# Paired t-test: Prometheus vs DQN (online)
t_stat_on, p_val_on = scipy_stats.ttest_rel(prom_arr, dqn_online_arr)
cohens_d_on = (prom_arr.mean() - dqn_online_arr.mean()) / (
    np.std(prom_arr - dqn_online_arr, ddof=1) + 1e-9
)

# Prometheus vs GPT-2
t2, p2 = scipy_stats.ttest_rel(prom_arr, gpt2_arr)
d2 = (prom_arr.mean() - gpt2_arr.mean()) / (
    np.std(prom_arr - gpt2_arr, ddof=1) + 1e-9
)

# Set p_val and cohens_d for compatibility with save_results
p_val = p_val_fz
cohens_d = cohens_d_fz

print('Statistical Analysis')
print('=' * 55)
print(f'Prometheus vs DQN (Frozen) — paired t-test')
print(f'  t = {t_stat_fz:+.3f}   p = {p_val_fz:.4f}   Cohen\'s d = {cohens_d_fz:.3f}')
print(f'  Significant (p<0.05): {p_val_fz < 0.05}')
print()
print(f'Prometheus vs DQN (Online) — paired t-test')
print(f'  t = {t_stat_on:+.3f}   p = {p_val_on:.4f}   Cohen\'s d = {cohens_d_on:.3f}')
print(f'  Significant (p<0.05): {p_val_on < 0.05}')
print()
print(f'Prometheus vs GPT-2 — paired t-test')
print(f'  t = {t2:+.3f}   p = {p2:.4f}   Cohen\'s d = {d2:.3f}')
print(f'  Significant (p<0.05): {p2 < 0.05}')
print()
print('Effect size guide: d<0.2 small | 0.2-0.5 medium | >0.5 large')"""
    cells["statistical_test"]["source"] = [line + "\n" for line in stat_code.split("\n")]
    print("Replaced statistical_test cell.")

# 9. Replace save_results cell (ID = save_results)
if "save_results" in cells:
    save_code = """import json
# ── 12. Save all results to JSON for reproducibility ──────────────────────
output = {
    'config': {
        'QUICK_MODE': QUICK_MODE,
        'N_GENERATIONS': N_GENERATIONS,
        'PUZZLES_PER_GEN': PUZZLES_PER_GEN,
        'BOARD_SIZE': BOARD_SIZE,
        'DQN_PRETRAIN_EP': DQN_PRETRAIN_EP,
        'DQN_ONLINE_EP': DQN_ONLINE_EP,
        'PROMETHEUS_GAMES': PROMETHEUS_GAMES,
        'SEED': SEED,
        'device': DEVICE,
    },
    'results': {
        'gpt2':       [float(x) for x in gpt2_arr],
        'dqn_frozen': [float(x) for x in dqn_frozen_arr],
        'dqn_online': [float(x) for x in dqn_online_arr],
        'prometheus': [float(x) for x in prom_arr],
        'regimes':    results['regimes'],
    },
    'summary': {
        'gpt2_mean':    float(gpt2_arr.mean()),
        'dqn_frozen_mean': float(dqn_frozen_arr.mean()),
        'dqn_online_mean': float(dqn_online_arr.mean()),
        'prometheus_mean': float(prom_arr.mean()),
        'prom_vs_dqn_frozen_mean_delta': float(prom_arr.mean() - dqn_frozen_arr.mean()),
        'prom_vs_dqn_online_mean_delta': float(prom_arr.mean() - dqn_online_arr.mean()),
        'prom_vs_gpt2_mean_delta': float(prom_arr.mean() - gpt2_arr.mean()),
        'p_value_vs_dqn_frozen': float(p_val_fz),
        'cohens_d_vs_dqn_frozen': float(cohens_d_fz),
        'p_value_vs_dqn_online': float(p_val_on),
        'cohens_d_vs_dqn_online': float(cohens_d_on),
    },
    'prometheus_meta': {
        'final_probabilities':  {k: float(v) for k, v in prometheus.meta.get_strategy_probabilities().items()},
        'best_strategy':        prometheus.meta.get_best_strategy(),
        'convergence_score':    float(prometheus.meta.get_statistics()['convergence_score']),
        'overall_success_rate': float(prometheus.meta.get_success_rate()),
        'safety_decisions':     prometheus.governor.get_safety_statistics(),
        'self_modifications':   len([e for e in prometheus.loop_log if e['correction_applied']]),
    },
}

out_path = 'go_game_learning_results.json'
with open(out_path, 'w') as f:
    json.dump(output, f, indent=2)

# Colab sync and automatic download boilerplate
def export_output_file(filename: str, gdrive_subdir: str = "results") -> bool:
    import os, sys
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found.")
        return False
    print(f"Saved locally: {os.path.abspath(filename)}")
    
    IN_COLAB = 'google.colab' in sys.modules
    if IN_COLAB:
        gdrive_dir = '/content/drive/MyDrive/Prometheus_v0_PoC'
        if os.path.exists('/content/drive'):
            dest_dir = os.path.join(gdrive_dir, gdrive_subdir)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(filename))
            import shutil
            shutil.copy(filename, dest_path)
            print(f"Saved permanently to GDrive: {dest_path}")
        else:
            print("Google Drive not mounted. Call mount_gdrive() to enable persistent GDrive saving.")
            
        try:
            from google.colab import files
            print(f"Triggering browser download for {filename}...")
            files.download(filename)
        except Exception as e:
            print(f"Failed to trigger browser download: {e}")
    return True

export_output_file('go_game_learning_results.json')
export_output_file('go_accuracy_comparison.png')
export_output_file('prometheus_synaptic_mutation.png')
export_output_file('prometheus_strange_loop.png')
export_output_file('architecture_comparison_table.png')

print(f'Results saved to {out_path}')
print()
print('Final summary:')
print(f'  GPT-2 mean accuracy        : {output["summary"]["gpt2_mean"]:.1%}')
print(f'  DQN (Frozen) mean accuracy : {output["summary"]["dqn_frozen_mean"]:.1%}')
print(f'  DQN (Online) mean accuracy : {output["summary"]["dqn_online_mean"]:.1%}')
print(f'  Prometheus mean accuracy   : {output["summary"]["prometheus_mean"]:.1%}')
print(f'  Prometheus vs DQN(On) (Δ)  : {output["summary"]["prom_vs_dqn_online_mean_delta"]:+.1%}')"""
    cells["save_results"]["source"] = [line + "\n" for line in save_code.split("\n")]
    print("Replaced save_results cell.")

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("Saved notebook enhancements successfully.")
