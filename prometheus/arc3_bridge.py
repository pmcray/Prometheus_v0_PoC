# -- Prometheus ARC-AGI-3 Bridge v15 (Production Module) ---------------------
# Neural Latent Reasoning Architecture
# ---------------------------------------------------------------------------
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import random, time, math, json, collections, heapq, os
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import deque

try:
    import arc_agi
    from arcengine import GameAction, GameState
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False

from prometheus.wp71_arc_agi3 import (
    ARC3Action, ARC3Observation, ARC3Episode,
    ARC3WorldModel, ARC3GoalInferrer,
    ARC3ExplorationPolicy, ARC3StrangeLoopAgent,
    _SyntheticARCGame,
)

class ARC3VisionTransformer(nn.Module):
    """Temporal Transformer for pattern recognition and object permanence."""
    def __init__(self, n_colors=16, latent_dim=64, frame_stack=4, nhead=4, num_layers=2):
        super().__init__()
        self.frame_stack = frame_stack
        self.latent_dim = latent_dim
        
        # CNN backbone for spatial feature extraction
        self.conv1 = nn.Conv2d(n_colors, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool  = nn.MaxPool2d(2, 2)
        self.gap   = nn.AdaptiveAvgPool2d((4, 4)) # Global Average Pooling to 4x4
        
        # Transformer for temporal reasoning across frames
        self.feature_extractor = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 128),
            nn.ReLU()
        )
        
        encoder_layer = nn.TransformerEncoderLayer(d_model=128, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc = nn.Linear(128, latent_dim)
        
        # Imagination: transition model (latent, action) -> next_latent
        self.action_embedding = nn.Embedding(8, 32) # 7 types + 1 padding
        self.transition = nn.Sequential(
            nn.Linear(latent_dim + 32, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim)
        )
        
        # Step 1: Success Simulation (Reward Predictor)
        self.reward_predictor = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # [M] Step 2: Latent Sequence Completer
        self.sequence_completer = nn.Sequential(
            nn.Linear(latent_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim)
        )
        
        self.optimizer = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self._device)

    def predict_next_in_sequence(self, latent_history):
        """Pattern completion: predict next latent based on recent trajectory."""
        if len(latent_history) < 2: return latent_history[-1]
        # Simple linear extrapolation in latent space for pattern completion
        last = latent_history[-1]
        prev = latent_history[-2]
        combined = torch.cat([last, prev], dim=1)
        return self.sequence_completer(combined)

    def forward(self, stack_list):
        # stack_list is (4, 64, 64)
        stack = torch.tensor(np.array(stack_list), dtype=torch.long, device=self._device)
        
        # One-hot encode each frame separately
        one_hot = F.one_hot(stack % 16, num_classes=16).permute(0, 3, 1, 2).float()
        
        # Spatial encoding
        x = self.pool(F.relu(self.conv1(one_hot))) # (4, 32, 32, 32)
        x = self.pool(F.relu(self.conv2(x)))       # (4, 64, 16, 16)
        x = self.gap(x)                            # (4, 64, 4, 4)
        
        # Temporal encoding
        features = self.feature_extractor(x)       # (4, 128)
        features = features.unsqueeze(0)           # (1, 4, 128)
        
        transformed = self.transformer(features)   # (1, 4, 128)
        
        # Use the latest frame's representation
        out = self.fc(transformed[:, -1, :])       # (1, 64)
        return out

    def imagine(self, latent, action_type_idx):
        """Predict the next latent state and extrinsic reward."""
        a_emb = self.action_embedding(torch.tensor([action_type_idx], device=self._device))
        combined = torch.cat([latent, a_emb], dim=1)
        next_lat = self.transition(combined)
        pred_rew = self.reward_predictor(next_lat)
        return next_lat, pred_rew.item()

    def train_step(self, obs_stack, next_obs_stack, action_type_idx=None, extrinsic_reward=0.0):
        if self.optimizer is None: 
            self.to(self._device)
            self.optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
            
        curr_lat = self.forward(obs_stack)
        next_lat = self.forward(next_obs_stack).detach()
        
        # Loss 1: Temporal Consistency (Physics learning)
        loss_cons = F.mse_loss(curr_lat, next_lat)
        
        # Loss 3: Spatial Consistency Loss (Consistency with reward signal)
        pred_rew = self.reward_predictor(curr_lat)
        rew_target = torch.tensor([[float(extrinsic_reward)]], device=self._device)
        # Weighted loss for sparse rewards: 100x weight on positive rewards
        if extrinsic_reward > 0:
            loss_rew = 100.0 * F.mse_loss(pred_rew, rew_target)
        else:
            loss_rew = F.mse_loss(pred_rew, rew_target)
        
        # Loss 2: Transition (Imagination training)
        if action_type_idx is not None:
            imag_next_lat, _ = self.imagine(curr_lat, action_type_idx)
            loss_trans = F.mse_loss(imag_next_lat, next_lat)
            loss = loss_cons + loss_trans + loss_rew
        else:
            loss = loss_cons + loss_rew

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return min(1.0, loss_cons.item()) # Return capped surprise for curiosity

