"""
Unit tests for Agent Roles (EMI Pattern).

Tests for: StepRoles, AgentRole, role parsing, and role validation.
Reference: Sprint 15 - E16-01
"""

import pytest
from textwrap import dedent

from services.process_engine.domain import (
    StepRoles,
    AgentRole,
    StepDefinition,
    ProcessDefinition,
)
from services.process_engine.services import ProcessValidator


# =============================================================================
# AgentRole Enum Tests
# =============================================================================


class TestAgentRole:
    """Tests for AgentRole enumeration."""

    def test_enum_values(self):
        """AgentRole has correct values."""
        assert AgentRole.EXECUTOR.value == "executor"
        assert AgentRole.MONITOR.value == "monitor"
        assert AgentRole.INFORMED.value == "informed"

    def test_enum_from_string(self):
        """AgentRole can be created from string."""
        assert AgentRole("executor") == AgentRole.EXECUTOR
        assert AgentRole("monitor") == AgentRole.MONITOR
        assert AgentRole("informed") == AgentRole.INFORMED


# =============================================================================
# StepRoles Dataclass Tests
# =============================================================================


class TestStepRoles:
    """Tests for StepRoles dataclass."""

    def test_create_with_executor_only(self):
        """StepRoles can be created with just an executor."""
        roles = StepRoles(executor="agent-1")

        assert roles.executor == "agent-1"
        assert roles.monitors == []
        assert roles.informed == []

    def test_create_with_all_roles(self):
        """StepRoles can be created with all role types."""
        roles = StepRoles(
            executor="executor-agent",
            monitors=["monitor-1", "monitor-2"],
            informed=["observer-1"],
        )

        assert roles.executor == "executor-agent"
        assert roles.monitors == ["monitor-1", "monitor-2"]
        assert roles.informed == ["observer-1"]

    def test_from_dict_minimal(self):
        """StepRoles.from_dict() with minimal data."""
        data = {"executor": "my-agent"}
        roles = StepRoles.from_dict(data)

        assert roles.executor == "my-agent"
        assert roles.monitors == []
        assert roles.informed == []

    def test_from_dict_full(self):
        """StepRoles.from_dict() with all fields."""
        data = {
            "executor": "exec-agent",
            "monitors": ["mon-1", "mon-2"],
            "informed": ["inf-1"],
        }
        roles = StepRoles.from_dict(data)

        assert roles.executor == "exec-agent"
        assert roles.monitors == ["mon-1", "mon-2"]
        assert roles.informed == ["inf-1"]

    def test_from_dict_empty_executor(self):
        """StepRoles.from_dict() with missing executor."""
        data = {"monitors": ["mon-1"]}
        roles = StepRoles.from_dict(data)

        assert roles.executor == ""
        assert roles.monitors == ["mon-1"]

    def test_to_dict_minimal(self):
        """StepRoles.to_dict() with only executor."""
        roles = StepRoles(executor="agent-1")
        result = roles.to_dict()

        assert result == {"executor": "agent-1"}
        assert "monitors" not in result
        assert "informed" not in result

    def test_to_dict_full(self):
        """StepRoles.to_dict() with all fields."""
        roles = StepRoles(
            executor="exec",
            monitors=["mon"],
            informed=["inf"],
        )
        result = roles.to_dict()

        assert result == {
            "executor": "exec",
            "monitors": ["mon"],
            "informed": ["inf"],
        }

    def test_all_agents(self):
        """StepRoles.all_agents() returns all referenced agents."""
        roles = StepRoles(
            executor="exec",
            monitors=["mon-1", "mon-2"],
            informed=["inf-1"],
        )

        agents = roles.all_agents()

        assert "exec" in agents
        assert "mon-1" in agents
        assert "mon-2" in agents
        assert "inf-1" in agents
        assert len(agents) == 4

    def test_all_agents_empty_executor(self):
        """StepRoles.all_agents() handles empty executor."""
        roles = StepRoles(executor="", monitors=["mon-1"])

        agents = roles.all_agents()

        assert "mon-1" in agents
        assert "" not in agents


# =============================================================================
# StepDefinition Role Parsing Tests
# =============================================================================


class TestStepDefinitionRoleParsing:
    """Tests for parsing roles in StepDefinition."""

    def test_step_without_roles(self):
        """Step definition without roles parses correctly."""
        data = {
            "id": "step-1",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Test message",
        }

        step = StepDefinition.from_dict(data)

        assert step.roles is None

    def test_step_with_roles(self):
        """Step definition with roles parses correctly."""
        data = {
            "id": "step-1",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Test message",
            "roles": {
                "executor": "exec-agent",
                "monitors": ["supervisor"],
                "informed": ["dashboard"],
            },
        }

        step = StepDefinition.from_dict(data)

        assert step.roles is not None
        assert step.roles.executor == "exec-agent"
        assert step.roles.monitors == ["supervisor"]
        assert step.roles.informed == ["dashboard"]

    def test_step_to_dict_includes_roles(self):
        """Step definition serialization includes roles."""
        data = {
            "id": "step-1",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Test message",
            "roles": {
                "executor": "exec-agent",
                "monitors": ["supervisor"],
            },
        }

        step = StepDefinition.from_dict(data)
        result = step.to_dict()

        assert "roles" in result
        assert result["roles"]["executor"] == "exec-agent"
        assert result["roles"]["monitors"] == ["supervisor"]

    def test_step_to_dict_no_roles(self):
        """Step definition serialization omits roles when None."""
        data = {
            "id": "step-1",
            "type": "agent_task",
            "agent": "test-agent",
            "message": "Test message",
        }

        step = StepDefinition.from_dict(data)
        result = step.to_dict()

        assert "roles" not in result


