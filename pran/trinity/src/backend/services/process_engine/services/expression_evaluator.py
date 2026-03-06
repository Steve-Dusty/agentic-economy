"""
Expression Evaluator Service

Evaluates template expressions in process messages and configurations.
Uses Jinja2-style syntax for familiarity.

Reference: BACKLOG_MVP.md - E2-07
Reference: IT2 Section 6 (Expression Language choice)
"""

import re
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:
    """
    Context for expression evaluation.
    
    Provides access to all data sources that can be referenced
    in expressions.
    """
    input_data: dict[str, Any]
    step_outputs: dict[str, Any]
    execution_id: Optional[str] = None
    process_name: Optional[str] = None
    
    def get(self, path: str) -> Any:
        """
        Get value by dotted path.
        
        Examples:
            get("input.topic") -> input_data["topic"]
            get("steps.research.output") -> step_outputs["research"]
            get("steps.research.output.summary") -> step_outputs["research"]["summary"]
            get("execution.id") -> execution_id
        """
        parts = path.split(".")
        
        if not parts:
            return None
        
        root = parts[0]
        rest = parts[1:] if len(parts) > 1 else []
        
        if root == "input":
            value = self.input_data
            for key in rest:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        
        elif root == "steps":
            if not rest:
                return None
            
            step_id = rest[0]
            step_output = self.step_outputs.get(step_id)
            
            if step_output is None:
                return None
            
            # Navigate deeper if needed
            # steps.X.output -> step_outputs[X]
            # steps.X.output.Y -> step_outputs[X][Y]
            if len(rest) == 1:
                return step_output
            
            if rest[1] == "output":
                value = step_output
                for key in rest[2:]:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return None
                return value
            
            return None
        
        elif root == "execution":
            if rest and rest[0] == "id":
                return self.execution_id
            return None
        
        elif root == "process":
            if rest and rest[0] == "name":
                return self.process_name
            return None
        
        return None


