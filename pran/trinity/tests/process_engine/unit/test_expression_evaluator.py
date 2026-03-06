"""
Unit tests for Expression Evaluator.

Tests for: E2-07 Expression Substitution in Messages
"""

import pytest

from services.process_engine.services import (
    ExpressionEvaluator,
    EvaluationContext,
    ExpressionError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def evaluator():
    """Create expression evaluator."""
    return ExpressionEvaluator()


@pytest.fixture
def context():
    """Create evaluation context with sample data."""
    return EvaluationContext(
        input_data={
            "topic": "Artificial Intelligence",
            "language": "English",
            "config": {
                "max_length": 1000,
                "format": "markdown",
            },
        },
        step_outputs={
            "research": {
                "response": "Research findings about AI",
                "summary": "AI is transforming industries",
                "sources": ["source1", "source2"],
            },
            "outline": "1. Introduction\n2. Body\n3. Conclusion",
        },
        execution_id="exec-123",
        process_name="content-pipeline",
    )


# =============================================================================
# EvaluationContext Tests
# =============================================================================


class TestEvaluationContext:
    """Tests for EvaluationContext path resolution."""

    def test_get_input_simple(self, context):
        """Get simple input value."""
        assert context.get("input.topic") == "Artificial Intelligence"

    def test_get_input_nested(self, context):
        """Get nested input value."""
        assert context.get("input.config.max_length") == 1000

    def test_get_input_missing(self, context):
        """Missing input returns None."""
        assert context.get("input.missing") is None

    def test_get_step_output(self, context):
        """Get step output."""
        result = context.get("steps.research.output")
        assert isinstance(result, dict)
        assert result["summary"] == "AI is transforming industries"

    def test_get_step_output_nested(self, context):
        """Get nested field in step output."""
        assert context.get("steps.research.output.summary") == "AI is transforming industries"

    def test_get_step_output_string(self, context):
        """Get string step output."""
        assert context.get("steps.outline.output") == "1. Introduction\n2. Body\n3. Conclusion"

    def test_get_step_missing(self, context):
        """Missing step returns None."""
        assert context.get("steps.nonexistent.output") is None

    def test_get_execution_id(self, context):
        """Get execution ID."""
        assert context.get("execution.id") == "exec-123"

    def test_get_process_name(self, context):
        """Get process name."""
        assert context.get("process.name") == "content-pipeline"


# =============================================================================
# Basic Evaluation Tests
# =============================================================================


class TestBasicEvaluation:
    """Tests for basic expression evaluation."""

    def test_no_expressions(self, evaluator, context):
        """String without expressions passes through."""
        result = evaluator.evaluate("Hello world", context)
        assert result == "Hello world"

    def test_single_expression(self, evaluator, context):
        """Single expression is replaced."""
        result = evaluator.evaluate("Topic: {{input.topic}}", context)
        assert result == "Topic: Artificial Intelligence"

    def test_multiple_expressions(self, evaluator, context):
        """Multiple expressions are replaced."""
        result = evaluator.evaluate(
            "Write about {{input.topic}} in {{input.language}}",
            context,
        )
        assert result == "Write about Artificial Intelligence in English"

    def test_expression_with_whitespace(self, evaluator, context):
        """Whitespace in expressions is handled."""
        result = evaluator.evaluate("Topic: {{ input.topic }}", context)
        assert result == "Topic: Artificial Intelligence"

    def test_undefined_expression_non_strict(self, evaluator, context):
        """Undefined expression is left as-is in non-strict mode."""
        result = evaluator.evaluate("Value: {{input.missing}}", context)
        assert result == "Value: {{input.missing}}"

    def test_undefined_expression_strict(self, evaluator, context):
        """Undefined expression raises in strict mode."""
        with pytest.raises(ExpressionError) as exc_info:
            evaluator.evaluate("Value: {{input.missing}}", context, strict=True)
        assert "Undefined expression" in str(exc_info.value)


# =============================================================================
# Step Output Tests
# =============================================================================


class TestStepOutputEvaluation:
    """Tests for step output expressions."""

    def test_step_output_full(self, evaluator, context):
        """Full step output is replaced."""
        result = evaluator.evaluate(
            "Previous: {{steps.outline.output}}",
            context,
        )
        assert "Introduction" in result

    def test_step_output_nested_field(self, evaluator, context):
        """Nested field in step output is replaced."""
        result = evaluator.evaluate(
            "Summary: {{steps.research.output.summary}}",
            context,
        )
        assert result == "Summary: AI is transforming industries"

    def test_step_output_dict_response(self, evaluator, context):
        """Dict output with 'response' field extracts response."""
        result = evaluator.evaluate(
            "Research: {{steps.research.output}}",
            context,
        )
        # Should use 'response' field from dict
        assert "Research findings about AI" in result


# =============================================================================
# Complex Expression Tests
# =============================================================================


class TestComplexExpressions:
    """Tests for complex expression scenarios."""

    def test_multiline_template(self, evaluator, context):
        """Multiline template works correctly."""
        template = """
Topic: {{input.topic}}
Language: {{input.language}}

Research Summary:
{{steps.research.output.summary}}
"""
        result = evaluator.evaluate(template, context)
        
        assert "Artificial Intelligence" in result
        assert "English" in result
        assert "AI is transforming industries" in result

    def test_expression_in_json_like_structure(self, evaluator, context):
        """Expressions in JSON-like structure."""
        template = '{"topic": "{{input.topic}}", "id": "{{execution.id}}"}'
        result = evaluator.evaluate(template, context)
        
        assert '"topic": "Artificial Intelligence"' in result
        assert '"id": "exec-123"' in result


# =============================================================================
# Extract/Validate Tests
# =============================================================================


class TestExpressionExtraction:
    """Tests for expression extraction."""

    def test_extract_expressions(self, evaluator):
        """Extracts all expressions from template."""
        template = "{{input.a}} and {{steps.b.output}} and {{execution.id}}"
        expressions = evaluator.extract_expressions(template)
        
        assert len(expressions) == 3
        assert "input.a" in expressions
        assert "steps.b.output" in expressions
        assert "execution.id" in expressions

    def test_extract_no_expressions(self, evaluator):
        """No expressions returns empty list."""
        expressions = evaluator.extract_expressions("Hello world")
        assert expressions == []


class TestExpressionValidation:
    """Tests for expression validation."""

    def test_validate_valid_expressions(self, evaluator):
        """Valid expressions pass validation."""
        template = "{{input.topic}} and {{steps.research.output}}"
        errors = evaluator.validate_expressions(
            template,
            available_inputs=["topic"],
            available_steps=["research"],
        )
        assert errors == []

    def test_validate_unknown_input(self, evaluator):
        """Unknown input field produces error."""
        errors = evaluator.validate_expressions(
            "{{input.unknown}}",
            available_inputs=["topic"],
        )
        assert len(errors) == 1
        assert "Unknown input field" in errors[0]

    def test_validate_unknown_step(self, evaluator):
        """Unknown step produces error."""
        errors = evaluator.validate_expressions(
            "{{steps.unknown.output}}",
            available_steps=["research"],
        )
        assert len(errors) == 1
        assert "Unknown step" in errors[0]

    def test_validate_invalid_root(self, evaluator):
        """Invalid expression root produces error."""
        errors = evaluator.validate_expressions("{{invalid.field}}")
        assert len(errors) == 1
        assert "Unknown expression root" in errors[0]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_template(self, evaluator, context):
        """Empty template returns empty string."""
        result = evaluator.evaluate("", context)
        assert result == ""

    def test_nested_braces(self, evaluator, context):
        """Handles expressions that look like nested braces."""
        # Only double braces should be treated as expressions
        result = evaluator.evaluate("{single} vs {{input.topic}}", context)
        assert "{single}" in result
        assert "Artificial Intelligence" in result

    def test_list_output(self, evaluator, context):
        """List values are converted to JSON."""
        result = evaluator.evaluate(
            "Sources: {{steps.research.output.sources}}",
            context,
        )
        assert "source1" in result
        assert "source2" in result

    def test_numeric_value(self, evaluator, context):
        """Numeric values are converted to string."""
        result = evaluator.evaluate(
            "Max length: {{input.config.max_length}}",
            context,
        )
        assert "1000" in result