# =============================================================================
# ProcessDefinition Role Parsing Tests
# =============================================================================


class TestProcessDefinitionRoleParsing:
    """Tests for parsing roles in ProcessDefinition from YAML."""

    def test_parse_process_with_roles(self):
        """Process definition with roles parses correctly."""
        yaml_dict = {
            "name": "test-process",
            "version": 1,
            "steps": [
                {
                    "id": "analyze",
                    "type": "agent_task",
                    "agent": "analyst",
                    "message": "Analyze data",
                    "roles": {
                        "executor": "analyst",
                        "monitors": ["supervisor"],
                        "informed": ["dashboard"],
                    },
                },
                {
                    "id": "review",
                    "type": "agent_task",
                    "agent": "reviewer",
                    "message": "Review analysis",
                    "roles": {
                        "executor": "reviewer",
                        "informed": ["analyst"],
                    },
                },
            ],
        }

        definition = ProcessDefinition.from_yaml_dict(yaml_dict)

        assert len(definition.steps) == 2

        # First step
        assert definition.steps[0].roles is not None
        assert definition.steps[0].roles.executor == "analyst"
        assert definition.steps[0].roles.monitors == ["supervisor"]
        assert definition.steps[0].roles.informed == ["dashboard"]

        # Second step
        assert definition.steps[1].roles is not None
        assert definition.steps[1].roles.executor == "reviewer"
        assert definition.steps[1].roles.informed == ["analyst"]

    def test_parse_process_mixed_roles(self):
        """Process with some steps having roles and some not."""
        yaml_dict = {
            "name": "test-process",
            "version": 1,
            "steps": [
                {
                    "id": "step-with-roles",
                    "type": "agent_task",
                    "agent": "agent-1",
                    "message": "Do work",
                    "roles": {"executor": "agent-1"},
                },
                {
                    "id": "step-without-roles",
                    "type": "agent_task",
                    "agent": "agent-2",
                    "message": "More work",
                },
            ],
        }

        definition = ProcessDefinition.from_yaml_dict(yaml_dict)

        assert definition.steps[0].roles is not None
        assert definition.steps[1].roles is None


# =============================================================================
# Role Validation Tests
# =============================================================================


class TestRoleValidation:
    """Tests for role validation in ProcessValidator."""

    @pytest.fixture
    def validator(self):
        """Create a validator without agent checking."""
        return ProcessValidator()

    @pytest.fixture
    def validator_with_agent_check(self):
        """Create a validator with mock agent checker."""
        def check_agent(name: str) -> tuple[bool, bool]:
            known_agents = {"analyst", "supervisor", "dashboard", "reviewer"}
            if name in known_agents:
                return (True, True)
            return (False, False)

        return ProcessValidator(agent_checker=check_agent)

    def test_valid_roles_passes(self, validator):
        """Valid roles configuration passes validation."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: analyst
                  monitors:
                    - supervisor
                  informed:
                    - dashboard
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert result.is_valid

    def test_missing_executor_error(self, validator):
        """Roles without executor produces error."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  monitors:
                    - supervisor
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("executor" in e.message.lower() for e in result.errors)

    def test_executor_differs_from_agent_warning(self, validator):
        """Executor different from step agent produces warning."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: different-agent
        """).strip()

        result = validator.validate_yaml(yaml_content)

        # Should still be valid but have a warning
        assert result.is_valid
        assert any("differs from step agent" in w.message for w in result.warnings)

    def test_executor_in_monitors_warning(self, validator):
        """Executor also in monitors produces warning."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: analyst
                  monitors:
                    - analyst
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert result.is_valid
        assert any("redundant" in w.message.lower() for w in result.warnings)

    def test_executor_in_informed_warning(self, validator):
        """Executor also in informed produces warning."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: analyst
                  informed:
                    - analyst
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert result.is_valid
        assert any("redundant" in w.message.lower() for w in result.warnings)

    def test_invalid_monitors_type_error(self, validator):
        """Non-list monitors produces error."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: analyst
                  monitors: not-a-list
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("list" in e.message.lower() for e in result.errors)

    def test_invalid_informed_type_error(self, validator):
        """Non-list informed produces error."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: analyst
                  informed: not-a-list
        """).strip()

        result = validator.validate_yaml(yaml_content)

        assert not result.is_valid
        assert any("list" in e.message.lower() for e in result.errors)

    def test_role_agent_existence_warning(self, validator_with_agent_check):
        """Unknown agents in roles produce warnings."""
        yaml_content = dedent("""
            name: test-process
            version: 1
            steps:
              - id: analyze
                type: agent_task
                agent: analyst
                message: Analyze data
                roles:
                  executor: analyst
                  monitors:
                    - unknown-agent
        """).strip()

        result = validator_with_agent_check.validate_yaml(yaml_content)

        assert result.is_valid
        assert any("unknown-agent" in w.message for w in result.warnings)
        assert any("does not exist" in w.message for w in result.warnings)
