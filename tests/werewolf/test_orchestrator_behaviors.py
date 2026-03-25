import tempfile
import unittest

from games.werewolf.config import GameConfig
from games.werewolf.orchestrator import WerewolfOrchestrator
from services.logger_service import LoggerService


class OrchestratorBehaviorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        config = GameConfig(
            player_count=4,
            roles=[
                {"role": "werewolf", "count": 2},
                {"role": "villager", "count": 1},
                {"role": "seer", "count": 1},
            ],
            personalities=["A", "B", "C", "D"],
        )
        logger = LoggerService(log_dir=self.temp_dir.name)
        self.orchestrator = WerewolfOrchestrator(
            config=config,
            llm_config={"provider": "mock"},
            logger=logger,
        )

    def tearDown(self):
        self.orchestrator.logger.close()
        self.temp_dir.cleanup()

    async def test_wolf_night_uses_majority_target(self):
        wolf_ids = self.orchestrator.state.get_werewolves()
        self.orchestrator.state.night_number = 1

        async def choose_two(_context):
            return {"action": "attack", "target": 3}

        async def choose_three(_context):
            return {"action": "attack", "target": 4}

        self.orchestrator.agents[wolf_ids[0]].night_action = choose_two
        self.orchestrator.agents[wolf_ids[1]].night_action = choose_two

        result = await self.orchestrator._run_wolf_night()
        self.assertEqual(result["action"], "attack")
        self.assertEqual(result["target"], 3)

        self.orchestrator.agents[wolf_ids[1]].night_action = choose_three
        result = await self.orchestrator._run_wolf_night()
        self.assertEqual(result["action"], "attack")
        self.assertEqual(result["target"], 3)

    async def test_self_explode_uses_agent_decision(self):
        wolf_id = self.orchestrator.state.get_werewolves()[0]
        self.orchestrator.state.day_number = 2

        async def explode(_context):
            return True

        self.orchestrator.agents[wolf_id].decide_self_explode = explode
        decision = await self.orchestrator._check_self_explode(wolf_id)
        self.assertTrue(decision)


if __name__ == "__main__":
    unittest.main()
