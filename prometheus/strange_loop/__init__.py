"""
prometheus.strange_loop package

Re-exports the original strange_loop module's public API so that
``from prometheus.strange_loop import StrangeLoopDetector`` continues
to work after the module was replaced by this package directory.

Also exposes the new sub-modules added in WP-06 (manager, analogy, etc.)
"""

import importlib.util
import sys
import os

# ---------------------------------------------------------------------------
# Bootstrap: load the original prometheus/strange_loop.py under a private name
# so we can re-export its symbols without circular-import issues.
# ---------------------------------------------------------------------------
_here    = os.path.dirname(__file__)                   # .../prometheus/strange_loop/
_orig_py = os.path.join(_here, os.pardir, "strange_loop.py")   # .../prometheus/strange_loop.py
_orig_py = os.path.normpath(_orig_py)

if os.path.exists(_orig_py):
    _spec   = importlib.util.spec_from_file_location(
        "prometheus._strange_loop_legacy", _orig_py
    )
    _legacy = importlib.util.module_from_spec(_spec)
    sys.modules["prometheus._strange_loop_legacy"] = _legacy
    _spec.loader.exec_module(_legacy)

    # Public re-exports expected by geb_integration and other callers
    LoopType                    = _legacy.LoopType
    StrangeLoop                 = _legacy.StrangeLoop
    Isomorphism                 = _legacy.Isomorphism
    StrangeLoopDetector         = _legacy.StrangeLoopDetector
    create_prometheus_strange_loops = _legacy.create_prometheus_strange_loops

    # Optional symbols (may or may not be present in the legacy file)
    for _sym in ("IsomorphismDetector",):
        if hasattr(_legacy, _sym):
            globals()[_sym] = getattr(_legacy, _sym)

# ---------------------------------------------------------------------------
# New sub-modules (import lazily to avoid heavy dependency chains at package
# import time; callers can do ``from prometheus.strange_loop.manager import &``
# directly).
# ---------------------------------------------------------------------------
from prometheus.strange_loop.manager            import StrangeLoopManager               # noqa: F401
from prometheus.strange_loop.goedelian_safety   import GoedelianSafetyGovernor          # noqa: F401
from prometheus.strange_loop.analogy            import AnalogicalSearchEngine           # noqa: F401
from prometheus.strange_loop.self_symbol        import SelfSymbol                       # noqa: F401
from prometheus.strange_loop.critique_generator import SelfReferentialCritiqueGenerator # noqa: F401
from prometheus.strange_loop.trace_logger       import CognitiveTraceLogger             # noqa: F401
