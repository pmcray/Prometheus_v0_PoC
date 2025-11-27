"""
Transfer Learning module for Prometheus

Enables knowledge transfer across:
- Board sizes (9x9 → 13x13 → 19x19)
- Domains (visual patterns → games)
- Games (chess ↔ Go)
- Model compression (teacher → student)
"""

from prometheus.transfer.transfer_learning import (
    BoardSizeTransfer,
    DomainTransfer,
    CrossGameTransfer,
    FineTuner,
    KnowledgeDistillation
)

__all__ = [
    'BoardSizeTransfer',
    'DomainTransfer',
    'CrossGameTransfer',
    'FineTuner',
    'KnowledgeDistillation'
]
