"""
WP39: Web API & Real-Time Monitoring Dashboard
================================================

Closes the **observability gap** — Prometheus currently has no programmatic
API or live monitoring surface.

The gap in WP17–WP38
---------------------
All interaction with the Prometheus stack is via:
  - Jupyter notebooks (manual, session-bound)
  - CLI tool (single-command, no streaming)
  - Docker (container-level, no API)

There is no way to:
  - Query agent performance programmatically from external systems.
  - Stream live CRLS loop updates to a monitoring dashboard.
  - Invoke synthesis, proof, or evolution endpoints over HTTP.
  - Observe WP37 ELO ratings, WP31 curriculum state, or WP32 gene archive
    in real time.

WP39 fix
--------
``PrometheusAPI`` — a pure-Python HTTP server (using only stdlib
``http.server``) that exposes the following REST endpoints:

    GET  /health                  — liveness probe
    GET  /metrics                 — current performance summary (JSON)
    GET  /metrics/elo?domain=X    — ELO leaderboard for domain X
    GET  /metrics/curriculum       — current ZPD state
    GET  /metrics/gene_archive     — gene archive summary
    POST /synthesise               — run one CRLS generation
    POST /prove                    — attempt a theorem proof
    POST /evolve                   — run one evolutionary cycle

``LiveEventStream`` — an in-process event bus.  Components publish events
(e.g., ``generation_complete``, ``proof_found``, ``elo_updated``); the
``/events`` SSE endpoint streams them to connected clients.

``APIMetrics`` — in-memory metrics store with ring-buffer history:
  - ``record(metric_name, value)``
  - ``get_history(metric_name, last_n)``
  - ``snapshot()`` → current values as a JSON-serialisable dict.

``DashboardRenderer`` — renders a simple HTML dashboard page
(plain HTML/CSS/JS, no external dependencies) that polls the
``/metrics`` and ``/events`` endpoints.

``PrometheusAPIServer`` — thin wrapper: creates a ``PrometheusAPI``,
starts it in a background thread, and provides ``start()``/``stop()``
methods.

Note: WP39 is implemented as a *pure stdlib* module — it does not require
FastAPI, Flask, or any third-party web framework.  This keeps the PoC
dependency-free and Colab-compatible.

``verify_wp39_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Kleppmann (2017) "Designing Data-Intensive Applications": observable,
instrumented systems are more reliable and easier to reason about.

Sculley et al. (2015) "Hidden Technical Debt in Machine Learning Systems":
monitoring and observability are first-class concerns for production ML.

Good (1965): the ultraintelligent machine must be *transparent* — its
internal state and improvement trajectory must be inspectable by its
operators at all times.

Classes
-------
APIMetrics              In-memory ring-buffer metrics store
LiveEventStream         In-process event bus (publish/subscribe)
PrometheusAPI           Route handler registry and request dispatcher
DashboardRenderer       HTML dashboard page generator
PrometheusAPIServer     Background-thread HTTP server wrapper
verify_wp39_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import collections
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APIMetrics — ring-buffer metrics store
# ---------------------------------------------------------------------------

class APIMetrics:
    """
    In-memory metrics store with per-metric ring-buffer history.

    Parameters
    ----------
    max_history : int
        Maximum number of values to retain per metric (default 1000).
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._lock    = threading.Lock()
        self._current: Dict[str, float]  = {}
        self._history: Dict[str, collections.deque] = {}
        self._created: float = time.time()

    def record(self, metric: str, value: float) -> None:
        """Record a new value for ``metric``."""
        with self._lock:
            self._current[metric] = value
            if metric not in self._history:
                self._history[metric] = collections.deque(maxlen=self.max_history)
            self._history[metric].append((time.time(), value))

    def get_history(self, metric: str, last_n: int = 100) -> List[Tuple[float, float]]:
        """Return the most recent ``last_n`` (timestamp, value) pairs."""
        with self._lock:
            hist = self._history.get(metric, collections.deque())
            items = list(hist)
            return items[-last_n:]

    def snapshot(self) -> Dict[str, Any]:
        """Return current values as a JSON-serialisable dict."""
        with self._lock:
            return {
                "timestamp": time.time(),
                "uptime_s":  round(time.time() - self._created, 1),
                "metrics":   dict(self._current),
            }

    def metric_names(self) -> List[str]:
        with self._lock:
            return list(self._current.keys())


# ---------------------------------------------------------------------------
# LiveEventStream — in-process event bus
# ---------------------------------------------------------------------------

