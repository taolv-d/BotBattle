import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from interfaces.web.app import WerewolfWebApplication
from runtime.werewolf.controller import WerewolfRuntimeController
from runtime.werewolf.event_store import WerewolfEventStore
from runtime.werewolf.errors import RuntimeApiError


class WerewolfUiRuntimeTests(unittest.TestCase):
    def _create_temp_config_dir(self) -> str:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config_dir = Path(temp_dir.name)
        (config_dir / "system.json").write_text(json.dumps({
            "llm": {
                "provider": "mock",
                "api_key": "test-key",
                "model": "mock-model"
            }
        }), encoding="utf-8")
        (config_dir / "werewolf_default.json").write_text(json.dumps({
            "player_count": 4,
            "roles": [
                {"role": "werewolf", "count": 1},
                {"role": "villager", "count": 1},
                {"role": "seer", "count": 1},
                {"role": "guard", "count": 1}
            ],
            "personalities": ["A", "B", "C", "D"],
            "game_rules": {
                "hunter_can_skill": True,
                "has_president_election": True
            }
        }), encoding="utf-8")
        (config_dir / "personalities.json").write_text(json.dumps({}), encoding="utf-8")
        return str(config_dir)

    def test_event_store_projects_public_events(self):
        store = WerewolfEventStore(max_events=10)
        raw_entries = [
            {
                "timestamp": "2026-03-25T21:00:00",
                "event_type": "phase_changed",
                "data": {"phase": "day_discussion"},
            },
            {
                "timestamp": "2026-03-25T21:00:01",
                "event_type": "speech",
                "data": {"player_id": 1, "content": "test"},
            },
        ]

        store.sync(raw_entries)
        events = store.get_events()

        self.assertEqual(2, len(events))
        self.assertEqual("phase_changed", events[0]["event_type"])
        self.assertEqual("speech", events[1]["event_type"])
        self.assertEqual(1, events[0]["sequence"])
        self.assertEqual(2, events[1]["sequence"])

    def test_controller_create_session_and_serialize_state(self):
        controller = WerewolfRuntimeController(config_dir=self._create_temp_config_dir(), max_events=50)
        controller.create_session({"mode": "observer", "review_enabled": False})
        summary = controller.get_session_summary()
        state = controller.get_state()

        self.assertEqual("created", summary["lifecycle_status"])
        self.assertEqual("observer", state["mode"])
        self.assertEqual("setup", state["phase"])
        self.assertEqual(4, len(state["players"]))
        self.assertEqual("disabled", state["review_status"]["status"])

    def test_controller_rejects_player_mode_for_current_release(self):
        controller = WerewolfRuntimeController(config_dir=self._create_temp_config_dir(), max_events=50)
        with self.assertRaises(RuntimeApiError) as context:
            controller.create_session({"mode": "player", "human_player_id": 1, "review_enabled": False})
        self.assertEqual("MODE_NOT_IMPLEMENTED", context.exception.info.code)
        self.assertEqual(501, context.exception.info.status_code)

    def test_controller_validates_player_view(self):
        controller = WerewolfRuntimeController(config_dir=self._create_temp_config_dir(), max_events=50)
        controller.create_session({"mode": "observer", "review_enabled": False})

        with self.assertRaises(RuntimeApiError) as missing_viewer:
            controller.get_state(view_type="player")
        self.assertEqual("VIEWER_REQUIRED", missing_viewer.exception.info.code)

        with self.assertRaises(RuntimeApiError) as unknown_viewer:
            controller.get_state(view_type="player", viewer_player_id=99)
        self.assertEqual("VIEWER_NOT_FOUND", unknown_viewer.exception.info.code)

        player_state = controller.get_state(view_type="player", viewer_player_id=1)
        self.assertIsNotNone(player_state["players"][0]["role"])
        self.assertTrue(all(player["role"] is None for player in player_state["players"][1:]))

    def test_web_application_routes(self):
        controller = WerewolfRuntimeController(config_dir=self._create_temp_config_dir(), max_events=50)
        app = WerewolfWebApplication(controller=controller)
        server = app.create_server("127.0.0.1", 0)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 1)

        def request(path: str, method: str = "GET", payload=None):
            data = None
            headers = {}
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return response.status, json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

        status, payload = request("/api/session")
        self.assertEqual(404, status)
        self.assertEqual("SESSION_NOT_FOUND", payload["error"]["code"])

        status, payload = request("/api/session", method="POST", payload={"mode": "observer", "review_enabled": False})
        self.assertEqual(201, status)
        self.assertTrue(payload["ok"])

        status, payload = request("/api/state?view_type=player")
        self.assertEqual(400, status)
        self.assertEqual("VIEWER_REQUIRED", payload["error"]["code"])

        status, payload = request("/api/session", method="POST", payload={"mode": "player", "human_player_id": 1})
        self.assertEqual(400, status)
        self.assertEqual("SESSION_ALREADY_EXISTS", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
