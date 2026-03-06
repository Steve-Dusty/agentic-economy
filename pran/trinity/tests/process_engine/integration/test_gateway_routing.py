"""
Integration Tests for Gateway Routing

Tests conditional routing with exclusive and parallel gateways.

Reference: BACKLOG_RELIABILITY_IMPROVEMENTS.md - RI-06
"""

import pytest

from services.process_engine.domain import (
    ExecutionStatus,
    StepStatus,
    ProcessDefinition,
    StepDefinition,
)

from .conftest import (
    create_gateway_definition,
    assert_step_status,
)


# =============================================================================
# Test: Exclusive Gateway Takes First Match
# =============================================================================


class TestExclusiveGateway:
    """Tests for exclusive (XOR) gateway routing."""

    @pytest.mark.asyncio
    async def test_exclusive_gateway_takes_first_match(self, integration_engine):
        """Exclusive gateway should route to first matching condition."""
        ctx = integration_engine

        # Arrange: Create gateway with score-based routing
        definition = create_gateway_definition(
            name="xor-first-match-test",
            routes=[
                {"condition": "input.score >= 80", "target": "high-path"},
                {"condition": "input.score >= 50", "target": "medium-path"},
            ],
            default_route="default-path",
        )

        ctx.gateway.responses = {
            "analyzer": "Analysis complete",
            "high-handler": "High score handling",
            "medium-handler": "Medium score handling",
            "default-handler": "Default handling",
        }

        # Act: Execute with high score
        execution = await ctx.start(definition, input_data={
            "data": "test",
            "score": 90,
        })

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: High path was taken
        assert_step_status(execution, "high-path", StepStatus.COMPLETED)

        # Assert: High handler was called
        high_calls = ctx.gateway.get_calls_for_agent("high-handler")
        assert len(high_calls) == 1

    @pytest.mark.asyncio
    async def test_gateway_uses_default_route(self, integration_engine):
        """Gateway should use default route when no conditions match."""
        ctx = integration_engine

        # Arrange: Create gateway
        definition = create_gateway_definition(
            name="default-route-test",
            routes=[
                {"condition": "input.score >= 80", "target": "high-path"},
                {"condition": "input.score >= 50", "target": "medium-path"},
            ],
            default_route="default-path",
        )

        ctx.gateway.responses = {
            "analyzer": "Analysis complete",
            "default-handler": "Default handling",
        }

        # Act: Execute with low score (no conditions match)
        execution = await ctx.start(definition, input_data={
            "data": "test",
            "score": 30,
        })

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Default path was taken
        assert_step_status(execution, "default-path", StepStatus.COMPLETED)

        # Assert: Default handler was called
        default_calls = ctx.gateway.get_calls_for_agent("default-handler")
        assert len(default_calls) == 1

    @pytest.mark.asyncio
    async def test_gateway_routes_based_on_step_output(self, integration_engine):
        """Gateway should be able to route based on previous step's output."""
        ctx = integration_engine

        # Arrange: Create definition where gateway routes based on analyzer output
        definition = ProcessDefinition.create(name="output-routing-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-analyze",
                "name": "Analyze",
                "type": "agent_task",
                "agent": "analyzer",
                "message": "Analyze data",
            }),
            StepDefinition.from_dict({
                "id": "step-gateway",
                "name": "Route Decision",
                "type": "gateway",
                "gateway_type": "exclusive",
                "depends_on": ["step-analyze"],
                "routes": [
                    # Route based on whether analyzer found "urgent" in response
                    {"condition": "'urgent' in steps['step-analyze'].output", "target": "urgent-path"},
                    {"condition": "'normal' in steps['step-analyze'].output", "target": "normal-path"},
                ],
                "default_route": "normal-path",
            }),
            StepDefinition.from_dict({
                "id": "urgent-path",
                "name": "Urgent Handler",
                "type": "agent_task",
                "agent": "urgent-handler",
                "message": "Handle urgent case",
                "depends_on": ["step-gateway"],
            }),
            StepDefinition.from_dict({
                "id": "normal-path",
                "name": "Normal Handler",
                "type": "agent_task",
                "agent": "normal-handler",
                "message": "Handle normal case",
                "depends_on": ["step-gateway"],
            }),
        ]
        definition = definition.publish()

        # Configure analyzer to return "urgent"
        ctx.gateway.responses = {
            "analyzer": "This is urgent and needs immediate attention",
            "urgent-handler": "Urgent case handled",
        }

        # Act
        execution = await ctx.start(definition)

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Urgent path was taken (based on analyzer output)
        assert_step_status(execution, "urgent-path", StepStatus.COMPLETED)

        # Assert: Urgent handler was called
        urgent_calls = ctx.gateway.get_calls_for_agent("urgent-handler")
        assert len(urgent_calls) == 1


# =============================================================================
# Test: Gateway with Multiple Conditions
# =============================================================================


class TestGatewayConditions:
    """Tests for complex gateway conditions."""

    @pytest.mark.asyncio
    async def test_gateway_with_complex_condition(self, integration_engine):
        """Gateway should handle complex boolean conditions."""
        ctx = integration_engine

        # Arrange: Create gateway with complex conditions
        definition = ProcessDefinition.create(name="complex-condition-test")
        definition.steps = [
            StepDefinition.from_dict({
                "id": "step-start",
                "name": "Start",
                "type": "agent_task",
                "agent": "starter",
                "message": "Start",
            }),
            StepDefinition.from_dict({
                "id": "step-gateway",
                "name": "Route",
                "type": "gateway",
                "gateway_type": "exclusive",
                "depends_on": ["step-start"],
                "routes": [
                    # Complex condition: high priority AND urgent
                    {"condition": "input.priority == 'high' and input.urgent == True", "target": "critical-path"},
                    # Medium priority OR not urgent
                    {"condition": "input.priority == 'medium' or input.urgent == False", "target": "normal-path"},
                ],
                "default_route": "normal-path",
            }),
            StepDefinition.from_dict({
                "id": "critical-path",
                "name": "Critical",
                "type": "agent_task",
                "agent": "critical-handler",
                "message": "Critical",
                "depends_on": ["step-gateway"],
            }),
            StepDefinition.from_dict({
                "id": "normal-path",
                "name": "Normal",
                "type": "agent_task",
                "agent": "normal-handler",
                "message": "Normal",
                "depends_on": ["step-gateway"],
            }),
        ]
        definition = definition.publish()

        ctx.gateway.responses = {
            "starter": "Started",
            "critical-handler": "Critical handled",
        }

        # Act: Execute with high priority AND urgent
        execution = await ctx.start(definition, input_data={
            "priority": "high",
            "urgent": True,
        })

        # Assert: Execution completed
        assert execution.status == ExecutionStatus.COMPLETED

        # Assert: Critical path was taken
        assert_step_status(execution, "critical-path", StepStatus.COMPLETED)

        # Assert: Critical handler was called
        critical_calls = ctx.gateway.get_calls_for_agent("critical-handler")
        assert len(critical_calls) == 1
