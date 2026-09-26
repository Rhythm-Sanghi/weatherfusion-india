"""Small local-only annotation server for WeatherFusion JSONL labels.

It intentionally saves REVIEWED records, never APPROVED records. Approval is a
separate accountable review step using ``validate_dataset.py``.
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TAXONOMY = ["HEAVY_RAINFALL", "FLOOD", "THUNDERSTORM", "HEATWAVE", "FOG", "DUST_STORM", "STRONG_WIND"]


def load_queue(path: Path) -> list[dict[str, object]]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def create_handler(queue_path: Path, output_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: object, content_type: str = "application/json") -> None:
            encoded = json.dumps(body).encode() if content_type == "application/json" else str(body).encode()
            self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
        def do_GET(self) -> None:
            if self.path == "/api/queue": self._send(HTTPStatus.OK, load_queue(queue_path)); return
            self._send(HTTPStatus.OK, PAGE, "text/html; charset=utf-8")
        def do_POST(self) -> None:
            if self.path != "/api/annotations": self._send(HTTPStatus.NOT_FOUND, {"detail":"not found"}); return
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                required = ["record_id", "report_text", "language", "source_dataset", "source_record_id", "source_type", "weather_relevance_label", "annotator_id"]
                if not all(isinstance(payload.get(key), str) and payload[key].strip() for key in required): raise ValueError("missing required annotation fields")
                if payload["weather_relevance_label"] not in {"WEATHER_RELEVANT", "NOT_WEATHER_RELEVANT", "UNCERTAIN"}: raise ValueError("invalid relevance")
                if payload["weather_relevance_label"] != "WEATHER_RELEVANT": payload["primary_event_type_label"] = None
                if payload["weather_relevance_label"] == "WEATHER_RELEVANT" and payload.get("primary_event_type_label") not in TAXONOMY: raise ValueError("select a supported event type")
                payload.update({"annotation_status":"REVIEWED", "annotation_guideline_version":"v1", "synthetic_fixture":False})
                output_path.parent.mkdir(parents=True, exist_ok=True)
                existing = [row for row in load_queue(output_path) if row.get("record_id") != payload["record_id"]]
                existing.append(payload); output_path.write_text("".join(json.dumps(row, sort_keys=True)+"\n" for row in existing), encoding="utf-8")
                self._send(HTTPStatus.CREATED, {"status":"REVIEWED", "record_id":payload["record_id"]})
            except (ValueError, json.JSONDecodeError) as error: self._send(HTTPStatus.BAD_REQUEST, {"detail":str(error)})
    return Handler


PAGE = """<!doctype html><title>WeatherFusion annotation</title><main><h1>WeatherFusion annotation queue</h1><p>Local only. Saving creates REVIEWED, never APPROVED, labels.</p><pre id=q>Loading…</pre></main><script>fetch('/api/queue').then(r=>r.json()).then(x=>q.textContent=JSON.stringify(x,null,2))</script>"""

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--queue", type=Path, default=Path("ml/data/input/annotation_queue.jsonl")); parser.add_argument("--output", type=Path, default=Path("ml/data/annotations/reviewed.jsonl")); parser.add_argument("--port", type=int, default=8765); args=parser.parse_args()
    server=ThreadingHTTPServer(("127.0.0.1",args.port),create_handler(args.queue,args.output)); print(f"http://127.0.0.1:{args.port}"); server.serve_forever()
