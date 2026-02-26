"""
Strategic Knowledge Base — Prometheus v0.98 (WP-02)

Provides pre-computed strategic knowledge to agents:
- Opening Books (Chess & Go)
- Interesting Position Database (for failure analysis)
- Domain-specific heuristics and rules (e.g., 3-fold repetition)
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

class StrategicKnowledgeBase:
    """
    Manages opening moves, Joseki, and critical positions.
    """
    def __init__(self, storage_dir: str = "strategic_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # In-memory caches
        self.opening_books = {
            "chess": self._load_chess_openings(),
            "go": self._load_go_joseki()
        }
        
        # Position DB (Interesting/Failed positions)
        self.position_db_path = self.storage_dir / "position_db.json"
        self.position_db = self._load_position_db()

    def _load_chess_openings(self) -> Dict[str, str]:
        """
        Loads a seed chess opening book. 
        Format: {FEN_hash: recommended_move_uci}
        """
        # Seed book with common moves (Starting position, etc.)
        # In a real system, this would load from a large BIN/JSON file.
        return {
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1": "e2e4",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1": "e7e5",
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2": "g1f3",
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3": "f1b5"  # Ruy Lopez
        }

    def _load_go_joseki(self) -> Dict[str, List[Tuple[int, int]]]:
        """Loads Go joseki patterns."""
        # Simple placeholder for 19x19 standard openings
        return {
            # (4,4) star point opening for Black
            "": [(3, 3), (15, 3), (3, 15), (15, 15)]
        }

    def _load_position_db(self) -> Dict[str, Any]:
        """Loads the failure/interesting position database."""
        if self.position_db_path.exists():
            try:
                with open(self.position_db_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_opening_move(self, domain: str, state_repr: str) -> Optional[str]:
        """
        Retrieves a recommended opening move from the book.
        
        Args:
            domain: "chess" or "go"
            state_repr: FEN for chess, or a board string for Go
        """
        book = self.opening_books.get(domain, {})
        return book.get(state_repr)

    def record_interesting_position(self, domain: str, state_repr: str, metadata: Dict):
        """
        Records a position that led to a failure or was strategically significant.
        """
        pos_id = hashlib.md5(state_repr.encode()).hexdigest()
        self.position_db[pos_id] = {
            "domain": domain,
            "state": state_repr,
            "metadata": metadata
        }
        self._save_position_db()

    def _save_position_db(self):
        """Saves the position database to disk."""
        with open(self.position_db_path, "w") as f:
            json.dump(self.position_db, f, indent=2)

    def _load_go_joseki(self) -> Dict[str, Any]:
        # Implementation for Go joseki lookup
        return {}

class ChessRulesManager:
    """
    Handles advanced chess rules like 3-fold repetition.
    """
    @staticmethod
    def check_repetition(board, move_history: List[str]) -> bool:
        """
        Checks if the current position has occurred 3 times.
        Note: board.is_repetition(3) is built into python-chess.
        """
        return board.is_repetition(3)

    @staticmethod
    def check_50_move_rule(board) -> bool:
        """Checks the 50-move rule."""
        return board.halfmove_clock >= 100 # 50 full moves = 100 half-moves