class ExpressionEvaluator:
    """
    Evaluates template expressions in strings.
    
    Supports Jinja2-style syntax:
    - {{input.topic}} - Process input data
    - {{steps.research.output}} - Full step output
    - {{steps.research.output.summary}} - Nested field in step output
    - {{execution.id}} - Execution metadata
    
    Example:
    ```python
    evaluator = ExpressionEvaluator()
    context = EvaluationContext(
        input_data={"topic": "AI"},
        step_outputs={"research": {"summary": "AI is interesting"}},
    )
    
    result = evaluator.evaluate(
        "Write about {{input.topic}}: {{steps.research.output.summary}}",
        context,
    )
    # result = "Write about AI: AI is interesting"
    ```
    """
    
    # Pattern to match {{expression}} placeholders
    EXPRESSION_PATTERN = re.compile(r"\{\{([^}]+)\}\}")
    
    def evaluate(
        self,
        template: str,
        context: EvaluationContext,
        strict: bool = False,
    ) -> str:
        """
        Evaluate all expressions in a template string.
        
        Args:
            template: String containing {{expression}} placeholders
            context: Context for resolving expressions
            strict: If True, raise error for undefined expressions.
                   If False, leave undefined expressions as-is.
                   
        Returns:
            String with expressions replaced by their values
            
        Raises:
            ExpressionError: If strict=True and an expression cannot be resolved
        """
        def replace_expression(match):
            expression = match.group(1).strip()
            value = context.get(expression)
            
            if value is None:
                if strict:
                    raise ExpressionError(f"Undefined expression: {expression}")
                # Leave as-is
                return match.group(0)
            
            # Convert value to string
            return self._value_to_string(value)
        
        return self.EXPRESSION_PATTERN.sub(replace_expression, template)
    
    def extract_expressions(self, template: str) -> list[str]:
        """
        Extract all expressions from a template.
        
        Args:
            template: String containing {{expression}} placeholders
            
        Returns:
            List of expression strings (without braces)
        """
        return [match.group(1).strip() for match in self.EXPRESSION_PATTERN.finditer(template)]
    
    def validate_expressions(
        self,
        template: str,
        available_inputs: list[str] = None,
        available_steps: list[str] = None,
    ) -> list[str]:
        """
        Validate expressions in a template.
        
        Args:
            template: String containing expressions
            available_inputs: List of valid input field names
            available_steps: List of valid step IDs
            
        Returns:
            List of error messages (empty if all valid)
        """
        errors = []
        expressions = self.extract_expressions(template)
        
        for expr in expressions:
            parts = expr.split(".")
            if not parts:
                errors.append(f"Empty expression")
                continue
            
            root = parts[0]
            
            if root == "input":
                if available_inputs is not None and len(parts) > 1:
                    field = parts[1]
                    if field not in available_inputs:
                        errors.append(f"Unknown input field: {field}")
            
            elif root == "steps":
                if len(parts) < 2:
                    errors.append(f"Invalid step reference: {expr}")
                elif available_steps is not None:
                    step_id = parts[1]
                    if step_id not in available_steps:
                        errors.append(f"Unknown step: {step_id}")
            
            elif root == "execution":
                if len(parts) < 2 or parts[1] not in ["id"]:
                    errors.append(f"Invalid execution reference: {expr}")
            
            elif root == "process":
                if len(parts) < 2 or parts[1] not in ["name"]:
                    errors.append(f"Invalid process reference: {expr}")
            
            else:
                errors.append(f"Unknown expression root: {root}")
        
        return errors
    
    def _value_to_string(self, value: Any) -> str:
        """Convert a value to string for substitution."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            # For dict, try to get a 'response' or 'value' field
            # Otherwise, convert to JSON-like string
            if "response" in value:
                return str(value["response"])
            if "value" in value:
                return str(value["value"])
            import json
            return json.dumps(value)
        if isinstance(value, (list, tuple)):
            import json
            return json.dumps(value)
        return str(value)


class ExpressionError(Exception):
    """Error evaluating an expression."""
    pass


class ConditionEvaluator:
    """
    Evaluates boolean conditions for gateway routing.
    
    Supports:
    - Comparison operators: ==, !=, >, <, >=, <=
    - Boolean operators: and, or, not
    - Accessing step outputs: steps.analyze.output.score
    - Accessing inputs: input.priority
    
    Example:
    ```python
    evaluator = ConditionEvaluator()
    context = EvaluationContext(
        input_data={"priority": "high"},
        step_outputs={"analyze": {"score": 85}},
    )
    
    result = evaluator.evaluate("steps.analyze.output.score > 80", context)
    # result = True
    ```
    
    Reference: BACKLOG_CORE.md - E7-02 (Expression Evaluator)
    """
    
    # Supported comparison operators
    COMPARISON_OPS = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: float(a) > float(b) if _is_numeric(a, b) else str(a) > str(b),
        "<": lambda a, b: float(a) < float(b) if _is_numeric(a, b) else str(a) < str(b),
        ">=": lambda a, b: float(a) >= float(b) if _is_numeric(a, b) else str(a) >= str(b),
        "<=": lambda a, b: float(a) <= float(b) if _is_numeric(a, b) else str(a) <= str(b),
    }
    
    def evaluate(self, condition: str, context: EvaluationContext) -> bool:
        """
        Evaluate a boolean condition.
        
        Args:
            condition: Boolean expression string
            context: Context for resolving values
            
        Returns:
            Boolean result of the condition
            
        Raises:
            ExpressionError: If condition cannot be evaluated
        """
        if not condition or not condition.strip():
            return True  # Empty condition is always true
        
        condition = condition.strip()
        
        try:
            # Handle 'and' operator (split and evaluate both sides)
            if " and " in condition:
                parts = condition.split(" and ", 1)
                return self.evaluate(parts[0], context) and self.evaluate(parts[1], context)
            
            # Handle 'or' operator
            if " or " in condition:
                parts = condition.split(" or ", 1)
                return self.evaluate(parts[0], context) or self.evaluate(parts[1], context)
            
            # Handle 'not' operator
            if condition.startswith("not "):
                return not self.evaluate(condition[4:], context)
            
            # Handle comparison operators
            for op in ["==", "!=", ">=", "<=", ">", "<"]:
                if op in condition:
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        left = self._resolve_value(parts[0].strip(), context)
                        right = self._resolve_value(parts[1].strip(), context)
                        return self.COMPARISON_OPS[op](left, right)
            
            # If no operator, treat as truthy check
            value = self._resolve_value(condition, context)
            return bool(value)
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            raise ExpressionError(f"Failed to evaluate condition: {condition}") from e
    
    def _resolve_value(self, expr: str, context: EvaluationContext) -> Any:
        """
        Resolve an expression to its value.
        
        Handles:
        - String literals: 'value' or "value"
        - Numeric literals: 123, 45.67
        - Boolean literals: true, false
        - Path expressions: steps.analyze.output.score
        """
        expr = expr.strip()
        
        # String literal (single or double quotes)
        if (expr.startswith("'") and expr.endswith("'")) or \
           (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]
        
        # Boolean literals
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
        
        # Null literal
        if expr.lower() in ("null", "none"):
            return None
        
        # Numeric literal
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        
        # Path expression - use context to resolve
        value = context.get(expr)
        if value is None:
            logger.warning(f"Expression '{expr}' resolved to None")
        return value


def _is_numeric(a: Any, b: Any) -> bool:
    """Check if both values can be compared numerically."""
    try:
        float(a)
        float(b)
        return True
    except (ValueError, TypeError):
        return False
