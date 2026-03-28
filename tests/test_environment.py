import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.environment import SupportTriageEnv
from src.models import Action, Priority, Department


@pytest.fixture
def env():
    return SupportTriageEnv()


@pytest.fixture
def sample_action():
    return Action(
        priority=Priority.P1,
        department=Department.billing,
        response="Thank you for reaching out. We are processing your request.",
        escalate=False,
    )


class TestReset:
    def test_reset_easy(self, env):
        obs = env.reset("easy")
        assert obs.ticket_id.startswith("EASY-")
        assert len(obs.ticket_text) > 0

    def test_reset_medium(self, env):
        obs = env.reset("medium")
        assert obs.ticket_id.startswith("MED-")

    def test_reset_hard(self, env):
        obs = env.reset("hard")
        assert obs.ticket_id.startswith("HARD-")

    def test_reset_invalid_task(self, env):
        with pytest.raises(FileNotFoundError):
            env.reset("nonexistent")

    def test_reset_clears_score(self, env, sample_action):
        env.reset("easy")
        env.step(sample_action)
        assert env.state().cumulative_score > 0

        env.reset("easy")
        assert env.state().cumulative_score == 0.0

    def test_reset_mid_episode(self, env, sample_action):
        env.reset("easy")
        env.step(sample_action)
        obs = env.reset("medium")
        assert obs.ticket_id.startswith("MED-")
        assert env.state().cumulative_score == 0.0


class TestStep:
    def test_step_returns_tuple(self, env, sample_action):
        env.reset("easy")
        result = env.step(sample_action)
        assert len(result) == 4
        next_obs, reward, done, info = result
        assert reward.score >= 0.0
        assert reward.score <= 1.0
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    def test_step_before_reset(self, env, sample_action):
        with pytest.raises(RuntimeError, match="not been reset"):
            env.step(sample_action)

    def test_step_after_done(self, env, sample_action):
        env.reset("easy")
        done = False
        while not done:
            _, _, done, _ = env.step(sample_action)

        with pytest.raises(RuntimeError, match="already done"):
            env.step(sample_action)

    def test_step_reward_range(self, env, sample_action):
        env.reset("easy")
        _, reward, _, _ = env.step(sample_action)
        assert 0.0 <= reward.score <= 1.0

    def test_step_processes_all_easy(self, env, sample_action):
        env.reset("easy")
        count = 0
        done = False
        while not done:
            _, _, done, _ = env.step(sample_action)
            count += 1
        assert count == 10

    def test_step_processes_all_medium(self, env, sample_action):
        env.reset("medium")
        count = 0
        done = False
        while not done:
            _, _, done, _ = env.step(sample_action)
            count += 1
        assert count == 15

    def test_step_processes_all_hard(self, env, sample_action):
        env.reset("hard")
        count = 0
        done = False
        while not done:
            _, _, done, _ = env.step(sample_action)
            count += 1
        assert count == 20

    def test_step_info_contains_ground_truth(self, env, sample_action):
        env.reset("easy")
        _, _, _, info = env.step(sample_action)
        assert "ground_truth" in info
        assert "priority" in info["ground_truth"]
        assert "department" in info["ground_truth"]

    def test_step_done_returns_none_observation(self, env, sample_action):
        env.reset("easy")
        done = False
        result = None
        while not done:
            result = env.step(sample_action)
            _, _, done, _ = result
        next_obs = result[0]
        assert next_obs is None


class TestState:
    def test_state_before_reset(self, env):
        state = env.state()
        assert state.status == "Not Started"
        assert state.tickets_processed == 0
        assert state.total_tickets == 0

    def test_state_in_progress(self, env, sample_action):
        env.reset("easy")
        env.step(sample_action)
        state = env.state()
        assert state.status == "In Progress"
        assert state.tickets_processed == 2  # first ticket served on reset, second after step
        assert state.total_tickets == 10

    def test_state_completed(self, env, sample_action):
        env.reset("easy")
        done = False
        while not done:
            _, _, done, _ = env.step(sample_action)
        state = env.state()
        assert state.status == "Completed"
        assert state.tickets_processed == state.total_tickets

    def test_state_cumulative_score(self, env, sample_action):
        env.reset("easy")
        total = 0.0
        done = False
        while not done:
            _, reward, done, _ = env.step(sample_action)
            total += reward.score
        state = env.state()
        assert abs(state.cumulative_score - total) < 1e-9


class TestRewardValues:
    def test_perfect_easy_score(self, env):
        """First easy ticket is duplicate charge: P1, billing, no escalation."""
        env.reset("easy")
        action = Action(
            priority=Priority.P1,
            department=Department.billing,
            response="We can see the duplicate charge on your order and have initiated a refund.",
            escalate=False,
        )
        _, reward, _, _ = env.step(action)
        assert reward.score >= 0.8

    def test_wrong_priority_partial_credit(self, env):
        """Off-by-one priority should give partial credit."""
        env.reset("easy")
        action = Action(
            priority=Priority.P2,  # should be P1, off by 1
            department=Department.billing,
            response="We are processing your refund for the duplicate charge.",
            escalate=False,
        )
        _, reward, _, _ = env.step(action)
        assert reward.score >= 0.5

    def test_completely_wrong_gets_low_score(self, env):
        env.reset("easy")
        action = Action(
            priority=Priority.P0,
            department=Department.security,
            response="Unrelated response about something else entirely.",
            escalate=True,
        )
        _, reward, _, _ = env.step(action)
        assert reward.score < 0.5


class TestEdgeCases:
    def test_empty_response_string(self, env):
        env.reset("easy")
        action = Action(
            priority=Priority.P1,
            department=Department.billing,
            response="",
            escalate=False,
        )
        _, reward, _, _ = env.step(action)
        assert 0.0 <= reward.score <= 1.0

    def test_very_long_response(self, env):
        env.reset("easy")
        action = Action(
            priority=Priority.P1,
            department=Department.billing,
            response="word " * 1000,
            escalate=False,
        )
        _, reward, _, _ = env.step(action)
        assert 0.0 <= reward.score <= 1.0
