import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pytest
import yaml

from src.models import Observation, Action, Reward, State, Priority, Department, CustomerTier, Channel


TASKS_DIR = os.path.join(os.path.dirname(__file__), '..', 'tasks')
OPENENV_YAML = os.path.join(os.path.dirname(__file__), '..', 'openenv.yaml')


class TestOpenEnvYaml:
    def test_yaml_exists(self):
        assert os.path.exists(OPENENV_YAML)

    def test_yaml_parseable(self):
        with open(OPENENV_YAML) as f:
            config = yaml.safe_load(f)
        assert isinstance(config, dict)

    def test_yaml_required_fields(self):
        with open(OPENENV_YAML) as f:
            config = yaml.safe_load(f)
        assert "name" in config
        assert "version" in config
        assert "entrypoint" in config
        assert "tasks" in config

    def test_yaml_tasks_defined(self):
        with open(OPENENV_YAML) as f:
            config = yaml.safe_load(f)
        tasks = config["tasks"]
        assert "easy" in tasks
        assert "medium" in tasks
        assert "hard" in tasks

    def test_yaml_has_schemas(self):
        with open(OPENENV_YAML) as f:
            config = yaml.safe_load(f)
        assert "observation_space" in config
        assert "action_space" in config

    def test_yaml_action_space_fields(self):
        with open(OPENENV_YAML) as f:
            config = yaml.safe_load(f)
        action_props = config["action_space"]["properties"]
        assert "priority" in action_props
        assert "department" in action_props
        assert "response" in action_props
        assert "escalate" in action_props


class TestTaskFiles:
    @pytest.mark.parametrize("task_name,expected_count", [
        ("task_easy", 10),
        ("task_medium", 15),
        ("task_hard", 20),
    ])
    def test_task_file_exists_and_count(self, task_name, expected_count):
        path = os.path.join(TASKS_DIR, f"{task_name}.json")
        assert os.path.exists(path), f"{task_name}.json not found"
        with open(path, encoding="utf-8") as f:
            tickets = json.load(f)
        assert len(tickets) == expected_count

    @pytest.mark.parametrize("task_name", ["task_easy", "task_medium", "task_hard"])
    def test_task_ticket_structure(self, task_name):
        path = os.path.join(TASKS_DIR, f"{task_name}.json")
        with open(path, encoding="utf-8") as f:
            tickets = json.load(f)
        for ticket in tickets:
            assert "observation" in ticket
            assert "ground_truth" in ticket
            obs = ticket["observation"]
            gt = ticket["ground_truth"]
            assert "ticket_id" in obs
            assert "ticket_text" in obs
            assert "subject" in obs
            assert "customer_email" in obs
            assert "priority" in gt
            assert "department" in gt
            assert "response" in gt
            assert "escalate" in gt

    @pytest.mark.parametrize("task_name", ["task_easy", "task_medium", "task_hard"])
    def test_task_observations_parseable(self, task_name):
        path = os.path.join(TASKS_DIR, f"{task_name}.json")
        with open(path, encoding="utf-8") as f:
            tickets = json.load(f)
        for ticket in tickets:
            obs = Observation(**ticket["observation"])
            assert obs.ticket_id is not None

    @pytest.mark.parametrize("task_name", ["task_easy", "task_medium", "task_hard"])
    def test_ground_truth_valid_enums(self, task_name):
        path = os.path.join(TASKS_DIR, f"{task_name}.json")
        with open(path, encoding="utf-8") as f:
            tickets = json.load(f)
        valid_priorities = {p.value for p in Priority}
        valid_departments = {d.value for d in Department}
        for ticket in tickets:
            gt = ticket["ground_truth"]
            assert gt["priority"] in valid_priorities, f"Invalid priority: {gt['priority']}"
            assert gt["department"] in valid_departments, f"Invalid department: {gt['department']}"
            assert isinstance(gt["escalate"], bool)

    @pytest.mark.parametrize("task_name", ["task_easy", "task_medium", "task_hard"])
    def test_unique_ticket_ids(self, task_name):
        path = os.path.join(TASKS_DIR, f"{task_name}.json")
        with open(path, encoding="utf-8") as f:
            tickets = json.load(f)
        ids = [t["observation"]["ticket_id"] for t in tickets]
        assert len(ids) == len(set(ids)), "Duplicate ticket IDs found"


class TestModelValidation:
    def test_action_valid_enums(self):
        action = Action(priority="P0", department="billing", response="test", escalate=True)
        assert action.priority == Priority.P0
        assert action.department == Department.billing

    def test_action_invalid_priority(self):
        with pytest.raises(Exception):
            Action(priority="P5", department="billing", response="test", escalate=True)

    def test_action_invalid_department(self):
        with pytest.raises(Exception):
            Action(priority="P0", department="nonexistent", response="test", escalate=True)

    def test_observation_valid_enums(self):
        obs = Observation(
            ticket_id="TEST-1",
            ticket_text="Test",
            subject="Test",
            customer_name="Test",
            customer_email="test@example.com",
            customer_tier="standard",
            channel="email",
            timestamp="2026-03-28T00:00:00",
            conversation_history=[],
            attachments=[],
        )
        assert obs.customer_tier == CustomerTier.standard

    def test_state_model(self):
        state = State(
            status="In Progress",
            tickets_processed=5,
            total_tickets=10,
            cumulative_score=3.5,
        )
        assert state.total_tickets == 10

    def test_reward_model(self):
        reward = Reward(score=0.85, metrics={"test": 1})
        assert 0.0 <= reward.score <= 1.0