_vision_model = ARC3VisionTransformer()

def save_vision_weights(path="arc3_vision_transformer.pth"):
    """Persist the world-model weights."""
    torch.save(_vision_model.state_dict(), path)
    return os.path.abspath(path)

def load_vision_weights(path="arc3_vision_transformer.pth"):
    """Restore the world-model weights."""
    if os.path.exists(path):
        _vision_model.load_state_dict(torch.load(path))
        return True
    return False

def visualize_latent_space(episodes):
    """[M] Step 3: Latent Space Visualization using PCA."""
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA
    
    latents = []
    colors = []
    
    for ep in episodes:
        for obs, action, reward in ep.history:
            # Reconstruct frame stack from history if possible, or just use grid
            # For simplicity, we'll just run forward on the single grid repeated
            g = [obs.grid] * 4
            with torch.no_grad():
                lat = _vision_model(g).cpu().numpy().flatten()
            latents.append(lat)
            # Use max color in grid as a proxy for 'object type'
            colors.append(np.max(obs.grid))
            
    if not latents: return
    
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(latents)
    
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(reduced[:, 0], reduced[:, 1], c=colors, cmap='tab10', alpha=0.6)
    plt.colorbar(scatter, label='Max Grid Color')
    plt.title('ARC-AGI-3 Latent Space (Transformer Embeddings)')
    plt.xlabel('PCA 1')
    plt.ylabel('PCA 2')
    plt.grid(True, alpha=0.3)
    plt.show()

_TO_GA = {"move_up":"ACTION1","move_down":"ACTION2","move_left":"ACTION3","move_right":"ACTION4","rotate":"ACTION5","place":"ACTION6","undo":"ACTION7"}

def _frame_to_grid(frame):
    raw = getattr(frame, "frame", None)
    if raw is None or not hasattr(raw, "__len__") or len(raw) == 0: 
        return [[0]*64 for _ in range(64)], 64, 64
    first = raw[0] if (hasattr(raw[0], "__len__") and len(raw[0]) > 0 and hasattr(raw[0][0], "__len__")) else raw
    h = len(first)
    w = len(first[0]) if h > 0 else 0
    grid = [[int(first[r][c]) % 16 for c in range(min(w, 64))] for r in range(min(h, 64))]
    actual_h, actual_w = len(grid), len(grid[0]) if len(grid) > 0 else 0
    for row in grid:
        while len(row) < 64: row.append(0)
    while len(grid) < 64: grid.append([0]*64)
    return grid, actual_h, actual_w