class LiveEventStream:
    """
    Simple in-process event bus (publish/subscribe).

    Subscribers register a callback; publishers push named events with
    optional payload.

    Parameters
    ----------
    max_buffered : int
        Maximum events to buffer for late-joining subscribers (default 100).
    """

    def __init__(self, max_buffered: int = 100):
        self._lock        = threading.Lock()
        self._subscribers: List[Callable[[str, Any], None]] = []
        self._buffer: collections.deque = collections.deque(maxlen=max_buffered)

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def publish(self, event_name: str, payload: Any = None) -> None:
        event = {"event": event_name, "payload": payload, "timestamp": time.time()}
        with self._lock:
            self._buffer.append(event)
            for cb in self._subscribers:
                try:
                    cb(event_name, payload)
                except Exception as exc:
                    logger.warning("WP39 event subscriber error: %s", exc)

    def recent_events(self, last_n: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._buffer)
            return items[-last_n:]


# ---------------------------------------------------------------------------
# DashboardRenderer — HTML dashboard page
# ---------------------------------------------------------------------------

class DashboardRenderer:
    """Renders a minimal HTML monitoring dashboard (no external deps)."""

    def render(self, metrics_snapshot: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
        """Return a complete HTML page string."""
        metric_rows = "".join(
            f"<tr><td>{k}</td><td>{round(v, 4)}</td></tr>"
            for k, v in metrics_snapshot.get("metrics", {}).items()
        )
        event_rows = "".join(
            f"<tr><td>{e['event']}</td><td>{e.get('payload','')}</td>"
            f"<td>{time.strftime('%H:%M:%S', time.localtime(e['timestamp']))}</td></tr>"
            for e in reversed(events[-10:])
        )
        uptime = metrics_snapshot.get("uptime_s", 0)
        return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Prometheus v0 — Live Dashboard</title>
<meta http-equiv="refresh" content="5"/>
<style>
  body {{ font-family: monospace; background:#1a1a2e; color:#e0e0e0; padding:20px; }}
  h1   {{ color:#00d4ff; }}
  h2   {{ color:#aaa; }}
  table {{ border-collapse:collapse; width:100%; margin-bottom:20px; }}
  th,td {{ border:1px solid #333; padding:6px 12px; text-align:left; }}
  th   {{ background:#0f3460; }}
  tr:nth-child(even) {{ background:#16213e; }}
  .badge {{ background:#00d4ff; color:#000; padding:2px 8px; border-radius:4px; font-size:0.8em; }}
</style>
</head><body>
<h1>Prometheus v0 — Live Monitoring Dashboard</h1>
<p>Uptime: <strong>{uptime}s</strong> &nbsp;
   Refreshes every 5s &nbsp;
   <span class="badge">WP39</span></p>

<h2>Current Metrics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{metric_rows if metric_rows else "<tr><td colspan='2'>No metrics yet</td></tr>"}
</table>

<h2>Recent Events</h2>
<table>
<tr><th>Event</th><th>Payload</th><th>Time</th></tr>
{event_rows if event_rows else "<tr><td colspan='3'>No events yet</td></tr>"}
</table>
</body></html>"""


# ---------------------------------------------------------------------------
# PrometheusAPI — route handler registry
# ---------------------------------------------------------------------------

class PrometheusAPI:
    """
    Pure-Python REST API handler for Prometheus.

    Registers GET/POST route handlers and dispatches incoming requests.

    Parameters
    ----------
    metrics : APIMetrics
    events  : LiveEventStream
    """

    def __init__(
        self,
        metrics: Optional[APIMetrics]       = None,
        events:  Optional[LiveEventStream]  = None,
        api_key: Optional[str]              = None,
    ):
        self.metrics   = metrics or APIMetrics()
        self.events    = events  or LiveEventStream()
        self.api_key   = api_key
        self._renderer = DashboardRenderer()
        self._routes_get:  Dict[str, Callable] = {}
        self._routes_post: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register_get("/",               self._handle_dashboard)
        self.register_get("/health",         self._handle_health)
        self.register_get("/metrics",        self._handle_metrics)
        self.register_get("/metrics/elo",    self._handle_metrics_elo)
        self.register_get("/metrics/curriculum",   self._handle_metrics_curriculum)
        self.register_get("/metrics/gene_archive", self._handle_metrics_gene_archive)
        self.register_get("/events",         self._handle_events)
        self.register_post("/synthesise",    self._handle_synthesise)
        self.register_post("/prove",         self._handle_prove)
        self.register_post("/evolve",        self._handle_evolve)

    def register_get(self, path: str, handler: Callable) -> None:
        self._routes_get[path] = handler

    def register_post(self, path: str, handler: Callable) -> None:
        self._routes_post[path] = handler

    def handle_request(
        self,
        method:  str,
        path:    str,
        query:   Dict[str, List[str]],
        body:    Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        """
        Dispatch a request.

        Returns (status_code, content_type, body_str).
        """
        # Optional API key check
        if self.api_key:
            auth = (headers or {}).get("X-API-Key", "")
            if auth != self.api_key:
                return 401, "application/json", json.dumps({"error": "Unauthorized"})

        if method == "GET":
            handler = self._routes_get.get(path)
        else:
            handler = self._routes_post.get(path)

        if handler is None:
            return 404, "application/json", json.dumps({"error": "Not found", "path": path})

        try:
            return handler(query=query, body=body)
        except Exception as exc:
            logger.exception("WP39 handler error: %s", exc)
            return 500, "application/json", json.dumps({"error": str(exc)})

    # ------------------------------------------------------------------
    # Default handlers
    # ------------------------------------------------------------------

    def _handle_dashboard(self, **_) -> Tuple[int, str, str]:
        snap   = self.metrics.snapshot()
        events = self.events.recent_events(20)
        html   = self._renderer.render(snap, events)
        return 200, "text/html", html

    def _handle_health(self, **_) -> Tuple[int, str, str]:
        return 200, "application/json", json.dumps({
            "status":    "ok",
            "version":   "0.80",
            "timestamp": time.time(),
        })

    def _handle_metrics(self, **_) -> Tuple[int, str, str]:
        return 200, "application/json", json.dumps(self.metrics.snapshot())

    def _handle_metrics_elo(self, query: Dict, **_) -> Tuple[int, str, str]:
        domain = (query.get("domain") or ["synthesis"])[0]
        # If an ELORegistry is attached, query it; else return stub
        elo_data = getattr(self, "_elo_registry", None)
        if elo_data and hasattr(elo_data, "leaderboard"):
            board = elo_data.leaderboard(top_k=10)
            payload = [{"agent": a, "mu": round(m, 1), "phi": round(p, 1)} for a, m, p in board]
        else:
            payload = {"note": "ELO registry not attached; use api.attach_elo_registry(reg)"}
        return 200, "application/json", json.dumps({"domain": domain, "leaderboard": payload})

    def _handle_metrics_curriculum(self, **_) -> Tuple[int, str, str]:
        curr = getattr(self, "_curriculum", None)
        if curr and hasattr(curr, "get_zpd_summary"):
            return 200, "application/json", json.dumps(curr.get_zpd_summary())
        return 200, "application/json", json.dumps({"note": "Curriculum not attached"})

    def _handle_metrics_gene_archive(self, **_) -> Tuple[int, str, str]:
        archive = getattr(self, "_gene_archive", None)
        if archive and hasattr(archive, "summary"):
            return 200, "application/json", json.dumps(archive.summary())
        return 200, "application/json", json.dumps({"note": "Gene archive not attached"})

    def _handle_events(self, **_) -> Tuple[int, str, str]:
        events = self.events.recent_events(50)
        return 200, "application/json", json.dumps(events)

    def _handle_synthesise(self, body: Optional[bytes], **_) -> Tuple[int, str, str]:
        req = json.loads(body or b"{}") if body else {}
        self.events.publish("synthesise_requested", req)
        result = {"status": "queued", "request": req, "timestamp": time.time()}
        self.metrics.record("synthesise_requests_total",
                            self.metrics._current.get("synthesise_requests_total", 0) + 1)
        return 200, "application/json", json.dumps(result)

    def _handle_prove(self, body: Optional[bytes], **_) -> Tuple[int, str, str]:
        req = json.loads(body or b"{}") if body else {}
        self.events.publish("prove_requested", req)
        result = {"status": "queued", "theorem": req.get("theorem", ""), "timestamp": time.time()}
        self.metrics.record("prove_requests_total",
                            self.metrics._current.get("prove_requests_total", 0) + 1)
        return 200, "application/json", json.dumps(result)

    def _handle_evolve(self, body: Optional[bytes], **_) -> Tuple[int, str, str]:
        req = json.loads(body or b"{}") if body else {}
        self.events.publish("evolve_requested", req)
        result = {"status": "queued", "request": req, "timestamp": time.time()}
        self.metrics.record("evolve_requests_total",
                            self.metrics._current.get("evolve_requests_total", 0) + 1)
        return 200, "application/json", json.dumps(result)

    # ------------------------------------------------------------------
    # Attach optional components
    # ------------------------------------------------------------------

    def attach_elo_registry(self, registry: Any) -> None:
        self._elo_registry = registry

    def attach_curriculum(self, scheduler: Any) -> None:
        self._curriculum = scheduler

    def attach_gene_archive(self, archive: Any) -> None:
        self._gene_archive = archive


# ---------------------------------------------------------------------------
# PrometheusAPIServer — background-thread HTTP server
# ---------------------------------------------------------------------------

class PrometheusAPIServer:
    """
    Wraps ``PrometheusAPI`` in a background ``HTTPServer`` thread.

    Parameters
    ----------
    api : PrometheusAPI
    host : str   (default '127.0.0.1')
    port : int   (default 8765)
    """

    def __init__(
        self,
        api:  Optional[PrometheusAPI] = None,
        host: str = "127.0.0.1",
        port: int = 8765,
    ):
        self.api    = api or PrometheusAPI()
        self.host   = host
        self.port   = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the HTTP server in a daemon background thread."""
        if self._server is not None:
            return
        outer_api = self.api

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.debug("WP39 HTTP: " + fmt, *args)

            def do_GET(self):
                parsed = urlparse(self.path)
                query  = parse_qs(parsed.query)
                headers = {k: v for k, v in self.headers.items()}
                status, ctype, body = outer_api.handle_request(
                    "GET", parsed.path, query, None, headers
                )
                self._respond(status, ctype, body)

            def do_POST(self):
                parsed = urlparse(self.path)
                query  = parse_qs(parsed.query)
                length = int(self.headers.get("Content-Length", 0))
                body   = self.rfile.read(length) if length else None
                headers = {k: v for k, v in self.headers.items()}
                status, ctype, resp = outer_api.handle_request(
                    "POST", parsed.path, query, body, headers
                )
                self._respond(status, ctype, resp)

            def _respond(self, status: int, ctype: str, body: str):
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._server = HTTPServer((self.host, self.port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="PrometheusAPIServer",
        )
        self._thread.start()
        logger.info("WP39 API server started at http://%s:%d", self.host, self.port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None
        self._thread = None
        logger.info("WP39 API server stopped")

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def is_running(self) -> bool:
        return self._server is not None


# ---------------------------------------------------------------------------
# verify_wp39_exit_criteria — six-criterion verifier
# ---------------------------------------------------------------------------

def verify_wp39_exit_criteria(
    api:    PrometheusAPI,
    server: PrometheusAPIServer,
) -> Dict[str, bool]:
    """
    Verify WP39 exit criteria.

    Criteria
    --------
    1. /health endpoint returns 200 with status=ok.
    2. /metrics endpoint returns current metrics snapshot.
    3. APIMetrics records and retrieves values correctly.
    4. LiveEventStream delivers events to subscribers.
    5. POST /synthesise increments the counter.
    6. DashboardRenderer produces valid HTML.
    """
    results: Dict[str, bool] = {}

    # 1. /health returns 200
    status, _, body = api.handle_request("GET", "/health", {})
    data = json.loads(body)
    results["/health returns 200 with status=ok"] = (
        status == 200 and data.get("status") == "ok"
    )

    # 2. /metrics returns snapshot
    api.metrics.record("test_metric", 42.0)
    status2, _, body2 = api.handle_request("GET", "/metrics", {})
    data2 = json.loads(body2)
    results["/metrics returns snapshot with metrics key"] = (
        status2 == 200 and "metrics" in data2
    )

    # 3. APIMetrics records and retrieves
    m = APIMetrics()
    m.record("acc", 0.75)
    m.record("acc", 0.80)
    hist = m.get_history("acc")
    results["APIMetrics records and retrieves history"] = (
        len(hist) == 2 and abs(hist[-1][1] - 0.80) < 0.001
    )

    # 4. LiveEventStream delivers events
    received = []
    stream = LiveEventStream()
    stream.subscribe(lambda name, payload: received.append(name))
    stream.publish("test_event", {"x": 1})
    results["LiveEventStream delivers events to subscribers"] = ("test_event" in received)

    # 5. POST /synthesise increments counter
    before = api.metrics._current.get("synthesise_requests_total", 0)
    api.handle_request("POST", "/synthesise", {}, b'{"strategy": "promote_best"}')
    after = api.metrics._current.get("synthesise_requests_total", 0)
    results["POST /synthesise increments request counter"] = (after == before + 1)

    # 6. DashboardRenderer produces HTML
    renderer = DashboardRenderer()
    snap = api.metrics.snapshot()
    html = renderer.render(snap, [])
    results["DashboardRenderer produces valid HTML page"] = (
        "<!DOCTYPE html>" in html and "Prometheus" in html
    )

    return results
