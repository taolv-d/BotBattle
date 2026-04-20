import json
import mimetypes
import urllib.parse
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.werewolf.controller import WerewolfRuntimeController
from runtime.werewolf.errors import RuntimeApiError, error_response, success_response


class WerewolfWebApplication:
    def __init__(self, controller: Optional[WerewolfRuntimeController] = None, static_dir: Optional[str] = None):
        self.controller = controller or WerewolfRuntimeController()
        self.static_dir = Path(static_dir or Path(__file__).parent / "static")

    def create_server(self, host: str, port: int) -> ThreadingHTTPServer:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                app.handle_request(self)

            def do_POST(self):
                app.handle_request(self)

            def log_message(self, _format: str, *_args):
                return

        return ThreadingHTTPServer((host, port), Handler)

    def handle_request(self, handler: BaseHTTPRequestHandler) -> None:
        request_id = f"req_srv_{uuid.uuid4().hex[:8]}"
        parsed = urllib.parse.urlparse(handler.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/" and handler.command == "GET":
                return self._serve_static(handler, "index.html")
            if path.startswith("/static/") and handler.command == "GET":
                return self._serve_static(handler, path.removeprefix("/static/"))

            if path == "/api/session" and handler.command == "GET":
                return self._send_json(handler, success_response(self.controller.get_session_summary(), meta=self._meta(request_id)))
            if path == "/api/session" and handler.command == "POST":
                payload = self._read_json(handler)
                session = self.controller.create_session(payload)
                return self._send_json(
                    handler,
                    success_response(
                        {
                            "session_id": session.session_id,
                            "game_id": session.game_id,
                            "mode": session.mode,
                            "human_player_id": session.human_player_id,
                            "lifecycle_status": session.lifecycle_status,
                        },
                        meta=self._meta(request_id),
                    ),
                    status=HTTPStatus.CREATED,
                )
            if path == "/api/session/start" and handler.command == "POST":
                session = self.controller.start_session()
                return self._send_json(
                    handler,
                    success_response(
                        {
                            "session_id": session.session_id,
                            "game_id": session.game_id,
                            "lifecycle_status": session.lifecycle_status,
                        },
                        meta=self._meta(request_id),
                    ),
                )
            if path == "/api/session/join" and handler.command == "POST":
                payload = self._read_json(handler)
                data = self.controller.join_session(payload)
                return self._send_json(handler, success_response(data, meta=self._meta(request_id)))
            if path == "/api/state" and handler.command == "GET":
                view_type = query.get("view_type", ["god"])[0]
                viewer_player_id = query.get("viewer_player_id", [None])[0]
                viewer_player_id = int(viewer_player_id) if viewer_player_id else None
                data = self.controller.get_state(view_type=view_type, viewer_player_id=viewer_player_id)
                return self._send_json(handler, success_response(data, meta=self._meta(request_id)))
            if path == "/api/events" and handler.command == "GET":
                last_sequence = int(query.get("last_sequence", ["0"])[0])
                limit = int(query.get("limit", ["200"])[0])
                view_type = query.get("view_type", ["god"])[0]
                viewer_player_id = query.get("viewer_player_id", [None])[0]
                viewer_player_id = int(viewer_player_id) if viewer_player_id else None
                data = self.controller.get_events(
                    last_sequence=last_sequence,
                    limit=limit,
                    view_type=view_type,
                    viewer_player_id=viewer_player_id,
                )
                return self._send_json(handler, success_response(data, meta=self._meta(request_id)))
            if path == "/api/review" and handler.command == "GET":
                data = self.controller.get_review_status()
                return self._send_json(handler, success_response(data, meta=self._meta(request_id)))
            if path == "/api/input" and handler.command == "POST":
                payload = self._read_json(handler)
                data = self.controller.submit_input(payload)
                return self._send_json(handler, success_response(data, meta=self._meta(request_id)))

            raise RuntimeApiError("ROUTE_NOT_FOUND", f"Route not found: {path}", "validation", status_code=404)
        except RuntimeApiError as exc:
            self._send_json(handler, error_response(exc.info, meta=self._meta(request_id)), status=HTTPStatus(exc.info.status_code))
        except Exception as exc:
            error = RuntimeApiError(
                "INTERNAL_ERROR",
                str(exc),
                "internal",
                retryable=True,
                status_code=500,
            ).info
            self._send_json(handler, error_response(error, meta=self._meta(request_id)), status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, handler: BaseHTTPRequestHandler, relative_path: str) -> None:
        target = self.static_dir / relative_path
        if not target.exists() or not target.is_file():
            raise RuntimeApiError("ROUTE_NOT_FOUND", f"Static asset not found: {relative_path}", "validation", status_code=404)

        mime_type, _ = mimetypes.guess_type(str(target))
        mime_type = mime_type or "application/octet-stream"
        content = target.read_bytes()
        handler.send_response(HTTPStatus.OK)
        content_type = mime_type
        if mime_type.startswith("text/") or mime_type == "application/javascript":
            content_type = f"{mime_type}; charset=utf-8"
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(content)))
        handler.end_headers()
        handler.wfile.write(content)

    def _send_json(self, handler: BaseHTTPRequestHandler, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(raw)))
        handler.end_headers()
        handler.wfile.write(raw)

    def _read_json(self, handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
        length = int(handler.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = handler.rfile.read(length).decode("utf-8")
        if not body:
            return {}
        return json.loads(body)

    def _meta(self, request_id: str) -> Dict[str, Any]:
        return {"request_id": request_id, "timestamp": datetime.now().isoformat()}


def run_server(host: str = "127.0.0.1", port: int = 8765, config_dir: str = "config") -> None:
    app = WerewolfWebApplication(controller=WerewolfRuntimeController(config_dir=config_dir))
    server = app.create_server(host, port)
    print(f"Werewolf UI server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()