class NavigationSolver:
    """[M] Navigation solver - Goal-Aware (Appearance Matching)."""
    def __init__(self, game_id="generic"):
        self._game_id = game_id
        self._agent_color = None
        self._last_pos = None
        self._steps_no_progress = 0
        self._current_direction = random.choice(["move_up", "move_down", "move_left", "move_right"])
        self._dir_steps = 0
        self._known_goal_color = None
        self._motion_history = collections.defaultdict(list) # Color -> positions
        self._background_color = 0
        self._confidence = 0.0

    def next_action(self, env, reward) -> Optional[str]:
        grid = np.array(env.frame_stack[-1])
        prev_grid = np.array(env.frame_stack[-2])
        
        # Detect background color if not already known
        self._background_color = env._scanner._background_color
        
        # [M] Motion tracking to identify agent
        changed_pixels = np.argwhere(grid != prev_grid)
        if len(changed_pixels) > 0 and len(changed_pixels) < 100: # Reasonable change size
             for r, c in changed_pixels:
                 color = grid[r, c]
                 if color != self._background_color and color != 0: # Not background
                     self._motion_history[color].append((r, c))
                     # Keep recent history
                     if len(self._motion_history[color]) > 20:
                         self._motion_history[color].pop(0)

        # Detect Goal Preview in common ARC-AGI-3 UI locations
        goal_areas = [
            grid[52:64, 0:32],   # Bottom left
            grid[0:16, 52:64],   # Top right
            grid[52:64, 52:64],  # Bottom right
        ]
        
        found_goal = None
        for goal_area in goal_areas:
            goal_pixels = goal_area[(goal_area != 0) & (goal_area != 1) & (goal_area != 3) & (goal_area != 4)]
            if len(goal_pixels) > 0:
                 counts = collections.Counter(goal_pixels.flatten())
                 found_goal = counts.most_common(1)[0][0]
                 break
        
        if found_goal is not None:
            self._known_goal_color = found_goal

        # Identify agent candidate
        field = grid[0:50, 0:50]
        agent_candidates = []
        
        # If we have motion history, prefer the most recently moved color
        active_colors = [c for c in self._motion_history if len(self._motion_history[c]) > 0]
        if active_colors:
            # Sort by frequency of motion
            active_colors.sort(key=lambda c: len(self._motion_history[c]), reverse=True)
            for c in active_colors:
                pos = np.argwhere(field == c)
                if len(pos) > 0:
                    agent_candidates.append((len(pos), c, pos))
                    break
        
        # Fallback to any non-static color if no motion history
        if not agent_candidates:
            for c in range(1, 16):
                if c == self._background_color: continue
                pos = np.argwhere(field == c)
                if 0 < len(pos) < 50: # Agents are usually small
                    agent_candidates.append((len(pos), c, pos))
        
        if not agent_candidates:
            return self._random_fallback()
            
        agent_candidates.sort(key=lambda x: x[0]) # Smallest object is likely agent
        _, self._agent_color, agent_pos = agent_candidates[0]
        ay, ax = np.mean(agent_pos, axis=0)
        
        # Appearance Matching: does agent color match goal color?
        needs_change = False
        if self._known_goal_color is not None and self._agent_color != self._known_goal_color:
            needs_change = True
            
        # Navigation logic
        target = None
        if needs_change:
            # Seek "Switchers": objects that match the goal color
            switchers = np.argwhere(field == self._known_goal_color)
            if len(switchers) > 0:
                target = switchers[np.argmin(np.sum(np.abs(switchers - [ay, ax]), axis=1))]
        
        if target is None:
            # Seek "Targets": Often color 5 or 2 or 8
            for t_color in [self._known_goal_color, 5, 2, 8]:
                if t_color is None or t_color == self._agent_color: continue
                targets = np.argwhere(field == t_color)
                if len(targets) > 0:
                    target = targets[np.argmin(np.sum(np.abs(targets - [ay, ax]), axis=1))]
                    break
            
        if target is None:
            # Fallback to any interactive object
            others = np.argwhere((field != self._background_color) & (field != 0) & (field != self._agent_color))
            if len(others) > 0:
                target = others[np.argmin(np.sum(np.abs(others - [ay, ax]), axis=1))]

        if target is None:
            return self._random_fallback()

        # Pathfinding to target
        ty, tx = target
        dy, dx = ty - ay, tx - ax
        
        if self._last_pos is not None and np.allclose([ay, ax], self._last_pos, atol=0.1):
            self._steps_no_progress += 1
        else:
            self._steps_no_progress = 0
            self._last_pos = (ay, ax)

        # If navigation is consistently failing (stalled), return None to let scanner take over
        if self._steps_no_progress > 15:
            return None

        if abs(dy) > abs(dx):
            return "move_up" if dy < 0 else "move_down"
        else:
            return "move_left" if dx < 0 else "move_right"

    def _random_fallback(self):
        self._dir_steps += 1
        if self._dir_steps > 8 or random.random() < 0.15:
            self._current_direction = random.choice(["move_up", "move_down", "move_left", "move_right"])
            self._dir_steps = 0
        return self._current_direction

