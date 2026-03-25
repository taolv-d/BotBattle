import unittest

from services.game_review_service import GameReviewService, ReviewConfig


class GameReviewEventTests(unittest.TestCase):
    def setUp(self):
        self.service = GameReviewService(
            config=ReviewConfig(enabled=False, output_dir="reviews_test")
        )

    def test_format_log_entries_supports_current_event_names(self):
        entries = [
            {
                "timestamp": "2026-03-24T10:00:00",
                "event_type": "speech",
                "data": {"player_id": 1, "content": "test"},
            },
            {
                "timestamp": "2026-03-24T10:01:00",
                "event_type": "president_candidate_speech",
                "data": {"player_id": 2, "content": "run for president"},
            },
            {
                "timestamp": "2026-03-24T10:02:00",
                "event_type": "game_result",
                "data": {"winner": "good"},
            },
        ]

        formatted = self.service._format_log_entries(entries)
        self.assertIn("speech", formatted)
        self.assertIn("president_candidate_speech", formatted)
        self.assertIn("game_result", formatted)


if __name__ == "__main__":
    unittest.main()
