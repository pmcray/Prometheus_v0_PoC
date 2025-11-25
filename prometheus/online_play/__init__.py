"""
Prometheus Online Play

This module enables Prometheus to play games online against human and computer opponents:
- Lichess API integration for chess
- OGS (Online Go Server) API integration for Go
- Unified interface for bot management
- Challenge handling and game state synchronization
"""

from prometheus.online_play.lichess import LichessBot
from prometheus.online_play.ogs import OGSBot
from prometheus.online_play.manager import OnlinePlayManager

__all__ = [
    'LichessBot',
    'OGSBot',
    'OnlinePlayManager'
]