class _GridScanner:
    def __init__(self, divisions=32):
        self.divisions, self.stalled_count, self._idx = divisions, 0, 0
        self._centres = []
        self.grid_h, self.grid_w = 64, 64
        self._last_grid_hash = None
        self._click_history = collections.Counter()
        self._recent_changes = set()
        self._reactive_pixels = collections.Counter() # Pixels that caused changes
        self._visit_count = np.zeros((64, 64))
        self._background_color = 0

    def reset_coverage(self):
        """Reset click history to force re-exploration."""
        self._click_history.clear()
        self._visit_count.fill(0)
        self.stalled_count = 0

    def _build(self, grid=None, h=64, w=64):
        self.grid_h, self.grid_w = h, w
        grid_np = np.array(grid) if grid is not None else np.zeros((h, w))
        
        # [M] Detect background color (most frequent in the grid)
        counts = collections.Counter(grid_np.flatten())
        if counts:
            self._background_color = counts.most_common(1)[0][0]
        
        # Comprehensive list of all pixels
        all_pixels = [(x, y) for y in range(h) for x in range(w)]
        scored = []
        
        # Find objects (non-background, non-black)
        objs = np.argwhere((grid_np != self._background_color) & (grid_np != 0))
        obj_set = set((int(o[1]), int(o[0])) for o in objs)
        
        # Priority 1: Objects (non-zero)
        # Priority 2: Neighbors of objects
        # Priority 3: Reactive pixels (ones that worked before)
        # Priority 4: Systematic sweep
        
        targets = set()
        for oy, ox in objs:
            for dy in [-2, -1, 0, 1, 2]:
                for dx in [-2, -1, 0, 1, 2]:
                    ny, nx = oy+dy, ox+dx
                    if 0 <= ny < h and 0 <= nx < w: 
                        targets.add((nx, ny))
        
        for x, y in all_pixels:
            dist_sq = 4000.0
            if targets:
                dist_sq = min((x-tx)**2 + (y-ty)**2 for tx, ty in targets)
            
            # Huge boost for objects, significant boost for neighbors
            obj_boost = 1200.0 if (x, y) in obj_set else 0.0
            neighbor_boost = 300.0 if (x, y) in targets else 0.0
            
            # Change-affinity: prefer areas that recently changed
            change_boost = 800.0 if (x, y) in self._recent_changes else 0.0
            
            # Reactive boost: prefer pixels that have reacted to clicks before
            reactive_boost = self._reactive_pixels[(x, y)] * 1000.0
            
            # Novelty: penalize frequent clicks heavily
            clicks = self._click_history[(x, y)]
            novelty_penalty = clicks * 150.0 + (500.0 if clicks > 0 else 0.0)
            
            # Systematic bonus: use larger primes for better 64x64 coverage
            systematic_bonus = ( (x % 7) * 10.0 + (y % 11) * 10.0 )
            
            # Random jitter to avoid getting stuck in patterns
            jitter = random.random() * 20.0
            
            score = obj_boost + neighbor_boost + change_boost + reactive_boost - novelty_penalty + (150.0 / (dist_sq + 1.0)) + systematic_bonus + jitter
            scored.append((score, (x, y)))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        self._centres = [s[1] for s in scored]
        self._idx = 0

    def refine(self, grid=None):
        self._build(grid, self.grid_h, self.grid_w)
        # Occasionally jump to a completely random low-click area
        if random.random() < 0.2:
            self._idx = random.randint(len(self._centres)//2, len(self._centres)-1)
        else:
            self._idx = random.randint(0, min(10, len(self._centres)-1))

    def next_click(self):
        if not self._centres: return ARC3Action(action_type="place", x=random.randint(0, self.grid_w-1), y=random.randint(0, self.grid_h-1))
        
        # Occasionally suggest a rotation before clicking to try different selections
        if random.random() < 0.05:
            return ARC3Action(action_type="rotate", param=random.randint(0, 15))
            
        if self._idx >= len(self._centres):
            self.refine()
            
        x, y = self._centres[self._idx]; self._idx += 1
        self._click_history[(x, y)] += 1
        # Use random param for place to explore color/value space
        param = random.randint(0, 15) if random.random() < 0.2 else None
        return ARC3Action(action_type="place", x=x, y=y, param=param)

class PrometheusARC3LiveEnv:
    def __init__(self, env_wrapper, game_id):
        self._env, self.game_type = env_wrapper, game_id
        self.frame_stack = deque([[[0]*64 for _ in range(64)]]*4, maxlen=4)
        # [M] NavigationSolver is now initialized for all games to catch any movement tasks
        self._navigation_solver = NavigationSolver(game_id=game_id)
        self._scanner = _GridScanner(); self.total_actions, self.total_levels = 0, 0
        self.state_novelty_buffer = set()
        self.actual_h, self.actual_w = 64, 64
        self._start_session()
    def _start_session(self):
        f = self._env.reset(); g, h, w = _frame_to_grid(f)
        self.actual_h, self.actual_w = h, w
        for _ in range(4): self.frame_stack.append(g)
        self.total_levels = int(getattr(f, "levels_completed", 0) or 0)
        self._scanner._build(g, h, w) # Pass grid and dims to scanner

    def begin_window(self): return ARC3Observation.from_grid_list(self.frame_stack[-1], score=float(self.total_levels), step=0)

    def solver_action(self, reward) -> Optional[ARC3Action]:
        """Restored logic: only returns an action if solver is confident."""
        # [M] Try NavigationSolver first
        act_name = self._navigation_solver.next_action(self, reward)
        if act_name:
             # Only use navigation actions if we've seen movement work before
             # or if it's the specific ls20 game
             if self.game_type == "ls20" or self._navigation_solver._steps_no_progress < 3:
                 return ARC3Action(action_type=act_name)

        # Grid scanner only runs if we haven't seen any changes or stalled
        if self._scanner.stalled_count > 10:
            return self._scanner.next_click()

        return None

    def step(self, action):
        prev_stack = list(self.frame_stack); prev_lvl = self.total_levels
        prev_h, prev_w = self.actual_h, self.actual_w
        ga_name = _TO_GA.get(action.action_type, "ACTION1")
        
        # Ensure action coordinates are valid
        ax, ay = int(action.x), int(action.y)
        if action.action_type == "place":
            ax = max(0, min(ax, self.actual_w - 1))
            ay = max(0, min(ay, self.actual_h - 1))

        # [M] Improved data payload to pass params for rotate/selection
        data = {}
        if "ACTION6" in ga_name:
            data = {"x": ax, "y": ay}
        if action.param is not None:
            # Pass param as both 'value' and 'param' for compatibility
            data["value"] = action.param
            data["param"] = action.param

        f = self._env.step(getattr(GameAction, ga_name), data=data if data else None)

        grid, h, w = _frame_to_grid(f); self.frame_stack.append(grid); next_stack = list(self.frame_stack)
        self.actual_h, self.actual_w = h, w
        self.total_actions += 1

        # Check if grid changed for the scanner
        if h != prev_h or w != prev_w:
            self._scanner._build(grid, h, w)
            self._scanner.stalled_count = 0
        elif np.array_equal(prev_stack[-1], grid):
            self._scanner.stalled_count += 1
            if self._scanner.stalled_count % 30 == 0: # More frequent refinement
                self._scanner.refine(grid)
        else:
            self._scanner.stalled_count = 0
            # Identify changed pixels for the scanner
            changed = np.argwhere(np.array(prev_stack[-1]) != np.array(grid))
            self._scanner._recent_changes = set((int(p[1]), int(p[0])) for p in changed)
            # [M] Track reactive pixels (ones that were actually clicked when a change happened)
            if action.action_type == "place" and len(changed) > 0:
                self._scanner._reactive_pixels[(action.x, action.y)] += 1
            
            # If place resulted in change, refine to prioritize near the change
            if action.action_type == "place": self._scanner.refine(grid)
        
        # [M] Step 4: Curiosity (Intrinsic Reward from prediction surprise)
        from prometheus.wp71_arc_agi3 import _ACTION_TYPES
        try: atype_idx = _ACTION_TYPES.index(action.action_type)
        except: atype_idx = 7
        
        # Combine rewards: Extrinsic (Levels) + Intrinsic (Surprise + Change + Novelty)
        self.total_levels = int(getattr(f, "levels_completed", prev_lvl) or prev_lvl)
        extrinsic = float(self.total_levels - prev_lvl)
        
        # Surprise from world model
        surprise = _vision_model.train_step(prev_stack, next_stack, action_type_idx=atype_idx, extrinsic_reward=extrinsic)
        
        # Grid change reward
        changed_pixels = not np.array_equal(prev_stack[-1], grid)
        change_reward = 0.20 if changed_pixels else 0.0 # Boost change reward
        
        # State novelty reward
        with torch.no_grad():
            next_lat = _vision_model(next_stack)
        lhash = hash(tuple(next_lat.cpu().numpy().flatten().round(2)))
        novelty_reward = 0.0
        if extrinsic > 0: self.state_novelty_buffer.clear() # Reset on reward
        
        if lhash not in self.state_novelty_buffer:
            self.state_novelty_buffer.add(lhash)
            novelty_reward = 0.15 # Boost novelty reward
            if len(self.state_novelty_buffer) > 2000: self.state_novelty_buffer.clear()
            
        intrinsic = min(0.5, (surprise * 0.5) + change_reward + novelty_reward)
        
        return ARC3Observation.from_grid_list(grid, score=float(self.total_levels), step=self.total_actions), extrinsic, intrinsic


class PrometheusARC3SyntheticEnv:
    """Fallback environment for when arc_agi toolkit is missing."""
    def __init__(self, synth_game):
        self._env = synth_game
        self.game_type = synth_game.game_type
        self.total_levels, self.total_actions = 0, 0
        self.frame_stack = deque([[[0]*64 for _ in range(64)]]*4, maxlen=4)
        self.actual_h, self.actual_w = 64, 64
        self._scanner = _GridScanner()
        # Initialize frame stack
        obs = self._env.observation()
        g, h, w = self._grid_to_64x64(obs.grid)
        for _ in range(4): self.frame_stack.append(g)
        self.actual_h, self.actual_w = h, w
        self._scanner._build(g, h, w)

    def _grid_to_64x64(self, grid_tuple):
        grid = [list(row) for row in grid_tuple]
        h, w = len(grid), len(grid[0]) if len(grid) > 0 else 0
        padded = [[grid[r][c] if r < h and c < w else 0 for c in range(64)] for r in range(64)]
        return padded, h, w

    def begin_window(self):
        return self._env.observation()
    def solver_action(self, reward) -> Optional[ARC3Action]:
        return None
    def step(self, action):
        self.total_actions += 1
        obs, extrinsic = self._env.step(action)
        self.total_levels = int(obs.score)
        
        # Update frame stack
        g, h, w = self._grid_to_64x64(obs.grid)
        self.frame_stack.append(g)
        
        intrinsic = 0.0 # Curiosity still 0 for synthetic without vision model training
        return obs, extrinsic, intrinsic


class PatchedExplorationPolicy(ARC3ExplorationPolicy):
    def select_action(self, obs, world_model, goal_inferrer, solved_episodes=None, strategy=None):
        if strategy:
            # Temporarily force the strategy if provided
            old_strat = self.active_strategy
            self._active_strategy = strategy
            res = super().select_action(obs, world_model, goal_inferrer, solved_episodes)
            self._active_strategy = old_strat
            return res
        return super().select_action(obs, world_model, goal_inferrer, solved_episodes)

    def _goal_directed_action(self, obs: ARC3Observation, goal_inferrer: ARC3GoalInferrer) -> ARC3Action:
        """Improved goal-directed action using vision model imagination."""
        goal = goal_inferrer.most_likely_goal
        if goal == "exploration":
            return self._random_action(obs)
            
        # For other goals, try to find an action that the model thinks is good
        # We'll use a 1-step lookahead here for speed, since select_action is called often
        best_action = self._random_action(obs)
        max_val = -1.0
        
        try:
            # We need the current latent
            # Note: we don't have the frame stack here, so we'll use the single grid
            g = [list(obs.grid)] * 4
            with torch.no_grad():
                curr_lat = _vision_model(g)
            
            from prometheus.wp71_arc_agi3 import _ACTION_TYPES
            for sim_idx, sim_atype in enumerate(_ACTION_TYPES):
                imag_lat, pred_extrinsic = _vision_model.imagine(curr_lat, sim_idx)
                
                # Valuation based on goal
                if goal == "maximise_score":
                    val = pred_extrinsic
                elif goal == "reach_target" or goal == "fill_pattern":
                    # Heuristic: grid changes are good for these goals
                    val = F.mse_loss(curr_lat, imag_lat).item()
                else:
                    val = 0.0
                
                if val > max_val:
                    max_val = val
                    if sim_atype == "place":
                        # Use object-centric bias for place
                        grid = np.array(obs.grid)
                        objects = np.argwhere(grid > 0)
                        if len(objects) > 0:
                            target = objects[random.randint(0, len(objects)-1)]
                            best_action = ARC3Action(action_type="place", x=int(target[1]), y=int(target[0]))
                        else:
                            best_action = ARC3Action(action_type="place", x=random.randint(0, 63), y=random.randint(0, 63))
                    else:
                        best_action = ARC3Action(action_type=sim_atype)
        except:
            pass
            
        return best_action

class PatchedStrangeLoopAgent(ARC3StrangeLoopAgent):
    def __init__(self, window_steps=100, mutation_rate=0.05, fitness_threshold=0.5):
        super().__init__(max_steps_per_episode=window_steps, mutation_rate=mutation_rate, fitness_threshold=fitness_threshold)
        self.policy, self.episode_logs = PatchedExplorationPolicy(mutation_rate=mutation_rate), []
    def run_episode(self, env):
        self._episode_count += 1; obs = env.begin_window(); episode = ARC3Episode(game_id=env.game_type, level=self._episode_count)
        strat, reward = self.policy.active_strategy, 0.0
        
        # Step 3: Hypothesis-driven exploration
        _ = self.goal_inferrer.get_hypothesis_for_test()
        
        curiosity_history = deque(maxlen=10)
        latent_history = deque(maxlen=5)
        action_history = collections.Counter()
        failure_buffer = set() # (x, y) coordinates that failed to react
        strat_reward = 0.0
        
        for step_idx in range(self.max_steps_per_episode):
            s_act = env.solver_action(reward)
            if s_act: 
                action = s_act
                # Ensure bounded place
                if action.action_type == "place":
                    action = ARC3Action(action_type="place", 
                                      x=max(0, min(action.x, env.actual_w - 1)),
                                      y=max(0, min(action.y, env.actual_h - 1)))
            else: 
                # [M] Step 2: Latent Sequence Completion
                curr_lat = _vision_model(list(env.frame_stack))
                latent_history.append(curr_lat)
                
                # Step 3: Beam Search Simulation
                from prometheus.wp71_arc_agi3 import _ACTION_TYPES
                
                # (total_score, action_type, sequence, current_latent)
                beam = [(0.0, None, [], curr_lat)]
                beam_depth = 4 # Increased depth
                beam_width = 4
                
                for _ in range(beam_depth):
                    new_candidates = []
                    for b_score, b_act, b_seq, b_lat in beam:
                        for sim_idx, sim_atype in enumerate(_ACTION_TYPES):
                            imag_lat, pred_extrinsic = _vision_model.imagine(b_lat, sim_idx)
                            curiosity = F.mse_loss(b_lat, imag_lat).item()
                            
                            if len(latent_history) >= 2:
                                pattern_lat = _vision_model.predict_next_in_sequence(list(latent_history))
                                pattern_score = 1.0 / (F.mse_loss(imag_lat, pattern_lat).item() + 1e-6)
                            else:
                                pattern_score = 0.0
                                
                            # Action Novelty: penalize actions we've taken a lot recently
                            novelty_score = 1.0 / (action_history[sim_atype] + 1.0)
                            
                            step_score = (pred_extrinsic * 100.0) + (curiosity * 5.0) + (pattern_score * 0.5) + (novelty_score * 2.0)
                            new_score = b_score + step_score
                            
                            new_seq = b_seq + [sim_atype]
                            new_candidates.append((new_score, new_seq[0], new_seq, imag_lat))
                    
                    # Sort and prune beam
                    new_candidates.sort(key=lambda x: x[0], reverse=True)
                    beam = new_candidates[:beam_width]
                
                best_sim_act = beam[0][1] if beam else None
                
                if best_sim_act and random.random() < 0.8: # 80% imagination influence
                    if best_sim_act == "place":
                        # [M] Step 3: Salient & Symmetric Interaction
                        grid = np.array(obs.grid)
                        objects = np.argwhere(grid > 0)
                        # Filter objects to within actual grid dimensions
                        valid_objects = [obj for obj in objects if (int(obj[1]), int(obj[0])) not in failure_buffer and int(obj[1]) < env.actual_w and int(obj[0]) < env.actual_h]
                        
                        if valid_objects:
                            target = valid_objects[random.randint(0, len(valid_objects)-1)]
                            action = ARC3Action(action_type="place", x=int(target[1]), y=int(target[0]))
                        else:
                            # Clear buffer and use scanner's systematic search
                            failure_buffer.clear()
                            action = env._scanner.next_click()
                    else:
                        action = ARC3Action(action_type=best_sim_act)
                else:
                    action = self.policy.select_action(obs, self.world_model, self.goal_inferrer, strategy=strat)
                    # Ensure place action from policy is also bounded
                    if action.action_type == "place":
                        action = ARC3Action(action_type="place", 
                                          x=max(0, min(action.x, env.actual_w - 1)),
                                          y=max(0, min(action.y, env.actual_h - 1)))
            
            # Step 3: Failure buffering and strategic reset
            # Strategic Reset on Boredom / Stagnation
            is_bored = len(curiosity_history) == 10 and sum(curiosity_history) < 0.10 # Increased threshold
            if is_bored or (step_idx > 50 and reward == 0 and random.random() < 0.15):
                # Force a scanner-led exploration burst
                if random.random() < 0.8:
                    # [M] More diverse exploration burst
                    for _ in range(15):
                        p = random.random()
                        if p < 0.6: # 60% place
                            if random.random() < 0.3:
                                reset_action = ARC3Action(action_type="place", x=random.randint(0, env.actual_w-1), y=random.randint(0, env.actual_h-1))
                            else:
                                reset_action = env._scanner.next_click()
                        elif p < 0.9: # 30% move
                            reset_action = ARC3Action(action_type=random.choice(["move_up", "move_down", "move_left", "move_right"]))
                        else: # 10% rotate/select
                            reset_action = ARC3Action(action_type="rotate", param=random.randint(0, 15))
                            
                        prev_obs_for_update = obs
                        obs, extrinsic, intrinsic = env.step(reset_action)
                        reward = extrinsic + intrinsic
                        self.world_model.update(prev_obs_for_update, reset_action, obs, reward)
                        self.goal_inferrer.observe(obs, prev_obs_for_update, reward)
                        episode.record(obs, reset_action, reward, extrinsic=extrinsic, intrinsic=intrinsic)
                        if extrinsic > 0: break
                
                if sum(h[2] for h in episode.history[-10:]) == 0:
                    self.goal_inferrer.reject_current_hypothesis()
                # Mutation and coverage reset
                self.policy.mutate()
                env._scanner.refine(obs.grid)
                if is_bored: 
                    env._scanner.reset_coverage()
                    failure_buffer.clear()
                
                strat = self.policy.active_strategy
                curiosity_history.clear()
            
            prev_obs_in_loop = obs
            obs, extrinsic, intrinsic = env.step(action)
            action_history[action.action_type] += 1
            reward = extrinsic + intrinsic
            strat_reward += reward
            curiosity_history.append(intrinsic)
            
            # Step 3: Failure buffering logic
            if action.action_type == "place" and intrinsic < 0.01:
                failure_buffer.add((action.x, action.y))
            
            # [M] Step 1: Counterfactual Goal Analysis (every 50 steps)
            if step_idx % 50 == 0:
                self.goal_inferrer.counterfactual_analysis(episode.history)
            
            self.world_model.update(prev_obs_in_loop, action, obs, reward)
            self.goal_inferrer.observe(obs, prev_obs_in_loop, reward)
            episode.record(obs, action, reward, extrinsic=extrinsic, intrinsic=intrinsic)
            
        self.policy.record_episode(strat, strat_reward)
        self.policy.mutate()
        self.episode_logs.append({"episode":self._episode_count, "strategy":strat, "total_reward":sum(h[2] for h in episode.history)})
        
        # [M] Post-Episode Experience Replay (Focus on extrinsic rewards)
        if len(episode.history) > 1:
            for _ in range(3): # 3 passes
                # Sample 16 transitions or all if less
                batch_size = min(16, len(episode.history) - 1)
                indices = list(range(len(episode.history) - 1))
                # Oversample reward transitions
                reward_indices = [i for i in indices if episode.history[i+1][2] > 0]
                if reward_indices:
                    indices.extend(reward_indices * 5)
                
                batch = random.sample(indices, batch_size)
                for i in batch:
                    obs, act, rew = episode.history[i]
                    next_obs, _, _ = episode.history[i+1]
                    
                    from prometheus.wp71_arc_agi3 import _ACTION_TYPES
                    try: atype_idx = _ACTION_TYPES.index(act.action_type)
                    except: atype_idx = 7
                    
                    # We need a frame stack for the transformer. 
                    # For simplicity, we'll repeat the grid or use history if available.
                    # Since we don't store stacks in history, we'll repeat the grid.
                    g1 = [list(obs.grid)] * 4
                    g2 = [list(next_obs.grid)] * 4
                    _vision_model.train_step(g1, g2, action_type_idx=atype_idx, extrinsic_reward=rew)

        return episode

def run_live_game(game_id="ls20", n_windows=40, window_steps=120, mutation_rate=0.10, fitness_threshold=0.5, verbose=True):
    if not TOOLKIT_AVAILABLE:
        print(f"Toolkit missing: Falling back to Synthetic ARC-AGI-3 [{game_id}]")
        synth_type = "navigate" if "ls" in game_id else "sort" if "ft" in game_id else "count"
        env = PrometheusARC3SyntheticEnv(_SyntheticARCGame(game_type=synth_type))
    else:
        print(f"Connecting to ARC-AGI-3 API [{game_id}]...")
        try:
            arc = arc_agi.Arcade(); env_w = arc.make(game_id, render_mode=None)
            if not env_w: return None
            env = PrometheusARC3LiveEnv(env_w, game_id)
        except:
            print(f"Failed to connect to ARC-AGI-3 API for {game_id}")
            return None

    agent = PatchedStrangeLoopAgent(window_steps=window_steps)
    episodes = []
    for win in range(n_windows):
        t0, ep = time.time(), agent.run_episode(env); episodes.append(ep)
        if verbose: print(f"  Win {win+1:>2}/{n_windows}: levels=+{ep.total_extrinsic:.0f} curiosity={ep.total_intrinsic:.1f} ({time.time()-t0:.1f}s)")
    return {
        "game_id":game_id, 
        "solve_rate":sum(1 for e in episodes if e.total_extrinsic > 0)/len(episodes), 
        "mean_score":sum(e.total_score for e in episodes)/len(episodes),
        "last_episode": episodes[-1] if episodes else None
    }
